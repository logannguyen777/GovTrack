"""backend/src/api/cases.py -- Case management endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import CurrentUser, TokenClaims, require_role
from ..database import oss_put_signed_url, pg_connection
from ..graph.deps import PermittedGDBDep
from ..models.enums import CaseType
from ..models.schemas import (
    BundleCreate,
    BundleResponse,
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    DocumentResponse,
    UploadURL,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


# Fallback SLA per TTHC (business-days) — matches authority regulation.
# Used when Case vertex has no sla_days_law property cached.
_TTHC_SLA_DAYS = {
    "1.004415": 15,  # Cấp phép xây dựng
    "1.000046": 10,  # Cấp GCN QSDĐ
    "1.001757": 5,   # Đăng ký doanh nghiệp
    "1.000122": 7,   # Phiếu LLTP
    "2.002154": 45,  # Giấy phép môi trường
}


def _compute_sla(
    tthc_code: str,
    submitted_at: str | None,
    status: str | None = None,
) -> tuple[int, int | None, bool]:
    """Return (sla_days, processing_days, is_overdue)."""
    sla_days = _TTHC_SLA_DAYS.get(tthc_code, 15)
    processing_days: int | None = None
    is_overdue = False
    if submitted_at:
        try:
            sub = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
            delta = (datetime.now(UTC) - sub).days
            processing_days = max(0, delta)
            is_overdue = (
                processing_days > sla_days
                and status not in ("published", "rejected", "approved")
            )
        except Exception:
            pass
    return sla_days, processing_days, is_overdue


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(body: CaseCreate, user: CurrentUser, gdb: PermittedGDBDep):
    """Create a new administrative case (ho so)."""
    case_id = str(uuid.uuid4())
    code = f"HS-{datetime.now(UTC).strftime('%Y%m%d')}-{case_id[:8].upper()}"
    now = datetime.now(UTC).isoformat()

    # Create Case vertex in GDB
    await gdb.execute(
        "g.addV('Case')"
        ".property('case_id', case_id).property('code', code)"
        ".property('status', 'submitted').property('submitted_at', now)"
        ".property('department_id', dept).property('tthc_code', tthc)"
        ".property('case_type', ctype)",
        {
            "case_id": case_id,
            "code": code,
            "now": now,
            "dept": body.department_id,
            "tthc": body.tthc_code,
            "ctype": body.case_type.value,
        },
    )

    # Create Applicant vertex + edge
    applicant_id = str(uuid.uuid4())
    await gdb.execute(
        "g.addV('Applicant')"
        ".property('applicant_id', aid).property('full_name', name)"
        ".property('id_number', id_num).property('phone', phone)"
        ".property('address', addr)",
        {
            "aid": applicant_id,
            "name": body.applicant_name,
            "id_num": body.applicant_id_number,
            "phone": body.applicant_phone,
            "addr": body.applicant_address,
        },
    )
    await gdb.execute(
        "g.V().has('Applicant', 'applicant_id', aid)"
        ".as('a').V().has('Case', 'case_id', cid)"
        ".addE('SUBMITTED_BY').to('a')",
        {"cid": case_id, "aid": applicant_id},
    )

    # Insert analytics row
    async with pg_connection() as conn:
        await conn.execute(
            "INSERT INTO analytics_cases (case_id, department_id, tthc_code, status) "
            "VALUES ($1, $2, $3, 'submitted')",
            case_id,
            body.department_id,
            body.tthc_code,
        )

    return CaseResponse(
        case_id=case_id,
        code=code,
        status="submitted",
        tthc_code=body.tthc_code,
        department_id=body.department_id,
        submitted_at=datetime.now(UTC),
        applicant_name=body.applicant_name,
        case_type=body.case_type,
    )


@router.get("", response_model=CaseListResponse)
async def list_cases(
    user: CurrentUser,
    gdb: PermittedGDBDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=1000),
    status: str | None = Query(default=None),
):
    """List cases with optional status filter and pagination."""
    bindings: dict = {}
    base = "g.V().hasLabel('Case')"
    if status:
        base += ".has('status', st)"
        bindings["st"] = status

    # Total count
    total_result = await gdb.execute(base + ".count()", bindings)
    total = total_result[0].get("value", 0) if total_result else 0

    # Page query — use named bindings instead of f-string interpolation
    skip = (page - 1) * page_size
    bindings["_range_skip"] = skip
    bindings["_range_limit"] = skip + page_size
    page_query = (
        base + ".order().by('submitted_at', desc).range(_range_skip, _range_limit).valueMap(true)"
    )
    rows = await gdb.execute(page_query, bindings) or []

    items = []
    for props in rows:
        cid = props.get("case_id", [""])[0] if isinstance(props.get("case_id"), list) else props.get("case_id", "")
        applicant = await gdb.execute(
            "g.V().has('Case', 'case_id', cid).out('SUBMITTED_BY').values('full_name')",
            {"cid": cid},
        )
        _tcode = props.get("tthc_code", [""])[0] if isinstance(props.get("tthc_code"), list) else props.get("tthc_code", "")
        _status = props.get("status", ["submitted"])[0] if isinstance(props.get("status"), list) else props.get("status", "submitted")
        _submitted = props.get("submitted_at", [datetime.now(UTC).isoformat()])[0] if isinstance(props.get("submitted_at"), list) else props.get("submitted_at", datetime.now(UTC).isoformat())
        _sla, _proc, _over = _compute_sla(_tcode, _submitted, _status)
        items.append(
            CaseResponse(
                case_id=cid,
                code=props.get("code", [""])[0] if isinstance(props.get("code"), list) else props.get("code", ""),
                status=_status,
                tthc_code=_tcode,
                department_id=props.get("department_id", [""])[0] if isinstance(props.get("department_id"), list) else props.get("department_id", ""),
                submitted_at=_submitted,
                applicant_name=applicant[0].get("value", "") if applicant and isinstance(applicant[0], dict) else (applicant[0] if applicant else ""),
                sla_days=_sla,
                processing_days=_proc,
                is_overdue=_over,
            )
        )

    return CaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, user: CurrentUser, gdb: PermittedGDBDep):
    """Get case details by ID.

    Looks up GDB first; if missing (e.g. benchmark seed rows exist only in
    analytics_cases), falls back to the analytics row so the UI doesn't 404.
    """
    result = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).valueMap(true)",
        {"cid": case_id},
    )
    if result:
        props = result[0]
        # Fetch Applicant vertex via PermittedGremlinClient so property_mask applies.
        applicant_props_raw = await gdb.execute(
            "g.V().has('Case', 'case_id', cid).out('SUBMITTED_BY').valueMap(true)",
            {"cid": case_id},
        )

        def _get(p: dict, key: str, default: str = "") -> str:
            v = p.get(key, default)
            return v[0] if isinstance(v, list) else (str(v) if v else default)

        app_name = ""
        app_id_number: str | None = None
        app_phone: str | None = None
        app_address: str | None = None
        if applicant_props_raw:
            ap = applicant_props_raw[0]
            app_name = _get(ap, "full_name")
            app_id_number = _get(ap, "id_number") or None
            app_phone = _get(ap, "phone") or None
            app_address = _get(ap, "address") or None

        raw_ctype = _get(props, "case_type", CaseType.CITIZEN_TTHC.value)
        try:
            ctype = CaseType(raw_ctype)
        except ValueError:
            ctype = CaseType.CITIZEN_TTHC

        _tcode = _get(props, "tthc_code")
        _status = _get(props, "status", "submitted")
        _submitted = _get(props, "submitted_at") or datetime.now(UTC).isoformat()
        _sla, _proc, _over = _compute_sla(_tcode, _submitted, _status)

        return CaseResponse(
            case_id=case_id,
            code=_get(props, "code"),
            status=_status,
            tthc_code=_tcode,
            department_id=_get(props, "department_id"),
            submitted_at=_submitted,
            applicant_name=app_name,
            case_type=ctype,
            applicant_id_number=app_id_number,
            applicant_phone=app_phone,
            applicant_address=app_address,
            sla_days=_sla,
            processing_days=_proc,
            is_overdue=_over,
        )

    # Fallback: analytics_cases row
    async with pg_connection() as conn:
        row = await conn.fetchrow(
            "SELECT case_id, tthc_code, department_id, status, submitted_at "
            "FROM analytics_cases WHERE case_id=$1",
            case_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(
        case_id=case_id,
        code=f"HS-{case_id[-10:].upper()}",
        status=row["status"] or "submitted",
        tthc_code=row["tthc_code"] or "",
        department_id=row["department_id"] or "",
        submitted_at=row["submitted_at"] or datetime.now(UTC),
        applicant_name="(benchmark case)",
    )


@router.get("/{case_id}/gaps")
async def get_case_gaps(
    case_id: str, user: CurrentUser, gdb: PermittedGDBDep
):
    """List compliance Gap vertices linked to a case."""
    try:
        rows = await gdb.execute(
            "g.V().has('Case', 'case_id', cid).out('HAS_GAP').valueMap(true)",
            {"cid": case_id},
        )
    except Exception:
        rows = []

    def _s(p: dict, k: str, d: str = "") -> str:
        v = p.get(k, d)
        return v[0] if isinstance(v, list) else (str(v) if v is not None else d)

    out: list[dict] = []
    for p in rows or []:
        out.append(
            {
                "id": _s(p, "gap_id") or _s(p, "id"),
                "description": _s(p, "description"),
                "severity": _s(p, "severity", "medium"),
                "fix_suggestion": _s(p, "fix_suggestion"),
                "requirement_ref": _s(p, "requirement_ref")
                or _s(p, "component_name"),
                "is_blocking": _s(p, "is_blocking", "false") == "true",
            }
        )
    return out


@router.get("/{case_id}/documents", response_model=list[DocumentResponse])
async def list_case_documents(case_id: str, user: CurrentUser, gdb: PermittedGDBDep):
    """List all documents attached to a case (via IN_BUNDLE/HAS_BUNDLE/HAS_DOCUMENT)."""
    try:
        rows = await gdb.execute(
            "g.V().has('Case', 'case_id', cid).out('HAS_DOCUMENT').valueMap(true)",
            {"cid": case_id},
        )
        if not rows:
            rows = await gdb.execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('HAS_BUNDLE').out('HAS_DOCUMENT').valueMap(true)",
                {"cid": case_id},
            )
    except Exception:
        rows = []

    def _s(p: dict, k: str, d: str = "") -> str:
        v = p.get(k, d)
        return v[0] if isinstance(v, list) else (str(v) if v is not None else d)

    out: list[DocumentResponse] = []
    for p in rows or []:
        try:
            doc_id = _s(p, "doc_id") or _s(p, "document_id") or _s(p, "id")
            out.append(
                DocumentResponse(
                    doc_id=doc_id,
                    filename=_s(p, "filename") or _s(p, "name") or "document",
                    content_type=_s(p, "content_type"),
                    page_count=int(_s(p, "page_count", "0") or 0) or None,
                    ocr_status=_s(p, "ocr_status", "pending"),
                    oss_key=_s(p, "oss_key") or _s(p, "oss_uri") or "",
                )
            )
        except Exception:
            continue
    return out


@router.post("/{case_id}/bundles", response_model=BundleResponse, status_code=201)
async def create_bundle(case_id: str, body: BundleCreate, user: CurrentUser, gdb: PermittedGDBDep):
    """Create a document bundle with pre-signed upload URLs.

    Also creates Document vertices in GDB and links them:
      Case -HAS_BUNDLE-> Bundle -CONTAINS-> Document
      Case -HAS_DOCUMENT-> Document
    so that downstream agents (Classifier, IntakeAgent) can discover files
    without waiting for a separate registration step.
    """
    bundle_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Create Bundle vertex
    await gdb.execute(
        "g.addV('Bundle').property('bundle_id', bid).property('case_id', cid)"
        ".property('uploaded_at', now).property('status', 'pending')",
        {"bid": bundle_id, "cid": case_id, "now": now},
    )
    await gdb.execute(
        "g.V().has('Bundle', 'bundle_id', bid)"
        ".as('b').V().has('Case', 'case_id', cid)"
        ".addE('HAS_BUNDLE').to('b')",
        {"cid": case_id, "bid": bundle_id},
    )

    # Create Document vertices + edges + generate signed upload URLs
    upload_urls = []
    for fi in body.files:
        doc_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
        oss_key = f"bundles/{case_id}/{bundle_id}/{fi.filename}"

        await gdb.execute(
            "g.addV('Document')"
            ".property('document_id', did).property('doc_id', did)"
            ".property('case_id', cid).property('bundle_id', bid)"
            ".property('filename', fn).property('content_type', ct)"
            ".property('size_bytes', sz).property('oss_key', ok)"
            ".property('ocr_status', 'pending').property('uploaded_at', now)",
            {
                "did": doc_id,
                "cid": case_id,
                "bid": bundle_id,
                "fn": fi.filename,
                "ct": fi.content_type or "application/octet-stream",
                "sz": int(fi.size_bytes or 0),
                "ok": oss_key,
                "now": now,
            },
        )
        # Bundle CONTAINS Document
        await gdb.execute(
            "g.V().has('Bundle', 'bundle_id', bid)"
            ".as('b').V().has('Document', 'document_id', did)"
            ".addE('CONTAINS').from('b')",
            {"bid": bundle_id, "did": doc_id},
        )
        # Case HAS_DOCUMENT Document (direct link for /cases/{id}/documents)
        await gdb.execute(
            "g.V().has('Case', 'case_id', cid)"
            ".as('c').V().has('Document', 'document_id', did)"
            ".addE('HAS_DOCUMENT').from('c')",
            {"cid": case_id, "did": doc_id},
        )

        signed = oss_put_signed_url(
            oss_key,
            content_type=fi.content_type or "application/octet-stream",
        )
        upload_urls.append(
            UploadURL(
                filename=fi.filename,
                signed_url=signed,
                oss_key=oss_key,
            )
        )

    return BundleResponse(
        bundle_id=bundle_id,
        case_id=case_id,
        upload_urls=upload_urls,
    )


class ConsultRequestBody(BaseModel):
    """Payload for creating a consult request from the compliance workspace."""

    target_department: str
    question: str
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    legal_refs: list[str] = []


@router.post("/{case_id}/consult-request", status_code=201)
async def create_consult_request(
    case_id: str,
    body: ConsultRequestBody,
    user: CurrentUser,
    gdb: PermittedGDBDep,
):
    """Create a ConsultRequest vertex + HAS_CONSULT_REQUEST + CONSULTED edges."""
    request_id = f"CR-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.now(UTC).isoformat()

    await gdb.execute(
        "g.addV('ConsultRequest')"
        ".property('request_id', rid).property('case_id', cid)"
        ".property('target_department', dept).property('question', q)"
        ".property('priority', prio).property('status', 'pending')"
        ".property('created_at', now).property('created_by', actor)",
        {
            "rid": request_id,
            "cid": case_id,
            "dept": body.target_department,
            "q": body.question,
            "prio": body.priority,
            "now": now,
            "actor": user.username,
        },
    )
    await gdb.execute(
        "g.V().has('Case', 'case_id', cid)"
        ".as('c').V().has('ConsultRequest', 'request_id', rid)"
        ".addE('HAS_CONSULT_REQUEST').from('c')",
        {"cid": case_id, "rid": request_id},
    )
    try:
        await gdb.execute(
            "g.V().has('Case', 'case_id', cid)"
            ".as('c').V().has('Organization', 'org_id', dept)"
            ".addE('CONSULTED').from('c')",
            {"cid": case_id, "dept": body.target_department},
        )
    except Exception:
        pass  # Organization may not exist; non-fatal

    return {
        "request_id": request_id,
        "case_id": case_id,
        "status": "pending",
        "target_department": body.target_department,
        "created_at": now,
    }


@router.post("/{case_id}/finalize", status_code=200)
async def finalize_case(
    case_id: str,
    user: CurrentUser,
    gdb: PermittedGDBDep,
    body: dict | None = None,
):
    """Finalize case.

    Without ``decision``: mark ``classifying`` to queue for agent processing.
    With ``decision`` (approve/reject/supplement): apply leader decision —
    update both GDB Case vertex and analytics_cases row.
    """
    decision_map = {
        "approve": "approved",
        "reject": "rejected",
        "supplement": "pending_supplement",
    }
    decision = (body or {}).get("decision") if body else None
    target_status = decision_map.get(decision, "classifying")

    await gdb.execute(
        "g.V().has('Case', 'case_id', cid).property('status', s)",
        {"cid": case_id, "s": target_status},
    )
    try:
        async with pg_connection() as conn:
            if decision in decision_map:
                await conn.execute(
                    "UPDATE analytics_cases SET status=$1, "
                    "completed_at = COALESCE(completed_at, NOW()) "
                    "WHERE case_id=$2",
                    target_status,
                    case_id,
                )
            else:
                await conn.execute(
                    "UPDATE analytics_cases SET status=$1 WHERE case_id=$2",
                    target_status,
                    case_id,
                )
    except Exception as exc:
        import logging as _logging

        _logging.getLogger("govflow.cases").warning(f"analytics update failed for {case_id}: {exc}")
    return {
        "case_id": case_id,
        "status": target_status,
        "decision": decision,
        "actor": user.username,
    }


# ---------------------------------------------------------------------------
# Batch finalize
# ---------------------------------------------------------------------------


class BatchFinalizeBody(BaseModel):
    case_ids: list[str]
    decision: Literal["approve", "reject", "request_supplement"]
    notes: str | None = None


class BatchFinalizeResult(BaseModel):
    # NOTE: field is "succeeded" (not "success") to match the frontend
    # BatchFinalizeResponse type in use-cases.ts.
    succeeded: list[str]
    failed: list[dict]


@router.post("/batch-finalize", response_model=BatchFinalizeResult)
async def batch_finalize(
    body: BatchFinalizeBody,
    gdb: PermittedGDBDep,
    user: TokenClaims = Depends(require_role("admin", "leader")),
):
    """Bulk approve/reject/request_supplement for multiple cases at once.

    Gated to admin and leader roles. Each case is finalized independently;
    single-case failures do not abort the rest.
    """
    # Map public decision names to internal status values (same as finalize_case)
    decision_map = {
        "approve": "approved",
        "reject": "rejected",
        "request_supplement": "pending_supplement",
    }
    target_status = decision_map[body.decision]

    succeeded: list[str] = []
    failed: list[dict] = []

    for case_id in body.case_ids:
        try:
            await gdb.execute(
                "g.V().has('Case', 'case_id', cid).property('status', s)",
                {"cid": case_id, "s": target_status},
            )
            async with pg_connection() as conn:
                await conn.execute(
                    "UPDATE analytics_cases SET status=$1, "
                    "completed_at = COALESCE(completed_at, NOW()) "
                    "WHERE case_id=$2",
                    target_status,
                    case_id,
                )
            succeeded.append(case_id)
        except Exception as exc:
            failed.append({"case_id": case_id, "error": str(exc)})

    return BatchFinalizeResult(succeeded=succeeded, failed=failed)
