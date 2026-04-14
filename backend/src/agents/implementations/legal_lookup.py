"""
backend/src/agents/implementations/legal_lookup.py
LegalLookup Agent (Agent 5): Agentic GraphRAG for Vietnamese legal reasoning.

5-step pipeline:
  1. Vector Recall — semantic search over law_chunks via pgvector
  2. Graph Expansion — traverse SUPERSEDED_BY/AMENDED_BY to current effective version
  3. Relevance Rerank — Qwen3-Max reranks candidates by case context
  4. Cross-Reference Expansion — follow REFERENCES edges 1-2 hops
  5. Citation Extraction — extract specific clause/point, write Citation + CITES edges
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from ...database import async_gremlin_submit, pg_connection
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.legal_lookup")


class LegalLookupAgent(BaseAgent):
    """Agentic GraphRAG — 5-step pipeline for Vietnamese legal citation."""

    profile_name = "legal_search_agent"

    TOP_K_VECTOR = 10
    TOP_K_RERANK = 5
    CONFIDENCE_THRESHOLD = 0.6
    MAX_CROSS_REF_DEPTH = 2
    MAX_CROSS_REF_PER_ARTICLE = 3

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    # ------------------------------------------------------------------
    # Main entry point (called by Orchestrator)
    # ------------------------------------------------------------------

    async def run(self, case_id: str) -> AgentResult:
        """Override BaseAgent.run() for deterministic 5-step pipeline."""
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[LegalLookup] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # Fetch case context for query building and reranking
            case_context = await self._get_case_context(case_id)
            query = self._build_query(case_context)
            logger.info(f"[LegalLookup] Query: {query}")

            # Run the 5-step pipeline
            citations = await self.lookup(query, case_context, case_id=case_id)

            # Build output
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_legal_lookup",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "citation_count": len(citations),
                "citations": citations,
                "query": query,
            }
            output_summary = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "citation_count": len(citations),
                "duration_ms": round(duration_ms),
            })

            logger.info(
                f"[LegalLookup] Case {case_id}: {len(citations)} citations, "
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
            logger.error(f"[LegalLookup] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_legal_lookup",
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
    # Public API — callable by other agents (e.g. Compliance)
    # ------------------------------------------------------------------

    async def lookup(
        self,
        query: str,
        case_context: dict[str, Any],
        case_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Core 5-step GraphRAG pipeline.

        Args:
            query: Natural language legal question in Vietnamese.
            case_context: Dict with tthc_name, project_type, area_m2, location, etc.
            case_id: Optional — when provided, Citation vertices are linked to the Case.

        Returns:
            List of citation dicts with: citation_id, law_code, article_num,
            clause_num, point_label, text_excerpt, applies_reason, confidence.
        """
        # ── Step 1: Vector Recall ────────────────────────────────
        candidates = await self._vector_recall(query)
        logger.info(f"[LegalLookup] Step 1 vector recall: {len(candidates)} candidates")

        if not candidates:
            logger.info("[LegalLookup] No vector matches, returning empty")
            return []

        # ── Step 2: Graph Expansion ──────────────────────────────
        expanded: list[dict[str, Any]] = []
        for c in candidates:
            effective = await self._resolve_effective_article(
                c["law_id"], str(c["article_number"])
            )
            if effective:
                effective["original_score"] = c.get("similarity", 0)
                expanded.append(effective)

        logger.info(f"[LegalLookup] Step 2 graph expansion: {len(expanded)} effective articles")

        if not expanded:
            logger.info("[LegalLookup] All articles superseded/repealed, returning empty")
            return []

        # ── Step 3: Relevance Rerank ─────────────────────────────
        reranked = await self._rerank_candidates(expanded, query, case_context)
        top_candidates = reranked[: self.TOP_K_RERANK]
        logger.info(f"[LegalLookup] Step 3 rerank: top {len(top_candidates)} selected")

        # ── Step 4: Cross-Reference Expansion ────────────────────
        enriched = await self._expand_cross_references(top_candidates)
        logger.info(f"[LegalLookup] Step 4 cross-ref expansion: {len(enriched)} total articles")

        # ── Step 5: Citation Extraction ──────────────────────────
        citations = await self._extract_citations(enriched, query, case_context, case_id)
        logger.info(f"[LegalLookup] Step 5 citation extraction: {len(citations)} citations written")

        return citations

    # ------------------------------------------------------------------
    # Step 1: Vector Recall
    # ------------------------------------------------------------------

    async def _vector_recall(self, query: str) -> list[dict[str, Any]]:
        """Semantic search over law_chunks via pgvector."""
        embeddings = await self.client.embed([query])
        query_vec = embeddings[0]
        vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

        sql = """
            SELECT law_id, article_number, clause_path, content, title,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM law_chunks
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """
        async with pg_connection() as conn:
            rows = await conn.fetch(sql, vec_str, self.TOP_K_VECTOR)

        return [
            {
                "law_id": r["law_id"],
                "article_number": r["article_number"],
                "clause_path": r["clause_path"],
                "content": r["content"],
                "title": r["title"],
                "similarity": float(r["similarity"]),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Step 2: Graph Expansion (amendment/supersession chain resolution)
    # ------------------------------------------------------------------

    async def _resolve_effective_article(
        self, law_id: str, article_number: str,
    ) -> dict[str, Any] | None:
        """
        For a candidate article, follow SUPERSEDED_BY then AMENDED_BY chains
        to find the current effective version. Returns None if fully repealed.
        """
        # Try to find the article in KG
        direct = await async_gremlin_submit(
            "g.V().hasLabel('Article')"
            ".has('law_code', law).has('num', num)"
            ".valueMap(true)",
            {"law": law_id, "num": article_number},
        )
        if not direct:
            # Article not in KG — use vector search content as-is
            return None

        article = direct[0]
        kg_id = self._extract_prop(article, "_kg_id")

        # Follow SUPERSEDED_BY chain to terminal node
        superseded = await async_gremlin_submit(
            "g.V().has('_kg_id', kg_id)"
            ".repeat(out('SUPERSEDED_BY'))"
            ".until(outE('SUPERSEDED_BY').count().is(0))"
            ".valueMap(true)",
            {"kg_id": kg_id},
        )
        if superseded:
            article = superseded[0]
            kg_id = self._extract_prop(article, "_kg_id")

        # Follow AMENDED_BY chain to get latest amendment
        amended = await async_gremlin_submit(
            "g.V().has('_kg_id', kg_id)"
            ".repeat(out('AMENDED_BY'))"
            ".until(outE('AMENDED_BY').count().is(0))"
            ".valueMap(true)",
            {"kg_id": kg_id},
        )
        if amended:
            article = amended[0]

        # Check if article was repealed
        status = self._extract_prop(article, "status")
        if status and status.lower() in ("repealed", "bai_bo"):
            return None

        return self._normalize_article(article)

    # ------------------------------------------------------------------
    # Step 3: Relevance Rerank
    # ------------------------------------------------------------------

    async def _rerank_candidates(
        self,
        candidates: list[dict[str, Any]],
        query: str,
        case_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """LLM rerank candidates by case-context relevance."""
        if len(candidates) <= 1:
            return candidates

        formatted = "\n".join(
            f"[{i}] {c['law_code']} Dieu {c['article_num']}: "
            f"{(c.get('content') or '')[:300]}"
            for i, c in enumerate(candidates)
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Ban la chuyen gia phap luat hanh chinh Viet Nam. "
                    "Xep hang cac dieu luat theo muc do lien quan den tinh huong cu the. "
                    "Chi giu lai cac dieu luat THUC SU lien quan."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": query,
                        "case_context": {
                            "tthc": case_context.get("tthc_name", ""),
                            "project": case_context.get("project_type", ""),
                            "location": case_context.get("location", ""),
                            "area": case_context.get("area_m2", ""),
                        },
                        "candidates": formatted,
                        "instruction": (
                            'Tra ve JSON: {"ranked_indices": [0,2,1,...], '
                            '"reasoning": "..."}'
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        completion = await self.client.chat(
            messages=messages,
            model=self.profile.model,
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content or ""
        try:
            result = json.loads(self._strip_markdown_fences(content))
            indices = result.get("ranked_indices", list(range(len(candidates))))
            return [
                candidates[i]
                for i in indices
                if isinstance(i, int) and 0 <= i < len(candidates)
            ]
        except (json.JSONDecodeError, IndexError, TypeError):
            logger.warning("[LegalLookup] Rerank JSON parse failed, using original order")
            return candidates

    # ------------------------------------------------------------------
    # Step 4: Cross-Reference Expansion
    # ------------------------------------------------------------------

    async def _expand_cross_references(
        self, candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Follow REFERENCES edges 1-2 hops, dedup by (law_code, article_num)."""
        visited: set[tuple[str, str]] = set()
        enriched: list[dict[str, Any]] = []

        for c in candidates:
            key = (c["law_code"], str(c["article_num"]))
            if key not in visited:
                visited.add(key)
                enriched.append(c)

        # BFS cross-reference expansion
        frontier = list(candidates)
        for depth in range(self.MAX_CROSS_REF_DEPTH):
            next_frontier: list[dict[str, Any]] = []
            for article in frontier:
                kg_id = article.get("_kg_id", "")
                if not kg_id:
                    continue
                refs = await async_gremlin_submit(
                    "g.V().has('_kg_id', kg_id)"
                    ".out('REFERENCES').valueMap(true)"
                    ".limit(lim)",
                    {"kg_id": kg_id, "lim": self.MAX_CROSS_REF_PER_ARTICLE},
                )
                for ref in refs:
                    normalized = self._normalize_article(ref)
                    ref_key = (normalized["law_code"], str(normalized["article_num"]))
                    if ref_key not in visited:
                        visited.add(ref_key)
                        normalized["is_cross_reference"] = True
                        normalized["cross_ref_depth"] = depth + 1
                        enriched.append(normalized)
                        next_frontier.append(normalized)
            frontier = next_frontier

        return enriched

    # ------------------------------------------------------------------
    # Step 5: Citation Extraction
    # ------------------------------------------------------------------

    async def _extract_citations(
        self,
        articles: list[dict[str, Any]],
        query: str,
        case_context: dict[str, Any],
        case_id: str | None,
    ) -> list[dict[str, Any]]:
        """For each article, extract citation via LLM, write to GDB."""
        citations: list[dict[str, Any]] = []

        for article in articles:
            citation = await self._extract_single_citation(article, query, case_context)
            if not citation or citation.get("confidence", 0) < self.CONFIDENCE_THRESHOLD:
                continue

            cit_id = str(uuid.uuid4())
            law_code = article["law_code"]
            article_num = article["article_num"]

            # Write Citation vertex
            await async_gremlin_submit(
                "g.addV('Citation')"
                ".property('citation_id', cit_id)"
                ".property('law_ref', law_ref)"
                ".property('article_ref', art_ref)"
                ".property('clause_num', clause_num)"
                ".property('point_label', point_label)"
                ".property('text_excerpt', excerpt)"
                ".property('applies_reason', reason)"
                ".property('confidence', conf)"
                ".property('relevance_score', conf)"
                ".property('snippet', excerpt)",
                {
                    "cit_id": cit_id,
                    "law_ref": law_code,
                    "art_ref": f"{law_code} Dieu {article_num}",
                    "clause_num": str(citation.get("clause_num", "")),
                    "point_label": citation.get("point_label", ""),
                    "excerpt": citation.get("text_excerpt", ""),
                    "reason": citation.get("applies_reason", ""),
                    "conf": float(citation.get("confidence", 0.0)),
                },
            )

            # Write CITES edge: Citation -> Article
            try:
                await async_gremlin_submit(
                    "g.V().has('Citation', 'citation_id', cit_id)"
                    ".addE('CITES')"
                    ".to(g.V().hasLabel('Article')"
                    ".has('law_code', law).has('num', num))",
                    {"cit_id": cit_id, "law": law_code, "num": str(article_num)},
                )
            except Exception as e:
                logger.warning(f"[LegalLookup] Failed to write CITES edge: {e}")

            # Link Citation to Case
            if case_id:
                try:
                    await async_gremlin_submit(
                        "g.V().has('Case', 'case_id', cid)"
                        ".addE('HAS_CITATION')"
                        ".to(g.V().has('Citation', 'citation_id', cit_id))",
                        {"cid": case_id, "cit_id": cit_id},
                    )
                except Exception as e:
                    logger.warning(f"[LegalLookup] Failed to link Citation to Case: {e}")

            citations.append({
                "citation_id": cit_id,
                "law_code": law_code,
                "article_num": article_num,
                "clause_num": citation.get("clause_num"),
                "point_label": citation.get("point_label"),
                "text_excerpt": citation.get("text_excerpt"),
                "applies_reason": citation.get("applies_reason"),
                "confidence": citation.get("confidence"),
                "article_ref": f"{law_code} Dieu {article_num}",
                "is_cross_reference": article.get("is_cross_reference", False),
            })

        return citations

    async def _extract_single_citation(
        self,
        article: dict[str, Any],
        query: str,
        case_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """LLM call to extract specific clause/point from one article."""
        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "article_text": article.get("content", ""),
                        "law_code": article["law_code"],
                        "article_num": article["article_num"],
                        "query": query,
                        "case_context": case_context,
                        "instruction": (
                            "Trich xuat citation cu the nhat tu dieu luat nay. "
                            'JSON: {"clause_num": X, "point_label": "...", '
                            '"text_excerpt": "...", "applies_reason": "...", '
                            '"confidence": 0.XX}'
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        completion = await self.client.chat(
            messages=messages,
            model=self.profile.model,
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content or ""
        try:
            return json.loads(self._strip_markdown_fences(content))
        except json.JSONDecodeError:
            logger.warning(
                f"[LegalLookup] Citation parse failed for "
                f"{article['law_code']} Dieu {article['article_num']}"
            )
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_case_context(self, case_id: str) -> dict[str, Any]:
        """Fetch case + matched TTHC info for query building."""
        cases = await async_gremlin_submit(
            "g.V().has('Case', 'case_id', cid).valueMap(true)",
            {"cid": case_id},
        )
        if not cases:
            raise ValueError(f"Case {case_id} not found")

        case = cases[0]
        tthc_code = self._extract_prop(case, "tthc_code")

        tthc: list[dict] = []
        if tthc_code:
            tthc = await async_gremlin_submit(
                "g.V().has('TTHCSpec', 'code', code).valueMap(true)",
                {"code": tthc_code},
            )

        return {
            "case_id": case_id,
            "tthc_code": tthc_code,
            "tthc_name": self._extract_prop(tthc[0], "name") if tthc else "",
            "project_type": self._extract_prop(case, "project_type"),
            "area_m2": self._extract_prop(case, "area_m2"),
            "location": self._extract_prop(case, "location"),
        }

    def _build_query(self, case_context: dict[str, Any]) -> str:
        """Build default legal search query from case context."""
        parts = ["Cac quy dinh phap luat lien quan den"]
        if case_context.get("tthc_name"):
            parts.append(case_context["tthc_name"])
        if case_context.get("project_type"):
            parts.append(f"loai du an: {case_context['project_type']}")
        if case_context.get("area_m2"):
            parts.append(f"dien tich: {case_context['area_m2']}m2")
        if case_context.get("location"):
            parts.append(f"tai: {case_context['location']}")
        return " ".join(parts)

    def _normalize_article(self, vertex_map: dict) -> dict[str, Any]:
        """Normalize a Gremlin valueMap(true) result into a flat dict."""
        return {
            "_kg_id": self._extract_prop(vertex_map, "_kg_id"),
            "law_code": (
                self._extract_prop(vertex_map, "law_code")
                or self._extract_prop(vertex_map, "law_id")
            ),
            "article_num": (
                self._extract_prop(vertex_map, "num")
                or self._extract_prop(vertex_map, "article_number")
            ),
            "content": (
                self._extract_prop(vertex_map, "text")
                or self._extract_prop(vertex_map, "content")
            ),
            "title": self._extract_prop(vertex_map, "title"),
            "status": self._extract_prop(vertex_map, "status"),
        }

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""

    @staticmethod
    def _strip_markdown_fences(content: str) -> str:
        """Strip ```json ... ``` fences from LLM output."""
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
        return re.sub(r"\n?```\s*$", "", cleaned).strip()


# Register with orchestrator
register_agent("legal_search_agent", LegalLookupAgent)
