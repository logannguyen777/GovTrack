"""backend/src/api/cases.py -- Case management endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..auth import CurrentUser
from ..database import gremlin_submit, pg_connection, oss_put_signed_url
from ..models.schemas import (
    CaseCreate, CaseResponse, CaseListResponse,
    BundleCreate, BundleResponse, UploadURL,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(body: CaseCreate, user: CurrentUser):
    """Create a new administrative case (ho so)."""
    case_id = str(uuid.uuid4())
    code = f"HS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{case_id[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    # Create Case vertex in GDB
    gremlin_submit(
        "g.addV('Case')"
        ".property('case_id', case_id).property('code', code)"
        ".property('status', 'submitted').property('submitted_at', now)"
        ".property('department_id', dept).property('tthc_code', tthc)",
        {"case_id": case_id, "code": code, "now": now,
         "dept": body.department_id, "tthc": body.tthc_code},
    )

    # Create Applicant vertex + edge
    applicant_id = str(uuid.uuid4())
    gremlin_submit(
        "g.addV('Applicant')"
        ".property('applicant_id', aid).property('full_name', name)"
        ".property('id_number', id_num).property('phone', phone)"
        ".property('address', addr)",
        {"aid": applicant_id, "name": body.applicant_name,
         "id_num": body.applicant_id_number, "phone": body.applicant_phone,
         "addr": body.applicant_address},
    )
    gremlin_submit(
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
            case_id, body.department_id, body.tthc_code,
        )

    return CaseResponse(
        case_id=case_id, code=code, status="submitted",
        tthc_code=body.tthc_code, department_id=body.department_id,
        submitted_at=datetime.now(timezone.utc), applicant_name=body.applicant_name,
    )


@router.get("", response_model=CaseListResponse)
async def list_cases(
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
):
    """List cases with optional status filter and pagination."""
    bindings: dict = {}
    base = "g.V().hasLabel('Case')"
    if status:
        base += ".has('status', st)"
        bindings["st"] = status

    # Total count
    total_result = gremlin_submit(base + ".count()", bindings)
    total = total_result[0] if total_result else 0

    # Page query
    skip = (page - 1) * page_size
    page_query = base + f".order().by('submitted_at', desc).range({skip}, {skip + page_size}).valueMap(true)"
    rows = gremlin_submit(page_query, bindings) or []

    items = []
    for props in rows:
        cid = props.get("case_id", [""])[0]
        applicant = gremlin_submit(
            "g.V().has('Case', 'case_id', cid).out('SUBMITTED_BY').values('full_name')",
            {"cid": cid},
        )
        items.append(CaseResponse(
            case_id=cid,
            code=props.get("code", [""])[0],
            status=props.get("status", ["submitted"])[0],
            tthc_code=props.get("tthc_code", [""])[0],
            department_id=props.get("department_id", [""])[0],
            submitted_at=props.get("submitted_at", [datetime.now(timezone.utc).isoformat()])[0],
            applicant_name=applicant[0] if applicant else "",
        ))

    return CaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, user: CurrentUser):
    """Get case details by ID."""
    result = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).valueMap(true)",
        {"cid": case_id},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")

    props = result[0]
    # Extract applicant name
    applicant = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).out('SUBMITTED_BY').values('full_name')",
        {"cid": case_id},
    )

    return CaseResponse(
        case_id=case_id,
        code=props.get("code", [""])[0],
        status=props.get("status", ["submitted"])[0],
        tthc_code=props.get("tthc_code", [""])[0],
        department_id=props.get("department_id", [""])[0],
        submitted_at=props.get("submitted_at", [datetime.now(timezone.utc).isoformat()])[0],
        applicant_name=applicant[0] if applicant else "",
    )


@router.post("/{case_id}/bundles", response_model=BundleResponse, status_code=201)
async def create_bundle(case_id: str, body: BundleCreate, user: CurrentUser):
    """Create a document bundle with pre-signed upload URLs."""
    bundle_id = str(uuid.uuid4())

    # Create Bundle vertex in GDB
    gremlin_submit(
        "g.addV('Bundle').property('bundle_id', bid).property('case_id', cid)"
        ".property('uploaded_at', now).property('status', 'pending')",
        {"bid": bundle_id, "cid": case_id,
         "now": datetime.now(timezone.utc).isoformat()},
    )
    gremlin_submit(
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
        upload_urls.append(UploadURL(
            filename=fi.filename, signed_url=signed, oss_key=oss_key,
        ))

    return BundleResponse(
        bundle_id=bundle_id, case_id=case_id, upload_urls=upload_urls,
    )


@router.post("/{case_id}/finalize", status_code=200)
async def finalize_case(case_id: str, user: CurrentUser):
    """Mark a case as ready for agent processing."""
    gremlin_submit(
        "g.V().has('Case', 'case_id', cid).property('status', 'classifying')",
        {"cid": case_id},
    )
    return {"case_id": case_id, "status": "classifying", "message": "Case queued for processing"}
