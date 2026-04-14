"""
backend/src/agents/implementations/drafter.py
Drafter Agent (Agent 9): generate ND 30/2020 compliant administrative documents.

Pipeline:
  1. Parallel-fetch case context (case, tthc, decision, opinions, summaries,
     gaps, citations, existing drafts)
  2. Idempotency check (skip if draft already exists)
  3. Determine document type from decision (approve/deny/request_more)
  4. Load Jinja2 template from Hologres (graceful fallback to LLM)
  5. Prepare template variables from case context
  6. Render template or generate body with LLM
  7. Build full ND 30/2020 document (9 mandatory sections + DU THAO watermark)
  8. Validate against ND 30/2020 format rules
  9. Fix validation issues via LLM if needed
  10. Generate citizen-facing plain-language explanation (PII-stripped)
  11. Write Draft vertex + HAS_DRAFT edge to Context Graph
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

import jinja2

from ...database import async_gremlin_submit, pg_connection
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.drafter")

# ── PII patterns (consistent with summarizer.py) ─────────────────
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


# ── ND 30/2020 constants ─────────────────────────────────────────

ND30_REQUIRED_SECTIONS = [
    "quoc_hieu", "tieu_ngu", "ten_co_quan", "so_ky_hieu",
    "noi_ban_hanh", "ngay_thang", "trich_yeu", "noi_dung",
    "noi_nhan", "nguoi_ky",
]

TRICH_YEU_MAX_WORDS = 80

# Decision type -> document type mapping
DOC_TYPE_MAP = {
    "approve": "QuyetDinh",
    "deny": "CongVan",
    "request_more": "ThongBao",
}

# TTHC-specific approval doc type overrides
APPROVAL_TTHC_MAP = {
    "1.004415": "GiayPhep",   # Cap phep xay dung
    "1.001757": "GiayCN",     # GCN PCCC
    "1.000046": "GiayCN",     # GCN QSD dat
}

# Document type abbreviation for so/ky hieu
DOC_TYPE_ABBREV = {
    "GiayPhep": "GPXD",
    "QuyetDinh": "QD",
    "CongVan": "CV",
    "ThongBao": "TB",
    "GiayCN": "GCN",
}


class DrafterAgent(BaseAgent):
    """Generate ND 30/2020 compliant administrative documents."""

    profile_name = "draft_agent"

    # ── ABC stub ────────────────────────────────────────────────
    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    # ── Main entry point ────────────────────────────────────────
    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for deterministic drafter pipeline.
        Generate ND 30/2020 compliant draft document for a case.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[Drafter] Starting on case {case_id}")
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # ── Step 1: Parallel-fetch all case context ─────────
            (
                case_result,
                tthc_match,
                decision_result,
                opinions,
                summaries,
                gaps,
                citations,
                existing_drafts,
            ) = await asyncio.gather(
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid).valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('MATCHES_TTHC').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_DECISION').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_OPINION').valueMap(true)",
                    {"cid": case_id},
                ),
                async_gremlin_submit(
                    "g.V().has('Case', 'case_id', cid)"
                    ".out('HAS_SUMMARY').valueMap(true)",
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
                    ".out('HAS_DRAFT').valueMap(true)",
                    {"cid": case_id},
                ),
            )

            if not case_result:
                raise ValueError(f"Case {case_id} not found in graph")

            # ── Step 2: Idempotency check ───────────────────────
            if existing_drafts:
                logger.info(
                    f"[Drafter] Draft already exists for case {case_id}, skipping"
                )
                duration_ms = (time.monotonic() - start_time) * 1000
                usage = self.client.reset_usage()

                await self._log_step(
                    step_id=step_id, case_id=case_id,
                    action="pipeline_drafter",
                    usage=usage, duration_ms=duration_ms,
                    status="completed",
                )
                await self._broadcast(case_id, "agent_completed", {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "reason": "draft_exists",
                    "duration_ms": round(duration_ms),
                })

                return AgentResult(
                    agent_name=self.profile.name,
                    case_id=case_id,
                    status="completed",
                    output=json.dumps({
                        "reason": "draft_exists",
                        "existing_draft_count": len(existing_drafts),
                    }),
                    usage=usage,
                    duration_ms=duration_ms,
                )

            case_vertex = case_result[0]

            # ── Step 3: Extract decision ────────────────────────
            decision_data: dict[str, Any] = {}
            if decision_result:
                d = decision_result[0]
                decision_data = {
                    "type": self._extract_prop(d, "type")
                    or self._extract_prop(d, "decision_type"),
                    "reasoning": self._extract_prop(d, "reasoning"),
                }

            decision_type = decision_data.get("type") or "request_more"

            # ── Step 4: Determine doc type ──────────────────────
            tthc_data: dict[str, Any] = {}
            tthc_code = ""
            if tthc_match:
                tthc_data = {
                    "code": self._extract_prop(tthc_match[0], "code"),
                    "name": self._extract_prop(tthc_match[0], "name"),
                    "authority_level": self._extract_prop(tthc_match[0], "authority_level"),
                }
                tthc_code = tthc_data["code"]

            doc_type = self._determine_doc_type(decision_type, tthc_code)

            logger.info(
                f"[Drafter] Case {case_id}: decision={decision_type}, "
                f"doc_type={doc_type}, tthc={tthc_code}"
            )

            # ── Step 5: Build case_data dict ────────────────────
            case_data = self._build_case_data(
                case_vertex, tthc_data, decision_data,
                summaries, gaps, citations, opinions,
            )

            # ── Step 6: Load Jinja2 template ────────────────────
            template_data = await self._load_jinja_template(tthc_code, doc_type)

            # ── Step 7: Prepare template variables ──────────────
            template_vars = self._prepare_template_vars(
                case_data, decision_data, tthc_data, citations, gaps, opinions,
            )

            # ── Step 8: Render template or generate with LLM ───
            if template_data and template_data.get("body_template"):
                try:
                    rendered_body = self._render_jinja_template(
                        template_data["body_template"], template_vars,
                    )
                    logger.info("[Drafter] Rendered body from Jinja2 template")
                except jinja2.TemplateSyntaxError as e:
                    logger.warning(
                        f"[Drafter] Jinja2 syntax error: {e}, falling back to LLM"
                    )
                    rendered_body = await self._generate_body_with_llm(
                        case_data, doc_type, decision_type, citations, gaps,
                    )
                except jinja2.UndefinedError as e:
                    logger.warning(
                        f"[Drafter] Jinja2 undefined var: {e}, falling back to LLM"
                    )
                    rendered_body = await self._generate_body_with_llm(
                        case_data, doc_type, decision_type, citations, gaps,
                    )
            else:
                logger.info("[Drafter] No Jinja2 template found, using LLM generation")
                rendered_body = await self._generate_body_with_llm(
                    case_data, doc_type, decision_type, citations, gaps,
                )

            # ── Step 9: Build full ND 30/2020 document ──────────
            full_document = self._build_nd30_document(
                rendered_body, case_data, doc_type, template_vars,
            )

            # ── Step 10: Validate against ND 30/2020 rules ─────
            validation = self._validate_nd30(full_document)

            if not validation["valid"]:
                logger.warning(
                    f"[Drafter] ND30 validation failed: {validation['issues']}"
                )
                full_document = await self._fix_validation_issues(
                    full_document, validation["issues"],
                )
                validation = self._validate_nd30(full_document)

            # ── Step 11: Generate citizen explanation ────────────
            citizen_explanation = await self._generate_citizen_explanation(
                case_data, decision_type, gaps,
            )

            # ── Step 12: Write Draft vertex + HAS_DRAFT edge ───
            draft_id = f"draft-{case_id}-{uuid.uuid4().hex[:8]}"
            now = datetime.now(UTC).isoformat()

            await async_gremlin_submit(
                "g.addV('Draft')"
                ".property('draft_id', did)"
                ".property('content_markdown', content)"
                ".property('doc_type', dtype)"
                ".property('decision_type', dec_type)"
                ".property('validation_valid', vv)"
                ".property('validation_issues', vi)"
                ".property('citizen_explanation', cit_exp)"
                ".property('status', 'draft')"
                ".property('case_id', cid)"
                ".property('created_at', ts)"
                ".as('draft')"
                ".V().has('Case', 'case_id', cid)"
                ".addE('HAS_DRAFT').to('draft')",
                {
                    "did": draft_id,
                    "content": full_document,
                    "dtype": doc_type,
                    "dec_type": decision_type,
                    "vv": validation["valid"],
                    "vi": json.dumps(validation.get("issues", []),
                                     ensure_ascii=False),
                    "cit_exp": citizen_explanation,
                    "cid": case_id,
                    "ts": now,
                },
            )

            logger.info(
                f"[Drafter] Created draft {draft_id} for case {case_id} "
                f"(doc_type={doc_type}, valid={validation['valid']})"
            )

            # ── Log, broadcast, return ──────────────────────────
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_drafter",
                usage=usage, duration_ms=duration_ms,
                status="completed",
            )

            output_data = {
                "draft_id": draft_id,
                "doc_type": doc_type,
                "decision_type": decision_type,
                "validation": validation,
                "status": "draft",
            }
            output_str = json.dumps(output_data, ensure_ascii=False)

            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "draft_id": draft_id,
                "doc_type": doc_type,
                "validation_valid": validation["valid"],
                "duration_ms": round(duration_ms),
            })

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=output_str,
                tool_calls_count=0,
                usage=usage,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[Drafter] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id, case_id=case_id,
                action="pipeline_drafter",
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

    # ── Document type determination ─────────────────────────────

    @staticmethod
    def _determine_doc_type(decision_type: str, tthc_code: str) -> str:
        """Map decision type + TTHC code to output document type."""
        if decision_type == "approve":
            return APPROVAL_TTHC_MAP.get(tthc_code, "QuyetDinh")
        return DOC_TYPE_MAP.get(decision_type, "ThongBao")

    # ── Jinja2 template loading from Hologres ───────────────────

    @staticmethod
    async def _load_jinja_template(
        tthc_code: str, doc_type: str,
    ) -> dict[str, Any] | None:
        """
        Load a Jinja2 template from Hologres templates_nd30 table.
        Returns None if table doesn't exist, is empty, or no match found.
        """
        try:
            async with pg_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT template_code, template_name, content_html, placeholders "
                    "FROM templates_nd30 "
                    "WHERE category = $1 AND is_active = true "
                    "ORDER BY version DESC LIMIT 1",
                    doc_type,
                )
            if row:
                return {
                    "template_code": row["template_code"],
                    "template_name": row["template_name"],
                    "body_template": row["content_html"],
                    "placeholders": row["placeholders"],
                }
        except Exception as e:
            logger.warning(f"[Drafter] Hologres template query failed: {e}")
        return None

    # ── Template variable preparation ───────────────────────────

    @staticmethod
    def _prepare_template_vars(
        case_data: dict,
        decision_data: dict,
        tthc_data: dict,
        citations: list,
        gaps: list,
        opinions: list,
    ) -> dict[str, Any]:
        """Prepare variables for Jinja2 template rendering."""

        # Format citations from real Citation vertices
        formatted_citations = []
        for c in citations:
            law_ref = c.get("law_ref", [""])[0] if isinstance(c.get("law_ref"), list) else c.get("law_ref", "")
            art_ref = c.get("article_ref", [""])[0] if isinstance(c.get("article_ref"), list) else c.get("article_ref", "")
            snippet = c.get("snippet", [""])[0] if isinstance(c.get("snippet"), list) else c.get("snippet", "")
            if law_ref:
                formatted_citations.append({
                    "law_ref": law_ref,
                    "article_ref": art_ref,
                    "snippet": (snippet or "")[:150],
                    "display": f"{law_ref} Dieu {art_ref}" if art_ref else law_ref,
                })

        # Format gaps
        formatted_gaps = []
        for g in gaps:
            desc = g.get("description", [""])[0] if isinstance(g.get("description"), list) else g.get("description", "")
            fix = g.get("fix_suggestion", [""])[0] if isinstance(g.get("fix_suggestion"), list) else g.get("fix_suggestion", "")
            comp = g.get("component_name", [""])[0] if isinstance(g.get("component_name"), list) else g.get("component_name", "")
            formatted_gaps.append({
                "description": desc,
                "fix_suggestion": fix,
                "component_name": comp,
            })

        return {
            "applicant_name": case_data.get("applicant_display_name", "___"),
            "project_name": case_data.get("project_name", "___"),
            "project_address": case_data.get("project_address", "___"),
            "tthc_name": tthc_data.get("name", ""),
            "tthc_code": tthc_data.get("code", ""),
            "decision_type": decision_data.get("type", ""),
            "decision_reasoning": decision_data.get("reasoning", ""),
            "citations": formatted_citations,
            "gaps": formatted_gaps,
            "signer_title": "GIAM DOC",
            "signer_name": "___",
            "org_name": case_data.get("assigned_org_name", "SO XAY DUNG"),
            "parent_org": case_data.get("parent_org", "UY BAN NHAN DAN"),
            "province": case_data.get("province", "TINH BINH DUONG"),
        }

    # ── Jinja2 rendering ────────────────────────────────────────

    @staticmethod
    def _render_jinja_template(template_str: str, template_vars: dict) -> str:
        """Render a Jinja2 template string with variables."""
        env = jinja2.Environment(
            autoescape=False,
            undefined=jinja2.Undefined,
        )
        template = env.from_string(template_str)
        return template.render(**template_vars)

    # ── LLM body generation (fallback) ──────────────────────────

    async def _generate_body_with_llm(
        self,
        case_data: dict,
        doc_type: str,
        decision_type: str,
        citations: list,
        gaps: list,
    ) -> str:
        """Generate document body with LLM when no Jinja2 template is available."""
        # Format citations for LLM context (from real vertices only)
        citation_refs = []
        for c in citations:
            law_ref = c.get("law_ref", [""])[0] if isinstance(c.get("law_ref"), list) else c.get("law_ref", "")
            art_ref = c.get("article_ref", [""])[0] if isinstance(c.get("article_ref"), list) else c.get("article_ref", "")
            if law_ref:
                citation_refs.append(
                    f"{law_ref} Dieu {art_ref}" if art_ref else law_ref
                )

        # Format gaps for LLM context
        gap_reasons = []
        for g in gaps:
            desc = g.get("description", [""])[0] if isinstance(g.get("description"), list) else g.get("description", "")
            if desc:
                gap_reasons.append(desc)

        # Get staff summary if available
        staff_summary = case_data.get("staff_summary", "")

        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": json.dumps({
                    "doc_type": doc_type,
                    "decision_type": decision_type,
                    "tthc_name": case_data.get("tthc_name", ""),
                    "case_summary": staff_summary,
                    "citations": citation_refs,
                    "gaps": gap_reasons,
                    "instruction": (
                        "Soan noi dung chinh cua van ban. "
                        "Chi phan THAN VAN BAN, KHONG bao gom header/footer/quoc hieu/tieu ngu. "
                        "Chi su dung cac trich dan phap luat da cho, KHONG tu tao them."
                    ),
                }, ensure_ascii=False),
            },
        ]

        completion = await self.client.chat(
            messages=messages,
            model=self.profile.model,
            temperature=0.3,
            max_tokens=2048,
        )

        return completion.choices[0].message.content or ""

    # ── ND 30/2020 document builder ─────────────────────────────

    @staticmethod
    def _build_nd30_document(
        rendered_body: str,
        case_data: dict,
        doc_type: str,
        template_vars: dict,
    ) -> str:
        """Build full ND 30/2020 compliant document structure."""
        now = datetime.now(UTC)
        org_name = template_vars.get("org_name", "SO XAY DUNG")
        parent_org = template_vars.get("parent_org", "UY BAN NHAN DAN")
        province = template_vars.get("province", "TINH BINH DUONG")
        province_short = province.replace("TINH ", "")
        abbrev = DOC_TYPE_ABBREV.get(doc_type, "VB")
        org_abbrev = "SXD"  # Simplified; production uses org mapping

        # Trich yeu (max 80 words)
        tthc_name = template_vars.get("tthc_name", "")
        trich_yeu = f"V/v {tthc_name}" if tthc_name else f"V/v xu ly ho so"
        trich_yeu_words = trich_yeu.split()
        if len(trich_yeu_words) > TRICH_YEU_MAX_WORDS:
            trich_yeu = " ".join(trich_yeu_words[:TRICH_YEU_MAX_WORDS])

        # Build noi nhan
        noi_nhan = "- Nhu tren;\n- Luu: VT, QLXD."

        doc = (
            f"**{parent_org}**\n"
            f"**{province}**\n"
            f"**{org_name}**\n"
            f"\n"
            f"**CONG HOA XA HOI CHU NGHIA VIET NAM**\n"
            f"*Doc lap - Tu do - Hanh phuc*\n"
            f"---\n"
            f"\n"
            f"So: ___/{abbrev}-{org_abbrev}"
            f"\n\n"
            f"{province_short}, ngay {now.day} thang {now.month} nam {now.year}\n"
            f"\n"
            f"**{trich_yeu}**\n"
            f"\n"
            f"{rendered_body}\n"
            f"\n"
            f"**Noi nhan:**\n"
            f"{noi_nhan}\n"
            f"\n"
            f"**{template_vars.get('signer_title', 'GIAM DOC')}**\n"
            f"*(Ky so)*\n"
            f"**{template_vars.get('signer_name', '___')}**\n"
            f"\n"
            f"---\n"
            f"*DU THAO - Chua phat hanh*\n"
        )

        return doc

    # ── ND 30/2020 validation ───────────────────────────────────

    @staticmethod
    def _validate_nd30(document: str) -> dict[str, Any]:
        """Validate document against ND 30/2020 format rules."""
        issues: list[str] = []

        # 1. Quoc hieu
        if "CONG HOA XA HOI CHU NGHIA VIET NAM" not in document:
            issues.append("Thieu quoc hieu")

        # 2. Tieu ngu
        if "Doc lap - Tu do - Hanh phuc" not in document:
            issues.append("Thieu tieu ngu")

        # 3. So/ky hieu
        if "So:" not in document:
            issues.append("Thieu so/ky hieu")

        # 4. Ngay thang nam
        if "ngay" not in document or "thang" not in document or "nam" not in document:
            issues.append("Thieu ngay thang nam")

        # 5. Noi nhan
        if "Noi nhan" not in document:
            issues.append("Thieu noi nhan")

        # 6. Nguoi ky
        if "Ky so" not in document and "Ky" not in document:
            issues.append("Thieu vi tri nguoi ky")

        # 7. DU THAO watermark
        if "DU THAO" not in document:
            issues.append("Thieu danh dau DU THAO")

        return {"valid": len(issues) == 0, "issues": issues}

    # ── Validation fix via LLM ──────────────────────────────────

    async def _fix_validation_issues(
        self, document: str, issues: list[str],
    ) -> str:
        """Use LLM to fix ND30 validation issues in the document."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Sua van ban cho dung the thuc ND 30/2020. "
                    "Giu nguyen noi dung chinh, chi sua format/cau truc."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Van ban:\n{document}\n\n"
                    f"Loi can sua: {json.dumps(issues, ensure_ascii=False)}\n\n"
                    f"Sua va tra ve van ban hoan chinh. "
                    f"Dam bao co DU THAO watermark o cuoi."
                ),
            },
        ]

        completion = await self.client.chat(
            messages=messages,
            model=self.profile.model,
            temperature=0.2,
            max_tokens=4096,
        )

        return completion.choices[0].message.content or document

    # ── Citizen explanation generation ──────────────────────────

    async def _generate_citizen_explanation(
        self,
        case_data: dict,
        decision_type: str,
        gaps: list,
    ) -> str:
        """Generate plain-language explanation for citizen. PII-stripped."""
        instruction_map = {
            "approve": (
                "Giai thich cho cong dan: ho so da duoc duyet, "
                "cac buoc nhan ket qua."
            ),
            "deny": (
                "Giai thich cho cong dan: vi sao bi tu choi, "
                "can lam gi tiep theo."
            ),
            "request_more": (
                "Giai thich cho cong dan: can bo sung gi, "
                "nop o dau, thoi han."
            ),
        }

        # Format gap fix suggestions for citizen context
        fix_suggestions = []
        for g in gaps:
            fix = g.get("fix_suggestion", [""])[0] if isinstance(g.get("fix_suggestion"), list) else g.get("fix_suggestion", "")
            if fix:
                fix_suggestions.append(fix)

        messages = [
            {
                "role": "system",
                "content": (
                    "Viet giai thich bang tieng Viet binh dan, than thien, "
                    "hanh dong duoc. KHONG chua thong tin ca nhan "
                    "(so CCCD, SDT, dia chi chi tiet, ten nguoi cu the). "
                    "Thay bang mo ta chung neu can."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "decision_type": decision_type,
                    "tthc_name": case_data.get("tthc_name", ""),
                    "gaps": fix_suggestions,
                    "instruction": instruction_map.get(
                        decision_type,
                        instruction_map["request_more"],
                    ),
                }, ensure_ascii=False),
            },
        ]

        completion = await self.client.chat(
            messages=messages,
            model=self.profile.model,
            temperature=0.4,
            max_tokens=1024,
        )

        explanation = completion.choices[0].message.content or ""

        # PII enforcement
        explanation = _strip_pii(explanation)
        if _has_pii(explanation):
            logger.warning(
                f"[Drafter] PII detected in citizen explanation after "
                f"stripping, regenerating for case {case_data.get('case_id', '')}"
            )
            explanation = await self._regenerate_without_pii(explanation)

        return explanation

    async def _regenerate_without_pii(self, original_text: str) -> str:
        """Regenerate text with explicit PII removal instruction."""
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
            max_tokens=1024,
        )

        result = completion.choices[0].message.content or original_text
        return _strip_pii(result)

    # ── Case data normalization ─────────────────────────────────

    def _build_case_data(
        self,
        case_vertex: dict,
        tthc_data: dict,
        decision_data: dict,
        summaries: list,
        gaps: list,
        citations: list,
        opinions: list,
    ) -> dict[str, Any]:
        """Normalize all fetched graph data into a single dict for rendering."""
        case_data: dict[str, Any] = {
            "case_id": self._extract_prop(case_vertex, "case_id"),
            "status": self._extract_prop(case_vertex, "status"),
            "tthc_name": tthc_data.get("name", ""),
            "tthc_code": tthc_data.get("code", ""),
            "assigned_org_name": self._extract_prop(case_vertex, "assigned_org_name") or "SO XAY DUNG",
            "parent_org": "UY BAN NHAN DAN",
            "province": self._extract_prop(case_vertex, "province") or "TINH BINH DUONG",
            "applicant_display_name": self._extract_prop(case_vertex, "applicant_name") or "___",
            "project_name": self._extract_prop(case_vertex, "project_name") or "___",
            "project_address": self._extract_prop(case_vertex, "project_address") or "___",
        }

        # Decision
        case_data["decision"] = decision_data

        # Staff summary (for LLM generation context)
        staff_summary = ""
        for s in summaries:
            mode = self._extract_prop(s, "mode")
            if mode == "staff":
                staff_summary = self._extract_prop(s, "text")
                break
        case_data["staff_summary"] = staff_summary

        # Gaps
        case_data["gaps"] = [
            {
                "description": self._extract_prop(g, "description"),
                "severity": self._extract_prop(g, "severity"),
                "component_name": self._extract_prop(g, "component_name"),
                "fix_suggestion": self._extract_prop(g, "fix_suggestion"),
            }
            for g in gaps
        ]

        # Citations
        case_data["citations"] = [
            {
                "law_ref": self._extract_prop(c, "law_ref"),
                "article_ref": self._extract_prop(c, "article_ref"),
                "snippet": (self._extract_prop(c, "snippet") or "")[:150],
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
            }
            for o in opinions
        ]

        return case_data

    # ── LLM JSON call with retry ────────────────────────────────

    async def _llm_json_call(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Call Qwen and parse JSON response. Retry once on parse failure.
        Pattern shared with summarizer.py and compliance.py.
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
                    logger.warning("[Drafter] Invalid JSON from Qwen, retrying")
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Output KHONG hop le JSON. Tra lai DUNG FORMAT: "
                            '{"content_markdown": "...", "doc_type": "...", '
                            '"validation": {"valid": true, "issues": []}, '
                            '"citizen_explanation": "..."}. '
                            "Chi tra ve JSON, khong co text khac."
                        ),
                    })
                else:
                    logger.error(
                        f"[Drafter] JSON parse failed after retry: {content[:200]}"
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


# Register with orchestrator
register_agent("draft_agent", DrafterAgent)
