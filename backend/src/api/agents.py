"""backend/src/api/agents.py"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import fastapi
from fastapi import APIRouter, BackgroundTasks

from ..auth import CurrentUser
from ..database import pg_connection
from ..graph.deps import PermittedGDBDep
from ..models.schemas import (
    AgentRunRequest,
    AgentStepResponse,
    AgentTraceResponse,
    ConsultOpinionSubmit,
    ConsultRequestResponse,
    ConsultSubmitRequest,
)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/trace/{case_id}", response_model=AgentTraceResponse)
async def get_agent_trace(case_id: str, user: CurrentUser, gdb: PermittedGDBDep):
    """Get the full agent processing trace for a case."""
    steps = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).out('PROCESSED_BY')"
        ".hasLabel('AgentStep').valueMap(true).order().by('step_id')",
        {"cid": case_id},
    )
    step_list = []
    total_tokens = 0
    total_ms = 0
    for s in steps:
        in_tok = (
            s.get("input_tokens", [0])[0]
            if isinstance(s.get("input_tokens"), list)
            else s.get("input_tokens", 0)
        )
        out_tok = (
            s.get("output_tokens", [0])[0]
            if isinstance(s.get("output_tokens"), list)
            else s.get("output_tokens", 0)
        )
        dur = (
            s.get("duration_ms", [0])[0]
            if isinstance(s.get("duration_ms"), list)
            else s.get("duration_ms", 0)
        )
        def _safe_int(v: object) -> int:
            try:
                return int(v) if v not in (None, "") else 0
            except (TypeError, ValueError):
                return 0

        total_tokens += _safe_int(in_tok) + _safe_int(out_tok)
        total_ms += _safe_int(dur)
        step_list.append(
            AgentStepResponse(
                step_id=s.get("step_id", [""])[0]
                if isinstance(s.get("step_id"), list)
                else s.get("step_id", ""),
                agent_name=s.get("agent_name", [""])[0]
                if isinstance(s.get("agent_name"), list)
                else s.get("agent_name", ""),
                action=s.get("action", [""])[0]
                if isinstance(s.get("action"), list)
                else s.get("action", ""),
                status=s.get("status", ["completed"])[0]
                if isinstance(s.get("status"), list)
                else s.get("status", "completed"),
                input_tokens=_safe_int(in_tok),
                output_tokens=_safe_int(out_tok),
                duration_ms=_safe_int(dur),
            )
        )

    case_status_result = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).values('status')",
        {"cid": case_id},
    )
    case_status = ""
    if case_status_result:
        first = case_status_result[0]
        case_status = first.get("value", "") if isinstance(first, dict) else str(first)

    return AgentTraceResponse(
        case_id=case_id,
        steps=step_list,
        status=case_status or "unknown",
        total_tokens=total_tokens,
        total_duration_ms=total_ms,
    )


@router.post("/run/{case_id}", status_code=202)
async def run_agents(
    case_id: str,
    body: AgentRunRequest,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    """Trigger agent pipeline on a case (runs in background)."""
    from ..agents.orchestrator import run_pipeline
    from ..auth import UserSession

    session = UserSession.from_token(user)
    background_tasks.add_task(run_pipeline, case_id, body.pipeline, session)
    return {"case_id": case_id, "pipeline": body.pipeline, "status": "accepted"}


# ---- Consult endpoints ----


@router.get("/consult/inbox", response_model=list[dict[str, Any]])
async def consult_inbox(
    user: CurrentUser, gdb: PermittedGDBDep, status: str = "pending", limit: int = 50
):
    """Cross-case consult inbox filtered to the user's departments."""
    see_all = user.role in ("admin", "security")
    query = (
        "g.V().hasLabel('ConsultRequest').has('status', st)"
        ".order().by('deadline', asc).limit(lim).as('req')"
        ".in('HAS_CONSULT_REQUEST').as('case')"
        ".select('req', 'case').by(valueMap(true))"
    )
    bindings = {"st": status, "lim": limit}
    results = await gdb.execute(query, bindings)

    rows: list[dict[str, Any]] = []
    for r in results:
        req = r.get("req", {}) or {}
        case = r.get("case", {}) or {}
        target = _v(req, "target_org_id")
        if not see_all and target not in (user.departments or []):
            continue
        rows.append(
            {
                "request_id": _v(req, "request_id"),
                "case_id": _v(req, "case_id"),
                "case_code": _v(case, "code"),
                "tthc_code": _v(case, "tthc_code"),
                "tthc_name": _v(case, "tthc_name"),
                "applicant_name": _v(case, "applicant_name"),
                "target_org_id": target,
                "target_org_name": _v(req, "target_org_name"),
                "context_summary": _v(req, "context_summary"),
                "main_question": _v(req, "main_question"),
                "sub_questions": _v(req, "sub_questions", "[]"),
                "deadline": _v(req, "deadline"),
                "urgency": _v(req, "urgency", "normal"),
                "status": _v(req, "status", "pending"),
                "created_at": _v(req, "created_at"),
            }
        )
    return rows


@router.get("/consult/{case_id}/requests", response_model=list[ConsultRequestResponse])
async def list_consult_requests(case_id: str, user: CurrentUser, gdb: PermittedGDBDep):
    """List all consult requests for a case."""
    results = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).out('HAS_CONSULT_REQUEST').valueMap(true)",
        {"cid": case_id},
    )
    items = []
    for r in results:
        items.append(
            ConsultRequestResponse(
                request_id=_v(r, "request_id"),
                case_id=_v(r, "case_id"),
                target_org_id=_v(r, "target_org_id"),
                target_org_name=_v(r, "target_org_name"),
                context_summary=_v(r, "context_summary"),
                main_question=_v(r, "main_question"),
                sub_questions=_v(r, "sub_questions", "[]"),
                deadline=_v(r, "deadline"),
                urgency=_v(r, "urgency", "normal"),
                status=_v(r, "status", "pending"),
                created_at=_v(r, "created_at"),
            )
        )
    return items


@router.post("/consult/{request_id}/submit", status_code=200)
async def submit_consult_request(
    request_id: str,
    body: ConsultSubmitRequest,
    user: CurrentUser,
    gdb: PermittedGDBDep,
):
    """
    Nop ket qua xin y kien (human-submitted).
    Ghi ConsultOpinion + CONSULTED_BY edge, cap nhat trang thai ConsultRequest,
    phat AuditEvent va WS event.
    """
    import time

    from ..database import get_pg_pool
    from ..graph.audit import AuditEvent, AuditLogger

    _ALLOWED_ROLES = {"legal", "officer", "leader", "admin"}
    if user.role not in _ALLOWED_ROLES:
        raise fastapi.HTTPException(
            status_code=403,
            detail={"detail": "Khong co quyen nop y kien", "code": "FORBIDDEN_ROLE"},
        )

    valid_recs = {"approve", "reject", "request_supplement"}
    if body.recommendation not in valid_recs:
        raise fastapi.HTTPException(
            status_code=422,
            detail={
                "detail": f"recommendation phai la {valid_recs}",
                "code": "INVALID_RECOMMENDATION",
            },
        )

    # 1. Load ConsultRequest
    req_rows = await gdb.execute(
        "g.V().has('ConsultRequest', 'request_id', req_id).valueMap(true)",
        {"req_id": request_id},
    )
    if not req_rows:
        raise fastapi.HTTPException(
            status_code=404,
            detail={"detail": "Khong tim thay yeu cau xin y kien", "code": "CONSULT_NOT_FOUND"},
        )
    req = req_rows[0]
    current_status = _v(req, "status", "pending")
    if current_status != "pending":
        raise fastapi.HTTPException(
            status_code=409,
            detail={
                "detail": f"Yeu cau xin y kien da o trang thai: {current_status}",
                "code": "CONSULT_ALREADY_COMPLETED",
            },
        )

    target_org_id = _v(req, "target_org_id")
    case_id = _v(req, "case_id")

    # 2. Check department membership (admin bypasses)
    if user.role != "admin" and target_org_id not in (user.departments or []):
        raise fastapi.HTTPException(
            status_code=403,
            detail={"detail": "Khong thuoc phong ban duoc xin y kien", "code": "WRONG_DEPARTMENT"},
        )

    now = datetime.now(UTC).isoformat()
    opinion_id = f"consult-op-{request_id}-{uuid.uuid4().hex[:8]}"
    audit_id = str(uuid.uuid4())

    # 3. Write ConsultOpinion vertex + CONSULTED_BY edge
    await gdb.execute(
        "g.addV('ConsultOpinion')"
        ".property('opinion_id', oid)"
        ".property('request_id', req_id)"
        ".property('case_id', cid)"
        ".property('opinion', op)"
        ".property('recommendation', rec)"
        ".property('submitted_by', uid)"
        ".property('submitted_at', ts)"
        ".as('co')"
        ".V().has('ConsultRequest', 'request_id', req_id)"
        ".addE('CONSULTED_BY').to('co')",
        {
            "oid": opinion_id,
            "req_id": request_id,
            "cid": case_id,
            "op": body.opinion,
            "rec": body.recommendation,
            "uid": user.sub,
            "ts": now,
        },
    )

    # Attach any referenced documents
    for doc_id in body.attachments or []:
        try:
            await gdb.execute(
                "g.V().has('ConsultOpinion', 'opinion_id', oid)"
                ".addE('REFERENCES_DOC')"
                ".to(__.V().has('Document', 'doc_id', did))",
                {"oid": opinion_id, "did": doc_id},
            )
        except Exception:
            pass  # non-critical — doc may not exist

    # 4. Update ConsultRequest status to COMPLETED
    await gdb.execute(
        "g.V().has('ConsultRequest', 'request_id', req_id)"
        ".property('status', 'completed')"
        ".property('completed_at', ts)",
        {"req_id": request_id, "ts": now},
    )

    # 5. AuditEvent
    try:
        pg = get_pg_pool()
        audit = AuditLogger(gdb_client=None, hologres_pool=pg)
        await audit.log(
            AuditEvent(
                event_id=audit_id,
                agent_id=user.sub,
                tier="HTTP_REQUEST",
                action="consult_submitted",
                detail=f"ConsultRequest {request_id} -> {body.recommendation}",
                query_snippet="",
                timestamp=time.time(),
                user_id=user.sub,
                case_id=case_id,
                target_type="ConsultRequest",
                target_id=request_id,
            )
        )
    except Exception:
        pass  # audit failure is non-blocking

    # 6. WebSocket events
    try:
        from ..api.ws import broadcast

        await broadcast(
            f"case:{case_id}",
            {
                "type": "consult_complete",
                "request_id": request_id,
                "recommendation": body.recommendation,
            },
        )
        await broadcast(
            f"consult:{request_id}:complete",
            {
                "type": "consult_complete",
                "request_id": request_id,
                "recommendation": body.recommendation,
                "case_id": case_id,
            },
        )
    except Exception:
        pass  # non-critical

    return {
        "status": "completed",
        "recommendation": body.recommendation,
        "opinion_id": opinion_id,
        "audit_id": audit_id,
    }


@router.post("/consult/{consult_request_id}/opinion", status_code=201)
async def submit_consult_opinion(
    consult_request_id: str,
    body: ConsultOpinionSubmit,
    user: CurrentUser,
    gdb: PermittedGDBDep,
):
    """Submit a department opinion for a consult request (human-submitted)."""
    op_id = f"op-{consult_request_id}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    await gdb.execute(
        "g.addV('Opinion')"
        ".property('opinion_id', op_id)"
        ".property('content', content)"
        ".property('verdict', verdict)"
        ".property('source_org_id', org_id)"
        ".property('source_org_name', org_name)"
        ".property('submitted_by', uid)"
        ".property('aggregated', false)"
        ".property('created_at', ts)"
        ".as('op')"
        ".V().has('ConsultRequest', 'request_id', req_id)"
        ".addE('HAS_OPINION').to('op')",
        {
            "op_id": op_id,
            "content": body.get_content(),
            "verdict": body.get_verdict(),
            "org_id": body.get_source_org_id(),
            "org_name": body.get_source_org_name(),
            "uid": user.sub,
            "ts": now,
            "req_id": consult_request_id,
        },
    )

    return {"opinion_id": op_id, "status": "submitted"}


@router.post("/consult/{consult_request_id}/aggregate", status_code=202)
async def aggregate_consult_opinions(
    consult_request_id: str,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    case_id: str = fastapi.Query(..., description="Case ID for the consult request"),
):
    """Trigger opinion aggregation for a consult request."""
    from ..agents.orchestrator import get_agent
    from ..auth import UserSession

    agent = get_agent("consult_agent")
    session = UserSession.from_token(user)
    background_tasks.add_task(
        agent.aggregate_opinions,
        case_id,
        consult_request_id,
        session,
    )
    return {
        "consult_request_id": consult_request_id,
        "status": "aggregating",
    }


@router.get("/trace/{case_id}/artifact")
async def get_artifact(case_id: str, user: CurrentUser, gdb: PermittedGDBDep) -> dict[str, Any]:
    """
    Hydrate endpoint for the frontend artifact panel.

    Returns a reconstructed event timeline for a case from AgentStep vertices
    (including reasoning_excerpt) and analytics_agents rows.
    """
    events: list[dict[str, Any]] = []

    steps = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).out('PROCESSED_BY')"
        ".hasLabel('AgentStep').valueMap(true).order().by('step_id')",
        {"cid": case_id},
    )

    for s in steps:
        agent_name = _v(s, "agent_name")
        step_id = _v(s, "step_id")
        status = _v(s, "status", "completed")
        ts = _v(s, "created_at") or datetime.now(UTC).isoformat()

        base: dict[str, Any] = {
            "agent_name": agent_name,
            "agent_id": step_id,
            "timestamp": ts,
        }

        events.append({"type": "agent_started", **base})

        reasoning = _v(s, "reasoning_excerpt")
        if reasoning:
            events.append(
                {
                    "type": "agent_thinking_chunk",
                    **base,
                    "delta": reasoning,
                    "synthetic": True,
                }
            )

        if status == "completed":
            events.append({"type": "agent_completed", **base})
        else:
            events.append({"type": "agent_failed", **base})

    # Enrich with analytics
    try:
        async with pg_connection() as conn:
            rows = await conn.fetch(
                "SELECT agent_name, duration_ms, input_tokens, output_tokens, tool_calls, status "
                "FROM analytics_agents WHERE case_id = $1 ORDER BY id",
                case_id,
            )
            for row in rows:
                events.append(
                    {
                        "type": "agent_analytics",
                        "agent_name": row["agent_name"],
                        "duration_ms": row["duration_ms"],
                        "input_tokens": row["input_tokens"],
                        "output_tokens": row["output_tokens"],
                        "tool_calls": row["tool_calls"],
                        "status": row["status"],
                    }
                )
    except Exception:
        pass

    case_status_result = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).values('status')",
        {"cid": case_id},
    )
    first = case_status_result[0] if case_status_result else {}
    case_status = first.get("value", "unknown") if isinstance(first, dict) else str(first)

    return {
        "case_id": case_id,
        "status": case_status,
        "events": events,
    }


def _v(vertex_map: dict, key: str, default: str = "") -> str:
    """Extract a property from Gremlin valueMap (handles list wrapping)."""
    val = vertex_map.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return str(val) if val else default
