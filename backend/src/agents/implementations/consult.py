"""
backend/src/agents/implementations/consult.py
Consult Agent (Agent 7): auto-draft cross-department consultation requests
and aggregate opinions after departments respond.

Pipeline (run):
  1. Get CONSULTED edges from Router
  2. Get case context (summary + gaps + citations)
  3. For each target: LLM drafts consult request
  4. PII scan on generated content
  5. Write ConsultRequest vertex + HAS_CONSULT_REQUEST edge
  6. Update case status to 'consultation'

Pipeline (aggregate_opinions):
  1. Get all opinions for a consult request
  2. LLM aggregates: consensus, dissenting views, recommendation
  3. Write Opinion vertex + HAS_OPINION from ConsultRequest
  4. Update ConsultRequest status to 'completed'
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ...database import async_gremlin_submit
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.consult")

# PII patterns for Vietnamese identity documents and phone numbers
_CCCD_PATTERN = re.compile(
    r"(?:CCCD|CMND|CMT|[Ss]o [Dd]inh [Dd]anh|[Ss]o [Cc]an [Cc]uoc)\s*:?\s*\d{9,12}"
)
_PHONE_PATTERN = re.compile(
    r"(?:SDT|[Ss]o [Dd]ien [Tt]hoai|[Dd]ien thoai|DT)\s*:?\s*0[3579]\d{8}"
)
_BARE_ID_PATTERN = re.compile(r"\b0\d{11}\b")  # 12-digit IDs starting with 0
_BARE_PHONE_PATTERN = re.compile(r"\b0[3579]\d{8}\b")
_ADDRESS_DETAIL_PATTERN = re.compile(
    r"(?:[Ss]o nha|[Dd]uong|[Pp]huong|[Qq]uan|[Hh]uyen)\s+[\w\s,]{5,50}"
)


class ConsultAgent(BaseAgent):
    """Auto-draft cross-department consultation requests and aggregate opinions."""

    profile_name = "consult_agent"
    DEFAULT_DEADLINE_DAYS = 2

    # ── ABC stub ────────────────────────────────────────────────
    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    # ── Main entry point ────────────────────────────────────────
    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for structured consult pipeline.
        Draft consult requests for all CONSULTED targets set by Router.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Consult] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # ── Step 1: Get consult targets from Router ─────────
            raw_targets = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".outE('CONSULTED').as('e').inV().as('org')"
                ".select('e', 'org').by(valueMap()).by(valueMap(true))",
                {"cid": case_id},
            )

            targets = self._parse_consult_targets(raw_targets)

            if not targets:
                logger.info(f"[Consult] No consult targets for case {case_id}")
                duration_ms = (time.monotonic() - start_time) * 1000
                usage = self.client.reset_usage()

                await self._log_step(
                    step_id=step_id, case_id=case_id,
                    action="pipeline_consult_drafter",
                    usage=usage, duration_ms=duration_ms,
                    status="completed",
                )
                await self._broadcast(case_id, "agent_completed", {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "consult_requests_count": 0,
                    "duration_ms": round(duration_ms),
                })

                output = json.dumps({
                    "consult_requests_count": 0,
                    "reason": "no_consult_targets",
                }, ensure_ascii=False)

                return AgentResult(
                    agent_name=self.profile.name,
                    case_id=case_id,
                    status="completed",
                    output=output,
                    usage=usage,
                    duration_ms=duration_ms,
                )

            logger.info(
                f"[Consult] Found {len(targets)} consult targets for case {case_id}"
            )

            # ── Step 2: Get case context ────────────────────────
            context_result = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".project('case', 'gaps', 'citations')"
                ".by(valueMap(true))"
                ".by(out('HAS_GAP').valueMap(true).fold())"
                ".by(out('HAS_GAP').out('CITES').valueMap(true).fold())",
                {"cid": case_id},
            )

            case_context = context_result[0] if context_result else {
                "case": {}, "gaps": [], "citations": [],
            }

            # Get TTHC name via MATCHES_TTHC
            tthc_match = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".out('MATCHES_TTHC').valueMap(true)",
                {"cid": case_id},
            )
            tthc_name = ""
            if tthc_match:
                tthc_name = self._extract_prop(tthc_match[0], "name")

            # ── Step 3: Draft consult request for each target ───
            requests = []
            for target in targets:
                try:
                    req = await self._draft_consult_request(
                        case_id, case_context, tthc_name, target,
                    )
                    requests.append(req)
                except Exception as e:
                    logger.error(
                        f"[Consult] Failed to draft request for "
                        f"{target.get('name', 'unknown')}: {e}",
                        exc_info=True,
                    )

            # ── Step 4: Update case status ──────────────────────
            if requests:
                await async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".property('status', status)",
                    {"cid": case_id, "status": "consultation"},
                )

            # ── Step 5: Build output, log, broadcast ────────────
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_consult_drafter",
                usage=usage, duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "consult_requests_count": len(requests),
                "consult_requests": requests,
                "tthc_name": tthc_name,
            }
            output_summary = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "consult_requests_count": len(requests),
                "targets": [r.get("target") for r in requests],
                "duration_ms": round(duration_ms),
            })

            logger.info(
                f"[Consult] Case {case_id}: "
                f"created {len(requests)} consult requests, "
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
            logger.error(f"[Consult] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_consult_drafter",
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

    # ── Opinion aggregation (called externally) ─────────────────
    async def aggregate_opinions(
        self,
        case_id: str,
        consult_request_id: str,
    ) -> AgentResult:
        """
        Aggregate opinions after departments respond.
        Called via API endpoint when all opinions are received.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(
            f"[Consult] Aggregating opinions for request {consult_request_id}"
        )
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
            "action": "aggregate_opinions",
        })

        try:
            # Get all opinions for this consult request
            opinions = await async_gremlin_submit(
                "g.V().has('ConsultRequest', 'request_id', req_id)"
                ".out('HAS_OPINION').has('aggregated', false)"
                ".valueMap(true)",
                {"req_id": consult_request_id},
            )

            if not opinions:
                logger.info(
                    f"[Consult] No opinions yet for request {consult_request_id}"
                )
                duration_ms = (time.monotonic() - start_time) * 1000
                usage = self.client.reset_usage()

                await self._log_step(
                    step_id=step_id, case_id=case_id,
                    action="aggregate_opinions",
                    usage=usage, duration_ms=duration_ms,
                    status="completed",
                )

                output = json.dumps({"status": "no_opinions_yet"})
                return AgentResult(
                    agent_name=self.profile.name,
                    case_id=case_id,
                    status="completed",
                    output=output,
                    usage=usage,
                    duration_ms=duration_ms,
                )

            # Get original ConsultRequest for context
            request_data = await async_gremlin_submit(
                "g.V().has('ConsultRequest', 'request_id', req_id).valueMap(true)",
                {"req_id": consult_request_id},
            )
            request = request_data[0] if request_data else {}

            # LLM aggregation
            opinion_summaries = []
            for op in opinions:
                opinion_summaries.append({
                    "source": self._extract_prop(op, "source_org_name"),
                    "content": self._extract_prop(op, "content"),
                    "verdict": self._extract_prop(op, "verdict"),
                })

            messages = [
                {
                    "role": "system",
                    "content": (
                        "Tong hop y kien tu cac phong ban. "
                        "Giu nguyen y nghia, neu ro dong thuan hay bat dong. "
                        "Tra ve JSON: {\"aggregated_opinion\": \"...\", "
                        "\"consensus\": true/false, "
                        "\"dissenting_views\": [...], "
                        "\"recommendation\": \"...\"}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "original_question": self._extract_prop(
                            request, "main_question",
                        ),
                        "context_summary": self._extract_prop(
                            request, "context_summary",
                        ),
                        "opinions": opinion_summaries,
                        "instruction": (
                            "Tong hop cac y kien tren. "
                            "Xac dinh dong thuan hay bat dong. "
                            "Neu de xuat hanh dong tiep theo."
                        ),
                    }, ensure_ascii=False),
                },
            ]

            aggregation = await self._llm_json_call(
                messages, temperature=0.2, max_tokens=2048,
            )

            # Write aggregated Opinion vertex
            op_id = f"agg-{consult_request_id}-{uuid.uuid4().hex[:8]}"
            now = datetime.now(UTC).isoformat()

            await async_gremlin_submit(
                "g.addV('Opinion')"
                ".property('opinion_id', op_id).property('agent_name', agent)"
                ".property('verdict', verdict).property('reasoning', reasoning)"
                ".property('confidence', conf).property('consensus', consensus)"
                ".property('recommendation', rec).property('opinion_count', cnt)"
                ".property('aggregated', agg).property('created_at', ts)"
                ".as('op')"
                ".V().has('ConsultRequest', 'request_id', req_id)"
                ".addE('HAS_OPINION').to('op')",
                {
                    "op_id": op_id,
                    "agent": "agent:Consult",
                    "verdict": aggregation.get("recommendation", ""),
                    "reasoning": aggregation.get("aggregated_opinion", ""),
                    "conf": str(1.0 if aggregation.get("consensus") else 0.7),
                    "consensus": str(aggregation.get("consensus", True)).lower(),
                    "rec": aggregation.get("recommendation", ""),
                    "cnt": str(len(opinions)),
                    "agg": "true",
                    "ts": now,
                    "req_id": consult_request_id,
                },
            )

            # Update ConsultRequest status to completed
            await async_gremlin_submit(
                "g.V().has('ConsultRequest', 'request_id', req_id)"
                ".property('status', status)",
                {"req_id": consult_request_id, "status": "completed"},
            )

            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="aggregate_opinions",
                usage=usage, duration_ms=duration_ms,
                status="completed",
            )

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "action": "aggregate_opinions",
                "consensus": aggregation.get("consensus"),
                "opinion_count": len(opinions),
                "duration_ms": round(duration_ms),
            })

            output = json.dumps(aggregation, ensure_ascii=False)
            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=output,
                usage=usage,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[Consult] Aggregation failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="aggregate_opinions",
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

    # ── Private methods ─────────────────────────────────────────

    async def _draft_consult_request(
        self,
        case_id: str,
        case_context: dict,
        tthc_name: str,
        target: dict,
    ) -> dict:
        """Draft a single consult request for a target department."""
        case_data = case_context.get("case", {})
        gaps = case_context.get("gaps", [])
        citations = case_context.get("citations", [])

        # Build sanitized context (no PII, no full doc content)
        sanitized_gaps = [
            {
                "reason": self._extract_prop(g, "description"),
                "severity": self._extract_prop(g, "severity"),
                "component": self._extract_prop(g, "component_name"),
            }
            for g in gaps
        ]

        sanitized_citations = [
            {
                "law": self._extract_prop(c, "law_ref"),
                "article": self._extract_prop(c, "article_ref"),
                "text": self._extract_prop(c, "snippet")[:200],
            }
            for c in citations
        ]

        urgency = self._extract_prop(case_data, "urgency") or "normal"
        deadline_days = 1 if urgency in ("critical", "high") else self.DEFAULT_DEADLINE_DAYS
        deadline = (datetime.now(UTC) + timedelta(days=deadline_days)).isoformat()

        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "target_department": target["name"],
                    "target_expertise": target.get("department_type", ""),
                    "consult_reason": target.get("reason", ""),
                    "case_context": {
                        "tthc_name": tthc_name,
                        "urgency": urgency,
                        "gaps": sanitized_gaps,
                        "citations": sanitized_citations,
                    },
                    "deadline_days": deadline_days,
                    "instruction": (
                        "Soan yeu cau xin y kien. "
                        "Tap trung vao van de can y kien tu phong ban nay."
                    ),
                }, ensure_ascii=False),
            },
        ]

        draft = await self._llm_json_call(
            messages, temperature=0.4, max_tokens=2048,
        )

        # PII scan on generated text
        context_summary = self._strip_pii(draft.get("context_summary", ""))
        main_question = self._strip_pii(draft.get("main_question", ""))
        sub_questions = draft.get("sub_questions", [])
        if isinstance(sub_questions, list):
            sub_questions = [self._strip_pii(q) for q in sub_questions]

        # Fallback if LLM returned empty context
        if not context_summary and sanitized_gaps:
            context_summary = "; ".join(
                g["reason"] for g in sanitized_gaps if g.get("reason")
            )
        if not main_question:
            main_question = (
                f"Xin y kien ve ho so lien quan {tthc_name}. "
                f"Ly do: {target.get('reason', 'can y kien chuyen mon')}."
            )

        # Write ConsultRequest vertex
        req_id = f"cr-{case_id}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        await async_gremlin_submit(
            "g.addV('ConsultRequest')"
            ".property('request_id', req_id).property('case_id', cid)"
            ".property('target_org_id', org_id).property('target_org_name', org_name)"
            ".property('context_summary', ctx).property('main_question', mq)"
            ".property('sub_questions', sq).property('deadline', dl)"
            ".property('urgency', urg).property('status', 'pending')"
            ".property('created_at', ts)"
            ".as('cr')"
            ".V().has('Case', 'case_id', cid).addE('HAS_CONSULT_REQUEST').to('cr')",
            {
                "req_id": req_id,
                "cid": case_id,
                "org_id": target["id"],
                "org_name": target["name"],
                "ctx": context_summary,
                "mq": main_question,
                "sq": json.dumps(sub_questions, ensure_ascii=False),
                "dl": deadline,
                "urg": draft.get("urgency", urgency),
                "ts": now,
            },
        )

        logger.info(
            f"[Consult] Created ConsultRequest {req_id} -> {target['name']}"
        )

        # Broadcast to dept inbox
        try:
            from ...api.ws import broadcast
            await broadcast(f"dept:{target['id']}:inbox", {
                "event": "consult_request_created",
                "data": {
                    "request_id": req_id,
                    "case_id": case_id,
                    "main_question": main_question,
                    "deadline": deadline,
                },
            })
        except Exception as e:
            logger.debug(f"Dept inbox broadcast failed (non-critical): {e}")

        return {
            "request_id": req_id,
            "target": target["name"],
            "main_question": main_question,
            "deadline": deadline,
            "urgency": draft.get("urgency", urgency),
        }

    async def _llm_json_call(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        """
        Call Qwen and parse JSON response. Retry once on parse failure.
        Same pattern as Router._disambiguate_with_llm.
        """
        for attempt in range(2):
            completion = await self.client.chat(
                messages=messages,
                model=self.profile.model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            content = completion.choices[0].message.content or ""

            # Strip markdown fences if present
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning(
                        "[Consult] Invalid JSON from Qwen, retrying with stricter prompt"
                    )
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Tra lai DUNG FORMAT JSON. "
                            "Chi tra ve JSON, khong co text khac."
                        ),
                    })
                else:
                    logger.error(
                        f"[Consult] JSON parse failed after retry: {content[:200]}"
                    )
                    return {}

        return {}

    def _parse_consult_targets(self, raw_results: list) -> list[dict]:
        """
        Parse the result of CONSULTED edge + Organization traversal.
        Returns a list of {id, name, reason, department_type}.
        """
        targets = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue

            edge_data = item.get("e", {})
            org_data = item.get("org", {})

            targets.append({
                "id": self._extract_prop(org_data, "org_id"),
                "name": self._extract_prop(org_data, "name"),
                "reason": self._extract_prop(edge_data, "reason"),
                "department_type": self._extract_prop(org_data, "department_type"),
            })

        return targets

    @staticmethod
    def _strip_pii(text: str) -> str:
        """Strip Vietnamese PII patterns from text."""
        if not text:
            return text
        text = _CCCD_PATTERN.sub("[DA XOA]", text)
        text = _PHONE_PATTERN.sub("[DA XOA]", text)
        text = _BARE_ID_PATTERN.sub("[DA XOA]", text)
        text = _BARE_PHONE_PATTERN.sub("[DA XOA]", text)
        text = _ADDRESS_DETAIL_PATTERN.sub("[DA XOA]", text)
        return text

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
register_agent("consult_agent", ConsultAgent)
