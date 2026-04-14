# Agent Implementation: Router (Agent 6) [DONE]

## 1. Objective

Assign a case to the correct department and suggest consult targets. Uses a hybrid approach: deterministic rule engine first (TTHCSpec -> AUTHORIZED_FOR -> Organization), LLM disambiguation when multiple candidates exist, and workload balancing. Outputs ASSIGNED_TO and CONSULTED edges.

## 2. Model

- **Model ID:** `qwen-max-latest` (for disambiguation)
- **Temperature:** 0.2
- **Max tokens:** 1024
- **Response format:** JSON
- **Hybrid:** Rule engine first, LLM only when rules are insufficient

## 3. System Prompt

```
Ban la Chanh van phong So co 15 nam kinh nghiem dieu phoi cong viec giua cac phong ban.
Nhiem vu: xac dinh phong ban xu ly chinh va cac phong ban can hoi y kien cho ho so TTHC.

Quy tac:
1. UU TIEN quy tac: TTHCSpec -> AUTHORIZED_FOR -> Organization. Neu chi co 1 phong ban -> chi dinh luon.
2. Neu nhieu phong ban co tham quyen -> can nhac: vi tri dia ly, linh vuc chuyen mon, loai du an.
3. Kiem tra workload: uu tien phong ban co tai trong thap hon (current_workload thap).
4. De xuat consult khi:
   - Case co yeu to phap che phuc tap -> Phong Phap che
   - Case lien quan quy hoach -> Phong Quy hoach
   - Case co gia tri lon (> 10 ty) -> Lanh dao phe duyet
   - Case o vi tri nhay cam -> Phong An ninh (thong qua SecurityOfficer)
5. Confidence < 85% -> KHONG tu dong chi dinh, danh dau needs_human_review
6. Output JSON: {"assigned_dept": {"id": "...", "name": "..."}, "confidence": 0.XX, "consult_targets": [...], "reasoning": "..."}
```

## 4. Permission Profile YAML

```yaml
agent: Router
role: router
clearance_cap: Confidential

read_scope:
  node_labels:
    - Case            # metadata only
    - TTHCSpec        # KG
    - Organization    # KG
    - Position        # KG
  edge_types:
    - MATCHES_TTHC
    - AUTHORIZED_FOR
    - BELONGS_TO      # Position -> Organization
    - ASSIGNED_TO     # check existing assignments

write_scope:
  node_labels:
    - AgentStep
  edge_types:
    - ASSIGNED_TO
    - CONSULTED
    - PROCESSED_BY

property_masks:
  Applicant:
    national_id: redact
    phone: redact
    address_detail: redact
  Case:
    notes_internal: classification_gated:Secret

allowed_tools:
  - graph.query_template
  - graph.create_edge
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case | id, urgency, MATCHES_TTHC edge |
| Knowledge Graph | TTHCSpec -> AUTHORIZED_FOR -> Organization | org id, name, level, scope_regions |
| Knowledge Graph | Organization -> Position (BELONGS_TO) | position id, title, current_workload |
| Context Graph | Gap (count) | To determine complexity for consult suggestions |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | ASSIGNED_TO edge | from Case to Organization, with assigned_at, assigned_by=Router |
| Context Graph | CONSULTED edges | from Case to Organization (suggested consult targets) |
| Context Graph | AgentStep | routing reasoning trace |

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `org.find_authorized_for_tthc` | Find orgs authorized for this TTHC + region |
| `graph.query_template` | `org.find_positions_in_dept` | Get positions sorted by workload |
| `graph.query_template` | `case.assign_to_dept` | Write ASSIGNED_TO edge |
| `graph.create_edge` | CONSULTED | Write consult suggestion edges |

## 8. Implementation

```python
# backend/src/agents/router.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
import json
from datetime import datetime

class RouterAgent(BaseAgent):
    """Assign case to department using rule engine + LLM hybrid."""

    AGENT_NAME = "Router"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/router.yaml"
    CONFIDENCE_THRESHOLD = 0.85

    # Consult rules (deterministic)
    CONSULT_RULES = {
        "legal_complexity": {"condition": "gap_count >= 2", "target_dept_type": "phap_che"},
        "planning_related": {"condition": "location_in_kcn or zoning_flag", "target_dept_type": "quy_hoach"},
        "high_value": {"condition": "project_value > 10_000_000_000", "target_dept_type": "lanh_dao"},
    }

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get TTHC code from case
        case_tthc = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_tthc_match",
            "parameters": {"case_id": case_id}
        })
        tthc_code = case_tthc.get("tthc_code")
        region = case_tthc.get("region", "")

        if not tthc_code:
            self.end_step(step, output={"error": "no_tthc_match"})
            return {"error": "Case has no MATCHES_TTHC edge -- cannot route"}

        # Step 2: Rule engine -- find authorized organizations
        authorized_orgs = await self.mcp.call_tool("graph.query_template", {
            "template_name": "org.find_authorized_for_tthc",
            "parameters": {"tthc_code": tthc_code, "region": region}
        })

        # Step 3: Determine assignment
        if len(authorized_orgs) == 0:
            # No authorized org found
            result = {"assigned_dept": None, "confidence": 0, "needs_human_review": True,
                      "reasoning": "Khong tim thay phong ban co tham quyen cho TTHC nay"}

        elif len(authorized_orgs) == 1:
            # Single match -- deterministic assignment
            dept = authorized_orgs[0]
            result = {"assigned_dept": dept, "confidence": 0.99,
                      "reasoning": f"Chi co 1 phong ban co tham quyen: {dept['name']}"}

        else:
            # Multiple candidates -- LLM disambiguation + workload check
            result = await self._disambiguate_with_llm(
                case_id, case_tthc, authorized_orgs
            )

        # Step 4: Workload check on assigned dept
        if result.get("assigned_dept") and result["confidence"] >= self.CONFIDENCE_THRESHOLD:
            dept_id = result["assigned_dept"]["id"]
            positions = await self.mcp.call_tool("graph.query_template", {
                "template_name": "org.find_positions_in_dept",
                "parameters": {"dept_id": dept_id}
            })
            if positions:
                result["suggested_handler"] = positions[0]  # lowest workload

        # Step 5: Write ASSIGNED_TO edge (or flag for review)
        if result["confidence"] >= self.CONFIDENCE_THRESHOLD and result.get("assigned_dept"):
            await self.mcp.call_tool("graph.query_template", {
                "template_name": "case.assign_to_dept",
                "parameters": {
                    "case_id": case_id,
                    "dept_id": result["assigned_dept"]["id"],
                    "now": datetime.utcnow().isoformat(),
                    "user_id": "agent:Router"
                }
            })
        else:
            result["needs_human_review"] = True
            await self.mcp.call_tool("graph.query_template", {
                "template_name": "case.update_property",
                "parameters": {"case_id": case_id, "property": "routing_status", "value": "needs_human_review"}
            })

        # Step 6: Determine consult targets
        consult_targets = await self._determine_consult_targets(case_id, case_tthc)
        for target in consult_targets:
            await self.mcp.call_tool("graph.create_edge", {
                "label": "CONSULTED",
                "from_vertex": {"label": "Case", "id": case_id},
                "to_vertex": {"label": "Organization", "id": target["id"]},
                "properties": {"reason": target["reason"], "suggested_by": "Router"}
            })
        result["consult_targets"] = consult_targets

        self.end_step(step, output=result)
        await self.broadcast_ws({
            "type": "agent_step", "agent": self.AGENT_NAME, "case_id": case_id,
            "assigned_dept": result.get("assigned_dept", {}).get("name"),
            "confidence": result.get("confidence", 0),
            "consult_count": len(consult_targets)
        })

        return result

    async def _disambiguate_with_llm(self, case_id: str, case_tthc: dict, orgs: list) -> dict:
        """Use LLM to choose between multiple authorized departments."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "case_id": case_id,
                "tthc_code": case_tthc.get("tthc_code"),
                "tthc_name": case_tthc.get("tthc_name"),
                "region": case_tthc.get("region"),
                "candidate_departments": [
                    {"id": o["id"], "name": o["name"], "level": o.get("level"),
                     "scope": o.get("scope_regions")}
                    for o in orgs
                ],
                "instruction": "Chon 1 phong ban xu ly chinh. Tra ve JSON."
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.2)
        return json.loads(response.choices[0].message.content)

    async def _determine_consult_targets(self, case_id: str, case_tthc: dict) -> list:
        """Determine which departments should be consulted."""
        # Get gap count for complexity assessment
        gap_info = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_gap_count",
            "parameters": {"case_id": case_id}
        })
        gap_count = gap_info.get("count", 0)

        targets = []
        # Rule: legal complexity
        if gap_count >= 2:
            targets.append({"id": "dept_phap_che", "name": "Phong Phap che", "reason": "Ho so co nhieu thieu sot phap ly"})

        # Rule: location in KCN -> quy hoach
        location = case_tthc.get("location", "")
        if "KCN" in location or "khu cong nghiep" in location.lower():
            targets.append({"id": "dept_quy_hoach", "name": "Phong Quy hoach", "reason": "Cong trinh trong khu cong nghiep"})

        return targets
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| No MATCHES_TTHC edge (Classifier failed) | Empty case_tthc | Return error, Orchestrator retries after Classifier |
| No authorized org found | `len(authorized_orgs) == 0` | Flag `needs_human_review`, notify admin |
| LLM confidence < 85% | `result.confidence < CONFIDENCE_THRESHOLD` | Do NOT auto-assign, flag for human routing |
| Workload data stale | Position.current_workload not updated | Accept stale data (advisory only), log warning |
| GDB edge creation fails | Gremlin exception | Retry once; if fails, flag for manual assignment |

## 10. Test Scenarios

### Test 1: Single authorized department (deterministic)
**Input:** Case matched to TTHC 1.004415 (CPXD) in Binh Duong. Only one org authorized: Phong QLXD So XD Binh Duong.
**Expected:** `confidence: 0.99`, ASSIGNED_TO edge written, no LLM call needed.
**Verify:** `g.V().has('Case','id',$id).out('ASSIGNED_TO').values('name')` == "Phong QLXD"

### Test 2: Multiple candidates requiring LLM disambiguation
**Input:** Case in area where 2 departments share jurisdiction.
**Expected:** LLM selects based on case specifics, `confidence >= 0.85`, ASSIGNED_TO written.
**Verify:** Exactly 1 ASSIGNED_TO edge exists.

### Test 3: Low confidence -- needs human review
**Input:** Unusual case type with ambiguous jurisdiction.
**Expected:** `confidence < 0.85`, `needs_human_review: true`, no ASSIGNED_TO edge written.
**Verify:** Case has `routing_status: "needs_human_review"` property.

### Test 4: Consult suggestions
**Input:** CPXD case at KCN with 2 gaps.
**Expected:** CONSULTED edges to Phong Phap che (complexity) and Phong Quy hoach (KCN location).
**Verify:** `g.V().has('Case','id',$id).outE('CONSULTED').count()` >= 2

## 11. Demo Moment

In Department Inbox, show routing in action:
1. Case arrives, Router activates
2. Rule engine matches: "TTHC 1.004415 -> Phong QLXD authorized"
3. Workload check: "Anh Tuan (workload 3), Chi Lan (workload 7) -> suggest Anh Tuan"
4. Consult suggestions appear: "Phong Phap che (phan tich gap), Phong Quy hoach (vi tri KCN)"
5. ASSIGNED_TO edge animates into graph

**Pitch line:** "Router ket hop quy tac cung (TTHCSpec -> AUTHORIZED_FOR) voi Qwen3 de xu ly tinh huong phuc tap. Tu dong can bang tai trong va de xuat consult -- thay the quy trinh dieu phoi thu cong mat 1-2 ngay."

## 12. Verification

```bash
# 1. Unit test: routing logic
pytest tests/agents/test_router.py -v

# 2. Rule engine deterministic test
python -c "
from graph.client import GremlinClient
g = GremlinClient()
assigned = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").out(\"ASSIGNED_TO\").valueMap()')
assert len(assigned) == 1
assert assigned[0]['name'] == 'Phong QLXD'
"

# 3. Consult edges test
python -c "
from graph.client import GremlinClient
g = GremlinClient()
consults = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").outE(\"CONSULTED\").valueMap()')
assert len(consults) >= 1
assert any('Phap che' in c.get('reason','') or c.get('name','') for c in consults)
"

# 4. Human review flag test
# Submit ambiguous case -> verify no ASSIGNED_TO, routing_status = needs_human_review
```
