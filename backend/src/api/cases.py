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
    UploadURL,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


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
        items.append(
            CaseResponse(
                case_id=cid,
                code=props.get("code", [""])[0] if isinstance(props.get("code"), list) else props.get("code", ""),
                status=props.get("status", ["submitted"])[0] if isinstance(props.get("status"), list) else props.get("status", "submitted"),
                tthc_code=props.get("tthc_code", [""])[0] if isinstance(props.get("tthc_code"), list) else props.get("tthc_code", ""),
                department_id=props.get("department_id", [""])[0] if isinstance(props.get("department_id"), list) else props.get("department_id", ""),
                submitted_at=props.get("submitted_at", [datetime.now(UTC).isoformat()])[0] if isinstance(props.get("submitted_at"), list) else props.get("submitted_at", datetime.now(UTC).isoformat()),
                applicant_name=applicant[0].get("value", "") if applicant and isinstance(applicant[0], dict) else (applicant[0] if applicant else ""),
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

        return CaseResponse(
            case_id=case_id,
            code=_get(props, "code"),
            status=_get(props, "status", "submitted"),
            tthc_code=_get(props, "tthc_code"),
            department_id=_get(props, "department_id"),
            submitted_at=_get(props, "submitted_at") or datetime.now(UTC).isoformat(),
            applicant_name=app_name,
            case_type=ctype,
            applicant_id_number=app_id_number,
            applicant_phone=app_phone,
            applicant_address=app_address,
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


@router.post("/{case_id}/bundles", response_model=BundleResponse, status_code=201)
async def create_bundle(case_id: str, body: BundleCreate, user: CurrentUser, gdb: PermittedGDBDep):
    """Create a document bundle with pre-signed upload URLs."""
    bundle_id = str(uuid.uuid4())

    # Create Bundle vertex in GDB
    await gdb.execute(
        "g.addV('Bundle').property('bundle_id', bid).property('case_id', cid)"
        ".property('uploaded_at', now).property('status', 'pending')",
        {"bid": bundle_id, "cid": case_id, "now": datetime.now(UTC).isoformat()},
    )
    await gdb.execute(
        "g.V().has('Bundle', 'bundle_id', bid)"
        ".as('b').V().has('Case', 'case_id', cid)"
        ".addE('HAS_BUNDLE').to('b')",
        {"cid": case_id, "bid": bundle_id},
    )

    # Generate signed upload URLs
    upload_urls = []
    for fi in body.files:
        oss_key = f"bundles/{case_id}/{bundle_id}/{fi.filename}"
        signed = oss_put_signed_url(oss_key)
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
