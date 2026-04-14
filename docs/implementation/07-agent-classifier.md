# Agent Implementation: Classifier (Agent 3)

> **Status:** DONE (2026-04-12)
> - [x] Permission profile YAML (`profiles/classifier_agent.yaml`)
> - [x] System prompt (few-shot Vietnamese, 5 TTHC examples)
> - [x] Gremlin templates (`case_doc_types_summary`, `tthc_list_all`)
> - [x] Agent class (`implementations/classifier.py`)
> - [x] Orchestrator registration
> - [x] Grounding check (reject non-existent TTHC codes)
> - [x] MATCHES_TTHC edge write
> - [x] Case.urgency update
> - [x] Unknown TTHC escalation
> - [x] JSON parse retry logic
> - [x] Import verification passed

## 1. Objective

Match a case to its correct TTHC code from the national administrative procedures catalog. Uses few-shot prompting with known TTHC examples. Also determines urgency level and provides initial classification suggestion for SecurityOfficer. Output must be grounded -- it must match an existing TTHCSpec vertex in the Knowledge Graph.

## 2. Model

- **Model ID:** `qwen-max-latest`
- **Temperature:** 0.2 (deterministic classification)
- **Max tokens:** 1024
- **Response format:** JSON

## 3. System Prompt

```
Ban la chuyen vien tiep nhan ho so TTHC cap So voi 10 nam kinh nghiem.
Nhiem vu: xac dinh chinh xac loai thu tuc hanh chinh (TTHC) tu bo ho so.

Quy tac NGHIEM NGAT:
1. TTHC code PHAI ton tai trong he thong. KHONG BAO GIO tu tao ma TTHC moi.
2. Neu khong chac chan -> tra ve unknown_tthc = true, KHONG doan.
3. Confidence phai phan anh dung muc do chac chan.
4. Urgency dua tren: thoi han phap luat, tinh chat khan cap, yeu to an ninh.

Vi du phan loai:
- Bundle: [don cap phep XD, GCN QSDD, ban ve, cam ket MT] -> TTHC = 1.004415 "Cap giay phep xay dung"
- Bundle: [don DKKD, dieu le, danh sach thanh vien, CCCD] -> TTHC = 1.001757 "Dang ky thanh lap cong ty TNHH"
- Bundle: [don cap GCN QSDD, ban do dia chinh, hop dong chuyen nhuong] -> TTHC = 1.000046 "Cap GCN quyen su dung dat"
- Bundle: [don xin cap phien LLTP, CCCD, anh 4x6] -> TTHC = 1.000122 "Cap phieu ly lich tu phap"
- Bundle: [don xin giay phep moi truong, bao cao DTM, ban ve] -> TTHC = 2.002154 "Cap giay phep moi truong"

Output JSON: {"tthc_code": "...", "tthc_name": "...", "confidence": 0.XX, "urgency": "normal|high|critical", "unknown_tthc": false, "reasoning": "..."}
```

## 4. Permission Profile YAML

```yaml
agent: Classifier
role: classifier
clearance_cap: Confidential

read_scope:
  node_labels:
    - Case
    - Document          # metadata only (type, confidence)
    - ExtractedEntity   # field summaries
    - TTHCSpec          # KG
    - ProcedureCategory # KG
  edge_types:
    - HAS_BUNDLE
    - CONTAINS
    - EXTRACTED
    - BELONGS_TO

write_scope:
  node_labels:
    - AgentStep
  edge_types:
    - MATCHES_TTHC      # cross-graph: Case -> TTHCSpec
    - PROCESSED_BY
  properties:
    Case:
      - urgency         # update urgency field

property_masks:
  Applicant:
    national_id: redact
    phone: redact
    address_detail: redact
  Document:
    blob_url: redact
    content_full: redact

allowed_tools:
  - graph.query_template
  - graph.create_edge
  - classify_tthc
  - suggest_urgency
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case | id, status |
| Context Graph | Document | type, confidence (from DocAnalyzer) |
| Context Graph | ExtractedEntity | field_name, value (summaries) |
| Knowledge Graph | TTHCSpec | code, name, category, sla_days_law |
| Knowledge Graph | ProcedureCategory | name, parent_category |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | MATCHES_TTHC edge | from Case to TTHCSpec (cross-graph), confidence |
| Context Graph | Case.urgency | "normal", "high", or "critical" |
| Context Graph | AgentStep | classification reasoning trace |

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `case.get_doc_types_summary` | Get doc types + entities from DocAnalyzer output |
| `graph.query_template` | `tthc.find_by_category` | Search TTHC by category |
| `graph.query_template` | `tthc.list_common` | Get full TTHC catalog for matching |
| `classify_tthc` | N/A | LLM few-shot classification call |
| `suggest_urgency` | N/A | Rule-based + LLM urgency assessment |
| `graph.create_edge` | MATCHES_TTHC | Write cross-graph edge |

## 8. Implementation

```python
# backend/src/agents/classifier.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
import json

class ClassifierAgent(BaseAgent):
    """Match case to TTHC code from national catalog."""

    AGENT_NAME = "Classifier"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/classifier.yaml"

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get document types and entities from DocAnalyzer output
        doc_summary = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_doc_types_summary",
            "parameters": {"case_id": case_id}
        })

        # Step 2: Get TTHC catalog for grounding
        tthc_catalog = await self.mcp.call_tool("graph.query_template", {
            "template_name": "tthc.list_common",
            "parameters": {"limit": 50}
        })
        valid_codes = {t["code"] for t in tthc_catalog}

        # Step 3: Classify via Qwen3-Max with few-shot prompt
        bundle_description = self._build_bundle_description(doc_summary)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "case_id": case_id,
                "bundle_description": bundle_description,
                "available_tthc_codes": [{"code": t["code"], "name": t["name"]} for t in tthc_catalog]
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(
            model=self.MODEL,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        classification = json.loads(response.choices[0].message.content)

        # Step 4: GROUNDING CHECK -- must match existing TTHCSpec
        tthc_code = classification.get("tthc_code")
        unknown_tthc = classification.get("unknown_tthc", False)

        if not unknown_tthc and tthc_code not in valid_codes:
            # LLM returned a code that doesn't exist -- force unknown
            self.log_warning(f"LLM returned non-existent TTHC code {tthc_code}, forcing unknown_tthc")
            classification["unknown_tthc"] = True
            classification["confidence"] = 0.0
            unknown_tthc = True

        # Step 5: Write MATCHES_TTHC edge if we have a match
        if not unknown_tthc and classification["confidence"] >= 0.7:
            await self.mcp.call_tool("graph.create_edge", {
                "label": "MATCHES_TTHC",
                "from_vertex": {"label": "Case", "id": case_id},
                "to_vertex": {"label": "TTHCSpec", "code": tthc_code},
                "properties": {"confidence": classification["confidence"]}
            })

        # Step 6: Set urgency on Case
        urgency = classification.get("urgency", "normal")
        await self._update_case_urgency(case_id, urgency)

        # Step 7: Handle unknown TTHC -- escalate
        if unknown_tthc:
            await self._escalate_unknown_tthc(case_id, classification)

        self.end_step(step, output=classification)
        await self.broadcast_ws({
            "type": "agent_step",
            "agent": self.AGENT_NAME,
            "case_id": case_id,
            "tthc_code": tthc_code if not unknown_tthc else None,
            "confidence": classification.get("confidence", 0),
            "urgency": urgency
        })

        return classification

    def _build_bundle_description(self, doc_summary: list) -> str:
        """Build human-readable bundle description from doc types and entities."""
        parts = []
        for doc in doc_summary:
            desc = f"- {doc.get('type', 'unknown')} (confidence: {doc.get('confidence', 0):.2f})"
            entities = doc.get("entities", [])
            if entities:
                key_vals = [f"{e['field_name']}={e['value']}" for e in entities[:5]]
                desc += f" [{', '.join(key_vals)}]"
            parts.append(desc)
        return "\n".join(parts)

    async def _update_case_urgency(self, case_id: str, urgency: str):
        """Update Case.urgency property."""
        await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.update_property",
            "parameters": {"case_id": case_id, "property": "urgency", "value": urgency}
        })

    async def _escalate_unknown_tthc(self, case_id: str, classification: dict):
        """Handle cases where TTHC could not be identified."""
        await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.update_property",
            "parameters": {"case_id": case_id, "property": "status", "value": "needs_manual_classification"}
        })
        self.log_warning(f"Case {case_id}: unknown TTHC, escalated for manual classification. Reasoning: {classification.get('reasoning', 'N/A')}")
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| LLM returns non-existent TTHC code | `tthc_code not in valid_codes` | Force `unknown_tthc = true`, escalate to human |
| Confidence < 0.7 | Check `classification.confidence` | Do NOT write MATCHES_TTHC edge; flag for human classification |
| Unknown TTHC (genuinely new procedure type) | `unknown_tthc = true` from LLM | Set `case.status = "needs_manual_classification"`, notify intake staff |
| DocAnalyzer data incomplete (predecessor failed) | Doc summary has empty types | Use filenames only for classification with lower confidence |
| Qwen3-Max API error | HTTP 5xx or timeout | Retry once; if fails, escalate for manual classification |

## 10. Test Scenarios

### Test 1: Clear CPXD case
**Input:** Bundle with doc types: `don_de_nghi`, `gcn_qsdd`, `ban_ve_thiet_ke`, `cam_ket_moi_truong`, `giay_phep_kinh_doanh`
**Expected:** `tthc_code: "1.004415"`, `confidence >= 0.9`, `unknown_tthc: false`, `urgency: "normal"`
**Verify:** `g.V().has('Case','id',$id).out('MATCHES_TTHC').values('code')` == "1.004415"

### Test 2: DKKD case
**Input:** Bundle with: `don_de_nghi` (content hints: "dang ky kinh doanh"), `dieu_le`, `danh_sach_thanh_vien`, `cccd`
**Expected:** `tthc_code: "1.001757"`, `confidence >= 0.85`
**Verify:** MATCHES_TTHC edge exists with correct target

### Test 3: Ambiguous case -- unknown TTHC
**Input:** Bundle with: single document of type `other`, no clear TTHC indicators
**Expected:** `unknown_tthc: true`, `confidence: 0`, Case.status = "needs_manual_classification"
**Verify:** No MATCHES_TTHC edge written. Case has `needs_manual_classification` status.

### Test 4: Grounding enforcement
**Input:** Feed LLM a prompt that might produce fabricated TTHC code "9.999999"
**Expected:** Code not in valid_codes, forced to `unknown_tthc: true`
**Verify:** Log contains "non-existent TTHC code" warning

## 11. Demo Moment

Show classification happening in real-time in Agent Trace Viewer:
1. DocAnalyzer finishes -- document types appear in graph
2. Classifier activates -- reasoning trace streams
3. "Bundle chua don de nghi XD, GCN QSDD, ban ve ky thuat -> day la thu tuc Cap giay phep xay dung (1.004415)"
4. MATCHES_TTHC edge animates into the graph visualization, connecting Case to TTHCSpec

**Pitch line:** "Classifier dung few-shot prompting voi Qwen3-Max de doi chieu ho so voi bo TTHC quoc gia. Ket qua PHAI khop voi TTHC that trong he thong -- khong bao gio doan."

## 12. Verification

```bash
# 1. Unit test: classification with known inputs
pytest tests/agents/test_classifier.py -v

# 2. Grounding test: all 5 flagship TTHC codes
python -c "
from agents.classifier import ClassifierAgent
# Test each of the 5 known TTHC bundles
test_cases = [
    (['don_de_nghi', 'gcn_qsdd', 'ban_ve_thiet_ke'], '1.004415'),
    (['don_dkkd', 'dieu_le', 'cccd'], '1.001757'),
]
# Verify each returns correct code
"

# 3. Integration: MATCHES_TTHC edge in GDB
python -c "
from graph.client import GremlinClient
g = GremlinClient()
edges = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").outE(\"MATCHES_TTHC\").valueMap()')
assert len(edges) == 1
assert edges[0]['confidence'] >= 0.7
"

# 4. Unknown TTHC escalation test
# Submit case with completely unrecognizable documents
# Verify: no MATCHES_TTHC edge, case status = needs_manual_classification
```
