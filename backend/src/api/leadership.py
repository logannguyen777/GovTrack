"""backend/src/api/leadership.py"""
import logging

from fastapi import APIRouter, Depends

from ..auth import TokenClaims, require_role
from ..database import pg_connection
from ..models.schemas import AgentPerformanceItem, DashboardResponse, InboxItem

logger = logging.getLogger("govflow.leadership")

router = APIRouter(prefix="/leadership", tags=["Leadership"])

STATUS_VI: dict[str, str] = {
    "submitted": "Đã nộp",
    "classifying": "Đang phân loại",
    "extracting": "Đang trích xuất",
    "gap_checking": "Kiểm tra bổ sung",
    "pending_supplement": "Chờ bổ sung",
    "legal_review": "Xem xét pháp lý",
    "drafting": "Soạn thảo",
    "leader_review": "Chờ lãnh đạo duyệt",
    "consultation": "Đang xin ý kiến",
    "approved": "Đã phê duyệt",
    "rejected": "Bị từ chối",
    "published": "Đã ban hành",
    "failed": "Lỗi pipeline",
}


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(user: TokenClaims = Depends(require_role("admin", "leader", "security"))):
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
async def get_inbox(user: TokenClaims = Depends(require_role("admin", "leader", "security"))):
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
            case_id=r["case_id"],
            code=r["case_id"],
            title=f"Hồ sơ {r['case_id']} · {STATUS_VI.get(r['status'], r['status'])}",
            action_required=r["status"], priority="high",
            created_at=r["submitted_at"],
        ) for r in rows
    ]


@router.get("/weekly-brief")
async def weekly_brief(
    user: TokenClaims = Depends(require_role("admin", "leader", "security")),
):
    """AI-generated weekly summary for leadership, covering the last 7 days.

    Aggregates analytics_cases metrics then calls Qwen3 for a ~100-word
    Vietnamese brief. Falls back to a template string if Qwen is unavailable.
    """
    async with pg_connection() as conn:
        new_cases = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases "
            "WHERE submitted_at >= NOW() - INTERVAL '7 days'"
        )
        prev_new = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases "
            "WHERE submitted_at >= NOW() - INTERVAL '14 days' "
            "AND submitted_at < NOW() - INTERVAL '7 days'"
        )
        completed = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases "
            "WHERE completed_at >= NOW() - INTERVAL '7 days'"
        )
        overdue = await conn.fetchval(
            "SELECT count(*) FROM analytics_cases WHERE is_overdue = TRUE"
        )
        avg_days_row = await conn.fetchval(
            "SELECT COALESCE(avg(processing_days), 0) FROM analytics_cases "
            "WHERE processing_days IS NOT NULL "
            "AND submitted_at >= NOW() - INTERVAL '7 days'"
        )
        # Top 3 stuck TTHC codes (most overdue)
        stuck_rows = await conn.fetch(
            "SELECT tthc_code, count(*) AS cnt "
            "FROM analytics_cases "
            "WHERE is_overdue = TRUE AND tthc_code IS NOT NULL "
            "GROUP BY tthc_code ORDER BY cnt DESC LIMIT 3"
        )

    new_cases = int(new_cases or 0)
    prev_new = int(prev_new or 0)
    completed = int(completed or 0)
    overdue = int(overdue or 0)
    avg_days = float(avg_days_row or 0)
    stuck = [{"tthc_code": r["tthc_code"], "count": int(r["cnt"])} for r in stuck_rows]

    wow_pct: str
    if prev_new > 0:
        delta = round((new_cases - prev_new) / prev_new * 100)
        sign = "+" if delta >= 0 else ""
        wow_pct = f"{sign}{delta}% WoW"
    else:
        wow_pct = "N/A WoW"

    stuck_summary = ", ".join(
        f"TTHC {s['tthc_code']} ({s['count']} hồ sơ trễ)" for s in stuck
    ) if stuck else "không có hồ sơ trễ đáng chú ý"

    stats = {
        "new_cases": new_cases,
        "prev_week_new_cases": prev_new,
        "wow_pct": wow_pct,
        "completed": completed,
        "overdue": overdue,
        "avg_processing_days": round(avg_days, 1),
        "top_stuck_tthc": stuck,
    }

    # --- Attempt Qwen3 brief generation ---
    brief: str
    try:
        from ..agents.qwen_client import QwenClient
        qwen = QwenClient()
        prompt = (
            "Bạn là trợ lý hành chính công. Hãy viết một đoạn tóm tắt tuần "
            "~100 từ bằng tiếng Việt cho lãnh đạo dựa trên số liệu sau:\n"
            f"- Hồ sơ mới 7 ngày qua: {new_cases} ({wow_pct})\n"
            f"- Đã hoàn thành: {completed}\n"
            f"- Đang vượt SLA: {overdue}\n"
            f"- Thời gian xử lý TB: {avg_days:.1f} ngày\n"
            f"- Điểm chú ý: {stuck_summary}\n"
            "Viết ngắn gọn, súc tích, dùng ngôn ngữ chuyên nghiệp."
        )
        completion = await qwen.chat(
            messages=[{"role": "user", "content": prompt}],
            model="reasoning",
            max_tokens=300,
            temperature=0.5,
        )
        brief = completion.choices[0].message.content or ""
    except Exception as exc:
        logger.warning(f"weekly_brief: Qwen unavailable, using template: {exc}")
        brief = (
            f"Tuần qua: {new_cases} hồ sơ mới ({wow_pct}), "
            f"{completed} đã hoàn thành, {overdue} vượt SLA. "
            f"Thời gian xử lý trung bình: {avg_days:.1f} ngày. "
            f"Điểm chú ý: {stuck_summary}."
        )

    return {"brief": brief, "stats": stats}
