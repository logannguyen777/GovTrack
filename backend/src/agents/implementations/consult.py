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

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent
from ..pii_filters import enforce_no_pii
from ..pii_filters import redact as _redact_pii
from ..streaming import StreamingAgentEvent

logger = logging.getLogger("govflow.agent.consult")


class ConsultAgent(BaseAgent):
    """Auto-draft cross-department consultation requests and aggregate opinions."""

    profile_name = "consult_agent"
    DEFAULT_DEADLINE_DAYS = 2

    # ── ABC stub ────────────────────────────────────────────────
    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """
        Xây dựng messages cho consult agent tư vấn liên phòng.

        Lấy case_context, consulted_department, consulted_aspect và
        related_laws từ Context Graph rồi nhúng vào user message để
        LLM đưa ra ý kiến chuyên môn về khía cạnh được yêu cầu tư vấn.
        run() được override trong production; hàm này đảm bảo ABC contract
        và dùng được trong unit test / graceful fallback.
        """
        # Lấy thông tin case
        case_result = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid).valueMap(true)",
            {"cid": case_id},
        )
        case_vertex = case_result[0] if case_result else {}

        # Lấy phòng ban được tư vấn (CONSULTED edge từ Router)
        raw_targets = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid)"
            ".outE('CONSULTED').as('e').inV().as('org')"
            ".select('e', 'org').by(valueMap()).by(valueMap(true))",
            {"cid": case_id},
        )
        targets = self._parse_consult_targets(raw_targets)

        # Lấy gaps và trích dẫn pháp lý
        gaps = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid).out('HAS_GAP').valueMap(true)",
            {"cid": case_id},
        )
        citations = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid)"
            ".out('HAS_GAP').out('CITES').valueMap(true)",
            {"cid": case_id},
        )

        # Lấy TTHC name
        tthc_match = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid).out('MATCHES_TTHC').valueMap(true)",
            {"cid": case_id},
        )
        tthc_name = self._extract_prop(tthc_match[0], "name") if tthc_match else ""

        # Phòng ban và khía cạnh tư vấn (từ target đầu tiên nếu có)
        consulted_department = targets[0]["name"] if targets else "Phòng chuyên môn"
        consulted_aspect = targets[0].get("reason", "kiểm tra chuyên môn") if targets else "kiểm tra chuyên môn"

        related_laws = [
            {
                "van_ban": self._extract_prop(c, "law_ref"),
                "dieu": self._extract_prop(c, "article_ref"),
                "trich_dan": (self._extract_prop(c, "snippet") or "")[:200],
            }
            for c in citations
            if self._extract_prop(c, "law_ref")
        ]

        case_context = {
            "case_id": case_id,
            "tthc_name": tthc_name,
            "status": self._extract_prop(case_vertex, "status"),
            "urgency": self._extract_prop(case_vertex, "urgency"),
            "gaps": [
                {
                    "mo_ta": self._extract_prop(g, "description"),
                    "muc_do": self._extract_prop(g, "severity"),
                    "thanh_phan": self._extract_prop(g, "component_name"),
                }
                for g in gaps
            ],
        }

        system_prompt = (
            f"Bạn là cán bộ {consulted_department} đang tư vấn liên phòng. "
            f"Đưa ra ý kiến chuyên môn về khía cạnh {consulted_aspect} "
            "của hồ sơ, trích dẫn văn bản pháp lý liên quan.\n\n"
            + self.profile.system_prompt
        )

        user_content = json.dumps(
            {
                "case_context": case_context,
                "consulted_department": consulted_department,
                "consulted_aspect": consulted_aspect,
                "related_laws": related_laws,
                "instruction": (
                    "Soạn yêu cầu xin ý kiến tư vấn cho phòng ban nêu trên. "
                    "Trả về JSON: {\"context_summary\": \"...\", "
                    "\"main_question\": \"...\", "
                    "\"sub_questions\": [...], "
                    "\"deadline_days\": 2, "
                    "\"urgency\": \"normal\"}."
                ),
            },
            ensure_ascii=False,
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    # ── Streaming entry point ────────────────────────────────────
    async def run_streaming(self, case_id: str) -> AsyncIterator[StreamingAgentEvent]:  # type: ignore[override]
        """Override: stream thinking + draft-text for each consult request."""
        queue: asyncio.Queue[StreamingAgentEvent | None] = asyncio.Queue()

        async def _put(evt: StreamingAgentEvent) -> None:
            await queue.put(evt)

        async def _run_and_signal() -> AgentResult:
            result = await self._run_with_streaming_callbacks(case_id, _put)
            await queue.put(None)
            return result

        task = asyncio.create_task(_run_and_signal())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        result = await task
        if result.status == "completed":
            yield StreamingAgentEvent(
                type="completed", agent_name=self.profile.name, result=result.output,
            )
        else:
            yield StreamingAgentEvent(
                type="failed", agent_name=self.profile.name, error=result.error,
            )

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
            raw_targets = await self._get_gdb().execute(
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
            context_result = await self._get_gdb().execute(
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
            tthc_match = await self._get_gdb().execute(
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
                await self._get_gdb().execute(
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

    # ── Finalize (called from API endpoint 2.1) ─────────────────
    async def finalize(
        self,
        request_id: str,
        opinion: str,
        recommendation: str,
        attachments: list[str],
        session: Any | None = None,
    ) -> dict:
        """
        Finalize a ConsultRequest by writing a ConsultOpinion vertex.
        Called by POST /agents/consult/{request_id}/submit.
        Returns {"opinion_id": ..., "completed_at": ...}.
        """

        if session is not None:
            self._session = session

        now = datetime.now(UTC).isoformat()
        opinion_id = f"consult-op-{request_id}-{uuid.uuid4().hex[:8]}"

        await self._get_gdb().execute(
            "g.addV('ConsultOpinion')"
            ".property('opinion_id', oid)"
            ".property('request_id', req_id)"
            ".property('opinion', op)"
            ".property('recommendation', rec)"
            ".property('submitted_at', ts)"
            ".as('co')"
            ".V().has('ConsultRequest', 'request_id', req_id)"
            ".addE('CONSULTED_BY').to('co')",
            {
                "oid": opinion_id,
                "req_id": request_id,
                "op": opinion,
                "rec": recommendation,
                "ts": now,
            },
        )

        for doc_id in (attachments or []):
            try:
                await self._get_gdb().execute(
                    "g.V().has('ConsultOpinion', 'opinion_id', oid)"
                    ".addE('REFERENCES_DOC')"
                    ".to(__.V().has('Document', 'doc_id', did))",
                    {"oid": opinion_id, "did": doc_id},
                )
            except Exception:
                pass

        await self._get_gdb().execute(
            "g.V().has('ConsultRequest', 'request_id', req_id)"
            ".property('status', 'completed')"
            ".property('completed_at', ts)",
            {"req_id": request_id, "ts": now},
        )

        logger.info(f"[Consult] Finalized ConsultRequest {request_id} -> {recommendation}")
        return {"opinion_id": opinion_id, "completed_at": now}

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
            opinions = await self._get_gdb().execute(
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
            request_data = await self._get_gdb().execute(
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

            await self._get_gdb().execute(
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
            await self._get_gdb().execute(
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

    # ── Streaming-enabled pipeline ──────────────────────────────

    async def _run_with_streaming_callbacks(
        self,
        case_id: str,
        emit: Callable[[StreamingAgentEvent], Awaitable[None]],
    ) -> AgentResult:
        """Same as run() but _draft_consult_request uses _stream_qwen."""

        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        try:
            raw_targets = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".outE('CONSULTED').as('e').inV().as('org')"
                ".select('e', 'org').by(valueMap()).by(valueMap(true))",
                {"cid": case_id},
            )
            targets = self._parse_consult_targets(raw_targets)

            if not targets:
                duration_ms = (time.monotonic() - start_time) * 1000
                usage = self.client.reset_usage()
                await self._log_step(step_id=step_id, case_id=case_id,
                                     action="pipeline_consult_drafter",
                                     usage=usage, duration_ms=duration_ms, status="completed")
                return AgentResult(
                    agent_name=self.profile.name, case_id=case_id, status="completed",
                    output=json.dumps({"consult_requests_count": 0, "reason": "no_consult_targets"},
                                      ensure_ascii=False),
                    usage=usage, duration_ms=duration_ms,
                )

            context_result = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".project('case', 'gaps', 'citations')"
                ".by(valueMap(true))"
                ".by(out('HAS_GAP').valueMap(true).fold())"
                ".by(out('HAS_GAP').out('CITES').valueMap(true).fold())",
                {"cid": case_id},
            )
            case_context = context_result[0] if context_result else {"case": {}, "gaps": [], "citations": []}

            tthc_match = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid).out('MATCHES_TTHC').valueMap(true)",
                {"cid": case_id},
            )
            tthc_name = self._extract_prop(tthc_match[0], "name") if tthc_match else ""

            requests = []
            for target in targets:
                try:
                    req = await self._draft_consult_request_streaming(
                        case_id, case_context, tthc_name, target, emit,
                    )
                    requests.append(req)
                except Exception as exc:
                    logger.error(f"[Consult] Streaming request for {target.get('name')}: {exc}", exc_info=True)

            if requests:
                await self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).property('status', status)",
                    {"cid": case_id, "status": "consultation"},
                )

            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()
            await self._log_step(step_id=step_id, case_id=case_id,
                                 action="pipeline_consult_drafter",
                                 usage=usage, duration_ms=duration_ms, status="completed")
            return AgentResult(
                agent_name=self.profile.name, case_id=case_id, status="completed",
                output=json.dumps({"consult_requests_count": len(requests),
                                   "consult_requests": requests, "tthc_name": tthc_name},
                                  ensure_ascii=False),
                tool_calls_count=0, usage=usage, duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            await self._log_step(step_id=step_id, case_id=case_id,
                                 action="pipeline_consult_drafter",
                                 usage=self.client.reset_usage(),
                                 duration_ms=duration_ms, status="failed", error=str(exc))
            return AgentResult(
                agent_name=self.profile.name, case_id=case_id, status="failed",
                output="", duration_ms=duration_ms, error=str(exc),
            )

    async def _draft_consult_request_streaming(
        self,
        case_id: str,
        case_context: dict,
        tthc_name: str,
        target: dict,
        emit: Callable[[StreamingAgentEvent], Awaitable[None]],
    ) -> dict:
        """
        Like _draft_consult_request but LLM call uses _stream_qwen so
        thinking + draft text are forwarded via emit.
        """
        from datetime import timedelta

        case_data = case_context.get("case", {})
        gaps = case_context.get("gaps", [])
        citations = case_context.get("citations", [])

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
                        "tthc_name": tthc_name, "urgency": urgency,
                        "gaps": sanitized_gaps, "citations": sanitized_citations,
                    },
                    "deadline_days": deadline_days,
                    "instruction": "Soan yeu cau xin y kien. Tap trung vao van de can y kien tu phong ban nay.",
                }, ensure_ascii=False),
            },
        ]

        text_parts: list[str] = []

        async def _on_thinking(chunk: str) -> None:
            await emit(StreamingAgentEvent(
                type="thinking_chunk", agent_name=self.profile.name, delta=chunk,
            ))

        async def _on_text(chunk: str) -> None:
            text_parts.append(chunk)
            await emit(StreamingAgentEvent(
                type="text_chunk", agent_name=self.profile.name, delta=chunk,
            ))

        response = await self._stream_qwen(
            model=self.profile.model,
            messages=messages,
            on_thinking=_on_thinking,
            on_text=_on_text,
        )

        full_text = response["content"] or "".join(text_parts)

        # Parse JSON from streamed output
        draft: dict = {}
        try:
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", full_text.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            draft = {}

        # Apply PII redaction using shared module, then post-check
        context_summary = enforce_no_pii(
            draft.get("context_summary", ""), context="ConsultAgent:context_summary"
        )
        main_question = enforce_no_pii(
            draft.get("main_question", ""), context="ConsultAgent:main_question"
        )
        sub_questions = draft.get("sub_questions", [])
        if isinstance(sub_questions, list):
            sub_questions = [
                enforce_no_pii(q, context="ConsultAgent:sub_question")
                for q in sub_questions
            ]

        if not context_summary and sanitized_gaps:
            context_summary = "; ".join(g["reason"] for g in sanitized_gaps if g.get("reason"))
        if not main_question:
            main_question = (
                f"Xin y kien ve ho so lien quan {tthc_name}. "
                f"Ly do: {target.get('reason', 'can y kien chuyen mon')}."
            )

        req_id = f"cr-{case_id}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        await self._get_gdb().execute(
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
                "req_id": req_id, "cid": case_id,
                "org_id": target["id"], "org_name": target["name"],
                "ctx": context_summary, "mq": main_question,
                "sq": json.dumps(sub_questions, ensure_ascii=False),
                "dl": deadline, "urg": draft.get("urgency", urgency), "ts": now,
            },
        )

        try:
            from ...api.ws import broadcast
            await broadcast(f"dept:{target['id']}:inbox", {
                "event": "consult_request_created",
                "data": {"request_id": req_id, "case_id": case_id,
                         "main_question": main_question, "deadline": deadline},
            })
        except Exception as exc:
            logger.debug(f"Dept inbox broadcast failed: {exc}")

        return {
            "request_id": req_id, "target": target["name"],
            "main_question": main_question, "deadline": deadline,
            "urgency": draft.get("urgency", urgency),
        }

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

        # PII scan on generated text — use shared module with post-check enforcement
        context_summary = enforce_no_pii(
            draft.get("context_summary", ""), context="ConsultAgent:draft:context_summary"
        )
        main_question = enforce_no_pii(
            draft.get("main_question", ""), context="ConsultAgent:draft:main_question"
        )
        sub_questions = draft.get("sub_questions", [])
        if isinstance(sub_questions, list):
            sub_questions = [
                enforce_no_pii(q, context="ConsultAgent:draft:sub_question")
                for q in sub_questions
            ]

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

        await self._get_gdb().execute(
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
        """Strip Vietnamese PII patterns from text (delegates to shared pii_filters)."""
        return _redact_pii(text)

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
