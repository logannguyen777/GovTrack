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
from datetime import UTC, datetime
from typing import Any

from ...database import async_gremlin_submit
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.summarizer")

# ── PII patterns for Vietnamese identity documents ──────────────────
_CCCD_PATTERN = re.compile(r"\b\d{9,12}\b")
_PHONE_PATTERN = re.compile(r"\b0\d{9,10}\b")
_LABELED_ID_PATTERN = re.compile(
    r"(?:CCCD|CMND|CMT|[Ss]o [Dd]inh [Dd]anh|[Ss]o [Cc]an [Cc]uoc)\s*:?\s*\d{9,12}"
)
_LABELED_PHONE_PATTERN = re.compile(
    r"(?:SDT|[Ss]o [Dd]ien [Tt]hoai|[Dd]ien thoai|DT)\s*:?\s*0\d{9,10}"
)
_ADDRESS_PATTERN = re.compile(
    r"(?:\d{1,4}[\/\-]\d{1,4}\s+)?"
    r"(?:duong|pho|ngo|hem|so nha"
    r"|đường|phố|ngõ|hẻm|số nhà)"
    r"\s+[\w\s,]{3,50}",
    re.IGNORECASE,
)

_ALL_PII_PATTERNS = [
    _LABELED_ID_PATTERN,
    _LABELED_PHONE_PATTERN,
    _ADDRESS_PATTERN,
    _CCCD_PATTERN,
    _PHONE_PATTERN,
]


class SummarizerAgent(BaseAgent):
    """Generate 3 role-aware summaries: executive, staff, citizen."""

    profile_name = "summary_agent"
    MODES = ["executive", "staff", "citizen"]

    # ── ABC stub ────────────────────────────────────────────────
    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

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
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid).valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_GAP').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_GAP').out('CITES').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_OPINION').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_DECISION').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                    ".out('EXTRACTED').hasLabel('ExtractedEntity')"
                    ".valueMap('field_name', 'value').limit(20)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
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
            tthc_match = await async_gremlin_submit(
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

        word_count = len(summary_text.split())

        # Determine clearance level for summary vertex
        clearance = 0 if mode == "citizen" else 1

        # Write Summary vertex + HAS_SUMMARY edge
        summary_id = f"sum-{case_id}-{mode}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()

        await async_gremlin_submit(
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


# ── Module-level PII utility functions ──────────────────────────


def _strip_pii(text: str) -> str:
    """Strip Vietnamese PII patterns from text."""
    if not text:
        return text
    for pattern in _ALL_PII_PATTERNS:
        text = pattern.sub("[***]", text)
    return text


def _has_pii(text: str) -> bool:
    """Check if text still contains PII patterns."""
    for pattern in _ALL_PII_PATTERNS:
        if pattern.search(text):
            return True
    return False


# Register with orchestrator
register_agent("summary_agent", SummarizerAgent)
