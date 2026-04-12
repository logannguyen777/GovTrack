# Agent Implementation: Compliance (Agent 4)

## 1. Objective

The heart of GovFlow. Check whether a case bundle has all required components per the matched TTHC specification. Detect gaps, cite governing law for each gap via LegalLookup, evaluate conditional requirements, and compute a compliance score. This agent bridges the Context Graph (case data) with the Knowledge Graph (TTHC requirements and legal articles).

## 2. Model

- **Model ID:** `qwen-max-latest` (high reasoning capability)
- **Temperature:** 0.2 (precision-critical legal analysis)
- **Max tokens:** 4096
- **Response format:** JSON

## 3. System Prompt

```
Ban la chuyen vien tham dinh ho so TTHC cap So voi 20 nam kinh nghiem ve phap che hanh chinh.
Nhiem vu: kiem tra ho so co du thanh phan khong, phat hien thieu sot, vien dan phap luat.

Quy tac:
1. So sanh TUNG thanh phan yeu cau (RequiredComponent) cua TTHCSpec voi tai lieu da nop
2. Moi thanh phan thieu = 1 Gap voi: reason (ly do thieu), severity (blocker/warning/info), fix_suggestion (huong dan bo sung)
3. Severity = blocker neu la thanh phan bat buoc theo luat; warning neu la thanh phan co dieu kien; info neu la khuyen nghi
4. Voi moi Gap, PHAI co citation phap luat cu the (so dieu/khoan/diem)
5. Mot so RequiredComponent co DIEU KIEN (condition). Vi du: "chi bat buoc neu cong trinh nhom I"
   -> Kiem tra dieu kien co ap dung cho case nay khong truoc khi tao Gap
6. KHONG bao gio doc thong tin ca nhan (CCCD, SDT) -- du lieu da bi mask
7. Compliance score = (so thanh phan da du / tong so bat buoc) * 100
8. Output JSON: {"gaps": [...], "compliance_score": XX, "satisfied_components": [...], "reasoning": "..."}

Moi gap: {"component_name": "...", "reason": "...", "severity": "blocker|warning|info", "fix_suggestion": "...", "law_query": "..."}
```

## 4. Permission Profile YAML

```yaml
agent: Compliance
role: compliance_checker
clearance_cap: Confidential

read_scope:
  node_labels:
    - Case
    - Bundle
    - Document
    - ExtractedEntity
    - TTHCSpec          # KG
    - RequiredComponent # KG
    - Article           # KG (via LegalLookup)
  edge_types:
    - HAS_BUNDLE
    - CONTAINS
    - EXTRACTED
    - MATCHES_TTHC
    - REQUIRES
    - GOVERNED_BY
    - SATISFIES

write_scope:
  node_labels:
    - Gap
    - AgentStep
  edge_types:
    - HAS_GAP
    - GAP_FOR
    - CITES
    - PROCESSED_BY
  properties:
    Case:
      - compliance_score

property_masks:
  Applicant:
    national_id: redact
    phone: redact
    address_detail: redact
  Document:
    blob_url: redact       # no raw content access

cannot_read:
  - Applicant.national_id
  - Applicant.phone
  - Applicant.address_detail

allowed_tools:
  - graph.query_template
  - graph.create_vertex
  - graph.create_edge
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case | id, status, MATCHES_TTHC edge |
| Context Graph | Document | type, confidence |
| Context Graph | ExtractedEntity | field_name, value |
| Knowledge Graph | TTHCSpec -> REQUIRES -> RequiredComponent | name, is_required, condition, doc_type_match |
| Knowledge Graph | TTHCSpec -> GOVERNED_BY -> Article | law_code, num, text |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | Gap | reason, severity, fix_suggestion, component_name |
| Context Graph | HAS_GAP | from Case to Gap |
| Context Graph | GAP_FOR | from Gap to RequiredComponent (cross-graph to KG) |
| Context Graph | Citation | text_excerpt, clause_num, point_label (written by LegalLookup) |
| Context Graph | CITES | from Gap to Citation |
| Context Graph | Case.compliance_score | float 0-100 |

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `case.find_missing_components` | Core Gremlin: traverse MATCHES_TTHC->REQUIRES vs SATISFIES |
| `graph.query_template` | `case.get_full_context` | Get all case data for reasoning |
| `graph.query_template` | `case.add_gap` | Write Gap vertex + HAS_GAP edge |
| `graph.create_vertex` | Gap | Create gap vertex |
| `graph.create_edge` | GAP_FOR, CITES | Link gap to requirement and citation |

## 8. Implementation

```python
# backend/src/agents/compliance.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
from agents.legal_lookup import LegalLookupAgent
import json

class ComplianceAgent(BaseAgent):
    """Check bundle completeness against TTHC requirements, detect gaps, cite law."""

    AGENT_NAME = "Compliance"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/compliance.yaml"

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get full case context
        case_context = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_full_context",
            "parameters": {"case_id": case_id}
        })

        # Step 2: Find missing components via core Gremlin template
        missing_components = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.find_missing_components",
            "parameters": {"case_id": case_id}
        })

        # Step 3: Get all required components for scoring
        all_required = await self.mcp.call_tool("graph.query_template", {
            "template_name": "tthc.get_required_components",
            "parameters": {"case_id": case_id}
        })

        # Step 4: Evaluate conditional requirements with LLM reasoning
        confirmed_gaps = []
        for component in missing_components:
            if component.get("condition"):
                # Conditional requirement -- check if condition applies
                applies = await self._evaluate_condition(
                    component["condition"],
                    case_context
                )
                if not applies:
                    continue  # Condition doesn't apply, skip
            confirmed_gaps.append(component)

        # Step 5: For each confirmed gap, get legal citation via LegalLookup
        legal_lookup = LegalLookupAgent(mcp=self.mcp)
        gap_results = []

        for component in confirmed_gaps:
            # Build law query from component context
            law_query = self._build_law_query(component, case_context)

            # Call LegalLookup agent
            citations = await legal_lookup.lookup(
                query=law_query,
                case_context=case_context
            )

            # Determine severity
            severity = "blocker" if component.get("is_required", True) else "warning"

            # Build fix suggestion
            fix_suggestion = await self._generate_fix_suggestion(
                component, citations, case_context
            )

            # Write Gap vertex
            gap_vertex = await self.mcp.call_tool("graph.create_vertex", {
                "label": "Gap",
                "properties": {
                    "component_name": component["name"],
                    "reason": f"Thieu {component['name']}",
                    "severity": severity,
                    "fix_suggestion": fix_suggestion,
                    "case_id": case_id
                }
            })

            # Write HAS_GAP edge (Case -> Gap)
            await self.mcp.call_tool("graph.create_edge", {
                "label": "HAS_GAP",
                "from_vertex": {"label": "Case", "id": case_id},
                "to_id": gap_vertex["id"]
            })

            # Write GAP_FOR edge (Gap -> RequiredComponent in KG)
            await self.mcp.call_tool("graph.create_edge", {
                "label": "GAP_FOR",
                "from_id": gap_vertex["id"],
                "to_vertex": {"label": "RequiredComponent", "id": component["id"]}
            })

            # Write CITES edges (Gap -> Citation)
            for citation in citations:
                await self.mcp.call_tool("graph.create_edge", {
                    "label": "CITES",
                    "from_id": gap_vertex["id"],
                    "to_id": citation["id"]
                })

            gap_results.append({
                "component": component["name"],
                "severity": severity,
                "fix_suggestion": fix_suggestion,
                "citations": [c["article_ref"] for c in citations]
            })

        # Step 6: Calculate compliance score
        total_required = len([c for c in all_required if c.get("is_required", True)])
        blocker_gaps = len([g for g in gap_results if g["severity"] == "blocker"])
        satisfied = total_required - blocker_gaps
        compliance_score = round((satisfied / max(total_required, 1)) * 100, 1)

        # Step 7: Write compliance score to Case
        await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.update_property",
            "parameters": {"case_id": case_id, "property": "compliance_score", "value": compliance_score}
        })

        result = {
            "compliance_score": compliance_score,
            "total_required": total_required,
            "satisfied": satisfied,
            "gaps": gap_results,
            "gap_count": len(gap_results)
        }

        self.end_step(step, output=result)
        await self.broadcast_ws({
            "type": "agent_step",
            "agent": self.AGENT_NAME,
            "case_id": case_id,
            "compliance_score": compliance_score,
            "gap_count": len(gap_results)
        })

        return result

    async def _evaluate_condition(self, condition: str, case_context: dict) -> bool:
        """Use LLM to evaluate if a conditional requirement applies to this case."""
        messages = [
            {"role": "system", "content": "Danh gia dieu kien yeu cau. Tra ve JSON: {\"applies\": true/false, \"reasoning\": \"...\"}"},
            {"role": "user", "content": json.dumps({
                "condition": condition,
                "case_context": {
                    "project_type": case_context.get("project_type"),
                    "area_m2": case_context.get("area_m2"),
                    "location": case_context.get("location"),
                    "building_class": case_context.get("building_class")
                }
            }, ensure_ascii=False)}
        ]
        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.1)
        result = json.loads(response.choices[0].message.content)
        return result["applies"]

    def _build_law_query(self, component: dict, case_context: dict) -> str:
        """Build a natural language query for LegalLookup."""
        return (
            f"Yeu cau phap luat ve '{component['name']}' "
            f"cho thu tuc {case_context.get('tthc_name', 'TTHC')}. "
            f"Loai cong trinh: {case_context.get('project_type', 'N/A')}, "
            f"Dien tich: {case_context.get('area_m2', 'N/A')}m2, "
            f"Vi tri: {case_context.get('location', 'N/A')}."
        )

    async def _generate_fix_suggestion(self, component: dict, citations: list, case_context: dict) -> str:
        """Generate actionable fix suggestion for citizen."""
        messages = [
            {"role": "system", "content": "Tao huong dan bo sung ho so bang tieng Viet de hieu, cu the, hanh dong duoc."},
            {"role": "user", "content": json.dumps({
                "missing_component": component["name"],
                "citations": [{"law": c.get("law_code"), "article": c.get("article_num"), "text": c.get("text_excerpt")} for c in citations],
                "location": case_context.get("location", ""),
            }, ensure_ascii=False)}
        ]
        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.3)
        return response.choices[0].message.content
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| MATCHES_TTHC edge missing (Classifier failed) | No TTHCSpec found in traversal | Abort compliance check, return error, escalate to Orchestrator |
| LegalLookup returns no citations | Empty citation list | Still write Gap without citation, add `citation_pending: true` flag |
| Condition evaluation uncertain | LLM returns ambiguous reasoning | Default to "applies" (conservative -- include the requirement) |
| PII leakage in reasoning | Property mask should prevent | Double-check: never include national_id/phone in gap reason or fix_suggestion |
| Compliance score = 0 (all missing) | Normal edge case | Valid result; all components are gaps, case needs full resubmission |
| GDB timeout on find_missing_components | Query timeout > 15s | Retry once; if fails, return partial results with error flag |

## 10. Test Scenarios

### Test 1: CPXD case missing PCCC approval
**Input:** Case C-001 matched to TTHC 1.004415 (CPXD). Bundle has 5/6 documents. Missing: "Van ban tham duyet PCCC".
**Expected:** 1 Gap vertex with severity="blocker", reason="Thieu van ban tham duyet PCCC", fix_suggestion references PCCC office in Binh Duong, CITES edge to Article{136/2020/ND-CP, Dieu 13}. compliance_score = 83.3 (5/6).
**Verify:**
```groovy
g.V().has('Case','id','C-001').out('HAS_GAP').count()  // == 1
g.V().has('Case','id','C-001').values('compliance_score')  // == 83.3
g.V().has('Case','id','C-001').out('HAS_GAP').out('CITES').values('law_code')  // == "136/2020/ND-CP"
```

### Test 2: Complete case -- no gaps
**Input:** Case C-002 with all 6/6 required documents for CPXD, all valid.
**Expected:** 0 gaps, compliance_score = 100.0
**Verify:** `g.V().has('Case','id','C-002').out('HAS_GAP').count()` == 0

### Test 3: Conditional requirement -- does not apply
**Input:** Case C-003 for small project (50m2). RequiredComponent "Bao cao danh gia tac dong moi truong" has condition "chi bat buoc neu dien tich > 5000m2".
**Expected:** Condition evaluated as not applicable. No gap for DTM. Only gaps for actually missing required items.
**Verify:** No Gap vertex with component_name containing "danh gia tac dong moi truong"

### Test 4: Multiple gaps with mixed severity
**Input:** Case C-004 missing 2 required docs + 1 conditional doc.
**Expected:** 2 blocker gaps + 1 warning gap. compliance_score reflects only blockers.
**Verify:** Gap vertices have correct severity values.

## 11. Demo Moment

The Compliance Workspace screen shows:
1. Left: Document checklist with green checks and red X marks
2. Center: Gap details with legal citations (clickable to jump to law text)
3. Right: Compliance score gauge (animated fill)
4. Each gap shows: what's missing, why it's required (law citation), where to get it

**Pitch line:** "Day la trai tim cua GovFlow. Compliance agent tu dong kiem tra ho so theo dung quy dinh phap luat. Moi thieu sot deu co can cu phap ly cu the -- dieu/khoan/diem -- khong phai y kien chu quan."

## 12. Verification

```bash
# 1. Unit test: gap detection logic
pytest tests/agents/test_compliance.py -v

# 2. Core Gremlin template test
python -c "
from graph.client import GremlinClient
g = GremlinClient()
missing = g.submit('''
    g.V().has('Case','id','TEST-CPXD-001')
     .out('MATCHES_TTHC').out('REQUIRES').as('req')
     .where(__.not(__.in('SATISFIES').out('EXTRACTED_FROM').in('CONTAINS').has('id','TEST-CPXD-001')))
     .valueMap('name','is_required','condition')
''')
print(f'Missing components: {len(missing)}')
assert any('PCCC' in m.get('name','') for m in missing)
"

# 3. Compliance score accuracy
python -c "
from graph.client import GremlinClient
g = GremlinClient()
score = g.submit('g.V().has(\"Case\",\"id\",\"TEST-CPXD-001\").values(\"compliance_score\")')
assert 80 <= score[0] <= 85  # 5/6 components
"

# 4. PII leak check: verify no PII in gap output
python -c "
from graph.client import GremlinClient
g = GremlinClient()
gaps = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").out(\"HAS_GAP\").valueMap()')
for gap in gaps:
    assert 'national_id' not in str(gap)
    assert 'CCCD' not in gap.get('reason','')
"
```
