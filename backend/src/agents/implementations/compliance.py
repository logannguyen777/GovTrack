"""
backend/src/agents/implementations/compliance.py
Compliance Agent (Agent 4): check case bundle completeness against TTHC
requirements, detect gaps, cite governing law, evaluate conditional
requirements, and compute compliance score.

Pipeline:
  1. Verify MATCHES_TTHC edge exists (Classifier must have run)
  2. Fetch all RequiredComponents for matched TTHC
  3. Fetch case documents with extracted entities
  4. Find missing components (no SATISFIES edge)
  5. Fetch legal basis articles from Knowledge Graph
  6. Single LLM call: evaluate conditions, generate gaps with citations
  7. Write Gap/Citation vertices and edges to Context Graph
  8. Compute and write compliance_score to Case
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

# async_gremlin_submit replaced by self._get_gdb().execute() per task 1.1
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.compliance")


class ComplianceAgent(BaseAgent):
    """Check bundle completeness against TTHC requirements, detect gaps, cite law."""

    profile_name = "compliance_agent"

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for deterministic compliance pipeline.
        Steps: verify TTHC match -> fetch requirements -> find missing ->
               LLM evaluation -> write gaps -> compute score.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Compliance] Starting on case {case_id}")
        await self._broadcast(
            case_id,
            "agent_started",
            {
                "agent_name": self.profile.name,
                "step_id": step_id,
            },
        )

        try:
            # ── Step 1: Verify MATCHES_TTHC edge exists ──────────────
            tthc_match = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid).out('MATCHES_TTHC').valueMap(true)",
                {"cid": case_id},
            )
            if not tthc_match:
                raise ValueError(
                    f"Case {case_id}: no MATCHES_TTHC edge found. "
                    "Classifier must run before Compliance."
                )

            tthc_spec = tthc_match[0]
            tthc_code = self._extract_prop(tthc_spec, "code")
            tthc_name = self._extract_prop(tthc_spec, "name")
            logger.info(f"[Compliance] Case {case_id} matched TTHC: {tthc_code} ({tthc_name})")

            # ── Step 2: Fetch all RequiredComponents for this TTHC ───
            all_required = await self._get_gdb().execute(
                "g.V().has('TTHCSpec', 'code', code).out('REQUIRES').valueMap(true)",
                {"code": tthc_code},
            )
            logger.info(
                f"[Compliance] TTHC {tthc_code} has {len(all_required)} required components"
            )

            # ── Step 3: Fetch case documents with entities ───────────
            documents = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                ".valueMap(true)",
                {"cid": case_id},
            )

            doc_summaries: list[dict[str, Any]] = []
            for doc in documents:
                doc_id = self._extract_prop(doc, "doc_id")
                doc_type = self._extract_prop(doc, "type") or "unknown"

                entities = await self._get_gdb().execute(
                    "g.V().has('Document', 'doc_id', did)"
                    ".out('EXTRACTED').hasLabel('ExtractedEntity')"
                    ".valueMap('field_name', 'value')",
                    {"did": doc_id},
                )

                entity_list = []
                for e in entities:
                    fname = self._extract_prop(e, "field_name")
                    val = self._extract_prop(e, "value")
                    if fname:
                        entity_list.append({"field_name": fname, "value": val})

                doc_summaries.append(
                    {
                        "doc_id": doc_id,
                        "type": doc_type,
                        "entities": entity_list,
                    }
                )

            # ── Step 4: Find missing components ──────────────────────
            missing_components = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('MATCHES_TTHC').out('REQUIRES').as('req')"
                ".where(__.not(__.in('SATISFIES')))"
                ".valueMap(true)",
                {"cid": case_id},
            )
            logger.info(f"[Compliance] Found {len(missing_components)} missing components")

            await self._emit(
                "graph_op",
                graph_op={
                    "query": "MATCHES_TTHC > REQUIRES WHERE NOT IN SATISFIES",
                    "nodes": [
                        {
                            "name": self._extract_prop(c, "name"),
                            "_kg_id": self._extract_prop(c, "_kg_id"),
                            "is_required": self._extract_prop(c, "is_required"),
                        }
                        for c in (missing_components or [])[:20]
                    ],
                    "edges": [],
                },
            )

            # ── Step 5: Fetch legal basis from KG ────────────────────
            legal_basis = await self._get_gdb().execute(
                "g.V().has('TTHCSpec', 'code', code).out('GOVERNED_BY').valueMap(true)",
                {"code": tthc_code},
            )

            await self._emit(
                "graph_op",
                graph_op={
                    "query": f"TTHCSpec[{tthc_code}] GOVERNED_BY > Article",
                    "nodes": [
                        {
                            "law_code": self._extract_prop(a, "law_code")
                            or self._extract_prop(a, "law_id"),
                            "num": self._extract_prop(a, "num")
                            or self._extract_prop(a, "article_number"),
                        }
                        for a in (legal_basis or [])[:20]
                    ],
                    "edges": [],
                },
            )

            legal_articles = []
            for art in legal_basis:
                legal_articles.append(
                    {
                        "law_code": self._extract_prop(art, "law_code")
                        or self._extract_prop(art, "law_id"),
                        "article_num": self._extract_prop(art, "num")
                        or self._extract_prop(art, "article_number"),
                        "title": self._extract_prop(art, "title"),
                        "text_excerpt": self._extract_prop(art, "text")
                        or self._extract_prop(art, "content"),
                    }
                )

            # ── Step 6: Build context for LLM ────────────────────────
            required_components_data = []
            for comp in all_required:
                required_components_data.append(
                    {
                        "name": self._extract_prop(comp, "name"),
                        "is_required": self._extract_bool(comp, "is_required", True),
                        "condition": self._extract_prop(comp, "condition"),
                        "doc_type_match": self._extract_prop(comp, "doc_type_match"),
                        "_kg_id": self._extract_prop(comp, "_kg_id"),
                    }
                )

            missing_data = []
            for comp in missing_components:
                missing_data.append(
                    {
                        "name": self._extract_prop(comp, "name"),
                        "is_required": self._extract_bool(comp, "is_required", True),
                        "condition": self._extract_prop(comp, "condition"),
                        "_kg_id": self._extract_prop(comp, "_kg_id"),
                    }
                )

            case_context = {
                "case_id": case_id,
                "tthc_code": tthc_code,
                "tthc_name": tthc_name,
                "documents_submitted": [
                    {"type": d["type"], "entities": d["entities"][:5]} for d in doc_summaries
                ],
                "total_required_components": len(all_required),
                "all_required_components": required_components_data,
                "missing_components": missing_data,
                "legal_basis": legal_articles,
            }

            # ── Step 7: Single LLM call for compliance evaluation ────
            evaluation = await self._evaluate_compliance(case_context)

            # ── Step 8: Write gaps to GDB (logical transaction) ──────
            confirmed_gaps = evaluation.get("gaps", [])
            gap_write_results: list[dict[str, Any]] = []

            # ── Step 9: Compute compliance score ─────────────────────
            total_mandatory = sum(1 for c in required_components_data if c["is_required"])
            blocker_count = sum(
                1 for g in confirmed_gaps
                if g.get("is_blocking", True) and g.get("severity") != "info"
            )
            warning_count = sum(
                1 for g in confirmed_gaps
                if not g.get("is_blocking", True) or g.get("severity") == "warning"
            )
            satisfied_count = total_mandatory - blocker_count
            compliance_score = round((satisfied_count / max(total_mandatory, 1)) * 100, 1)

            # Collect all gap mutations + the compliance_score update into a
            # logical transaction so they commit atomically.  Retry on
            # ConcurrentModificationException (max 3 tries, 100ms-1s backoff).
            gdb_tx = self._get_gdb()
            async with gdb_tx.transaction() as tx:
                for gap in confirmed_gaps:
                    gap_id = str(uuid.uuid4())
                    component_name = gap.get("component_name", "unknown")
                    severity = gap.get("severity", "blocker")
                    is_blocking = gap.get("is_blocking", True)
                    reason = gap.get("reason", f"Thieu {component_name}")
                    fix_suggestion = gap.get("fix_suggestion", "")

                    # Gap vertex + HAS_GAP edge
                    await tx.submit(
                        "g.addV('Gap')"
                        ".property('gap_id', gap_id)"
                        ".property('description', desc)"
                        ".property('severity', severity)"
                        ".property('is_blocking', is_blk)"
                        ".property('component_name', comp)"
                        ".property('fix_suggestion', fix_sug)"
                        ".property('case_id', cid)"
                        ".as('gap')"
                        ".V().has('Case', 'case_id', cid)"
                        ".addE('HAS_GAP').to('gap')",
                        {
                            "gap_id": gap_id,
                            "desc": reason,
                            "severity": severity,
                            "is_blk": is_blocking,
                            "comp": component_name,
                            "fix_sug": fix_suggestion,
                            "cid": case_id,
                        },
                    )

                    # Optional GAP_FOR edge (non-fatal if missing)
                    req_kg_id = self._find_req_kg_id(component_name, missing_data)
                    if req_kg_id:
                        await tx.submit(
                            "g.V().has('gap_id', gid)"
                            ".addE('GAP_FOR')"
                            ".to(__.V().has('_kg_id', rid))",
                            {"gid": gap_id, "rid": req_kg_id},
                        )

                    # Citation vertex + CITES edge
                    law_citation = gap.get("law_citation", "")
                    if law_citation:
                        cit_id = str(uuid.uuid4())
                        await tx.submit(
                            "g.addV('Citation')"
                            ".property('citation_id', cit_id)"
                            ".property('law_ref', law_ref)"
                            ".property('article_ref', art_ref)"
                            ".property('relevance_score', score)"
                            ".property('snippet', snippet)",
                            {
                                "cit_id": cit_id,
                                "law_ref": law_citation,
                                "art_ref": law_citation,
                                "score": 1.0,
                                "snippet": reason,
                            },
                        )
                        await tx.submit(
                            "g.V().has('gap_id', gid)"
                            ".addE('CITES')"
                            ".to(__.V().has('citation_id', cid))",
                            {"gid": gap_id, "cid": cit_id},
                        )

                    gap_write_results.append(
                        {
                            "component_name": component_name,
                            "severity": severity,
                            "is_blocking": is_blocking,
                            "reason": reason,
                            "fix_suggestion": fix_suggestion,
                            "law_citation": law_citation,
                        }
                    )

                # ── Step 10: Write compliance_score to Case ──────────────
                # Included in same transaction as gap writes
                await tx.submit(
                    "g.V().has('Case', 'case_id', cid).property('compliance_score', score)",
                    {"cid": case_id, "score": compliance_score},
                )
                await tx.submit(
                    "g.V().has('Case', 'case_id', cid).property('status', 'gap_checked')",
                    {"cid": case_id},
                )

            # ── Step 11: Build output, log, broadcast ────────────────
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_compliance_checker",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "compliance_score": compliance_score,
                "total_required": len(all_required),
                "total_mandatory": total_mandatory,
                "satisfied": satisfied_count,
                "blocker_count": blocker_count,
                "warning_count": warning_count,
                "gaps": gap_write_results,
                "gap_count": len(gap_write_results),
                "conditional_skipped": evaluation.get("conditional_skipped", []),
                "satisfied_components": evaluation.get("satisfied_components", []),
                "reasoning": evaluation.get("reasoning", ""),
            }

            output_summary = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(
                case_id,
                "agent_completed",
                {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "compliance_score": compliance_score,
                    "gap_count": len(gap_write_results),
                    "duration_ms": round(duration_ms),
                },
            )

            logger.info(
                f"[Compliance] Case {case_id}: score={compliance_score}, "
                f"gaps={len(gap_write_results)}, duration={round(duration_ms)}ms"
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
            logger.error(f"[Compliance] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_compliance_checker",
                usage=self.client.reset_usage(),
                duration_ms=duration_ms,
                status="failed",
                error=str(e),
            )

            await self._broadcast(
                case_id,
                "agent_failed",
                {
                    "agent_name": self.profile.name,
                    "error": str(e),
                },
            )

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

    async def _evaluate_compliance(self, case_context: dict) -> dict[str, Any]:
        """
        Single Qwen call to evaluate all missing components.
        Returns JSON with gaps, conditional_skipped, satisfied_components, reasoning.
        """
        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps(case_context, ensure_ascii=False),
            },
        ]

        for attempt in range(2):
            completion = await self.client.chat(
                messages=messages,
                model=self.profile.model,
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            content = completion.choices[0].message.content or ""

            # Strip markdown fences if present
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

            try:
                result = json.loads(cleaned)
                # Validate structure
                if "gaps" not in result:
                    result["gaps"] = []
                return result
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning("[Compliance] Invalid JSON from Qwen, retrying")
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Output KHONG hop le JSON. Tra lai DUNG FORMAT: "
                                '{"gaps": [{"component_name": "...", "reason": "...", '
                                '"severity": "blocker|warning|info", '
                                '"is_blocking": true, '
                                '"fix_suggestion": "...", '
                                '"law_citation": "..."}], "compliance_score": XX, '
                                '"satisfied_components": [...], "conditional_skipped": [...], '
                                '"reasoning": "..."}'
                            ),
                        }
                    )
                else:
                    logger.error(f"[Compliance] JSON parse failed after retry: {content[:200]}")
                    return {
                        "gaps": [
                            {
                                "component_name": m["name"],
                                "reason": f"Thieu {m['name']}",
                                "severity": "blocker" if m["is_required"] else "warning",
                                "fix_suggestion": "",
                                "law_citation": "",
                            }
                            for m in case_context.get("missing_components", [])
                        ],
                        "satisfied_components": [],
                        "conditional_skipped": [],
                        "reasoning": "Fallback: LLM JSON parse failed, all missing treated as gaps",
                    }

        # Unreachable but satisfies type checker
        return {"gaps": [], "reasoning": "unexpected"}

    async def _call_legal_lookup(self, case_id: str, query: str) -> str:
        """
        Call LegalLookupAgent directly (not via orchestrator) for additional
        legal context.  Propagates self._event_emitter so WS events flow
        through to the client even when invoked from within ComplianceAgent.
        """
        from .legal_lookup import LegalLookupAgent

        agent = LegalLookupAgent()
        # Forward the orchestrator-injected emitter so _emit() calls inside
        # LegalLookupAgent reach the WebSocket broadcast layer.
        agent._event_emitter = self._event_emitter
        return (await agent.run(case_id)).output

    @staticmethod
    def _find_req_kg_id(component_name: str, missing_data: list[dict]) -> str:
        """Find the _kg_id for a missing component by name."""
        for comp in missing_data:
            if comp.get("name", "").lower() == component_name.lower():
                return comp.get("_kg_id", "")
        # Fuzzy fallback: partial match
        for comp in missing_data:
            if component_name.lower() in comp.get("name", "").lower():
                return comp.get("_kg_id", "")
        return ""

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


# Register with orchestrator
register_agent("compliance_agent", ComplianceAgent)
