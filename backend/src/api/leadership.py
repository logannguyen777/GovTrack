"""backend/src/api/leadership.py"""
from fastapi import APIRouter, Depends

from ..auth import CurrentUser, TokenClaims, require_role
from ..database import pg_connection
from ..models.schemas import DashboardResponse, AgentPerformanceItem, InboxItem

router = APIRouter(prefix="/leadership", tags=["Leadership"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(user: TokenClaims = Depends(require_role("admin", "leader"))):
    """Leadership dashboard with KPIs."""
    async with pg_connection() as conn:
        total = await conn.fetchval("SELECT count(*) FROM analytics_cases")
        pending = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases WHERE status NOT IN ('approved','rejected','published')"
        )
        overdue = await conn.fetchval("SELECT count(*) FROM analytics_cases WHERE is_overdue = TRUE")
        completed_today = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases WHERE completed_at::date = CURRENT_DATE"
        )
        avg_days = await conn.fetchval(
            "SELECT COALESCE(avg(processing_days), 0) FROM analytics_cases WHERE processing_days IS NOT NULL"
        )

        by_status = await conn.fetch(
            "SELECT status, count(*) as cnt FROM analytics_cases GROUP BY status"
        )
        by_dept = await conn.fetch(
            "SELECT department_id, count(*) as cnt FROM analytics_cases GROUP BY department_id"
        )

        agent_perf = await conn.fetch("""
            SELECT agent_name, count(*) as runs,
                   avg(duration_ms)::int as avg_dur,
                   avg(input_tokens + output_tokens)::int as avg_tok
            FROM analytics_agents WHERE status = 'completed'
            GROUP BY agent_name
        """)

    return DashboardResponse(
        total_cases=total, pending_cases=pending, overdue_cases=overdue,
        completed_today=completed_today, avg_processing_days=float(avg_days),
        cases_by_status={r["status"]: r["cnt"] for r in by_status},
        cases_by_department={r["department_id"]: r["cnt"] for r in by_dept},
        agent_performance=[
            AgentPerformanceItem(
                agent_name=r["agent_name"], total_runs=r["runs"],
                avg_duration_ms=float(r["avg_dur"]), avg_tokens=r["avg_tok"],
            ) for r in agent_perf
        ],
    )


@router.get("/inbox", response_model=list[InboxItem])
async def get_inbox(user: TokenClaims = Depends(require_role("admin", "leader"))):
    """Items requiring leader attention."""
    async with pg_connection() as conn:
        rows = await conn.fetch("""
            SELECT case_id, status, department_id, submitted_at
            FROM analytics_cases
            WHERE status IN ('leader_review', 'consultation')
            ORDER BY submitted_at ASC
            LIMIT 20
        """)
    return [
        InboxItem(
            case_id=r["case_id"], code=f"HS-{r['case_id'][:8]}",
            title=f"Case {r['case_id'][:8]} - {r['status']}",
            action_required=r["status"], priority="high",
            created_at=r["submitted_at"],
        ) for r in rows
    ]
