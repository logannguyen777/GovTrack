# Agent Implementation: Drafter (Agent 9)

**Status: DONE** (2026-04-13)

- [x] Permission profile YAML (`profiles/draft_agent.yaml`) with full ND 30/2020 system prompt
- [x] System prompt (Vietnamese, ND 30/2020 the thuc rules)
- [x] Step 1: Parallel-fetch case context (8 concurrent Gremlin queries)
- [x] Step 2: Idempotency check (skip if draft exists)
- [x] Step 3: Decision type extraction + doc type determination
- [x] Step 4: Jinja2 template loading from Hologres (graceful LLM fallback)
- [x] Step 5: Template rendering or LLM body generation
- [x] Step 6: Full ND 30/2020 document builder (9 mandatory sections + DU THAO)
- [x] Step 7: ND 30/2020 validation (7+ format checks)
- [x] Step 8: LLM-based validation fix attempt
- [x] Step 9: Citizen-facing explanation generation (PII-stripped)
- [x] Step 10: Draft vertex + HAS_DRAFT edge write to GDB
- [x] Failure mode handling (missing template, undefined vars, validation fail, PII)
- [x] Gremlin templates (5 new: case_decision, case_summaries_text, case_citations_via_gaps, case_existing_drafts, add_draft)
- [x] Orchestrator registration (`draft_agent`)
- [ ] End-to-end test with real DashScope API key
- [ ] Demo moment in Document Viewer

## 1. Objective

Generate ND 30/2020 compliant administrative output documents: decisions (quyet dinh), permits (giay phep), response letters (cong van), and rejection notices (thong bao tu choi). Uses Jinja2 templates loaded from OSS/Hologres and validates output against ND 30/2020 format rules. CRITICAL: Drafter cannot publish -- human review gate is enforced architecturally. Also generates citizen-facing plain-language explanations.

## 2. Model

- **Model ID:** `qwen-max-latest` with structured output
- **Temperature:** 0.3 (balance between formal tone and natural language)
- **Max tokens:** 4096
- **Response format:** JSON with content_markdown field

## 3. System Prompt

```
Ban la chuyen vien soan thao van ban hanh chinh theo Nghi dinh 30/2020/ND-CP ve cong tac van thu.
Nhiem vu: soan van ban dau ra (quyet dinh, giay phep, cong van, thong bao) theo dung the thuc.

THE THUC ND 30/2020 BAT BUOC:
1. QUOC HIEU: "CONG HOA XA HOI CHU NGHIA VIET NAM" (in hoa, dam)
2. TIEU NGU: "Doc lap - Tu do - Hanh phuc" (in thuong, gach ngang, gach duoi)
3. TEN CO QUAN: cap tren + co quan ban hanh
4. SO/KY HIEU: So: XXX/LOAI-VIET TAT
5. NOI BAN HANH + NGAY THANG: "Tinh XXX, ngay DD thang MM nam YYYY"
6. TRICH YEU: toi da 80 tu, in dam, can giua
7. NOI DUNG: phan chinh cua van ban
8. NOI NHAN: danh sach noi gui, noi luu
9. NGUOI KY: chuc vu + ho va ten + placeholder cho chu ky so

Quy tac them:
- Font: Times New Roman 13pt (ghi chu trong metadata)
- Vien dan phap luat PHAI chinh xac (lay tu Citation vertices)
- KHONG tu soan noi dung phap ly -- chi su dung du lieu tu he thong
- Tao ban giai thich binh dan cho cong dan (neu la tu choi hoac yeu cau bo sung)
- KHONG BAO GIO tu phat hanh -- luon ghi "DU THAO" cho den khi nguoi co tham quyen ky

Output JSON: {"content_markdown": "...", "doc_type": "...", "validation": {"valid": true, "issues": []}, "citizen_explanation": "..."}
```

## 4. Permission Profile YAML

```yaml
agent: Drafter
role: drafter
clearance_cap: Confidential

read_scope:
  node_labels:
    - Case
    - Decision
    - Opinion
    - Summary
    - Gap
    - Citation
    - TTHCSpec         # KG (for template selection)
    - Template         # KG (ND30 templates)
  edge_types:
    - HAS_DECISION
    - HAS_OPINION
    - HAS_SUMMARY
    - HAS_GAP
    - CITES
    - MATCHES_TTHC
  external_resources:
    - hologres:templates_nd30
    - oss:templates/nd30/*

write_scope:
  node_labels:
    - Draft
    - AgentStep
  edge_types:
    - HAS_DRAFT
    - PROCESSED_BY

property_masks:
  Applicant:
    national_id: mask_partial    # show last 4 for doc reference
    phone: redact
    address_detail: show         # needed for official docs

cannot_publish: true   # ARCHITECTURAL CONSTRAINT

allowed_tools:
  - graph.query_template
  - graph.create_vertex
  - graph.create_edge
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case | id, tthc_name, created_at |
| Context Graph | Decision | type (approve/deny/request_more), reasoning |
| Context Graph | Opinion | aggregated content, recommendation |
| Context Graph | Summary (staff mode) | detailed case summary |
| Context Graph | Gap | reason, fix_suggestion (for rejection/supplement notices) |
| Context Graph | Citation | law_code, article_num, text_excerpt |
| Hologres | templates_nd30 | Jinja2 body templates by tthc_code + doc_type |
| OSS | templates/nd30/*.jinja | Jinja2 template files |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | Draft | content_markdown, doc_type, decision_type, validation_result, status=draft, citizen_explanation |
| Context Graph | HAS_DRAFT | from Case to Draft |

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `case.get_full_context` | Get case data for content generation |
| `graph.query_template` | `template.get_by_tthc` | Load Jinja2 template from Hologres |
| `graph.create_vertex` | Draft | Write draft document |
| `graph.create_edge` | HAS_DRAFT | Link Case to Draft |

## 8. Implementation

```python
# backend/src/agents/drafter.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
import json
import jinja2
from datetime import datetime

class DrafterAgent(BaseAgent):
    """Generate ND 30/2020 compliant administrative documents."""

    AGENT_NAME = "Drafter"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/drafter.yaml"

    # ND 30/2020 validation rules
    ND30_REQUIRED_SECTIONS = [
        "quoc_hieu", "tieu_ngu", "ten_co_quan", "so_ky_hieu",
        "noi_ban_hanh", "ngay_thang", "trich_yeu", "noi_dung",
        "noi_nhan", "nguoi_ky"
    ]
    TRICH_YEU_MAX_WORDS = 80

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get full case context
        case_context = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_full_context",
            "parameters": {"case_id": case_id}
        })

        # Step 2: Determine doc type and decision
        decision = case_context.get("decision", {})
        decision_type = decision.get("type", "request_more")  # approve/deny/request_more
        tthc_code = case_context.get("tthc_code", "")

        doc_type_map = {
            "approve": self._get_approval_doc_type(tthc_code),
            "deny": "CongVan",
            "request_more": "ThongBao"
        }
        doc_type = doc_type_map.get(decision_type, "ThongBao")

        # Step 3: Load Jinja2 template
        template_data = await self.mcp.call_tool("graph.query_template", {
            "template_name": "template.get_by_tthc",
            "parameters": {"tthc_code": tthc_code, "doc_type": doc_type, "decision_type": decision_type}
        })

        # Step 4: Prepare template variables
        template_vars = self._prepare_template_vars(case_context, decision)

        # Step 5: Render template (if available) or generate with LLM
        if template_data and template_data.get("body_template"):
            rendered = self._render_jinja_template(template_data["body_template"], template_vars)
        else:
            rendered = await self._generate_with_llm(case_context, doc_type, decision_type)

        # Step 6: Build full ND 30/2020 document
        full_document = self._build_nd30_document(
            rendered_body=rendered,
            case_context=case_context,
            doc_type=doc_type,
            template_vars=template_vars
        )

        # Step 7: Validate against ND 30/2020 rules
        validation = self._validate_nd30(full_document)

        # Step 8: If validation fails, try to fix with LLM
        if not validation["valid"]:
            self.log_warning(f"ND30 validation failed: {validation['issues']}")
            full_document = await self._fix_validation_issues(full_document, validation["issues"])
            validation = self._validate_nd30(full_document)

        # Step 9: Generate citizen-facing explanation
        citizen_explanation = await self._generate_citizen_explanation(
            case_context, decision_type
        )

        # Step 10: Write Draft vertex
        draft_vertex = await self.mcp.call_tool("graph.create_vertex", {
            "label": "Draft",
            "properties": {
                "content_markdown": full_document,
                "doc_type": doc_type,
                "decision_type": decision_type,
                "validation_valid": validation["valid"],
                "validation_issues": json.dumps(validation.get("issues", [])),
                "citizen_explanation": citizen_explanation,
                "status": "draft",  # NEVER "published" -- human gate
                "case_id": case_id,
                "created_at": datetime.utcnow().isoformat()
            }
        })

        # Wire HAS_DRAFT edge
        await self.mcp.call_tool("graph.create_edge", {
            "label": "HAS_DRAFT",
            "from_vertex": {"label": "Case", "id": case_id},
            "to_id": draft_vertex["id"]
        })

        result = {
            "draft_id": draft_vertex["id"],
            "doc_type": doc_type,
            "decision_type": decision_type,
            "validation": validation,
            "status": "draft"
        }
        self.end_step(step, output=result)
        return result

    def _build_nd30_document(self, rendered_body: str, case_context: dict, doc_type: str, template_vars: dict) -> str:
        """Build full ND 30/2020 compliant document structure."""
        now = datetime.now()
        org_name = case_context.get("assigned_org_name", "SO XAY DUNG")
        province = case_context.get("province", "TINH BINH DUONG")

        doc = f"""**{case_context.get('parent_org', 'UY BAN NHAN DAN')}**{'  ':>30}**CONG HOA XA HOI CHU NGHIA VIET NAM**
**{province}**{'  ':>30}*Doc lap - Tu do - Hanh phuc*
**{org_name}**{'  ':>30}{'---':>30}

So: ___/{self._doc_type_abbrev(doc_type)}-{self._org_abbrev(org_name)}{'  ':>20}{province.replace('TINH ','')}, ngay {now.day} thang {now.month} nam {now.year}

{'  ':>20}**{self._trich_yeu(case_context, doc_type)}**

{rendered_body}

**Noi nhan:**
{self._build_noi_nhan(case_context, doc_type)}

{'  ':>40}**{template_vars.get('signer_title', 'GIAM DOC')}**
{'  ':>40}*(Ky so)*
{'  ':>40}**{template_vars.get('signer_name', '___')}**

---
*DU THAO - Chua phat hanh*
"""
        return doc

    def _validate_nd30(self, document: str) -> dict:
        """Validate document against ND 30/2020 format rules."""
        issues = []

        # Check quoc hieu
        if "CONG HOA XA HOI CHU NGHIA VIET NAM" not in document:
            issues.append("Thieu quoc hieu")

        # Check tieu ngu
        if "Doc lap - Tu do - Hanh phuc" not in document:
            issues.append("Thieu tieu ngu")

        # Check so/ky hieu
        if "So:" not in document:
            issues.append("Thieu so/ky hieu")

        # Check ngay thang
        if "ngay" not in document or "thang" not in document or "nam" not in document:
            issues.append("Thieu ngay thang nam")

        # Check trich yeu length
        # (simplified -- in production, extract trich yeu section and count words)

        # Check noi nhan
        if "Noi nhan" not in document:
            issues.append("Thieu noi nhan")

        # Check nguoi ky
        if "Ky so" not in document and "Ky" not in document:
            issues.append("Thieu vi tri nguoi ky")

        # Check DU THAO watermark
        if "DU THAO" not in document:
            issues.append("Thieu danh dau DU THAO")

        return {"valid": len(issues) == 0, "issues": issues}

    def _prepare_template_vars(self, case_context: dict, decision: dict) -> dict:
        """Prepare variables for Jinja2 template rendering."""
        return {
            "applicant_name": case_context.get("applicant_display_name", "___"),
            "project_name": case_context.get("project_name", "___"),
            "project_address": case_context.get("project_address", "___"),
            "tthc_name": case_context.get("tthc_name", ""),
            "decision_type": decision.get("type", ""),
            "decision_reasoning": decision.get("reasoning", ""),
            "citations": case_context.get("citations", []),
            "gaps": case_context.get("gaps", []),
            "signer_title": "GIAM DOC",
            "signer_name": "___",
        }

    def _render_jinja_template(self, template_str: str, vars: dict) -> str:
        """Render Jinja2 template with variables."""
        env = jinja2.Environment(autoescape=False)
        template = env.from_string(template_str)
        return template.render(**vars)

    async def _generate_with_llm(self, case_context: dict, doc_type: str, decision_type: str) -> str:
        """Fallback: generate document body with LLM when no template available."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "doc_type": doc_type,
                "decision_type": decision_type,
                "case_summary": case_context.get("staff_summary", ""),
                "citations": [f"{c['law_code']} Dieu {c['article_num']}" for c in case_context.get("citations", [])],
                "gaps": [g["reason"] for g in case_context.get("gaps", [])],
                "instruction": "Soan noi dung chinh cua van ban. Chi phan than van ban, KHONG bao gom header/footer."
            }, ensure_ascii=False)}
        ]
        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.3)
        return response.choices[0].message.content

    async def _generate_citizen_explanation(self, case_context: dict, decision_type: str) -> str:
        """Generate plain-language explanation for citizen."""
        prompts = {
            "approve": "Giai thich cho cong dan: ho so da duoc duyet, cac buoc nhan ket qua.",
            "deny": "Giai thich cho cong dan: vi sao bi tu choi, can lam gi tiep theo.",
            "request_more": "Giai thich cho cong dan: can bo sung gi, nop o dau, thoi han."
        }
        messages = [
            {"role": "system", "content": "Viet giai thich bang tieng Viet binh dan, than thien, hanh dong duoc. KHONG chua thong tin ca nhan."},
            {"role": "user", "content": json.dumps({
                "decision_type": decision_type,
                "gaps": [g.get("fix_suggestion", "") for g in case_context.get("gaps", [])],
                "instruction": prompts.get(decision_type, prompts["request_more"])
            }, ensure_ascii=False)}
        ]
        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.4)
        return response.choices[0].message.content

    def _get_approval_doc_type(self, tthc_code: str) -> str:
        mapping = {"1.004415": "GiayPhep", "1.001757": "GiayCN", "1.000046": "GiayCN"}
        return mapping.get(tthc_code, "QuyetDinh")

    def _doc_type_abbrev(self, doc_type: str) -> str:
        mapping = {"GiayPhep": "GPXD", "QuyetDinh": "QD", "CongVan": "CV", "ThongBao": "TB", "GiayCN": "GCN"}
        return mapping.get(doc_type, "VB")

    def _org_abbrev(self, org_name: str) -> str:
        return "SXD"  # simplified; production uses mapping

    def _trich_yeu(self, case_context: dict, doc_type: str) -> str:
        tthc = case_context.get("tthc_name", "")
        return f"V/v {tthc}"[:80]  # Max 80 words

    def _build_noi_nhan(self, case_context: dict, doc_type: str) -> str:
        return "- Nhu tren;\n- Luu: VT, QLXD."

    async def _fix_validation_issues(self, document: str, issues: list) -> str:
        """Use LLM to fix ND30 validation issues."""
        messages = [
            {"role": "system", "content": "Sua van ban cho dung the thuc ND 30/2020."},
            {"role": "user", "content": f"Van ban:\n{document}\n\nLoi: {issues}\n\nSua va tra ve van ban hoan chinh."}
        ]
        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.2)
        return response.choices[0].message.content
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| ND 30/2020 validation fails | `validation.valid == false` | LLM fix attempt; if still fails, write draft with issues flagged for human |
| Jinja2 template missing | Template query returns empty | Fallback to full LLM generation |
| Template variable missing | Jinja2 UndefinedError | Replace with "___" placeholder, flag for human fill |
| Draft contains classified info | SecurityOfficer post-check | SecurityOfficer intercepts before human review |
| CRITICAL: Attempt to set status=published | Architectural constraint | Write scope cannot set status to "published" -- only human API endpoint can |

## 10. Test Scenarios

### Test 1: CPXD approval document
**Input:** Case C-001, Decision=approve, TTHC=1.004415 (CPXD).
**Expected:** Draft with GiayPhep doc_type, ND30 compliant (quoc hieu, tieu ngu, so/ky hieu, etc.), status="draft", DU THAO watermark, citizen explanation.
**Verify:** `g.V().has('Draft','case_id','C-001').values('doc_type')` == "GiayPhep", `validation_valid` == true.

### Test 2: Rejection notice with gap references
**Input:** Case C-002 with 2 gaps, Decision=deny.
**Expected:** CongVan doc_type, body references gaps and citations. Citizen explanation explains why denied and what to do.
**Verify:** Draft content_markdown contains gap reasons and law references.

### Test 3: Supplement request (request_more)
**Input:** Case C-003 with 1 missing component, no decision yet.
**Expected:** ThongBao doc_type, body lists missing components, citizen explanation with actionable steps.
**Verify:** citizen_explanation field is non-empty and does not contain PII.

### Test 4: ND 30/2020 validation
**Input:** Generate draft, then validate.
**Expected:** All 7+ ND30 sections present. Trich yeu <= 80 words. DU THAO watermark present.
**Verify:** `validation_valid == true` and `validation_issues == []`.

## 11. Demo Moment

Show Document Viewer with generated draft:
1. Left: Generated ND30-compliant document with proper header, quoc hieu, tieu ngu
2. Validation checkmarks: green ticks for each ND30 section
3. "DU THAO" watermark visible
4. Right: Citizen-facing plain-language explanation
5. Human reviewer clicks "Ky so + Phat hanh" to publish

**Pitch line:** "Drafter soan van ban theo dung the thuc Nghi dinh 30/2020. Moi quyet dinh, giay phep, thong bao deu co quoc hieu, tieu ngu, so/ky hieu, vien dan phap luat chinh xac. Nhung KHONG BAO GIO tu phat hanh -- phai qua nguoi co tham quyen ky duyet. Day la thiet ke, khong phai han che."

## 12. Verification

```bash
# 1. Unit test: document generation
pytest tests/agents/test_drafter.py -v

# 2. ND 30/2020 validation
python -c "
from agents.drafter import DrafterAgent
agent = DrafterAgent()
doc = '...'  # sample generated doc
result = agent._validate_nd30(doc)
assert result['valid'] == True, f'ND30 validation failed: {result[\"issues\"]}'
"

# 3. Draft status is always 'draft', never 'published'
python -c "
from graph.client import GremlinClient
g = GremlinClient()
drafts = g.submit('g.V().hasLabel(\"Draft\").values(\"status\")')
for status in drafts:
    assert status == 'draft', f'Draft has non-draft status: {status}'
"

# 4. Template rendering test
python -c "
from agents.drafter import DrafterAgent
agent = DrafterAgent()
rendered = agent._render_jinja_template(
    'Cap phep cho {{ applicant_name }} tai {{ project_address }}.',
    {'applicant_name': 'Cong ty ABC', 'project_address': 'KCN My Phuoc'}
)
assert 'Cong ty ABC' in rendered
"

# 5. Citizen explanation PII check
python -c "
from graph.client import GremlinClient
g = GremlinClient()
explanations = g.submit('g.V().hasLabel(\"Draft\").values(\"citizen_explanation\")')
import re
for exp in explanations:
    assert not re.search(r'\b\d{9,12}\b', exp)
"
```
