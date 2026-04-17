"""
backend/src/agents/implementations/summarizer.py
Summarizer Agent (Agent 8): generate 3 role-aware summaries per case.

Pipeline:
  1. Parallel-fetch case data, gaps, citations, opinions, decision, entities
  2. Check existing summaries (idempotency)
  3. For each mode (executive, staff, citizen):
     a. Build mode-specific context (citizen gets minimal, no PII)
     b. Single LLM call for JSON summary
     c. PII enforcement for citizen mode (strip + regenerate if needed)
     d. Write Summary vertex + HAS_SUMMARY edge to Context Graph
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent
from ..pii_filters import PIILeakDetected, enforce_no_pii, has_pii
from ..pii_filters import redact as _redact_pii
from ..streaming import StreamingAgentEvent

logger = logging.getLogger("govflow.agent.summarizer")


class SummarizerAgent(BaseAgent):
    """Generate 3 role-aware summaries: executive, staff, citizen."""

    profile_name = "summary_agent"
    MODES = ["executive", "staff", "citizen"]

    # ── ABC stub ────────────────────────────────────────────────
    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """
        Xây dựng messages cho summarizer.

        Lấy case_summary, danh sách tài liệu, gaps, và target role/length
        từ Context Graph rồi nhúng vào user message.  Nếu gọi qua base-class
        run() (không override), agent sẽ tạo tóm tắt role-aware cho mode mặc
        định "staff".  Trong thực tế run() được override; hàm này đảm bảo
        ABC contract được thỏa mãn và có thể dùng trong unit test.
        """
        # Lấy thông tin case từ graph
        case_result = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid).valueMap(true)",
            {"cid": case_id},
        )
        case_vertex = case_result[0] if case_result else {}

        # Lấy gaps
        gaps = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid).out('HAS_GAP').valueMap(true)",
            {"cid": case_id},
        )

        # Lấy tài liệu
        documents = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid)"
            ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
            ".valueMap('filename', 'doc_type').limit(20)",
            {"cid": case_id},
        )

        # Lấy TTHC name
        tthc_match = await self._get_gdb().execute(
            "g.V().has('Case', 'case_id', cid).out('MATCHES_TTHC').valueMap(true)",
            {"cid": case_id},
        )
        tthc_name = self._extract_prop(tthc_match[0], "name") if tthc_match else ""

        # Role mặc định khi gọi qua base run()
        role = "staff"
        length = "tối đa 10 dòng"

        case_summary = {
            "tthc_name": tthc_name,
            "status": self._extract_prop(case_vertex, "status"),
            "urgency": self._extract_prop(case_vertex, "urgency"),
            "compliance_score": self._extract_prop(case_vertex, "compliance_score"),
            "sla_deadline": self._extract_prop(case_vertex, "sla_deadline"),
        }

        gaps_found = [
            {
                "mo_ta": self._extract_prop(g, "description"),
                "muc_do": self._extract_prop(g, "severity"),
                "huong_xu_ly": self._extract_prop(g, "fix_suggestion"),
            }
            for g in gaps
        ]

        documents_list = [
            {
                "ten_file": self._extract_prop(d, "filename"),
                "loai_tai_lieu": self._extract_prop(d, "doc_type"),
            }
            for d in documents
        ]

        system_prompt = (
            "Bạn là chuyên viên tóm tắt hồ sơ hành chính. "
            f"Tạo tóm tắt role-aware cho {role} với độ dài {length}. "
            "Giữ diacritics Vietnamese, định dạng markdown.\n\n"
            + self.profile.system_prompt
        )

        user_content = json.dumps(
            {
                "case_id": case_id,
                "case_summary": case_summary,
                "documents_list": documents_list,
                "gaps_found": gaps_found,
                "target_role": role,
                "target_length": length,
                "instruction": (
                    "Viết tóm tắt theo role đã chỉ định. "
                    "Trả về JSON: {\"summary_text\": \"...\", "
                    "\"mode\": \"staff\", \"word_count\": XX}."
                ),
            },
            ensure_ascii=False,
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    # ── Streaming entry point ─────────────────────────────────────
    async def run_streaming(self, case_id: str) -> AsyncIterator[StreamingAgentEvent]:  # type: ignore[override]
        """
        Override: run the summarizer pipeline and stream text/thinking events.

        3 summaries are generated in parallel via asyncio.gather.  Each
        `_stream_qwen` call fires `on_thinking` / `on_text` callbacks that
        emit StreamingAgentEvent objects; the generator yields those via
        an asyncio.Queue fed by the callbacks.
        """
        # Use a queue to bridge callbacks → async generator
        queue: asyncio.Queue[StreamingAgentEvent | None] = asyncio.Queue()

        async def _put(evt: StreamingAgentEvent) -> None:
            await queue.put(evt)

        async def _run_and_signal() -> AgentResult:
            result = await self._run_with_streaming_callbacks(case_id, _put)
            await queue.put(None)  # sentinel
            return result

        task = asyncio.create_task(_run_and_signal())

        # Yield events as they arrive until sentinel
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        result = await task
        if result.status == "completed":
            yield StreamingAgentEvent(
                type="completed",
                agent_name=self.profile.name,
                result=result.output,
            )
        else:
            yield StreamingAgentEvent(
                type="failed",
                agent_name=self.profile.name,
                error=result.error,
            )

    # ── Main entry point ────────────────────────────────────────
    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for deterministic summarizer pipeline.
        Generate 3 role-aware summaries from case context graph.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Summarizer] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # ── Step 1: Parallel-fetch all case context ─────────
            (
                case_result,
                gaps,
                citations,
                opinions,
                decision_result,
                entities,
                existing_summaries_raw,
            ) = await asyncio.gather(
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_GAP').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_GAP').out('CITES').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_OPINION').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_DECISION').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                    ".out('EXTRACTED').hasLabel('ExtractedEntity')"
                    ".valueMap('field_name', 'value').limit(20)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_SUMMARY').values('mode')",
                    {"cid": case_id},
                ),
            )

            if not case_result:
                raise ValueError(f"Case {case_id} not found in graph")

            case_vertex = case_result[0]

            # ── Step 2: Check idempotency ───────────────────────
            existing_modes = set(existing_summaries_raw) if existing_summaries_raw else set()
            modes_to_generate = [m for m in self.MODES if m not in existing_modes]

            if not modes_to_generate:
                logger.info(
                    f"[Summarizer] All 3 summaries already exist for case {case_id}"
                )
                duration_ms = (time.monotonic() - start_time) * 1000
                usage = self.client.reset_usage()

                await self._log_step(
                    step_id=step_id, case_id=case_id,
                    action="pipeline_summarizer",
                    usage=usage, duration_ms=duration_ms,
                    status="completed",
                )
                await self._broadcast(case_id, "agent_completed", {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "summaries_generated": 0,
                    "reason": "all_exist",
                    "duration_ms": round(duration_ms),
                })

                return AgentResult(
                    agent_name=self.profile.name,
                    case_id=case_id,
                    status="completed",
                    output=json.dumps({
                        "summaries_generated": 0,
                        "reason": "all_exist",
                        "existing_modes": list(existing_modes),
                    }),
                    usage=usage,
                    duration_ms=duration_ms,
                )

            # ── Step 3: Build combined case_data dict ───────────
            # Get TTHC name via MATCHES_TTHC
            tthc_match = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('MATCHES_TTHC').valueMap(true)",
                {"cid": case_id},
            )
            tthc_name = ""
            if tthc_match:
                tthc_name = self._extract_prop(tthc_match[0], "name")

            case_data = self._build_case_data(
                case_vertex, gaps, citations, opinions,
                decision_result, entities, tthc_name,
            )

            # ── Step 4: Generate summaries per mode ─────────────
            summaries: list[dict[str, Any]] = []
            for mode in modes_to_generate:
                try:
                    result = await self._generate_one_summary(
                        case_id, case_data, mode,
                    )
                    summaries.append(result)
                except Exception as e:
                    logger.error(
                        f"[Summarizer] Failed to generate {mode} summary: {e}",
                        exc_info=True,
                    )

            # ── Step 5: Build output, log, broadcast ────────────
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_summarizer",
                usage=usage, duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "summaries_generated": len(summaries),
                "summaries": summaries,
                "skipped_modes": list(existing_modes),
                "word_counts": {s["mode"]: s["word_count"] for s in summaries},
            }
            output_summary = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "summaries_generated": len(summaries),
                "modes": [s["mode"] for s in summaries],
                "duration_ms": round(duration_ms),
            })

            logger.info(
                f"[Summarizer] Case {case_id}: generated {len(summaries)} summaries, "
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
            logger.error(f"[Summarizer] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_summarizer",
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
        """
        Same logic as run() but 3 LLM calls use _stream_qwen so text/thinking
        events are forwarded via `emit`.  Called by run_streaming().
        """

        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        try:
            (
                case_result, gaps, citations, opinions,
                decision_result, entities, existing_summaries_raw,
            ) = await asyncio.gather(
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).valueMap(true)", {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).out('HAS_GAP').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_GAP').out('CITES').valueMap(true)", {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).out('HAS_OPINION').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).out('HAS_DECISION').valueMap(true)",
                    {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                    ".out('EXTRACTED').hasLabel('ExtractedEntity')"
                    ".valueMap('field_name', 'value').limit(20)", {"cid": case_id},
                ),
                self._get_gdb().execute(
                    "g.V().has('Case', 'case_id', cid).out('HAS_SUMMARY').values('mode')",
                    {"cid": case_id},
                ),
            )

            if not case_result:
                raise ValueError(f"Case {case_id} not found in graph")

            case_vertex = case_result[0]
            existing_modes = set(existing_summaries_raw) if existing_summaries_raw else set()
            modes_to_generate = [m for m in self.MODES if m not in existing_modes]

            if not modes_to_generate:
                duration_ms = (time.monotonic() - start_time) * 1000
                usage = self.client.reset_usage()
                await self._log_step(
                    step_id=step_id, case_id=case_id,
                    action="pipeline_summarizer",
                    usage=usage, duration_ms=duration_ms, status="completed",
                )
                return AgentResult(
                    agent_name=self.profile.name, case_id=case_id,
                    status="completed",
                    output=json.dumps({
                        "summaries_generated": 0, "reason": "all_exist",
                        "existing_modes": list(existing_modes),
                    }),
                    usage=usage, duration_ms=duration_ms,
                )

            tthc_match = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid).out('MATCHES_TTHC').valueMap(true)",
                {"cid": case_id},
            )
            tthc_name = self._extract_prop(tthc_match[0], "name") if tthc_match else ""
            case_data = self._build_case_data(
                case_vertex, gaps, citations, opinions,
                decision_result, entities, tthc_name,
            )

            # Generate 3 summaries in parallel with streaming callbacks
            async def _gen_streaming(mode: str) -> dict[str, Any] | None:
                try:
                    return await self._generate_one_summary_streaming(
                        case_id, case_data, mode, emit,
                    )
                except Exception as exc:
                    logger.error(f"[Summarizer] Streaming {mode} summary failed: {exc}", exc_info=True)
                    return None

            results = await asyncio.gather(*[_gen_streaming(m) for m in modes_to_generate])
            summaries = [r for r in results if r is not None]

            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()
            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_summarizer",
                usage=usage, duration_ms=duration_ms, status="completed",
            )

            output_data = {
                "summaries_generated": len(summaries),
                "summaries": summaries,
                "skipped_modes": list(existing_modes),
                "word_counts": {s["mode"]: s["word_count"] for s in summaries},
            }
            return AgentResult(
                agent_name=self.profile.name, case_id=case_id,
                status="completed",
                output=json.dumps(output_data, ensure_ascii=False),
                tool_calls_count=0, usage=usage, duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_summarizer",
                usage=self.client.reset_usage(),
                duration_ms=duration_ms, status="failed", error=str(exc),
            )
            return AgentResult(
                agent_name=self.profile.name, case_id=case_id,
                status="failed", output="",
                duration_ms=duration_ms, error=str(exc),
            )

    async def _generate_one_summary_streaming(
        self,
        case_id: str,
        case_data: dict,
        mode: str,
        emit: Callable[[StreamingAgentEvent], Awaitable[None]],
    ) -> dict[str, Any]:
        """
        Like _generate_one_summary but uses _stream_qwen so text/thinking
        tokens are forwarded via `emit` with `variant=mode`.
        """
        context_for_llm = self._build_mode_context(case_data, mode)
        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "case_context": context_for_llm,
                    "mode": mode,
                    "instruction": self._mode_instruction(mode),
                }, ensure_ascii=False),
            },
        ]

        text_parts: list[str] = []

        async def _on_thinking(chunk: str) -> None:
            await emit(StreamingAgentEvent(
                type="thinking_chunk",
                agent_name=self.profile.name,
                delta=chunk,
                variant=mode,
            ))

        async def _on_text(chunk: str) -> None:
            text_parts.append(chunk)
            await emit(StreamingAgentEvent(
                type="text_chunk",
                agent_name=self.profile.name,
                delta=chunk,
                variant=mode,
            ))

        response = await self._stream_qwen(
            model=self.profile.model,
            messages=messages,
            on_thinking=_on_thinking,
            on_text=_on_text,
        )

        full_text = response["content"] or "".join(text_parts)

        # Try to parse as JSON (Qwen may have produced JSON in the stream)
        summary_data: dict = {}
        try:
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", full_text.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
            summary_data = json.loads(cleaned)
        except json.JSONDecodeError:
            summary_data = {"summary_text": full_text}

        summary_text = summary_data.get("summary_text", full_text)
        if not summary_text:
            summary_text = self._fallback_summary(case_data, mode)

        if mode == "citizen":
            summary_text = _strip_pii(summary_text)
            if _has_pii(summary_text):
                logger.warning("[Summarizer] PII in citizen summary, regenerating")
                summary_text = await self._regenerate_without_pii(summary_text)
            # Post-generation hard check — reject if still leaking
            try:
                summary_text = enforce_no_pii(summary_text, context=f"SummarizerAgent:{mode}")
            except PIILeakDetected:
                logger.error("[Summarizer] PII leak in citizen summary after regeneration — rejecting")
                raise

        word_count = len(summary_text.split())
        clearance = 0 if mode == "citizen" else 1
        summary_id = f"sum-{case_id}-{mode}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        await self._get_gdb().execute(
            "g.addV('Summary')"
            ".property('summary_id', sid).property('text', text)"
            ".property('mode', mode).property('word_count', wc)"
            ".property('case_id', cid).property('clearance', cl)"
            ".property('created_at', ts).as('sum')"
            ".V().has('Case', 'case_id', cid).addE('HAS_SUMMARY').to('sum')",
            {
                "sid": summary_id, "text": summary_text, "mode": mode,
                "wc": word_count, "cid": case_id, "cl": clearance, "ts": now,
            },
        )

        return {
            "summary_id": summary_id, "mode": mode,
            "text": summary_text, "word_count": word_count, "clearance": clearance,
        }

    # ── Summary generation per mode ─────────────────────────────

    async def _generate_one_summary(
        self,
        case_id: str,
        case_data: dict,
        mode: str,
    ) -> dict[str, Any]:
        """Generate a single summary for the given mode and write to GDB."""
        logger.info(f"[Summarizer] Generating {mode} summary for case {case_id}")

        # Build mode-specific context
        context_for_llm = self._build_mode_context(case_data, mode)

        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "case_context": context_for_llm,
                    "mode": mode,
                    "instruction": self._mode_instruction(mode),
                }, ensure_ascii=False),
            },
        ]

        summary_data = await self._llm_json_call(
            messages, temperature=0.4, max_tokens=2048,
        )

        summary_text = summary_data.get("summary_text", "")

        # Fallback: if LLM returned empty text
        if not summary_text:
            summary_text = self._fallback_summary(case_data, mode)

        # ── CRITICAL: PII enforcement for citizen mode ──────
        if mode == "citizen":
            summary_text = _strip_pii(summary_text)
            if _has_pii(summary_text):
                logger.warning(
                    f"[Summarizer] PII detected in citizen summary after stripping, "
                    f"regenerating for case {case_id}"
                )
                summary_text = await self._regenerate_without_pii(summary_text)
            # Hard post-check — reject if still leaking after regeneration
            try:
                summary_text = enforce_no_pii(
                    summary_text, context=f"SummarizerAgent:non-stream:{mode}"
                )
            except PIILeakDetected:
                logger.error(
                    f"[Summarizer] PII leak in citizen summary after regeneration "
                    f"for case {case_id} — rejecting"
                )
                raise

        word_count = len(summary_text.split())

        # Determine clearance level for summary vertex
        clearance = 0 if mode == "citizen" else 1

        # Write Summary vertex + HAS_SUMMARY edge
        summary_id = f"sum-{case_id}-{mode}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        await self._get_gdb().execute(
            "g.addV('Summary')"
            ".property('summary_id', sid)"
            ".property('text', text)"
            ".property('mode', mode)"
            ".property('word_count', wc)"
            ".property('case_id', cid)"
            ".property('clearance', cl)"
            ".property('created_at', ts)"
            ".as('sum')"
            ".V().has('Case', 'case_id', cid)"
            ".addE('HAS_SUMMARY').to('sum')",
            {
                "sid": summary_id,
                "text": summary_text,
                "mode": mode,
                "wc": word_count,
                "cid": case_id,
                "cl": clearance,
                "ts": now,
            },
        )

        logger.info(
            f"[Summarizer] Wrote {mode} summary {summary_id} "
            f"({word_count} words, clearance={clearance})"
        )

        return {
            "summary_id": summary_id,
            "mode": mode,
            "text": summary_text,
            "word_count": word_count,
            "clearance": clearance,
        }

    # ── Context building ────────────────────────────────────────

    def _build_case_data(
        self,
        case_vertex: dict,
        gaps: list,
        citations: list,
        opinions: list,
        decision_result: list,
        entities: list,
        tthc_name: str,
    ) -> dict[str, Any]:
        """Normalize all fetched data into a single dict."""
        case_data: dict[str, Any] = {
            "tthc_name": tthc_name,
            "status": self._extract_prop(case_vertex, "status"),
            "urgency": self._extract_prop(case_vertex, "urgency"),
            "compliance_score": self._extract_prop(case_vertex, "compliance_score"),
            "sla_deadline": self._extract_prop(case_vertex, "sla_deadline"),
            "sla_remaining_days": self._extract_prop(case_vertex, "sla_remaining_days"),
        }

        # Gaps
        case_data["gaps"] = [
            {
                "reason": self._extract_prop(g, "description"),
                "severity": self._extract_prop(g, "severity"),
                "component_name": self._extract_prop(g, "component_name"),
                "fix_suggestion": self._extract_prop(g, "fix_suggestion"),
            }
            for g in gaps
        ]

        # Citations
        case_data["citations"] = [
            {
                "law_code": self._extract_prop(c, "law_ref"),
                "article_num": self._extract_prop(c, "article_ref"),
                "clause_num": self._extract_prop(c, "clause_num"),
                "text_excerpt": (self._extract_prop(c, "snippet") or "")[:150],
            }
            for c in citations
        ]

        # Opinions
        case_data["opinions"] = [
            {
                "source": self._extract_prop(o, "source_org_name")
                or self._extract_prop(o, "agent_name"),
                "recommendation": self._extract_prop(o, "recommendation")
                or self._extract_prop(o, "verdict"),
                "reasoning": self._extract_prop(o, "reasoning"),
                "consensus": self._extract_prop(o, "consensus"),
            }
            for o in opinions
        ]

        # Decision
        if decision_result:
            d = decision_result[0]
            case_data["decision"] = {
                "type": self._extract_prop(d, "type")
                or self._extract_prop(d, "decision_type"),
                "reasoning": self._extract_prop(d, "reasoning"),
            }
        else:
            case_data["decision"] = {}

        # Entities (for staff mode)
        case_data["entities"] = [
            {
                "field_name": self._extract_prop(e, "field_name"),
                "value": self._extract_prop(e, "value"),
            }
            for e in entities
        ]

        return case_data

    def _build_mode_context(self, case_data: dict, mode: str) -> dict[str, Any]:
        """Build appropriate context per mode -- citizen gets minimal info."""
        base: dict[str, Any] = {
            "tthc_name": case_data.get("tthc_name", ""),
            "status": case_data.get("status", ""),
            "compliance_score": case_data.get("compliance_score"),
        }

        if mode == "executive":
            gaps = case_data.get("gaps", [])
            base["gap_count"] = len(gaps)
            base["gap_severities"] = [g["severity"] for g in gaps]
            base["opinions_summary"] = [
                o.get("recommendation", "") for o in case_data.get("opinions", [])
            ]
            base["decision"] = case_data.get("decision", {})
            base["sla_remaining_days"] = case_data.get("sla_remaining_days")

        elif mode == "staff":
            base["gaps"] = case_data.get("gaps", [])
            base["citations"] = case_data.get("citations", [])
            base["opinions"] = case_data.get("opinions", [])
            base["entities"] = case_data.get("entities", [])[:20]
            base["sla_deadline"] = case_data.get("sla_deadline")

        elif mode == "citizen":
            # Minimal -- no PII, no internal details
            base["gap_descriptions"] = [
                g.get("fix_suggestion", "") or g.get("reason", "")
                for g in case_data.get("gaps", [])
            ]
            # Do NOT include entities, citations, opinions, internal notes

        return base

    @staticmethod
    def _mode_instruction(mode: str) -> str:
        """Return mode-specific LLM instruction."""
        instructions = {
            "executive": (
                "Viet tom tat toi da 3 dong cho lanh dao. "
                "Tap trung quyet dinh can dua, rui ro, de xuat hanh dong. "
                "Bao gom compliance score va y kien phong ban."
            ),
            "staff": (
                "Viet tom tat toi da 10 dong cho chuyen vien xu ly ho so. "
                "Bao gom deadline, tham chieu phap luat (dieu/khoan/diem), "
                "van de con mo, lich su xu ly."
            ),
            "citizen": (
                "Viet tom tat bang tieng Viet binh dan cho cong dan. "
                "Giai thich tinh trang ho so, buoc tiep theo, thoi gian du kien. "
                "TUYET DOI KHONG chua thong tin ca nhan (so CCCD, SDT, dia chi). "
                "Khong dung thuat ngu phap ly phuc tap."
            ),
        }
        return instructions[mode]

    @staticmethod
    def _fallback_summary(case_data: dict, mode: str) -> str:
        """Generate a minimal template-based summary when LLM fails."""
        tthc = case_data.get("tthc_name", "TTHC")
        status = case_data.get("status", "dang xu ly")
        score = case_data.get("compliance_score", "N/A")

        if mode == "executive":
            return f"Ho so {tthc}. Trang thai: {status}. Compliance: {score}%."
        elif mode == "staff":
            gap_count = len(case_data.get("gaps", []))
            return (
                f"Ho so {tthc}. Trang thai: {status}. "
                f"Compliance score: {score}%. So gap: {gap_count}."
            )
        else:  # citizen
            return (
                f"Ho so thu tuc \"{tthc}\" cua ban dang duoc xu ly. "
                f"Trang thai hien tai: {status}. "
                f"Vui long cho them thong bao tu co quan."
            )

    # ── PII enforcement ─────────────────────────────────────────

    async def _regenerate_without_pii(self, original_text: str) -> str:
        """Regenerate citizen summary with explicit PII removal instruction."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Viet lai doan van sau, LOAI BO hoan toan moi thong tin ca nhan "
                    "(so CCCD, CMND, SDT, dia chi chi tiet, ten nguoi cu the). "
                    "Thay bang '[***]' hoac mo ta chung. "
                    "Giu nguyen noi dung chinh va tone than thien."
                ),
            },
            {"role": "user", "content": original_text},
        ]

        completion = await self.client.chat(
            messages=messages,
            model=self.profile.model,
            temperature=0.2,
            max_tokens=2048,
        )

        result = completion.choices[0].message.content or original_text
        # Safety net: strip PII from regenerated text too
        return _strip_pii(result)

    # ── LLM JSON call with retry ────────────────────────────────

    async def _llm_json_call(
        self,
        messages: list[dict],
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> dict:
        """
        Call Qwen and parse JSON response. Retry once on parse failure.
        Same pattern as consult.py and compliance.py.
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
                        "[Summarizer] Invalid JSON from Qwen, retrying"
                    )
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Tra lai DUNG FORMAT: "
                            '{"summary_text": "...", "mode": "...", "word_count": XX}. '
                            "Chi tra ve JSON, khong co text khac."
                        ),
                    })
                else:
                    logger.error(
                        f"[Summarizer] JSON parse failed after retry: {content[:200]}"
                    )
                    return {}

        return {}

    # ── Static helpers ──────────────────────────────────────────

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""

    @staticmethod
    def _extract_bool(vertex_map: dict, key: str, default: bool = True) -> bool:
        """Extract a boolean property from Gremlin valueMap result."""
        val = vertex_map.get(key, default)
        if isinstance(val, list):
            val = val[0] if val else default
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)


# ── Module-level PII utility functions (delegate to shared module) ──


def _strip_pii(text: str) -> str:
    """Strip Vietnamese PII patterns from text."""
    return _redact_pii(text)


def _has_pii(text: str) -> bool:
    """Check if text still contains PII patterns."""
    return has_pii(text)


# Register with orchestrator
register_agent("summary_agent", SummarizerAgent)
