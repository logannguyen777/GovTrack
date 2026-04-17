"""
backend/src/agents/implementations/dispatch_router.py
DispatchRouterAgent (Agent 11): phân phối công văn nội bộ đến các phòng ban.

Pipeline:
  1. Load case context (subject_tags, clearance_level, explicit recipients)
  2. If explicit recipients -> use directly (skip LLM)
  3. Else: call Qwen3-Max to determine recipient departments
  4. Filter by clearance: dept.max_clearance_level >= case clearance
  5. Write DispatchLog vertex + DISPATCHED_TO edge per recipient
  6. Emit WS event per dispatch for live fan-out visualization
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.dispatch_router")

# Candidate departments for dispatch (injected at demo time or loaded from GDB)
_DEFAULT_DEPT_CANDIDATES = [
    {"dept_id": "dept-phap-che", "name": "Phòng Pháp chế"},
    {"dept_id": "dept-hanh-chinh", "name": "Phòng Hành chính - Tổng hợp"},
    {"dept_id": "dept-ke-hoach", "name": "Phòng Kế hoạch - Tài chính"},
    {"dept_id": "dept-ky-thuat", "name": "Phòng Kỹ thuật - Nghiệp vụ"},
    {"dept_id": "dept-lien-quan", "name": "Phòng Liên quan"},
]


class DispatchRouterAgent(BaseAgent):
    """Phân phối công văn nội bộ đến các phòng ban phù hợp."""

    profile_name = "dispatch_router_agent"

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC — not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    async def run(self, case_id: str) -> AgentResult:
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[DispatchRouter] Starting on case {case_id}")
        await self._broadcast(
            case_id,
            "agent_started",
            {
                "agent_name": self.profile.name,
                "step_id": step_id,
            },
        )

        try:
            # 1. Load case context
            case_rows = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid).valueMap(true)",
                {"cid": case_id},
            )
            case_data = case_rows[0] if case_rows else {}

            subject_tags_raw = self._extract_prop(case_data, "subject_tags") or "[]"
            try:
                subject_tags: list[str] = json.loads(subject_tags_raw)
            except (json.JSONDecodeError, ValueError):
                subject_tags = []

            clearance_str = self._extract_prop(case_data, "current_classification") or "0"
            try:
                case_clearance = int(clearance_str)
            except ValueError:
                case_clearance = 0

            doc_summary = self._extract_prop(case_data, "document_summary") or ""
            explicit_recipients_raw = self._extract_prop(case_data, "explicit_recipients") or "[]"
            try:
                explicit_recipients: list[str] = json.loads(explicit_recipients_raw)
            except (json.JSONDecodeError, ValueError):
                explicit_recipients = []

            # 2. Load candidate organizations from GDB
            org_rows = await self._get_gdb().execute(
                "g.V().hasLabel('Organization').valueMap(true).limit(20)",
                {},
            )
            dept_candidates: list[dict[str, str]] = []
            for org in org_rows:
                oid = self._extract_prop(org, "org_id")
                oname = self._extract_prop(org, "name")
                if oid and oname:
                    dept_candidates.append({"dept_id": oid, "name": oname})

            if not dept_candidates:
                dept_candidates = list(_DEFAULT_DEPT_CANDIDATES)

            # 3. Determine recipients
            if explicit_recipients:
                logger.info(
                    f"[DispatchRouter] Using {len(explicit_recipients)} explicit recipients"
                )
                recipients = [
                    {
                        "dept_id": did,
                        "dept_name": did,
                        "confidence": 1.0,
                        "rationale": "Người nhận được chỉ định rõ ràng",
                    }
                    for did in explicit_recipients
                ]
            else:
                recipients = await self._llm_determine_recipients(
                    case_id,
                    subject_tags,
                    doc_summary,
                    dept_candidates,
                )

            # 4. Filter by clearance
            cleared_recipients = await self._filter_by_clearance(recipients, case_clearance)

            if not cleared_recipients:
                logger.warning(
                    f"[DispatchRouter] All recipients filtered out by clearance {case_clearance}"
                )
                cleared_recipients = recipients[:1] if recipients else []

            # 5. Write DispatchLog vertices + DISPATCHED_TO edges
            now = datetime.now(UTC).isoformat()
            dispatch_logs: list[dict[str, Any]] = []

            for rec in cleared_recipients:
                log_id = f"dl-{case_id}-{uuid.uuid4().hex[:8]}"
                dept_id = rec.get("dept_id", "")
                dept_name = rec.get("dept_name", dept_id)
                confidence = float(rec.get("confidence", 0.8))
                rationale = rec.get("rationale", "")

                await self._get_gdb().execute(
                    "g.addV('DispatchLog')"
                    ".property('log_id', lid)"
                    ".property('case_id', cid)"
                    ".property('dept_id', did)"
                    ".property('dept_name', dname)"
                    ".property('sent_at', ts)"
                    ".property('status', 'pending')"
                    ".property('confidence', conf)"
                    ".property('rationale', rat)"
                    ".as('dl')"
                    ".V().has('Case', 'case_id', cid)"
                    ".addE('DISPATCHED_TO').to('dl')"
                    ".property('sent_at', ts)"
                    ".property('status', 'pending')"
                    ".property('confidence', conf)"
                    ".property('rationale', rat)",
                    {
                        "lid": log_id,
                        "cid": case_id,
                        "did": dept_id,
                        "dname": dept_name,
                        "ts": now,
                        "conf": str(confidence),
                        "rat": rationale,
                    },
                )

                dispatch_logs.append(
                    {
                        "log_id": log_id,
                        "dept_id": dept_id,
                        "dept_name": dept_name,
                        "confidence": confidence,
                        "rationale": rationale,
                        "sent_at": now,
                    }
                )

                # 6. Emit WS event per dispatch for live fan-out
                try:
                    from ...api.ws import broadcast

                    await broadcast(
                        f"case:{case_id}",
                        {
                            "type": "dispatch_sent",
                            "log_id": log_id,
                            "dept_id": dept_id,
                            "dept_name": dept_name,
                            "confidence": confidence,
                        },
                    )
                except Exception as exc:
                    logger.debug(f"[DispatchRouter] WS broadcast failed: {exc}")

            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_dispatch_router",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )
            await self._broadcast(
                case_id,
                "agent_completed",
                {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "dispatch_count": len(dispatch_logs),
                    "duration_ms": round(duration_ms),
                },
            )

            logger.info(
                f"[DispatchRouter] Case {case_id}: dispatched to "
                f"{len(dispatch_logs)} departments, duration={round(duration_ms)}ms"
            )

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=json.dumps(
                    {
                        "dispatch_count": len(dispatch_logs),
                        "dispatch_logs": dispatch_logs,
                    },
                    ensure_ascii=False,
                ),
                tool_calls_count=0,
                usage=usage,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[DispatchRouter] Failed: {exc}", exc_info=True)
            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_dispatch_router",
                usage=self.client.reset_usage(),
                duration_ms=duration_ms,
                status="failed",
                error=str(exc),
            )
            await self._broadcast(
                case_id,
                "agent_failed",
                {
                    "agent_name": self.profile.name,
                    "error": str(exc),
                },
            )
            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                duration_ms=duration_ms,
                error=str(exc),
            )

    # ── Private methods ─────────────────────────────────────────

    async def _llm_determine_recipients(
        self,
        case_id: str,
        subject_tags: list[str],
        doc_summary: str,
        dept_candidates: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Use Qwen3-Max to determine which departments should receive the dispatch."""
        dept_list_str = "\n".join(f"- {d['dept_id']}: {d['name']}" for d in dept_candidates[:10])
        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case_id": case_id,
                        "subject_tags": subject_tags,
                        "document_summary": doc_summary or "Công văn nội bộ",
                        "available_departments": dept_list_str,
                        "instruction": (
                            "Công văn này nên gửi phòng ban nào trong các phòng trên? "
                            "Trả về JSON danh sách người nhận với dept_id, dept_name, "
                            "confidence (0-1), rationale. "
                            "Chỉ chọn các phòng ban thực sự liên quan. Tối đa 5 phòng ban."
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        for attempt in range(2):
            completion = await self.client.chat(
                messages=messages,
                model=self.profile.model,
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content or ""
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
            try:
                parsed = json.loads(cleaned)
                recs = parsed.get("recipients", [])
                if not isinstance(recs, list):
                    recs = []
                return recs[:5]
            except json.JSONDecodeError:
                if attempt == 1:
                    logger.warning(
                        "[DispatchRouter] LLM JSON parse failed, using fallback recipients"
                    )
                    # Fallback: return first 2 candidates with medium confidence
                    return [
                        {
                            "dept_id": d["dept_id"],
                            "dept_name": d["name"],
                            "confidence": 0.6,
                            "rationale": "Phân phối mặc định (LLM không phản hồi đúng định dạng)",
                        }
                        for d in dept_candidates[:2]
                    ]

        return []

    async def _filter_by_clearance(
        self,
        recipients: list[dict[str, Any]],
        case_clearance: int,
    ) -> list[dict[str, Any]]:
        """
        Filter recipients: dept.max_clearance_level >= case_clearance.
        If dept has no max_clearance_level property, allow by default.
        """
        if case_clearance == 0:
            return recipients  # Unclassified — no restriction

        cleared: list[dict[str, Any]] = []
        for rec in recipients:
            dept_id = rec.get("dept_id", "")
            try:
                rows = await self._get_gdb().execute(
                    "g.V().has('Organization', 'org_id', oid).values('max_clearance_level')",
                    {"oid": dept_id},
                )
                if rows:
                    first = rows[0]
                    max_cl = (
                        first.get("value", case_clearance) if isinstance(first, dict) else first
                    )
                    max_cl = int(max_cl) if max_cl is not None else case_clearance
                    if max_cl >= case_clearance:
                        cleared.append(rec)
                else:
                    # No clearance property — allow by default
                    cleared.append(rec)
            except Exception:
                cleared.append(rec)  # Fail-open

        return cleared

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""


# Register with orchestrator
register_agent("dispatch_router_agent", DispatchRouterAgent)
