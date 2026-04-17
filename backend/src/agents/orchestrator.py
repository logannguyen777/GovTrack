"""
backend/src/agents/orchestrator.py
AgentRuntime: reads Task DAG from GDB, dispatches agents, manages parallel execution.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ..database import pg_connection
from .base import AgentResult, BaseAgent
from .streaming import StreamingAgentEvent

if TYPE_CHECKING:
    from ..auth import UserSession

logger = logging.getLogger("govflow.orchestrator")

# Agent name -> class mapping (registered by each agent module)
_AGENT_CLASSES: dict[str, type[BaseAgent]] = {}


def register_agent(name: str, cls: type[BaseAgent]) -> None:
    """Register an agent class by name."""
    _AGENT_CLASSES[name] = cls
    logger.info(f"Registered agent: {name}")


def get_agent(name: str) -> BaseAgent:
    """Instantiate an agent by name."""
    if name not in _AGENT_CLASSES:
        raise ValueError(f"Unknown agent: {name}. Registered: {list(_AGENT_CLASSES.keys())}")
    return _AGENT_CLASSES[name]()


# ============================================================
# Pipeline definitions: ordered lists of agent tasks
# ============================================================

PIPELINE_FULL = [
    ("intake", "intake_agent", []),
    ("classify", "classifier_agent", ["intake"]),
    ("doc_analyze", "doc_analyze_agent", ["intake"]),
    ("legal_search", "legal_search_agent", ["classify"]),
    ("compliance", "compliance_agent", ["classify", "doc_analyze", "legal_search"]),
    ("route", "router_agent", ["classify"]),
    ("consult", "consult_agent", ["route", "compliance"]),
    ("summary", "summary_agent", ["compliance", "consult"]),
    ("draft", "draft_agent", ["summary"]),
]

PIPELINE_CLASSIFY_ONLY = [
    ("intake", "intake_agent", []),
    ("classify", "classifier_agent", ["intake"]),
]

PIPELINE_GAP_CHECK_ONLY = [
    ("intake", "intake_agent", []),
    ("classify", "classifier_agent", ["intake"]),
    ("doc_analyze", "doc_analyze_agent", ["intake"]),
    ("compliance", "compliance_agent", ["classify", "doc_analyze"]),
]

PIPELINE_DISPATCH = [
    ("intake", "doc_analyze_agent", []),
    ("classify", "classifier_agent", ["intake"]),
    ("security", "security_officer_agent", ["classify"]),
    ("dispatch", "dispatch_router_agent", ["security"]),
    ("review", "compliance_agent", ["dispatch"]),
    ("response", "drafter_agent", ["review"]),
]

PIPELINES = {
    "full": PIPELINE_FULL,
    "classify_only": PIPELINE_CLASSIFY_ONLY,
    "gap_check_only": PIPELINE_GAP_CHECK_ONLY,
    "dispatch": PIPELINE_DISPATCH,
    "dynamic": None,  # Planner agent generates the DAG at runtime
}


TASK_TIMEOUT_SECONDS = 120


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_system_gdb():
    """Return a PermittedGremlinClient bound to SYSTEM_SESSION for orchestrator writes."""
    from ..auth import SYSTEM_SESSION
    from ..graph.permitted_client import PermittedGremlinClient

    return PermittedGremlinClient(SYSTEM_SESSION)


async def _ws_broadcast(topic: str, message: dict) -> None:
    try:
        from ..api.ws import broadcast

        await broadcast(topic, message)
    except Exception as exc:
        logger.debug(f"WS broadcast failed (non-critical): {exc}")


class AgentRuntime:
    """
    Orchestrator that manages agent execution.

    Accepts an optional `session` (UserSession) from the API layer.  When
    present it is propagated to each agent via AgentContext so that
    PermittedGremlinClient calls inside agents use the caller's identity.
    Falls back to SYSTEM_SESSION when absent (e.g. background tasks without
    an authenticated caller).
    """

    def __init__(
        self,
        case_id: str,
        pipeline_name: str = "full",
        max_retries: int = 2,
        session: "UserSession | None" = None,
    ):
        self.case_id = case_id
        self.dynamic = pipeline_name == "dynamic"
        self.pipeline = PIPELINES.get(pipeline_name, PIPELINE_FULL) if not self.dynamic else []
        self.max_retries = max_retries
        self.results: dict[str, AgentResult] = {}
        self.task_status: dict[str, str] = {}

        # Session propagation: use caller's session or fall back to SYSTEM_SESSION
        if session is None:
            from ..auth import SYSTEM_SESSION

            self.session: "UserSession" = SYSTEM_SESSION
        else:
            self.session = session

    async def _resolve_pipeline_from_case(self) -> None:
        """
        If pipeline_name was 'full', check case.case_type and switch to
        PIPELINE_DISPATCH automatically for internal_dispatch cases.
        """
        if self.dynamic or self.pipeline is not PIPELINE_FULL:
            return
        try:
            gdb = _get_system_gdb()
            rows = await gdb.execute(
                "g.V().has('Case', 'case_id', cid).values('case_type')",
                {"cid": self.case_id},
            )
            if rows:
                first = rows[0]
                ctype = first.get("value", "") if isinstance(first, dict) else str(first)
                if ctype == "internal_dispatch":
                    logger.info(
                        f"[Orchestrator] Switching to PIPELINE_DISPATCH for case {self.case_id}"
                    )
                    self.pipeline = PIPELINE_DISPATCH
        except Exception as exc:
            logger.debug(f"[Orchestrator] case_type lookup failed (using default): {exc}")

    async def run(self) -> dict[str, AgentResult]:
        """Execute the full pipeline."""
        self.trace_id = uuid.uuid4().hex[:12]
        logger.info(f"[Orchestrator:{self.trace_id}] Starting pipeline on case {self.case_id}")

        # Auto-select dispatch pipeline when case.case_type == internal_dispatch
        await self._resolve_pipeline_from_case()

        if self.dynamic:
            await self._run_dynamic_planning()
        else:
            await self._create_task_dag()

        while True:
            ready_tasks = self._get_ready_tasks()
            if not ready_tasks:
                pending = [t for t, s in self.task_status.items() if s in ("pending", "running")]
                if not pending:
                    break
                failed_tasks = {t for t, s in self.task_status.items() if s == "failed"}
                if failed_tasks:
                    can_progress = False
                    for task_name, agent_name, deps in self.pipeline:
                        if self.task_status.get(task_name) != "pending":
                            continue
                        if all(self.task_status.get(d) == "completed" for d in deps):
                            can_progress = True
                            break
                    if not can_progress:
                        logger.error(
                            f"[Orchestrator] Pipeline blocked: all pending tasks have failed dependencies. "
                            f"Failed: {sorted(failed_tasks)}"
                        )
                        break
                await asyncio.sleep(0.1)
                continue

            logger.info(
                f"[Orchestrator:{self.trace_id}] Dispatching: {[t for t, _ in ready_tasks]}"
            )
            coros = [self._run_task(task_name, agent_name) for task_name, agent_name in ready_tasks]
            await asyncio.gather(*coros)

        all_completed = all(s == "completed" for s in self.task_status.values())
        final_status = "approved" if all_completed else "failed"

        gdb = _get_system_gdb()
        await gdb.execute(
            "g.V().has('Case', 'case_id', cid).property('status', status)",
            {"cid": self.case_id, "status": final_status},
        )

        try:
            async with pg_connection() as conn:
                await conn.execute(
                    "UPDATE analytics_cases SET status = $1, completed_at = $2 WHERE case_id = $3",
                    final_status,
                    datetime.now(UTC),
                    self.case_id,
                )
        except Exception as e:
            logger.warning(f"Failed to update analytics_cases: {e}")

        logger.info(f"[Orchestrator:{self.trace_id}] Pipeline finished: {final_status}")
        return self.results

    async def _create_task_dag(self) -> None:
        """Create Task vertices and DEPENDS_ON edges in GDB."""
        gdb = _get_system_gdb()
        for task_name, agent_name, deps in self.pipeline:
            task_id = f"{self.case_id}:{task_name}"
            self.task_status[task_name] = "pending"

            await gdb.execute(
                "g.addV('Task')"
                ".property('task_id', tid).property('name', name)"
                ".property('status', 'pending').property('agent_name', agent)"
                ".property('case_id', cid)",
                {"tid": task_id, "name": task_name, "agent": agent_name, "cid": self.case_id},
            )

            for dep in deps:
                dep_id = f"{self.case_id}:{dep}"
                await gdb.execute(
                    "g.V().has('Task', 'task_id', downstream)"
                    ".addE('DEPENDS_ON')"
                    ".to(__.V().has('Task', 'task_id', upstream))",
                    {"downstream": task_id, "upstream": dep_id},
                )

    def _get_ready_tasks(self) -> list[tuple[str, str]]:
        if self.dynamic:
            return self._get_ready_tasks_dynamic()
        ready = []
        for task_name, agent_name, deps in self.pipeline:
            if self.task_status.get(task_name) != "pending":
                continue
            if all(self.task_status.get(d) == "completed" for d in deps):
                ready.append((task_name, agent_name))
        return ready

    async def _run_task(self, task_name: str, agent_name: str) -> None:
        """Run a single task with retry logic, using run_streaming for WS events."""
        task_id = f"{self.case_id}:{task_name}"
        self.task_status[task_name] = "running"
        topic = f"case:{self.case_id}"

        gdb = _get_system_gdb()
        await gdb.execute(
            "g.V().has('Task', 'task_id', tid).property('status', 'running')",
            {"tid": task_id},
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                agent = get_agent(agent_name)
                agent_id = f"{agent.profile.name}:{int(time.time() * 1000)}"

                thinking_buf: list[str] = []

                async def _emitter(evt: StreamingAgentEvent) -> None:
                    ws_event = self._translate(evt, agent_id)
                    if ws_event:
                        await _ws_broadcast(topic, ws_event)
                    if evt.type == "thinking_chunk" and evt.delta:
                        thinking_buf.append(evt.delta)

                agent._event_emitter = _emitter
                # Propagate caller session and case_type context to agent
                agent._session = self.session
                agent._case_type = (
                    "internal_dispatch" if self.pipeline is PIPELINE_DISPATCH else "citizen_tthc"
                )

                await _ws_broadcast(
                    topic,
                    {
                        "event": "agent_started",
                        "data": {
                            "agent_name": agent.profile.name,
                            "agent_id": agent_id,
                            "task_name": task_name,
                            "timestamp": _now_iso(),
                        },
                    },
                )

                result: AgentResult | None = None

                async def _run_with_timeout():
                    nonlocal result
                    async for event in agent.run_streaming(self.case_id):
                        ws_event = self._translate(event, agent_id)
                        if ws_event:
                            await _ws_broadcast(topic, ws_event)
                        if event.type == "thinking_chunk" and event.delta:
                            thinking_buf.append(event.delta)
                        if event.type == "completed":
                            from .base import AgentResult as _AR

                            result = _AR(
                                agent_name=agent.profile.name,
                                case_id=self.case_id,
                                status="completed",
                                output=str(event.result or ""),
                            )
                        elif event.type == "failed":
                            from .base import AgentResult as _AR

                            result = _AR(
                                agent_name=agent.profile.name,
                                case_id=self.case_id,
                                status="failed",
                                output="",
                                error=event.error,
                            )

                await asyncio.wait_for(_run_with_timeout(), timeout=TASK_TIMEOUT_SECONDS)

                if result is None:
                    result = await asyncio.wait_for(
                        agent.run(self.case_id),
                        timeout=TASK_TIMEOUT_SECONDS,
                    )

                self.results[task_name] = result

                if result.status == "completed":
                    self.task_status[task_name] = "completed"
                    await gdb.execute(
                        "g.V().has('Task', 'task_id', tid).property('status', 'completed')",
                        {"tid": task_id},
                    )

                    reasoning_excerpt = "".join(thinking_buf)[:2000]
                    if reasoning_excerpt:
                        try:
                            await gdb.execute(
                                "g.V().has('Case', 'case_id', cid)"
                                ".out('PROCESSED_BY').has('agent_name', aname)"
                                ".order().by('started_at', decr).limit(1)"
                                ".property('reasoning_excerpt', excerpt)",
                                {
                                    "cid": self.case_id,
                                    "aname": agent.profile.name,
                                    "excerpt": reasoning_excerpt,
                                },
                            )
                        except Exception as exc:
                            logger.debug(f"reasoning_excerpt write failed: {exc}")

                    await _ws_broadcast(
                        topic,
                        {
                            "event": "agent_completed",
                            "data": {
                                "agent_name": agent.profile.name,
                                "agent_id": agent_id,
                                "task_name": task_name,
                                "timestamp": _now_iso(),
                            },
                        },
                    )
                    logger.info(f"[Orchestrator:{self.trace_id}] Task '{task_name}' completed")
                    return
                else:
                    logger.warning(
                        f"[Orchestrator] Task '{task_name}' returned status={result.status} "
                        f"(attempt {attempt}/{self.max_retries})"
                    )

            except asyncio.TimeoutError:
                logger.error(
                    f"[Orchestrator] Task '{task_name}' timed out after {TASK_TIMEOUT_SECONDS}s "
                    f"(attempt {attempt}/{self.max_retries})"
                )
            except Exception as e:
                logger.error(
                    f"[Orchestrator] Task '{task_name}' exception (attempt {attempt}): {e}"
                )

            if attempt < self.max_retries:
                await asyncio.sleep(2.0 * attempt)

        self.task_status[task_name] = "failed"
        await gdb.execute(
            "g.V().has('Task', 'task_id', tid).property('status', 'failed')",
            {"tid": task_id},
        )
        logger.error(
            f"[Orchestrator:{self.trace_id}] Task '{task_name}' FAILED after {self.max_retries} retries"
        )

    @staticmethod
    def _translate(event: StreamingAgentEvent, agent_id: str) -> dict | None:
        base: dict[str, Any] = {
            "agent_name": event.agent_name,
            "agent_id": agent_id,
            "timestamp": _now_iso(),
        }

        if event.type == "thinking_chunk":
            return {"event": "agent_thinking_chunk", "data": {**base, "delta": event.delta}}
        elif event.type == "text_chunk":
            payload = {**base, "delta": event.delta}
            if event.variant:
                payload["variant"] = event.variant
            return {"event": "agent_text_chunk", "data": payload}
        elif event.type == "tool_call_start":
            return {
                "event": "agent_tool_call_start",
                "data": {
                    **base,
                    "tool_call_id": event.tool_call_id,
                    "tool_name": event.tool_name,
                    "args": event.tool_args,
                },
            }
        elif event.type == "tool_call_result":
            result_payload = {
                **base,
                "tool_call_id": event.tool_call_id,
                "result": event.tool_result,
                "status": "success",
            }
            if event.tool_duration_ms is not None:
                result_payload["duration_ms"] = event.tool_duration_ms
            return {"event": "agent_tool_call_result", "data": result_payload}
        elif event.type == "search_log" and event.search_log:
            return {"event": "search_log", "data": {**base, **event.search_log}}
        elif event.type == "graph_op" and event.graph_op:
            return {"event": "graph_operation", "data": {**base, **event.graph_op}}

        return None

    async def _run_dynamic_planning(self) -> None:
        """Run the Planner agent to generate a Task DAG, then load it into task_status."""
        logger.info(f"[Orchestrator] Running dynamic planning for case {self.case_id}")

        planner = get_agent("planner_agent")
        planner._session = self.session
        result = await planner.run(self.case_id)
        self.results["planner"] = result

        if result.status != "completed":
            logger.warning("[Orchestrator] Planner failed, falling back to static full pipeline")
            self.dynamic = False
            self.pipeline = PIPELINE_FULL
            await self._create_task_dag()
            return

        gdb = _get_system_gdb()
        tasks = []
        for _attempt in range(3):
            tasks = await gdb.execute(
                "g.V().has('Task', 'case_id', cid).valueMap(true)",
                {"cid": self.case_id},
            )
            if tasks:
                break
            await asyncio.sleep(0.5)

        if not tasks:
            logger.warning(
                "[Orchestrator] No tasks found after planning, falling back to static pipeline"
            )
            self.dynamic = False
            self.pipeline = PIPELINE_FULL
            await self._create_task_dag()
            return

        for t in tasks:
            name = t.get("name", [""])[0] if isinstance(t.get("name"), list) else t.get("name", "")
            agent = (
                t.get("agent_name", [""])[0]
                if isinstance(t.get("agent_name"), list)
                else t.get("agent_name", "")
            )
            self.task_status[name] = "pending"
            if not hasattr(self, "_dynamic_agents"):
                self._dynamic_agents: dict[str, str] = {}
            self._dynamic_agents[name] = agent

        if not hasattr(self, "_dynamic_deps"):
            self._dynamic_deps: dict[str, list[str]] = {name: [] for name in self.task_status}
        for t in tasks:
            name = t.get("name", [""])[0] if isinstance(t.get("name"), list) else t.get("name", "")
            task_id = (
                t.get("task_id", [""])[0]
                if isinstance(t.get("task_id"), list)
                else t.get("task_id", "")
            )
            deps = await gdb.execute(
                "g.V().has('Task', 'task_id', tid).out('DEPENDS_ON').values('name')",
                {"tid": task_id},
            )
            self._dynamic_deps[name] = (
                [d.get("value", "") if isinstance(d, dict) else str(d) for d in deps]
                if deps
                else []
            )

    def _get_ready_tasks_dynamic(self) -> list[tuple[str, str]]:
        ready = []
        for name, status in self.task_status.items():
            if status != "pending":
                continue
            deps = self._dynamic_deps.get(name, [])
            if all(self.task_status.get(d) == "completed" for d in deps):
                agent = self._dynamic_agents.get(name, "")
                if agent:
                    ready.append((name, agent))
        return ready


# ============================================================
# Entry point: called from api/agents.py background task
# ============================================================


async def run_pipeline(
    case_id: str,
    pipeline_name: str = "full",
    session: "UserSession | None" = None,
) -> dict[str, AgentResult]:
    """Run an agent pipeline on a case. Called as a BackgroundTask."""
    runtime = AgentRuntime(case_id, pipeline_name, session=session)
    return await runtime.run()
