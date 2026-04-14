"""backend/src/api/public.py -- No authentication required."""
from fastapi import APIRouter, HTTPException

from ..database import gremlin_submit, pg_connection
from ..models.schemas import PublicCaseStatus, PublicTTHCItem, PublicStatsResponse

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/cases/{code}", response_model=PublicCaseStatus)
async def public_case_status(code: str):
    """Public case status lookup by case code (no auth)."""
    result = gremlin_submit(
        "g.V().has('Case', 'code', code).valueMap(true)", {"code": code},
    )
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")
    props = result[0]
    return PublicCaseStatus(
        code=code,
        status=props.get("status", ["unknown"])[0],
        submitted_at=props.get("submitted_at", [""])[0],
        current_step=props.get("status", [""])[0],
        estimated_completion=None,
    )


@router.get("/tthc", response_model=list[PublicTTHCItem])
async def list_public_tthc():
    """List all public TTHC procedures."""
    results = gremlin_submit("g.V().hasLabel('TTHCSpec').valueMap(true).limit(100)")
    items = []
    for r in results:
        # Property may be 'code' or 'tthc_code' depending on how data was ingested
        code = r.get("tthc_code", r.get("code", [""]))[0]
        comps = gremlin_submit(
            "g.V().hasLabel('TTHCSpec').has('code', c).out('REQUIRES').values('name')",
            {"c": code},
        )
        items.append(PublicTTHCItem(
            tthc_code=code, name=r.get("name", [""])[0],
            department=r.get("authority_name", r.get("department", [""]))[0],
            sla_days=r.get("sla_days_law", r.get("sla_days", [15]))[0],
            fee=str(r.get("fee_vnd", r.get("fee", [0]))[0]),
            required_components=comps,
        ))
    return items


@router.get("/stats", response_model=PublicStatsResponse)
async def public_stats():
    """Public statistics."""
    async with pg_connection() as conn:
        total = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases WHERE status IN ('approved','published')"
        )
        avg = await conn.fetchval(
            "SELECT COALESCE(avg(processing_days),0) FROM analytics_cases WHERE processing_days IS NOT NULL"
        )
        month = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases WHERE submitted_at >= date_trunc('month', CURRENT_DATE)"
        )
    return PublicStatsResponse(
        total_cases_processed=total, avg_processing_days=float(avg), cases_this_month=month,
    )
