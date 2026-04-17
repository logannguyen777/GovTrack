"""
backend/src/agents/implementations/doc_analyzer.py
DocAnalyzer Agent (Agent 2): multimodal document analysis using Qwen3-VL.

Pipeline per document:
  1. OCR with layout understanding
  2. Document type detection
  3. Entity extraction (per doc-type schema)
  4. Stamp / signature detection
  5. ND 30/2020 format validation (if applicable)
  6. Write results to GDB (Document properties + ExtractedEntity vertices)
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

from ...database import oss_get_signed_url
from ..base import AgentResult, BaseAgent
from ..orchestrator import register_agent

logger = logging.getLogger("govflow.agent.doc_analyzer")


class DocAnalyzerAgent(BaseAgent):
    """Multimodal document analysis: OCR, type detection, entity extraction."""

    profile_name = "doc_analyze_agent"

    CONFIDENCE_THRESHOLD = 0.7

    # Entity schemas per document type
    ENTITY_SCHEMAS: dict[str, list[str]] = {
        "gcn_qsdd": [
            "gcn_number",
            "owner_name",
            "land_parcel",
            "area_m2",
            "location",
            "issuing_authority",
            "issue_date",
        ],
        "don_de_nghi": [
            "applicant_name",
            "project_name",
            "project_type",
            "project_address",
            "request_type",
        ],
        "ban_ve_thiet_ke": [
            "building_type",
            "floor_area_m2",
            "height_m",
            "floors",
            "construction_class",
        ],
        "giay_phep_kinh_doanh": [
            "company_name",
            "tax_id",
            "business_type",
            "registered_address",
            "representative",
        ],
        "van_ban_tham_duyet_pccc": [
            "approval_number",
            "issuing_authority",
            "approval_date",
            "building_type",
            "conditions",
        ],
        "cam_ket_moi_truong": [
            "project_name",
            "investor",
            "commitment_number",
            "approval_authority",
            "approval_date",
        ],
        "chung_minh_nhan_dan": [
            "full_name",
            "date_of_birth",
            "id_number",
            "place_of_origin",
            "place_of_residence",
        ],
        "ho_chieu": [
            "full_name",
            "passport_number",
            "nationality",
            "date_of_birth",
            "expiry_date",
        ],
        "giay_khai_sinh": [
            "full_name",
            "date_of_birth",
            "place_of_birth",
            "father_name",
            "mother_name",
            "registration_number",
        ],
    }

    # Doc types requiring ND 30/2020 format validation
    ND30_DOC_TYPES: set[str] = {
        "quyet_dinh",
        "cong_van",
        "thong_bao",
        "giay_phep",
        "bien_ban",
        "giay_uy_quyen",
    }

    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """Required by ABC. Not used since run() is overridden."""
        return [{"role": "system", "content": self.profile.system_prompt}]

    async def run(self, case_id: str) -> AgentResult:
        """
        Override BaseAgent.run() for structured sequential document processing.
        Pattern follows PlannerAgent: fetch context → process → write GDB → return.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())

        logger.info(f"[DocAnalyzer] Starting on case {case_id}")
        await self._broadcast(
            case_id,
            "agent_started",
            {
                "agent_name": self.profile.name,
                "step_id": step_id,
            },
        )

        try:
            # Fetch all documents in the case's bundles
            documents = await self._get_gdb().execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document')"
                ".valueMap(true)",
                {"cid": case_id},
            )

            if not documents:
                logger.warning(f"[DocAnalyzer] No documents found for case {case_id}")

            # Process each document
            results: list[dict[str, Any]] = []
            for doc in documents:
                try:
                    result = await self._process_document(case_id, doc)
                    results.append(result)
                    await self._broadcast(
                        case_id,
                        "doc_processed",
                        {
                            "agent_name": self.profile.name,
                            "doc_id": result["doc_id"],
                            "doc_type": result["doc_type"],
                            "confidence": result["confidence"],
                        },
                    )
                except Exception as e:
                    doc_id = self._extract_prop(doc, "doc_id")
                    logger.error(f"[DocAnalyzer] Failed on doc {doc_id}: {e}", exc_info=True)
                    results.append(
                        {
                            "doc_id": doc_id,
                            "doc_type": "unknown",
                            "confidence": 0.0,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

            # Finalize
            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_doc_analyzer",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            output_summary = json.dumps(
                {
                    "documents_processed": len(results),
                    "documents_succeeded": sum(1 for r in results if r.get("status") != "failed"),
                    "results": results,
                },
                ensure_ascii=False,
            )

            await self._broadcast(
                case_id,
                "agent_completed",
                {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "documents_processed": len(results),
                    "duration_ms": round(duration_ms),
                },
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
            logger.error(f"[DocAnalyzer] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action="pipeline_doc_analyzer",
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

    async def _process_document(self, case_id: str, doc: dict) -> dict[str, Any]:
        """Run the full analysis pipeline on a single document."""
        doc_id = self._extract_prop(doc, "doc_id")
        oss_key = self._extract_prop(doc, "oss_key")
        filename = self._extract_prop(doc, "filename")

        logger.info(f"[DocAnalyzer] Processing doc {doc_id} ({filename})")

        # Step 1: Get signed URL for the document blob
        signed_url = oss_get_signed_url(oss_key)

        # Step 2: OCR with layout understanding
        ocr_result = await self._ocr_with_layout(signed_url)
        ocr_text = ocr_result.get("text", "")
        ocr_quality = ocr_result.get("quality_score", 1.0)

        if not ocr_text.strip():
            logger.warning(f"[DocAnalyzer] Empty OCR for doc {doc_id}")
            ocr_quality = 0.0

        # Step 3: Detect document type
        doc_type, type_confidence = await self._detect_doc_type(signed_url, ocr_text)

        # Step 4: Extract entities (if confidence is sufficient and schema exists)
        entities: list[dict[str, Any]] = []
        if doc_type in self.ENTITY_SCHEMAS and type_confidence >= self.CONFIDENCE_THRESHOLD:
            entities = await self._extract_entities(ocr_text, doc_type)

        # Step 5: Detect stamps and signatures
        stamp_sig = await self._detect_stamp_signature(signed_url)

        # Step 6: ND 30/2020 format validation (if applicable)
        format_result: dict[str, Any] | None = None
        format_valid: bool | None = None
        if doc_type in self.ND30_DOC_TYPES:
            format_result = await self._validate_nd30(ocr_text)
            format_valid = format_result.get("valid")

        # Step 7: Write Document property updates to GDB
        needs_review = type_confidence < self.CONFIDENCE_THRESHOLD
        await self._get_gdb().execute(
            "g.V().has('Document', 'doc_id', did)"
            ".property('type', dtype).property('confidence', conf)"
            ".property('has_red_stamp', stamp).property('has_signature', sig)"
            ".property('format_valid', fmt).property('ocr_quality', quality)"
            ".property('needs_review', review)",
            {
                "did": doc_id,
                "dtype": doc_type,
                "conf": type_confidence,
                "stamp": stamp_sig.get("has_stamp", False),
                "sig": stamp_sig.get("has_signature", False),
                "fmt": format_valid if format_valid is not None else "",
                "quality": ocr_quality,
                "review": needs_review,
            },
        )

        # Step 8: Write ExtractedEntity vertices + EXTRACTED edges
        for entity in entities:
            entity_id = str(uuid.uuid4())
            await self._get_gdb().execute(
                "g.addV('ExtractedEntity')"
                ".property('entity_id', eid).property('field_name', fname)"
                ".property('value', val).property('confidence', conf)"
                ".property('page_num', pnum)"
                ".as('entity')"
                ".V().has('Document', 'doc_id', did).addE('EXTRACTED').to('entity')",
                {
                    "eid": entity_id,
                    "fname": entity.get("field_name", ""),
                    "val": str(entity.get("value", "")),
                    "conf": entity.get("confidence", 0.0),
                    "pnum": entity.get("page_num", 1),
                    "did": doc_id,
                },
            )

        if needs_review:
            logger.warning(
                f"[DocAnalyzer] Doc {doc_id} confidence {type_confidence:.2f} "
                f"< threshold {self.CONFIDENCE_THRESHOLD}, flagged for review"
            )

        return {
            "doc_id": doc_id,
            "filename": filename,
            "doc_type": doc_type,
            "confidence": type_confidence,
            "entity_count": len(entities),
            "has_stamp": stamp_sig.get("has_stamp", False),
            "has_signature": stamp_sig.get("has_signature", False),
            "format_valid": format_valid,
            "ocr_quality": ocr_quality,
            "needs_human_review": needs_review,
        }

    # ------------------------------------------------------------------
    # VL / LLM call methods
    # ------------------------------------------------------------------

    async def _ocr_with_layout(self, signed_url: str) -> dict[str, Any]:
        """Send image to Qwen3-VL for OCR with layout understanding."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Trich xuat toan bo noi dung van ban tu hinh anh, giu nguyen bo cuc. "
                    'Tra ve JSON: {"text": "...", "layout_blocks": '
                    '[{"type": "header|body|table|footer", "text": "..."}], '
                    '"quality_score": 0.0-1.0}'
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": signed_url}},
                    {
                        "type": "text",
                        "text": "OCR toan bo van ban nay, giu nguyen bo cuc. Tra ve JSON.",
                    },
                ],
            },
        ]
        return await self._vl_call_json(messages, model="vision")

    async def _detect_doc_type(self, signed_url: str, ocr_text: str) -> tuple[str, float]:
        """Few-shot document type classification using image + OCR text."""
        messages = [
            {"role": "system", "content": self.profile.system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": signed_url}},
                    {
                        "type": "text",
                        "text": (
                            f"OCR text (500 ky tu dau): {ocr_text[:500]}\n\n"
                            "Nhan dien loai tai lieu. Chi tra ve JSON: "
                            '{"doc_type": "...", "confidence": 0.XX}'
                        ),
                    },
                ],
            },
        ]
        result = await self._vl_call_json(messages, model="vision")
        return (
            result.get("doc_type", "other"),
            float(result.get("confidence", 0.0)),
        )

    async def _extract_entities(self, ocr_text: str, doc_type: str) -> list[dict[str, Any]]:
        """Extract structured fields per document type schema. Text-only (no vision)."""
        schema_fields = self.ENTITY_SCHEMAS.get(doc_type, [])
        messages = [
            {
                "role": "system",
                "content": (
                    "Trich xuat thong tin tu van ban hanh chinh Viet Nam. "
                    "Chi tra ve gia tri doc duoc, khong doan. "
                    'Tra ve JSON array: [{"field_name": "...", "value": "...", '
                    '"confidence": 0.XX, "page_num": 1}]'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Loai tai lieu: {doc_type}\n"
                    "Cac truong can trich xuat: "
                    f"{json.dumps(schema_fields, ensure_ascii=False)}\n\n"
                    f"Noi dung van ban:\n{ocr_text[:3000]}\n\n"
                    "Trich xuat va tra ve JSON array."
                ),
            },
        ]
        result = await self._vl_call_json(messages, model="reasoning")
        if isinstance(result, list):
            return result
        return result.get("entities", result.get("extracted_fields", []))

    async def _detect_stamp_signature(self, signed_url: str) -> dict[str, Any]:
        """Detect red stamps (con dau do) and signatures in document image."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": signed_url}},
                    {
                        "type": "text",
                        "text": (
                            "Kiem tra tai lieu nay:\n"
                            "1) Co con dau do (moc tron co quan nha nuoc) khong?\n"
                            "2) Co chu ky khong?\n"
                            'Tra ve JSON: {"has_stamp": true/false, '
                            '"stamp_details": "...", "has_signature": true/false}'
                        ),
                    },
                ],
            },
        ]
        return await self._vl_call_json(messages, model="vision")

    async def _validate_nd30(self, ocr_text: str) -> dict[str, Any]:
        """Check ND 30/2020 format compliance. Text-only (no vision)."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Kiem tra the thuc van ban theo Nghi dinh 30/2020/ND-CP. "
                    "Cac thanh phan bat buoc: quoc_hieu, tieu_ngu, so_ky_hieu, "
                    "noi_ban_hanh, ngay_thang, trich_yeu, noi_dung, noi_nhan, nguoi_ky."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Noi dung van ban:\n{ocr_text[:2000]}\n\n"
                    "Kiem tra the thuc ND 30/2020. Tra ve JSON:\n"
                    '{"valid": true/false, "checks": '
                    '{"quoc_hieu": true/false, "tieu_ngu": true/false, ...}, '
                    '"issues": ["..."]}'
                ),
            },
        ]
        return await self._vl_call_json(messages, model="reasoning")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _vl_call_json(
        self,
        messages: list[dict[str, Any]],
        model: str = "vision",
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Call Qwen and parse the response as JSON.
        Strips markdown fences, retries once on parse failure.
        """
        for attempt in range(2):
            completion = await self.client.chat(
                messages=messages,
                model=model,
                temperature=0.2,
                max_tokens=1500,
            )

            content = completion.choices[0].message.content or ""

            # Strip markdown code fences (```json ... ```)
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

            try:
                parsed = json.loads(cleaned)
                return parsed
            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning("[DocAnalyzer] Invalid JSON from Qwen, retrying")
                    messages.append({"role": "assistant", "content": content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Output KHONG hop le JSON. Hay tra lai DUNG FORMAT JSON. "
                                "Khong markdown, khong comment. Chi JSON thuan tuy."
                            ),
                        }
                    )
                else:
                    logger.error(f"[DocAnalyzer] JSON parse failed after retry: {content[:200]}")
                    return {"error": "json_parse_failed", "raw": content[:500]}

        return {"error": "unreachable"}

    # ------------------------------------------------------------------
    # Public facade for /api/documents/extract (no GDB writes)
    # ------------------------------------------------------------------

    async def extract_entities_public(
        self,
        url: str,
        tthc_hint: str | None = None,
    ) -> Any:
        """
        Citizen-facing document extraction.
        Reuses private VL methods; does NOT write to GDB.
        Returns ExtractResponse suitable for wizard pre-fill.
        """
        from ...models.chat_schemas import ExtractedEntity, ExtractResponse

        extraction_id = str(uuid.uuid4())

        # OCR
        ocr_result = await self._ocr_with_layout(url)
        raw_text = ocr_result.get("text", "")

        # Detect document type
        doc_type, type_confidence = await self._detect_doc_type(url, raw_text)

        # Use tthc_hint to bias schema selection when doc type is unclear
        effective_doc_type = doc_type
        if tthc_hint and doc_type not in self.ENTITY_SCHEMAS:
            # Try to infer schema from TTHC context
            tthc_to_schema = {
                "1.001757": "chung_minh_nhan_dan",
                "1.004415": "don_de_nghi",
                "1.000046": "gcn_qsdd",
            }
            effective_doc_type = tthc_to_schema.get(tthc_hint, doc_type)

        # Extract entities (no GDB write)
        entities: list[dict] = []
        if (
            effective_doc_type in self.ENTITY_SCHEMAS
            and type_confidence >= self.CONFIDENCE_THRESHOLD
        ):
            raw_entities = await self._extract_entities(raw_text, effective_doc_type)
            if isinstance(raw_entities, list):
                entities = raw_entities

        # Map to ExtractedEntity schema
        extracted = [
            ExtractedEntity(
                key=e.get("field_name", e.get("key", "")),
                value=e.get("value", ""),
                confidence=float(e.get("confidence", 0.7)),
                bbox=e.get("bbox"),
            )
            for e in entities
            if e.get("field_name") or e.get("key")
        ]

        return ExtractResponse(
            extraction_id=extraction_id,
            document_type=doc_type if doc_type != "other" else None,
            entities=extracted,
            raw_text=raw_text[:3000],  # truncate for response size
            confidence=type_confidence,
        )

    @staticmethod
    def _extract_prop(vertex_map: dict, key: str) -> str:
        """Extract a property from Gremlin valueMap result (handles list wrapping)."""
        val = vertex_map.get(key, "")
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""


# Register with orchestrator
register_agent("doc_analyze_agent", DocAnalyzerAgent)
