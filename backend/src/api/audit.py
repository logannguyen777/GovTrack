"""backend/src/api/audit.py"""
import json

from fastapi import APIRouter, Depends, Query

from ..auth import TokenClaims, require_role
from ..database import pg_connection
from ..models.schemas import AuditEventResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    event_type: str | None = None,
    case_id: str | None = None,
    limit: int = Query(default=50, le=200),
    user: TokenClaims = Depends(require_role("admin", "leader", "security")),
):
    """List audit events with optional filters."""
    sql = "SELECT * FROM audit_events_flat WHERE 1=1"
    params: list = []
    idx = 1

    if event_type:
        sql += f" AND event_type = ${idx}"
        params.append(event_type)
        idx += 1
    if case_id:
        sql += f" AND case_id = ${idx}"
        params.append(case_id)
        idx += 1

    sql += f" ORDER BY created_at DESC LIMIT ${idx}"
    params.append(limit)

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)

    def _as_dict(v):
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"_raw": v}
        return {}

    return [
        AuditEventResponse(
            id=str(r["id"]), event_type=r["event_type"],
            actor_name=r["actor_name"], target_type=r["target_type"],
            target_id=r["target_id"], case_id=r["case_id"],
            details=_as_dict(r["details"]), created_at=r["created_at"],
        ) for r in rows
    ]
