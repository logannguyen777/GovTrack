"""
backend/src/agents/implementations/planner.py
Planner Agent: generates a dynamic Task DAG for each incoming case.
Reads case metadata + TTHC spec, calls Qwen3-Max for structured plan,
writes Task vertices + DEPENDS_ON edges to the Context Graph.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import deque
from typing import Any

# async_gremlin_submit replaced by self._get_gdb().execute() per task 1.1
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.planner")


class PlannerInvalidDAG(ValueError):
    """Raised when the LLM-generated task DAG contains invalid dependencies or cycles."""


class PlannerAgent(BaseAgent):
    """Generate Task DAG for a new case."""

    profile_name = "planner_agent"

    KNOWN_TASK_NAMES: set[str] = {
        "doc_analyze",
        "classify",
        "security_scan_initial",
        "compliance_check",
        "legal_lookup",
        "route",
        "summarize",
        "draft_notice_if_gap",
    }

    TASK_TO_AGENT: dict[str, str] = {
        "doc_analyze": "doc_analyze_agent",
        "classify": "classifier_agent",
        "security_scan_initial": "security_officer_agent",
        "compliance_check": "compliance_agent",
        "legal_lookup": "legal_search_agent",
        "route": "router_agent",
        "summarize": "summary_agent",
        "draft_notice_if_gap": "draft_agent",
    }

    SENSITIVE_KEYWORDS: list[str] = [
        "quoc phong", "mat", "ngoai giao", "an ninh", "quan su",
    ]

    DEFAULT_PLANS: dict[str, list[dict[str, Any]]] = {
        "xay_dung": [
            {"name": "doc_analyze", "agent": "doc_analyze_agent", "depends_on": [], "priority": "high", "conditional": None},
            {"name": "security_scan_initial", "agent": "security_officer_agent", "depends_on": [], "priority": "high", "conditional": None},
            {"name": "classify", "agent": "classifier_agent", "depends_on": ["doc_analyze"], "priority": "high", "conditional": None},
            {"name": "compliance_check", "agent": "compliance_agent", "depends_on": ["classify", "doc_analyze"], "priority": "high", "conditional": None},
            {"name": "legal_lookup", "agent": "legal_search_agent", "depends_on": ["compliance_check"], "priority": "normal", "conditional": None},
            {"name": "route", "agent": "router_agent", "depends_on": ["classify"], "priority": "normal", "conditional": None},
            {"name": "summarize", "agent": "summary_agent", "depends_on": ["compliance_check", "legal_lookup"], "priority": "normal", "conditional": None},
            {"name": "draft_notice_if_gap", "agent": "draft_agent", "depends_on": ["compliance_check"], "priority": "normal", "conditional": "has_gaps"},
        ],
        "_default": [
            {"name": "doc_analyze", "agent": "doc_analyze_agent", "depends_on": [], "priority": "normal", "conditional": None},
            {"name": "security_scan_initial", "agent": "security_officer_agent", "depends_on": [], "priority": "normal", "conditional": None},
            {"name": "classify", "agent": "classifier_agent", "depends_on": ["doc_analyze"], "priority": "normal", "conditional": None},
            {"name": "compliance_check", "agent": "compliance_agent", "depends_on": ["classify", "doc_analyze"], "priority": "normal", "conditional": None},
            {"name": "legal_lookup", "agent": "legal_search_agent", "depends_on": ["compliance_check"], "priority": "normal", "conditional": None},
            {"name": "route", "agent": "router_agent", "depends_on": ["classify"], "priority": "normal", "conditional": None},
            {"name": "summarize", "agent": "summary_agent", "depends_on": ["compliance_check", "legal_lookup"], "priority": "normal", "conditional": None},
            {"name": "draft_notice_if_gap", "agent": "draft_agent", "depends_on": ["compliance_check"], "priority": "normal", "conditional": "has_gaps"},
        ],
    }

    def __init__(self, profile_name: str | None = None):
        super().__init__(profile_name)
        self._case_meta: dict[str, Any] = {}
        self._documents: list[dict[str, Any]] = []
        self._tthc_spec: dict[str, Any] = {}

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Build system + user messages with case context for plan generation."""
        doc_names = []
        for d in self._documents:
            filename = d.get("filename", d.get("name", ["unknown"]))
            if isinstance(filename, list):
                filename = filename[0] if filename else "unknown"
            doc_names.append(filename)

        # Extract case title for sensitive keyword detection
        case_title = ""
        if self._case_meta:
            title_val = self._case_meta.get("title", self._case_meta.get("code", ""))
            if isinstance(title_val, list):
                case_title = title_val[0] if title_val else ""
            else:
                case_title = str(title_val)

        user_content = json.dumps({
            "case_id": case_id,
            "case_title": case_title,
            "case_status": self._extract_prop(self._case_meta, "status"),
            "urgency": self._extract_prop(self._case_meta, "urgency"),
            "document_count": len(self._documents),
            "document_names": doc_names,
            "tthc_code": self._extract_prop(self._tthc_spec, "code"),
            "tthc_name": self._extract_prop(self._tthc_spec, "name"),
            "tthc_category": self._extract_prop(self._tthc_spec, "category"),
            "instruction": "Phan tich va tao execution plan cho case nay.",
        }, ensure_ascii=False)

        return [
            {"role": "system", "content": self.profile.system_prompt},
            {"role": "user", "content": user_content},
        ]

    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for single-call structured planning.
        Steps: fetch context → call Qwen once → validate → write DAG to GDB.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Planner] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # Step 1: Fetch case metadata
            case_data = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid).valueMap(true)",
                {"cid": case_id},
            )
            self._case_meta = case_data[0] if case_data else {}

            # Step 2: Fetch documents
            self._documents = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                ".valueMap(true)",
                {"cid": case_id},
            )

            # Step 3: Fetch TTHC spec if available
            tthc_code = self._extract_prop(self._case_meta, "tthc_code")
            self._tthc_spec = {}
            if tthc_code:
                specs = await self._get_gdb().execute(
                    "g.V().has('TTHCSpec', 'code', code).valueMap(true)",
                    {"code": tthc_code},
                )
                if specs:
                    self._tthc_spec = specs[0]

            # Step 4: Build messages and call Qwen
            messages = await self.build_messages(case_id)
            plan = await self._call_qwen_for_plan(messages)

            # Step 5: Validate plan
            plan = self._validate_plan(plan)

            # Step 6: Confidence check
            confidence = plan.get("confidence", 1.0)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except ValueError:
                    confidence = 0.0

            fallback_used = False
            if confidence < 0.6:
                category = self._guess_category(self._case_meta, self._tthc_spec)
                plan["tasks"] = self.DEFAULT_PLANS.get(category, self.DEFAULT_PLANS["_default"])
                plan["fallback_used"] = True
                fallback_used = True
                logger.warning(
                    f"[Planner] Low confidence {confidence:.2f}, "
                    f"using default plan for category={category}"
                )

            # Step 7: Cycle/closure detection — fall back to default on any DAG error
            try:
                self._detect_cycles(plan.get("tasks", []))
            except PlannerInvalidDAG as dag_err:
                category = self._guess_category(self._case_meta, self._tthc_spec)
                plan["tasks"] = self.DEFAULT_PLANS.get(category, self.DEFAULT_PLANS["_default"])
                plan["fallback_used"] = True
                fallback_used = True
                logger.warning(f"[Planner] Invalid DAG: {dag_err}. Using default plan.")

            # Step 8: Apply sensitive keyword escalation
            plan = self._apply_sensitivity_escalation(plan, case_id)

            # Step 9: Write Task vertices to GDB
            tasks = plan.get("tasks", [])
            task_ids: dict[str, str] = {}

            for t in tasks:
                task_id = f"{case_id}:{t['name']}"
                await self._get_gdb().execute(
                    "g.addV('Task')"
                    ".property('task_id', tid).property('name', name)"
                    ".property('agent_name', agent).property('case_id', cid)"
                    ".property('priority', pri).property('status', 'pending')"
                    ".property('conditional', cond)",
                    {
                        "tid": task_id,
                        "name": t["name"],
                        "agent": t["agent"],
                        "cid": case_id,
                        "pri": t.get("priority", "normal"),
                        "cond": t.get("conditional") or "",
                    },
                )
                task_ids[t["name"]] = task_id

            # Step 10: Write DEPENDS_ON edges
            for t in tasks:
                for dep_name in t.get("depends_on", []):
                    if dep_name in task_ids:
                        await self._get_gdb().execute(
                            "g.V().has('Task', 'task_id', downstream)"
                            ".addE('DEPENDS_ON')"
                            ".to(__.V().has('Task', 'task_id', upstream))",
                            {
                                "downstream": task_ids[t["name"]],
                                "upstream": task_ids[dep_name],
                            },
                        )

            # Step 11: Log and broadcast
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_planner",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_summary = json.dumps({
                "task_count": len(tasks),
                "task_names": list(task_ids.keys()),
                "priority": plan.get("priority", "normal"),
                "fallback_used": fallback_used,
                "confidence": confidence,
                "reasoning": plan.get("reasoning", ""),
            }, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "task_count": len(tasks),
                "duration_ms": round(duration_ms),
            })

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=output_summary,
                tool_calls_count=0,
                usage=usage,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[Planner] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_planner",
                usage=self.client.reset_usage(),
                duration_ms=duration_ms,
                status="failed",
                error=str(e),
            )

            await self._broadcast(case_id, "agent_failed", {
                "agent_name": self.profile.name,
                "error": str(e),
            })

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                duration_ms=duration_ms,
                error=str(e),
            )

    async def _call_qwen_for_plan(self, messages: list[dict]) -> dict:
        """Call Qwen3-Max once for structured JSON plan output. Retry on parse error."""
        for attempt in range(2):
            completion = await self.client.chat(
                messages=messages,
                model=self.profile.model,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            content = completion.choices[0].message.content or ""

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning("[Planner] Invalid JSON from Qwen, retrying with stricter prompt")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Hay tra lai DUNG FORMAT JSON. "
                            "Khong markdown, khong comment. Chi JSON thuan tuy."
                        ),
                    })
                else:
                    logger.error("[Planner] JSON parse failed after retry, using default plan")
                    return {"tasks": [], "confidence": 0.0, "priority": "normal", "reasoning": "JSON parse failed"}

        return {"tasks": [], "confidence": 0.0, "priority": "normal", "reasoning": "unreachable"}

    def _validate_plan(self, plan: dict) -> dict:
        """Validate and normalize the plan from Qwen output."""
        tasks = plan.get("tasks", [])
        valid_tasks = []

        for t in tasks:
            if not isinstance(t, dict):
                continue
            name = t.get("name", "")
            if name not in self.KNOWN_TASK_NAMES:
                logger.warning(f"[Planner] Stripping unknown task: {name}")
                continue

            # Normalize agent name
            agent = t.get("agent", "")
            if agent not in self.TASK_TO_AGENT.values():
                agent = self.TASK_TO_AGENT.get(name, agent)

            # Validate depends_on references
            valid_deps = [d for d in t.get("depends_on", []) if d in self.KNOWN_TASK_NAMES]

            valid_tasks.append({
                "name": name,
                "agent": agent,
                "depends_on": valid_deps,
                "priority": t.get("priority", "normal"),
                "conditional": t.get("conditional"),
            })

        plan["tasks"] = valid_tasks
        return plan

    @classmethod
    def _detect_cycles(cls, tasks: list[dict]) -> bool:
        """
        Detect cycles in the task DAG using Kahn's algorithm.

        Also validates closure: every ``depends_on`` entry must refer to a
        task that exists in *both* ``KNOWN_TASK_NAMES`` **and** the current
        plan's own task list.  Unknown references raise ``PlannerInvalidDAG``.

        Raises:
            PlannerInvalidDAG: if an unknown dependency is found, or if a
                cycle is present (unreachable tasks after Kahn).

        Returns:
            True  – never (raises instead); kept as bool for legacy callers
                    that check the return value.
            False – DAG is valid (no cycles, closure satisfied).
        """
        if not tasks:
            return False

        task_names = {t["name"] for t in tasks}

        # ── Closure check ────────────────────────────────────────
        for t in tasks:
            for dep in t.get("depends_on", []):
                if dep not in cls.KNOWN_TASK_NAMES:
                    raise PlannerInvalidDAG(
                        f"Task '{t['name']}' depends on unknown task '{dep}' "
                        f"(not in KNOWN_TASK_NAMES)"
                    )
                if dep not in task_names:
                    raise PlannerInvalidDAG(
                        f"Task '{t['name']}' depends on '{dep}' "
                        f"which is not present in this plan's task list"
                    )

        # ── Kahn's BFS cycle detection ───────────────────────────
        in_degree: dict[str, int] = {t["name"]: 0 for t in tasks}
        adjacency: dict[str, list[str]] = {t["name"]: [] for t in tasks}

        for t in tasks:
            for dep in t.get("depends_on", []):
                if dep in task_names:
                    adjacency[dep].append(t["name"])
                    in_degree[t["name"]] += 1

        queue = deque([name for name, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(task_names):
            unvisited = [n for n in task_names if in_degree.get(n, 0) > 0]
            raise PlannerInvalidDAG(
                f"Cycle detected: unvisited tasks {unvisited}"
            )

        return False  # DAG is valid

    def _guess_category(self, case_meta: dict, tthc_spec: dict) -> str:
        """Determine category for DEFAULT_PLANS fallback selection."""
        # Try TTHC spec category first
        category = self._extract_prop(tthc_spec, "category")
        if category and category in self.DEFAULT_PLANS:
            return category

        # Heuristic: many documents suggests construction permit
        if len(self._documents) >= 4:
            return "xay_dung"

        return "_default"

    def _apply_sensitivity_escalation(self, plan: dict, case_id: str) -> dict:
        """Escalate security_scan_initial priority if sensitive keywords detected."""
        case_title = self._extract_prop(self._case_meta, "title") or ""
        case_code = self._extract_prop(self._case_meta, "code") or ""
        text_to_check = f"{case_title} {case_code}".lower()

        is_sensitive = any(kw in text_to_check for kw in self.SENSITIVE_KEYWORDS)
        if is_sensitive:
            plan["priority"] = "critical"
            for t in plan.get("tasks", []):
                if t["name"] == "security_scan_initial":
                    t["priority"] = "critical"
            logger.info(f"[Planner] Sensitive keywords detected for case {case_id}, escalating priority")

        return plan

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""


# Register with orchestrator
register_agent("planner_agent", PlannerAgent)
