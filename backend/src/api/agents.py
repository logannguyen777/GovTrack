"""backend/src/api/agents.py"""
import uuid
from datetime import UTC, datetime

import fastapi
from fastapi import APIRouter, BackgroundTasks

from ..auth import CurrentUser
from ..models.schemas import (
    AgentRunRequest,
    AgentTraceResponse,
    AgentStepResponse,
    ConsultOpinionSubmit,
    ConsultRequestResponse,
)
from ..database import async_gremlin_submit, gremlin_submit

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/trace/{case_id}", response_model=AgentTraceResponse)
async def get_agent_trace(case_id: str, user: CurrentUser):
    """Get the full agent processing trace for a case."""
    steps = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).out('PROCESSED_BY')"
        ".valueMap(true).order().by('step_id')",
        {"cid": case_id},
    )
    step_list = []
    total_tokens = 0
    total_ms = 0
    for s in steps:
        in_tok = s.get("input_tokens", [0])[0]
        out_tok = s.get("output_tokens", [0])[0]
        dur = s.get("duration_ms", [0])[0]
        total_tokens += in_tok + out_tok
        total_ms += dur
        step_list.append(AgentStepResponse(
            step_id=s.get("step_id", [""])[0],
            agent_name=s.get("agent_name", [""])[0],
            action=s.get("action", [""])[0],
            status=s.get("status", ["completed"])[0],
            input_tokens=in_tok,
            output_tokens=out_tok,
            duration_ms=dur,
        ))

    case_status = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).values('status')", {"cid": case_id},
    )

    return AgentTraceResponse(
        case_id=case_id,
        steps=step_list,
        status=case_status[0] if case_status else "unknown",
        total_tokens=total_tokens,
        total_duration_ms=total_ms,
    )


@router.post("/run/{case_id}", status_code=202)
async def run_agents(
    case_id: str, body: AgentRunRequest,
    user: CurrentUser, background_tasks: BackgroundTasks,
):
    """Trigger agent pipeline on a case (runs in background)."""
    from ..agents.orchestrator import run_pipeline
    background_tasks.add_task(run_pipeline, case_id, body.pipeline)
    return {"case_id": case_id, "pipeline": body.pipeline, "status": "accepted"}


# ---- Consult endpoints ----

@router.get("/consult/{case_id}/requests", response_model=list[ConsultRequestResponse])
async def list_consult_requests(case_id: str, user: CurrentUser):
    """List all consult requests for a case."""
    results = await async_gremlin_submit(
        "g.V().has('Case', 'case_id', cid)"
        ".out('HAS_CONSULT_REQUEST').valueMap(true)",
        {"cid": case_id},
    )
    items = []
    for r in results:
        items.append(ConsultRequestResponse(
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
        ))
    return items


@router.post("/consult/{consult_request_id}/opinion", status_code=201)
async def submit_consult_opinion(
    consult_request_id: str,
    body: ConsultOpinionSubmit,
    user: CurrentUser,
):
    """Submit a department opinion for a consult request (human-submitted)."""
    op_id = f"op-{consult_request_id}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    await async_gremlin_submit(
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
            "content": body.content,
            "verdict": body.verdict,
            "org_id": body.source_org_id,
            "org_name": body.source_org_name,
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
    agent = get_agent("consult_agent")
    background_tasks.add_task(
        agent.aggregate_opinions, case_id, consult_request_id,
    )
    return {
        "consult_request_id": consult_request_id,
        "status": "aggregating",
    }


def _v(vertex_map: dict, key: str, default: str = "") -> str:
    """Extract a property from Gremlin valueMap (handles list wrapping)."""
    val = vertex_map.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return str(val) if val else default
