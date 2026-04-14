"""
backend/src/agents/implementations/classifier.py
Classifier Agent (Agent 3): match a case to its correct TTHC code
from the national administrative procedures catalog.

Pipeline:
  1. Fetch case metadata + DocAnalyzer output (doc types, entities)
  2. Fetch full TTHC catalog from Knowledge Graph for grounding
  3. Call Qwen3-Max with few-shot prompt for classification
  4. Grounding check: verify TTHC code exists in catalog
  5. Write MATCHES_TTHC edge if confident, update Case.urgency
  6. Escalate unknown TTHC for manual classification
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from ...database import async_gremlin_submit
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.classifier")


class ClassifierAgent(BaseAgent):
    """Match case to TTHC code from national catalog via few-shot classification."""

    profile_name = "classifier_agent"

    CONFIDENCE_THRESHOLD = 0.7

    VALID_URGENCY_LEVELS = {"normal", "high", "critical"}

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for single-call structured classification.
        Steps: fetch context -> build bundle description -> call Qwen once
               -> grounding check -> write edges -> return.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Classifier] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # Step 1: Fetch case metadata
            case_data = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid).valueMap(true)",
                {"cid": case_id},
            )
            case_meta = case_data[0] if case_data else {}

            # Step 2: Fetch documents with types from DocAnalyzer
            documents = await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                ".valueMap(true)",
                {"cid": case_id},
            )

            # Step 3: Fetch extracted entities for each document
            doc_summaries: list[dict[str, Any]] = []
            for doc in documents:
                doc_id = self._extract_prop(doc, "doc_id")
                doc_type = self._extract_prop(doc, "type") or "unknown"
                confidence = doc.get("confidence", [0.0])
                if isinstance(confidence, list):
                    confidence = confidence[0] if confidence else 0.0
                confidence = float(confidence)

                # Get entities extracted by DocAnalyzer
                entities = await async_gremlin_submit(
                    "g.V().has('Document', 'doc_id', did)"
                    ".out('EXTRACTED').hasLabel('ExtractedEntity')"
                    ".valueMap('field_name', 'value')",
                    {"did": doc_id},
                )

                entity_list = []
                for e in entities:
                    fname = e.get("field_name", [""])[0] if isinstance(e.get("field_name"), list) else e.get("field_name", "")
                    val = e.get("value", [""])[0] if isinstance(e.get("value"), list) else e.get("value", "")
                    if fname:
                        entity_list.append({"field_name": fname, "value": val})

                doc_summaries.append({
                    "doc_id": doc_id,
                    "type": doc_type,
                    "confidence": confidence,
                    "entities": entity_list,
                })

            # Step 4: Fetch TTHC catalog from KG for grounding
            tthc_catalog = await async_gremlin_submit(
                "g.V().hasLabel('TTHCSpec').valueMap(true)",
                {},
            )

            valid_codes: set[str] = set()
            tthc_list: list[dict[str, str]] = []
            for t in tthc_catalog:
                code = self._extract_prop(t, "code")
                name = self._extract_prop(t, "name")
                if code:
                    valid_codes.add(code)
                    tthc_list.append({"code": code, "name": name})

            # Step 5: Build bundle description
            bundle_description = self._build_bundle_description(doc_summaries)

            # Step 6: Call Qwen3-Max for classification
            classification = await self._classify(
                case_id, bundle_description, tthc_list,
            )

            # Step 7: Grounding check
            tthc_code = classification.get("tthc_code", "")
            unknown_tthc = classification.get("unknown_tthc", False)

            if not unknown_tthc and tthc_code not in valid_codes:
                logger.warning(
                    f"[Classifier] LLM returned non-existent TTHC code "
                    f"'{tthc_code}', forcing unknown_tthc"
                )
                classification["unknown_tthc"] = True
                classification["confidence"] = 0.0
                unknown_tthc = True

            confidence_val = float(classification.get("confidence", 0.0))

            # Step 8: Write MATCHES_TTHC edge if confident match
            if not unknown_tthc and confidence_val >= self.CONFIDENCE_THRESHOLD:
                await async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".addE('MATCHES_TTHC')"
                    ".to(g.V().has('TTHCSpec', 'code', code))"
                    ".property('confidence', conf)",
                    {
                        "cid": case_id,
                        "code": tthc_code,
                        "conf": confidence_val,
                    },
                )
                logger.info(
                    f"[Classifier] Matched case {case_id} -> TTHC {tthc_code} "
                    f"(confidence={confidence_val:.2f})"
                )

            # Step 9: Update Case.urgency
            urgency = classification.get("urgency", "normal")
            if urgency not in self.VALID_URGENCY_LEVELS:
                urgency = "normal"

            await async_gremlin_submit(
                "g.V().has('Case', 'case_id', cid).property('urgency', urg)",
                {"cid": case_id, "urg": urgency},
            )

            # Step 10: Handle unknown TTHC -- escalate
            if unknown_tthc:
                await async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".property('status', 'needs_manual_classification')",
                    {"cid": case_id},
                )
                logger.warning(
                    f"[Classifier] Case {case_id}: unknown TTHC, escalated. "
                    f"Reasoning: {classification.get('reasoning', 'N/A')}"
                )

            # Step 11: Log and broadcast
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_tthc_classifier",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_summary = json.dumps({
                "tthc_code": tthc_code if not unknown_tthc else None,
                "tthc_name": classification.get("tthc_name", ""),
                "confidence": confidence_val,
                "urgency": urgency,
                "unknown_tthc": unknown_tthc,
                "reasoning": classification.get("reasoning", ""),
                "documents_analyzed": len(doc_summaries),
            }, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "tthc_code": tthc_code if not unknown_tthc else None,
                "confidence": confidence_val,
                "urgency": urgency,
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
            logger.error(f"[Classifier] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_tthc_classifier",
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
    # Internal methods
    # ------------------------------------------------------------------

    def _build_bundle_description(self, doc_summaries: list[dict[str, Any]]) -> str:
        """Build human-readable bundle description from doc types and entities."""
        if not doc_summaries:
            return "(khong co tai lieu)"

        parts: list[str] = []
        for doc in doc_summaries:
            desc = f"- {doc['type']} (confidence: {doc['confidence']:.2f})"
            entities = doc.get("entities", [])
            if entities:
                key_vals = [
                    f"{e['field_name']}={e['value']}"
                    for e in entities[:5]
                ]
                desc += f" [{', '.join(key_vals)}]"
            parts.append(desc)
        return "\n".join(parts)

    async def _classify(
        self,
        case_id: str,
        bundle_description: str,
        tthc_list: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Call Qwen3-Max for TTHC classification.
        Retry once on JSON parse failure.
        """
        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "case_id": case_id,
                    "bundle_description": bundle_description,
                    "available_tthc_codes": tthc_list,
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
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning(
                        "[Classifier] Invalid JSON from Qwen, retrying with stricter prompt"
                    )
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Hay tra lai DUNG FORMAT JSON. "
                            "Khong markdown, khong comment. Chi JSON thuan tuy: "
                            '{"tthc_code": "...", "tthc_name": "...", "confidence": 0.XX, '
                            '"urgency": "normal|high|critical", "unknown_tthc": false, '
                            '"reasoning": "..."}'
                        ),
                    })
                else:
                    logger.error(
                        f"[Classifier] JSON parse failed after retry: {content[:200]}"
                    )
                    return {
                        "tthc_code": "",
                        "tthc_name": "",
                        "confidence": 0.0,
                        "urgency": "normal",
                        "unknown_tthc": True,
                        "reasoning": "JSON parse failed after retry",
                    }

        # Unreachable but satisfies type checker
        return {"unknown_tthc": True, "confidence": 0.0, "urgency": "normal"}

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""


# Register with orchestrator
register_agent("classifier_agent", ClassifierAgent)
