"""
backend/src/agents/implementations/router.py
Router Agent (Agent 6): assign case to the correct department using
a hybrid rule-engine + LLM approach.

Pipeline:
  1. Verify MATCHES_TTHC edge exists (Classifier must have run)
  2. Fetch case metadata (region, location)
  3. Rule engine: TTHCSpec -> AUTHORIZED_FOR -> Organization
  4. Determine assignment:
     - 0 orgs -> needs_human_review
     - 1 org  -> deterministic (confidence=0.99)
     - N orgs -> LLM disambiguation
  5. Workload check: query Position vertices sorted by current_workload
  6. Write ASSIGNED_TO edge (or flag needs_human_review)
  7. Determine consult targets (rule-based: gap count, location)
  8. Write CONSULTED edges
  9. Log, broadcast, return
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from ...database import async_gremlin_submit
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.router")


class RouterAgent(BaseAgent):
    """Assign case to department using rule engine + LLM hybrid."""

    profile_name = "router_agent"

    CONFIDENCE_THRESHOLD = 0.85

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for structured routing pipeline.
        Steps: verify TTHC match -> rule engine -> determine assignment ->
               workload check -> write edges -> consult targets -> return.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Router] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # ── Step 1: Verify MATCHES_TTHC edge exists ──────────────
            tthc_match = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".out('MATCHES_TTHC').valueMap(true)",
                {"cid": case_id},
            )
            if not tthc_match:
                raise ValueError(
                    f"Case {case_id}: no MATCHES_TTHC edge found. "
                    "Classifier must run before Router."
                )

            tthc_spec = tthc_match[0]
            tthc_code = self._extract_prop(tthc_spec, "code")
            tthc_name = self._extract_prop(tthc_spec, "name")
            logger.info(f"[Router] Case {case_id} matched TTHC: {tthc_code} ({tthc_name})")

            # ── Step 2: Fetch case metadata ──────────────────────────
            case_data = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid).valueMap(true)",
                {"cid": case_id},
            )
            case_meta = case_data[0] if case_data else {}
            region = (
                self._extract_prop(case_meta, "region")
                or self._extract_prop(case_meta, "location")
            )
            location = self._extract_prop(case_meta, "location") or region

            # ── Step 3: Rule engine — find authorized organizations ──
            authorized_orgs = await async_gremlin_submit(
                "g.V().has('TTHCSpec', 'code', code)"
                ".out('AUTHORIZED_FOR').hasLabel('Organization')"
                ".valueMap(true)",
                {"code": tthc_code},
            )
            logger.info(
                f"[Router] Found {len(authorized_orgs)} authorized orgs "
                f"for TTHC {tthc_code}"
            )

            # ── Step 4: Determine assignment ─────────────────────────
            assigned_dept: dict[str, Any] | None = None
            confidence: float = 0.0
            reasoning: str = ""
            needs_human_review = False

            if len(authorized_orgs) == 0:
                # No authorized org found
                confidence = 0.0
                needs_human_review = True
                reasoning = (
                    f"Khong tim thay phong ban co tham quyen cho TTHC {tthc_code}. "
                    "Can phan cong thu cong."
                )
                logger.warning(f"[Router] No authorized org for TTHC {tthc_code}")

            elif len(authorized_orgs) == 1:
                # Single match — deterministic assignment
                org = authorized_orgs[0]
                assigned_dept = {
                    "id": self._extract_prop(org, "org_id"),
                    "name": self._extract_prop(org, "name"),
                    "level": self._extract_prop(org, "level"),
                }
                confidence = 0.99
                reasoning = (
                    f"Chi co 1 phong ban co tham quyen: {assigned_dept['name']}. "
                    "Chi dinh truc tiep (rule engine)."
                )
                logger.info(
                    f"[Router] Deterministic assignment: {assigned_dept['name']}"
                )

            else:
                # Multiple candidates — LLM disambiguation
                llm_result = await self._disambiguate_with_llm(
                    case_id, tthc_code, tthc_name, region, authorized_orgs,
                )
                assigned_dept = llm_result.get("assigned_dept")
                confidence = float(llm_result.get("confidence", 0.0))
                reasoning = llm_result.get("reasoning", "LLM disambiguation")
                needs_human_review = llm_result.get("needs_human_review", False)

                if confidence < self.CONFIDENCE_THRESHOLD:
                    needs_human_review = True

                logger.info(
                    f"[Router] LLM disambiguation: "
                    f"dept={assigned_dept.get('name') if assigned_dept else 'None'}, "
                    f"confidence={confidence:.2f}"
                )

            # ── Step 5: Workload check on assigned dept ──────────────
            suggested_handler: dict[str, Any] | None = None
            if assigned_dept and confidence >= self.CONFIDENCE_THRESHOLD:
                dept_id = assigned_dept["id"]
                try:
                    positions = await async_gremlin_submit(
                        "g.V().has('Organization', 'org_id', oid)"
                        ".in('BELONGS_TO').hasLabel('Position')"
                        ".order().by("
                        "coalesce(values('current_workload'), constant(999)), asc"
                        ").valueMap(true)",
                        {"oid": dept_id},
                    )
                    if positions:
                        top = positions[0]
                        suggested_handler = {
                            "position_id": self._extract_prop(top, "position_id"),
                            "title": self._extract_prop(top, "title"),
                            "name": self._extract_prop(top, "name"),
                            "current_workload": self._extract_int(
                                top, "current_workload", 0
                            ),
                        }
                        logger.info(
                            f"[Router] Suggested handler: {suggested_handler['name']} "
                            f"(workload={suggested_handler['current_workload']})"
                        )
                except Exception as e:
                    logger.warning(f"[Router] Workload check failed: {e}")

            # ── Step 6: Write ASSIGNED_TO edge or flag for review ────
            if assigned_dept and confidence >= self.CONFIDENCE_THRESHOLD:
                now = datetime.now(UTC).isoformat()
                await async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".addE('ASSIGNED_TO')"
                    ".to(g.V().has('Organization', 'org_id', oid))"
                    ".property('assigned_at', ts)"
                    ".property('assigned_by', agent)",
                    {
                        "cid": case_id,
                        "oid": assigned_dept["id"],
                        "ts": now,
                        "agent": "agent:Router",
                    },
                )
                logger.info(
                    f"[Router] ASSIGNED_TO edge written: "
                    f"Case {case_id} -> {assigned_dept['name']}"
                )
            else:
                needs_human_review = True
                await async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".property('routing_status', status)",
                    {"cid": case_id, "status": "needs_human_review"},
                )
                logger.info(
                    f"[Router] Flagged for human review: Case {case_id} "
                    f"(confidence={confidence:.2f})"
                )

            # ── Step 7: Determine consult targets ────────────────────
            consult_targets = await self._determine_consult_targets(
                case_id, location,
            )

            # ── Step 8: Write CONSULTED edges ────────────────────────
            for target in consult_targets:
                try:
                    await async_gremlin_submit(
                        "g.V().has('Case', 'case_id', cid)"
                        ".addE('CONSULTED')"
                        ".to(g.V().has('Organization', 'org_id', oid))"
                        ".property('reason', reason)"
                        ".property('suggested_by', agent)",
                        {
                            "cid": case_id,
                            "oid": target["id"],
                            "reason": target["reason"],
                            "agent": "agent:Router",
                        },
                    )
                except Exception as e:
                    logger.warning(
                        f"[Router] Failed to write CONSULTED edge "
                        f"to {target['name']}: {e}"
                    )

            # ── Step 9: Build output, log, broadcast ─────────────────
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_router",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "assigned_dept": assigned_dept,
                "confidence": confidence,
                "needs_human_review": needs_human_review,
                "reasoning": reasoning,
                "suggested_handler": suggested_handler,
                "consult_targets": consult_targets,
                "tthc_code": tthc_code,
                "tthc_name": tthc_name,
            }

            output_summary = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "assigned_dept": assigned_dept.get("name") if assigned_dept else None,
                "confidence": confidence,
                "consult_count": len(consult_targets),
                "needs_human_review": needs_human_review,
                "duration_ms": round(duration_ms),
            })

            logger.info(
                f"[Router] Case {case_id}: "
                f"dept={assigned_dept.get('name') if assigned_dept else 'None'}, "
                f"confidence={confidence:.2f}, "
                f"consults={len(consult_targets)}, "
                f"duration={round(duration_ms)}ms"
            )

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
            logger.error(f"[Router] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_router",
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

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    async def _disambiguate_with_llm(
        self,
        case_id: str,
        tthc_code: str,
        tthc_name: str,
        region: str,
        authorized_orgs: list[dict],
    ) -> dict[str, Any]:
        """
        Use Qwen3-Max to choose between multiple authorized departments.
        Retry once on JSON parse failure.
        """
        candidate_depts = []
        for org in authorized_orgs:
            candidate_depts.append({
                "id": self._extract_prop(org, "org_id"),
                "name": self._extract_prop(org, "name"),
                "level": self._extract_prop(org, "level"),
                "scope_regions": self._extract_prop(org, "scope_regions"),
            })

        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "case_id": case_id,
                    "tthc_code": tthc_code,
                    "tthc_name": tthc_name,
                    "region": region,
                    "candidate_departments": candidate_depts,
                    "instruction": (
                        "Chon 1 phong ban xu ly chinh tu danh sach tren. "
                        "Tra ve JSON voi format: "
                        '{"assigned_dept": {"id": "...", "name": "..."}, '
                        '"confidence": 0.XX, "reasoning": "..."}'
                    ),
                }, ensure_ascii=False),
            },
        ]

        for attempt in range(2):
            completion = await self.client.chat(
                messages=messages,
                model=self.profile.model,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            content = completion.choices[0].message.content or ""

            # Strip markdown fences if present
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

            try:
                result = json.loads(cleaned)
                # Validate structure
                if "assigned_dept" not in result:
                    result["assigned_dept"] = None
                if "confidence" not in result:
                    result["confidence"] = 0.0
                return result
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning(
                        "[Router] Invalid JSON from Qwen, retrying with stricter prompt"
                    )
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Tra lai DUNG FORMAT: "
                            '{"assigned_dept": {"id": "...", "name": "..."}, '
                            '"confidence": 0.XX, "reasoning": "..."}'
                        ),
                    })
                else:
                    logger.error(
                        f"[Router] JSON parse failed after retry: {content[:200]}"
                    )
                    return {
                        "assigned_dept": None,
                        "confidence": 0.0,
                        "needs_human_review": True,
                        "reasoning": "LLM JSON parse failed, requires manual routing",
                    }

        # Unreachable but satisfies type checker
        return {"assigned_dept": None, "confidence": 0.0, "needs_human_review": True}

    async def _determine_consult_targets(
        self,
        case_id: str,
        location: str,
    ) -> list[dict[str, str]]:
        """
        Determine which departments should be consulted based on rules.
        Rules:
          - gap_count >= 2 -> Phong Phap che (legal complexity)
          - location in KCN -> Phong Quy hoach (planning)
        """
        targets: list[dict[str, str]] = []

        # Rule 1: Legal complexity — check gap count
        try:
            gap_result = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid).out('HAS_GAP').count()",
                {"cid": case_id},
            )
            gap_count = int(gap_result[0]) if gap_result else 0
        except Exception:
            gap_count = 0

        if gap_count >= 2:
            targets.append({
                "id": "dept_phap_che",
                "name": "Phong Phap che",
                "reason": (
                    f"Ho so co {gap_count} thieu sot phap ly, "
                    "can y kien phong Phap che"
                ),
            })

        # Rule 2: Location in KCN -> Phong Quy hoach
        location_lower = location.lower() if location else ""
        if "kcn" in location_lower or "khu cong nghiep" in location_lower:
            targets.append({
                "id": "dept_quy_hoach",
                "name": "Phong Quy hoach",
                "reason": "Cong trinh trong khu cong nghiep, can y kien Quy hoach",
            })

        return targets

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""

    @staticmethod
    def _extract_int(vertex_map: dict, key: str, default: int = 0) -> int:
        """Extract an integer property from Gremlin valueMap result."""
        val = vertex_map.get(key, default)
        if isinstance(val, list):
            val = val[0] if val else default
        try:
            return int(val)
        except (TypeError, ValueError):
            return default


# Register with orchestrator
register_agent("router_agent", RouterAgent)
