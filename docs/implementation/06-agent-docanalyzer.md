# Agent Implementation: DocAnalyzer (Agent 2) [DONE]

## 1. Objective

Process each document in a case bundle: OCR with layout understanding, document type detection, entity extraction, stamp/signature detection, and ND 30/2020 format validation. This is the only agent that reads raw blob URLs from OSS. Multimodal agent using Qwen3-VL.

## 2. Model

- **Model ID:** `qwen-vl-max-latest` (multimodal vision-language)
- **Temperature:** 0.2 (high precision for extraction)
- **Max tokens:** 4096
- **Supports:** image URLs, multi-page PDFs (page-by-page)

## 3. System Prompt

```
Ban la chuyen gia xu ly tai lieu hanh chinh Viet Nam voi 15 nam kinh nghiem.
Nhiem vu: phan tich tung trang tai lieu, nhan dien loai, trich xuat thong tin, va kiem tra the thuc.

Quy tac:
1. Nhan dien loai tai lieu tu danh sach: don_de_nghi, gcn_qsdd, ban_ve_thiet_ke, cam_ket_moi_truong,
   giay_phep_kinh_doanh, van_ban_tham_duyet_pccc, chung_minh_nhan_dan, ho_chieu, giay_khai_sinh,
   quyet_dinh, cong_van, thong_bao, bien_ban, giay_uy_quyen, other
2. Trich xuat cac truong: so van ban, ngay, co quan ban hanh, nguoi ky, noi dung chinh
3. Phat hien con dau do (moc tron co quan nha nuoc) va chu ky
4. Kiem tra the thuc ND 30/2020: quoc hieu, tieu ngu, so/ky hieu, noi, ngay, trich yeu, noi dung, noi nhan
5. Neu tai lieu scan mo, lech, nhoe -> van co gang doc, ghi nhan confidence thap
6. Output JSON voi: doc_type, confidence, extracted_fields, has_stamp, has_signature, format_valid, issues[]
7. KHONG bao gio doan noi dung khong doc duoc -- ghi "unreadable" va confidence = 0
```

## 4. Permission Profile YAML

```yaml
agent: DocAnalyzer
role: doc_analyzer
clearance_cap: Top Secret   # Must see raw content for OCR

read_scope:
  node_labels:
    - Case
    - Bundle
    - Document
  edge_types:
    - HAS_BUNDLE
    - CONTAINS
  external_resources:
    - oss:bundles/*         # Raw blob access

write_scope:
  node_labels:
    - Document              # Update properties
    - ExtractedEntity
    - AgentStep
  edge_types:
    - EXTRACTED
    - PROCESSED_BY

property_masks:
  Applicant:
    national_id: redact
    phone: redact

allowed_tools:
  - graph.query_template
  - graph.create_vertex
  - graph.create_edge
  - ocr_with_layout
  - detect_doc_type
  - extract_entities
  - detect_stamp_signature
  - validate_nd30_format
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case -> HAS_BUNDLE -> Bundle | bundle_id |
| Context Graph | Bundle -> CONTAINS -> Document | id, blob_url, filename, page_count |
| OSS | Raw blob | Image/PDF binary via presigned URL |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | Document (update) | type, confidence, pages, has_red_stamp, has_signature, format_valid, ocr_quality |
| Context Graph | ExtractedEntity | field_name, value, confidence, page_num, bounding_box |
| Context Graph | EXTRACTED | from Document to ExtractedEntity |
| Context Graph | AgentStep | full trace per document processed |

## 7. MCP Tools Used

| Tool | Purpose |
|------|---------|
| `ocr_with_layout` | Send image to Qwen3-VL for OCR + layout analysis |
| `detect_doc_type` | Classify document type using few-shot VL prompt |
| `extract_entities` | Extract structured fields per doc type schema |
| `detect_stamp_signature` | Detect red stamps (con dau do) and signatures |
| `validate_nd30_format` | Check ND 30/2020 format compliance (quoc hieu, tieu ngu, etc.) |
| `graph.query_template` | Read bundle documents list |
| `graph.create_vertex` | Write ExtractedEntity vertices |

## 8. Implementation

```python
# backend/src/agents/doc_analyzer.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_vl_chat
import json

class DocAnalyzerAgent(BaseAgent):
    """Multimodal document analysis: OCR, type detection, entity extraction."""

    AGENT_NAME = "DocAnalyzer"
    MODEL = "qwen-vl-max-latest"
    PROFILE_PATH = "agents/profiles/doc_analyzer.yaml"
    CONFIDENCE_THRESHOLD = 0.7

    # Entity schemas per doc type
    ENTITY_SCHEMAS = {
        "gcn_qsdd": ["gcn_number", "owner_name", "land_parcel", "area_m2", "location", "issuing_authority", "issue_date"],
        "don_de_nghi": ["applicant_name", "project_name", "project_type", "project_address", "request_type"],
        "ban_ve_thiet_ke": ["building_type", "floor_area_m2", "height_m", "floors", "construction_class"],
        "giay_phep_kinh_doanh": ["company_name", "tax_id", "business_type", "registered_address", "representative"],
        "van_ban_tham_duyet_pccc": ["approval_number", "issuing_authority", "approval_date", "building_type", "conditions"],
    }

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get all documents in the bundle
        docs = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_bundle_documents",
            "parameters": {"case_id": case_id}
        })

        results = []
        for doc in docs:
            doc_result = await self._process_single_document(case_id, doc)
            results.append(doc_result)

        self.end_step(step, output={"documents_processed": len(results), "results": results})
        return {"documents": results}

    async def _process_single_document(self, case_id: str, doc: dict) -> dict:
        doc_id = doc["id"]
        blob_url = doc["blob_url"]
        step = self.begin_step("process_document", {"doc_id": doc_id})

        # Step 2: OCR with layout understanding
        ocr_result = await self._ocr_with_layout(blob_url)

        # Step 3: Detect document type
        doc_type, type_confidence = await self._detect_doc_type(blob_url, ocr_result)

        # Step 4: Extract entities based on detected type
        entities = []
        if doc_type in self.ENTITY_SCHEMAS and type_confidence >= self.CONFIDENCE_THRESHOLD:
            entities = await self._extract_entities(ocr_result, doc_type)

        # Step 5: Detect stamps and signatures
        stamp_sig = await self._detect_stamp_signature(blob_url)

        # Step 6: Validate ND 30/2020 format (if applicable)
        format_valid = None
        if doc_type in ("quyet_dinh", "cong_van", "thong_bao", "giay_phep"):
            format_valid = await self._validate_nd30_format(ocr_result)

        # Step 7: Update Document vertex properties
        await self.mcp.call_tool("graph.query_template", {
            "template_name": "document.update_properties",
            "parameters": {
                "doc_id": doc_id,
                "type": doc_type,
                "confidence": type_confidence,
                "has_red_stamp": stamp_sig["has_stamp"],
                "has_signature": stamp_sig["has_signature"],
                "format_valid": format_valid,
                "ocr_quality": ocr_result.get("quality_score", 1.0)
            }
        })

        # Step 8: Write ExtractedEntity vertices
        for entity in entities:
            entity_vertex = await self.mcp.call_tool("graph.create_vertex", {
                "label": "ExtractedEntity",
                "properties": {
                    "field_name": entity["field_name"],
                    "value": entity["value"],
                    "confidence": entity["confidence"],
                    "page_num": entity.get("page_num", 1),
                    "source_doc_id": doc_id
                }
            })
            await self.mcp.call_tool("graph.create_edge", {
                "label": "EXTRACTED",
                "from_id": doc_id,
                "to_id": entity_vertex["id"]
            })

        # Step 9: Flag for human review if low confidence
        needs_review = type_confidence < self.CONFIDENCE_THRESHOLD
        if needs_review:
            self.log_warning(f"Doc {doc_id} type confidence {type_confidence} < threshold, flagging for review")

        result = {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "confidence": type_confidence,
            "entity_count": len(entities),
            "has_stamp": stamp_sig["has_stamp"],
            "has_signature": stamp_sig["has_signature"],
            "format_valid": format_valid,
            "needs_human_review": needs_review
        }
        self.end_step(step, output=result)
        return result

    async def _ocr_with_layout(self, blob_url: str) -> dict:
        """Send image to Qwen3-VL for OCR with layout understanding."""
        messages = [
            {"role": "system", "content": "Extract all text from this Vietnamese document with layout structure. Return JSON: {text, layout_blocks: [{type, text, bbox}], quality_score}"},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": blob_url}},
                {"type": "text", "text": "OCR toan bo van ban nay, giu nguyen bo cuc."}
            ]}
        ]
        response = await qwen_vl_chat(model=self.MODEL, messages=messages, temperature=0.1)
        return json.loads(response.choices[0].message.content)

    async def _detect_doc_type(self, blob_url: str, ocr_result: dict) -> tuple[str, float]:
        """Few-shot document type classification."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": blob_url}},
                {"type": "text", "text": f"OCR text: {ocr_result.get('text', '')[:500]}\n\nNhan dien loai tai lieu. Tra ve JSON: {{\"doc_type\": \"...\", \"confidence\": 0.XX}}"}
            ]}
        ]
        response = await qwen_vl_chat(model=self.MODEL, messages=messages, temperature=0.1)
        result = json.loads(response.choices[0].message.content)
        return result["doc_type"], result["confidence"]

    async def _extract_entities(self, ocr_result: dict, doc_type: str) -> list[dict]:
        """Extract structured fields per document type schema."""
        schema = self.ENTITY_SCHEMAS.get(doc_type, [])
        messages = [
            {"role": "system", "content": "Trich xuat thong tin tu van ban hanh chinh Viet Nam. Chi tra ve gia tri doc duoc, khong doan."},
            {"role": "user", "content": f"Doc type: {doc_type}\nFields can trich xuat: {schema}\nText: {ocr_result['text']}\n\nTra ve JSON array: [{{\"field_name\": \"...\", \"value\": \"...\", \"confidence\": 0.XX}}]"}
        ]
        response = await qwen_vl_chat(model=self.MODEL, messages=messages, temperature=0.1)
        return json.loads(response.choices[0].message.content)

    async def _detect_stamp_signature(self, blob_url: str) -> dict:
        """Detect red stamps and signatures in document image."""
        messages = [
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": blob_url}},
                {"type": "text", "text": "Kiem tra: 1) Co con dau do (moc tron co quan nha nuoc) khong? 2) Co chu ky khong? Tra ve JSON: {\"has_stamp\": bool, \"stamp_details\": \"...\", \"has_signature\": bool}"}
            ]}
        ]
        response = await qwen_vl_chat(model=self.MODEL, messages=messages, temperature=0.1)
        return json.loads(response.choices[0].message.content)

    async def _validate_nd30_format(self, ocr_result: dict) -> dict:
        """Check ND 30/2020 format compliance."""
        messages = [
            {"role": "system", "content": "Kiem tra the thuc van ban theo ND 30/2020/ND-CP."},
            {"role": "user", "content": f"Text: {ocr_result['text'][:2000]}\n\nKiem tra: quoc_hieu, tieu_ngu, so_ky_hieu, noi_ban_hanh, ngay_thang, trich_yeu, noi_dung, noi_nhan, nguoi_ky. Tra ve JSON: {{\"valid\": bool, \"checks\": {{...}}, \"issues\": [...]}}"}
        ]
        response = await qwen_vl_chat(model=self.MODEL, messages=messages, temperature=0.1)
        return json.loads(response.choices[0].message.content)
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| OCR confidence < 0.7 for doc type | `type_confidence < CONFIDENCE_THRESHOLD` | Flag document for human review in Intake UI. Write `needs_review=true` on Document vertex |
| Blob URL expired or inaccessible | HTTP 403/404 from OSS | Generate new presigned URL via OSS service, retry once |
| Qwen3-VL timeout (large multi-page PDF) | `asyncio.TimeoutError` after 30s | Process page-by-page instead of full PDF, merge results |
| Unreadable scan (blurry, rotated >45 degrees) | `quality_score < 0.3` | Return `doc_type: "unreadable"`, flag for manual re-scan |
| Invalid JSON from Qwen3-VL | `json.loads` fails | Retry with explicit JSON schema in prompt; if fails, write partial results |
| Red stamp detection false positive | N/A (human verifies downstream) | Stamp detection is advisory; Compliance agent cross-checks |

## 10. Test Scenarios

### Test 1: Standard GCN QSDD scan (2 pages, clear)
**Input:** Scanned GCN QSDD with red stamp, readable text
**Expected:** `doc_type: "gcn_qsdd"`, `confidence >= 0.9`, entities include `gcn_number`, `owner_name`, `area_m2`, `location`. `has_red_stamp: true`, `has_signature: true`.
**Verify:** `g.V().has('Document','id',$id).values('type')` == "gcn_qsdd"

### Test 2: Poor quality scan (blurry, rotated)
**Input:** Heavily degraded scan of don de nghi
**Expected:** `confidence < 0.7`, `needs_human_review: true`, `ocr_quality < 0.5`. Some entities extracted with low confidence.
**Verify:** Document vertex has `needs_review: true`

### Test 3: Technical drawing (ban ve thiet ke)
**Input:** CAD-style PDF with dimensions and labels
**Expected:** `doc_type: "ban_ve_thiet_ke"`, entities include `floor_area_m2`, `height_m`, `construction_class`.
**Verify:** ExtractedEntity vertices exist with field_name in schema

### Test 4: Multi-page PDF processing
**Input:** 5-page PDF with mixed content
**Expected:** Each page processed, entities merged, no duplicate entities across pages.
**Verify:** Entity count matches expected, no duplicate field_names for single-value fields

## 11. Demo Moment

Show Document Viewer with side-by-side:
- **Left panel:** Original scan image
- **Right panel:** Extracted entities highlighted with bounding boxes
- Red stamp circled with green checkmark overlay
- Signature area highlighted
- Entity values displayed in structured table below

**Pitch line:** "DocAnalyzer dung Qwen3-VL doc duoc ca scan mo, lech, nhan dien con dau do cua co quan nha nuoc, va trich xuat thong tin co cau truc -- tat ca trong vai giay."

## 12. Verification

```bash
# 1. Unit test: OCR + type detection
pytest tests/agents/test_doc_analyzer.py -v

# 2. Integration: entities written to graph
python -c "
from graph.client import GremlinClient
g = GremlinClient()
entities = g.submit('g.V().has(\"Document\",\"id\",\"DOC-001\").out(\"EXTRACTED\").valueMap()')
assert len(entities) >= 3
assert any(e['field_name'] == 'gcn_number' for e in entities)
"

# 3. Stamp detection on sample documents
python scripts/test_stamp_detection.py --samples data/samples/stamps/

# 4. ND 30/2020 format validation
python -c "
from agents.doc_analyzer import DocAnalyzerAgent
agent = DocAnalyzerAgent()
# Test with known-good ND30 format document
result = asyncio.run(agent._validate_nd30_format({'text': '...sample...'}))
assert result['valid'] == True
"
```
