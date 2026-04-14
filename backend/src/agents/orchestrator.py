"""
backend/src/agents/orchestrator.py
AgentRuntime: reads Task DAG from GDB, dispatches agents, manages parallel execution.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from ..database import async_gremlin_submit, pg_connection
from .base import AgentResult, BaseAgent

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
    # (task_name, agent_name, depends_on[])
    ("intake",        "intake_agent",        []),
    ("classify",      "classifier_agent",    ["intake"]),
    ("doc_analyze",   "doc_analyze_agent",   ["intake"]),
    ("gap_check",     "gap_agent",           ["classify", "doc_analyze"]),
    ("legal_search",  "legal_search_agent",  ["classify"]),
    ("compliance",    "compliance_agent",    ["gap_check", "legal_search"]),
    ("route",         "router_agent",        ["classify"]),
    ("consult",       "consult_agent",       ["route", "compliance"]),
    ("summary",       "summary_agent",       ["compliance", "consult"]),
    ("draft",         "draft_agent",         ["summary"]),
    ("review",        "review_agent",        ["draft"]),
    ("publish",       "publish_agent",       ["review"]),
]

PIPELINE_CLASSIFY_ONLY = [
    ("intake",   "intake_agent",       []),
    ("classify", "classifier_agent",   ["intake"]),
]

PIPELINE_GAP_CHECK_ONLY = [
    ("intake",       "intake_agent",       []),
    ("classify",     "classifier_agent",   ["intake"]),
    ("doc_analyze",  "doc_analyze_agent",  ["intake"]),
    ("gap_check",    "gap_agent",          ["classify", "doc_analyze"]),
]

PIPELINES = {
    "full": PIPELINE_FULL,
    "classify_only": PIPELINE_CLASSIFY_ONLY,
    "gap_check_only": PIPELINE_GAP_CHECK_ONLY,
    "dynamic": None,  # Planner agent generates the DAG at runtime
}


TASK_TIMEOUT_SECONDS = 120  # Max time per agent task before timeout


class AgentRuntime:
    """
    Orchestrator that manages agent execution.

    1. Creates Task vertices in GDB for the pipeline
    2. Topologically dispatches agents respecting dependencies
    3. Runs independent tasks in parallel via asyncio.gather
    4. Tracks status and retries failed tasks (up to max_retries)
    """

    def __init__(self, case_id: str, pipeline_name: str = "full", max_retries: int = 2):
        self.case_id = case_id
        self.dynamic = pipeline_name == "dynamic"
        self.pipeline = PIPELINES.get(pipeline_name, PIPELINE_FULL) if not self.dynamic else []
        self.max_retries = max_retries
        self.results: dict[str, AgentResult] = {}
        self.task_status: dict[str, str] = {}  # task_name -> pending|running|completed|failed

    async def run(self) -> dict[str, AgentResult]:
        """Execute the full pipeline."""
        self.trace_id = uuid.uuid4().hex[:12]
        logger.info(f"[Orchestrator:{self.trace_id}] Starting pipeline on case {self.case_id}")

        # Dynamic mode: run Planner agent first to generate the DAG
        if self.dynamic:
            await self._run_dynamic_planning()
        else:
            # Create Task vertices in GDB from static pipeline
            await self._create_task_dag()

        # Topological execution loop
        while True:
            ready_tasks = self._get_ready_tasks()
            if not ready_tasks:
                # Check if all done or stuck
                pending = [t for t, s in self.task_status.items() if s in ("pending", "running")]
                if not pending:
                    break
                # Check if any pending task can still become ready
                # (i.e., none of its dependencies are failed)
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

            # Run ready tasks in parallel
            logger.info(f"[Orchestrator:{self.trace_id}] Dispatching: {[t for t, _ in ready_tasks]}")
            coros = [self._run_task(task_name, agent_name) for task_name, agent_name in ready_tasks]
            await asyncio.gather(*coros)

        # Update case status based on results
        all_completed = all(s == "completed" for s in self.task_status.values())
        final_status = "approved" if all_completed else "failed"
        await async_gremlin_submit(
            "g.V().has('Case', 'case_id', cid).property('status', status)",
            {"cid": self.case_id, "status": final_status},
        )

        # Update analytics
        try:
            async with pg_connection() as conn:
                await conn.execute(
                    "UPDATE analytics_cases SET status = $1, completed_at = $2 WHERE case_id = $3",
                    final_status, datetime.now(UTC), self.case_id,
                )
        except Exception as e:
            logger.warning(f"Failed to update analytics_cases: {e}")

        logger.info(f"[Orchestrator:{self.trace_id}] Pipeline finished: {final_status}")
        return self.results

    async def _create_task_dag(self) -> None:
        """Create Task vertices and DEPENDS_ON edges in GDB."""
        for task_name, agent_name, deps in self.pipeline:
            task_id = f"{self.case_id}:{task_name}"
            self.task_status[task_name] = "pending"

            await async_gremlin_submit(
                "g.addV('Task')"
                ".property('task_id', tid).property('name', name)"
                ".property('status', 'pending').property('agent_name', agent)"
                ".property('case_id', cid)",
                {"tid": task_id, "name": task_name, "agent": agent_name, "cid": self.case_id},
            )

            # Create dependency edges
            for dep in deps:
                dep_id = f"{self.case_id}:{dep}"
                await async_gremlin_submit(
                    "g.V().has('Task', 'task_id', downstream)"
                    ".addE('DEPENDS_ON')"
                    ".to(g.V().has('Task', 'task_id', upstream))",
                    {"downstream": task_id, "upstream": dep_id},
                )

    def _get_ready_tasks(self) -> list[tuple[str, str]]:
        """Get tasks whose dependencies are all completed."""
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
        """Run a single task with retry logic."""
        task_id = f"{self.case_id}:{task_name}"
        self.task_status[task_name] = "running"

        # Update GDB task status
        await async_gremlin_submit(
            "g.V().has('Task', 'task_id', tid).property('status', 'running')",
            {"tid": task_id},
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                agent = get_agent(agent_name)
                result = await asyncio.wait_for(
                    agent.run(self.case_id),
                    timeout=TASK_TIMEOUT_SECONDS,
                )
                self.results[task_name] = result

                if result.status == "completed":
                    self.task_status[task_name] = "completed"
                    await async_gremlin_submit(
                        "g.V().has('Task', 'task_id', tid).property('status', 'completed')",
                        {"tid": task_id},
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

        # All retries exhausted
        self.task_status[task_name] = "failed"
        await async_gremlin_submit(
            "g.V().has('Task', 'task_id', tid).property('status', 'failed')",
            {"tid": task_id},
        )
        logger.error(f"[Orchestrator:{self.trace_id}] Task '{task_name}' FAILED after {self.max_retries} retries")

    async def _run_dynamic_planning(self) -> None:
        """Run the Planner agent to generate a Task DAG, then load it into task_status."""
        logger.info(f"[Orchestrator] Running dynamic planning for case {self.case_id}")

        planner = get_agent("planner_agent")
        result = await planner.run(self.case_id)
        self.results["planner"] = result

        if result.status != "completed":
            logger.warning("[Orchestrator] Planner failed, falling back to static full pipeline")
            self.dynamic = False
            self.pipeline = PIPELINE_FULL
            await self._create_task_dag()
            return

        # Load tasks written by the Planner from GDB (retry to handle write propagation delay)
        tasks = []
        for _attempt in range(3):
            tasks = await async_gremlin_submit(
                "g.V().has('Task', 'case_id', cid).valueMap(true)",
                {"cid": self.case_id},
            )
            if tasks:
                break
            await asyncio.sleep(0.5)

        if not tasks:
            logger.warning("[Orchestrator] No tasks found after planning, falling back to static pipeline")
            self.dynamic = False
            self.pipeline = PIPELINE_FULL
            await self._create_task_dag()
            return

        # Build pipeline from GDB task data
        for t in tasks:
            name = t.get("name", [""])[0] if isinstance(t.get("name"), list) else t.get("name", "")
            agent = t.get("agent_name", [""])[0] if isinstance(t.get("agent_name"), list) else t.get("agent_name", "")
            self.task_status[name] = "pending"
            # We need deps for _get_ready_tasks_dynamic
            # Store agent mapping for dispatch
            if not hasattr(self, "_dynamic_agents"):
                self._dynamic_agents: dict[str, str] = {}
            self._dynamic_agents[name] = agent

        # Load dependency info
        if not hasattr(self, "_dynamic_deps"):
            self._dynamic_deps: dict[str, list[str]] = {name: [] for name in self.task_status}
        for t in tasks:
            name = t.get("name", [""])[0] if isinstance(t.get("name"), list) else t.get("name", "")
            task_id = t.get("task_id", [""])[0] if isinstance(t.get("task_id"), list) else t.get("task_id", "")
            # Query upstream dependencies for this task
            deps = await async_gremlin_submit(
                "g.V().has('Task', 'task_id', tid).out('DEPENDS_ON').values('name')",
                {"tid": task_id},
            )
            self._dynamic_deps[name] = deps if deps else []

    def _get_ready_tasks_dynamic(self) -> list[tuple[str, str]]:
        """Get ready tasks from dynamically generated DAG."""
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

async def run_pipeline(case_id: str, pipeline_name: str = "full") -> dict[str, AgentResult]:
    """Run an agent pipeline on a case. Called as a BackgroundTask."""
    runtime = AgentRuntime(case_id, pipeline_name)
    return await runtime.run()
