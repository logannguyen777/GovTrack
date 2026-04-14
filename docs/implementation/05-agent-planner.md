# Agent Implementation: Planner (Agent 1) [DONE]

## 1. Objective

Generate a dynamic Task DAG for each incoming case. Read case metadata + bundle info, query the TTHC catalog from the Knowledge Graph, and write Task vertices with DEPENDS_ON edges into the Context Graph so the Orchestrator can dispatch agents in correct order.

## 2. Model

- **Model ID:** `qwen-max-latest`
- **Temperature:** 0.3 (structured output, low creativity)
- **Max tokens:** 2048
- **Response format:** JSON

## 3. System Prompt

```
Ban la Pho phong Mot cua cap So co 20 nam kinh nghiem tai co quan nha nuoc Viet Nam.
Nhiem vu cua ban: phan tich bo ho so TTHC dau vao va quyet dinh pipeline xu ly.

Quy tac:
1. Luon tao cac task: doc_analyze, classify, security_scan_initial, compliance_check, legal_lookup, route, summarize, draft_notice_if_gap
2. security_scan_initial LUON chay song song voi doc_analyze (khong co dependency)
3. classify phu thuoc doc_analyze
4. compliance_check phu thuoc classify VA doc_analyze
5. legal_lookup phu thuoc compliance_check
6. route phu thuoc classify
7. summarize phu thuoc compliance_check VA legal_lookup
8. draft_notice_if_gap phu thuoc compliance_check, chi chay neu co gap
9. Neu case co tu khoa nhay cam (quoc phong, mat, ngoai giao) -> security_scan_initial co priority = critical
10. Output PHAI la JSON voi format: {"tasks": [...], "priority": "normal|high|critical", "reasoning": "..."}

Moi task co format: {"name": "...", "agent": "...", "depends_on": [...], "priority": "...", "conditional": null | "has_gaps"}
```

## 4. Permission Profile YAML

```yaml
agent: Planner
role: planner
clearance_cap: Confidential

read_scope:
  node_labels:
    - Case
    - Bundle
    - Document        # metadata only
    - TTHCSpec        # KG
    - ProcedureCategory  # KG
  edge_types:
    - HAS_BUNDLE
    - CONTAINS
    - SUBMITTED_BY
    - BELONGS_TO      # TTHCSpec -> ProcedureCategory

write_scope:
  node_labels:
    - Task
    - AgentStep
  edge_types:
    - DEPENDS_ON
    - PROCESSED_BY

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
  - graph.create_vertex
  - graph.create_edge
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case | id, status, created_at, urgency |
| Context Graph | Bundle -> CONTAINS -> Document | count, filenames |
| Context Graph | Case -> SUBMITTED_BY -> Applicant | display_name (masked) |
| Knowledge Graph | TTHCSpec | code, name, category, sla_days_law |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | Task | name, agent, priority, status=pending, conditional |
| Context Graph | DEPENDS_ON | from Task to Task |
| Context Graph | PROCESSED_BY | from Case to AgentStep |
| Context Graph | AgentStep | agent_name, tool_used, input/output, latency_ms, tokens |

Typical output: ~8 Task vertices with ~10 DEPENDS_ON edges.

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `case.get_initial_metadata` | Read case + bundle size + doc count |
| `graph.query_template` | `tthc.list_common` | Get TTHC catalog for context |
| `graph.create_vertex` | Task | Write each task vertex |
| `graph.create_edge` | DEPENDS_ON | Wire dependency edges |

## 8. Implementation

```python
# backend/src/agents/planner.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
from graph.permitted_client import PermittedGremlinClient
import json

class PlannerAgent(BaseAgent):
    """Generate Task DAG for a new case."""

    AGENT_NAME = "Planner"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/planner.yaml"

    # Default fallback plan keyed by TTHC category
    DEFAULT_PLANS = {
        "xay_dung": [
            {"name": "doc_analyze", "agent": "DocAnalyzer", "depends_on": [], "priority": "high"},
            {"name": "classify", "agent": "Classifier", "depends_on": ["doc_analyze"], "priority": "high"},
            {"name": "security_scan_initial", "agent": "SecurityOfficer", "depends_on": [], "priority": "high"},
            {"name": "compliance_check", "agent": "Compliance", "depends_on": ["classify", "doc_analyze"], "priority": "high"},
            {"name": "legal_lookup", "agent": "LegalLookup", "depends_on": ["compliance_check"], "priority": "normal"},
            {"name": "route", "agent": "Router", "depends_on": ["classify"], "priority": "normal"},
            {"name": "summarize", "agent": "Summarizer", "depends_on": ["compliance_check", "legal_lookup"], "priority": "normal"},
            {"name": "draft_notice_if_gap", "agent": "Drafter", "depends_on": ["compliance_check"], "priority": "normal", "conditional": "has_gaps"},
        ],
        "_default": [...]  # same structure with normal priorities
    }

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Read case metadata via MCP tool
        case_meta = await self.mcp.call_tool(
            "graph.query_template",
            {"template_name": "case.get_initial_metadata", "parameters": {"case_id": case_id}}
        )

        # Step 2: Read TTHC catalog for context
        tthc_catalog = await self.mcp.call_tool(
            "graph.query_template",
            {"template_name": "tthc.list_common", "parameters": {"limit": 20}}
        )

        # Step 3: Call Qwen3-Max to generate plan
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "case_id": case_id,
                "case_metadata": case_meta,
                "tthc_catalog_summary": [t["code"] + ": " + t["name"] for t in tthc_catalog],
                "instruction": "Phan tich va tao execution plan cho case nay."
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(
            model=self.MODEL,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        plan = json.loads(response.choices[0].message.content)

        # Step 4: Confidence check — fallback to default if uncertain
        confidence = plan.get("confidence", 1.0)
        if confidence < 0.6:
            category = self._guess_category(case_meta)
            plan["tasks"] = self.DEFAULT_PLANS.get(category, self.DEFAULT_PLANS["_default"])
            plan["fallback_used"] = True
            self.log_warning(f"Low confidence {confidence}, using default plan for category={category}")

        # Step 5: Write Task vertices to Context Graph
        task_ids = {}
        for task in plan["tasks"]:
            task_vertex = await self.mcp.call_tool("graph.create_vertex", {
                "label": "Task",
                "properties": {
                    "name": task["name"],
                    "agent": task["agent"],
                    "priority": task.get("priority", "normal"),
                    "status": "pending",
                    "conditional": task.get("conditional"),
                    "case_id": case_id
                }
            })
            task_ids[task["name"]] = task_vertex["id"]

        # Step 6: Write DEPENDS_ON edges
        for task in plan["tasks"]:
            for dep_name in task.get("depends_on", []):
                if dep_name in task_ids:
                    await self.mcp.call_tool("graph.create_edge", {
                        "label": "DEPENDS_ON",
                        "from_id": task_ids[task["name"]],
                        "to_id": task_ids[dep_name]
                    })

        # Step 7: Log agent step + broadcast
        self.end_step(step, output={"task_count": len(plan["tasks"]), "plan": plan})
        await self.broadcast_ws({"type": "agent_step", "agent": self.AGENT_NAME, "case_id": case_id, "tasks": list(task_ids.keys())})

        return {"task_ids": task_ids, "plan": plan}

    def _guess_category(self, case_meta: dict) -> str:
        doc_count = case_meta.get("doc_count", 0)
        if doc_count >= 4:
            return "xay_dung"
        return "_default"
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Qwen3-Max returns invalid JSON | `json.loads` raises `JSONDecodeError` | Retry once with stricter prompt; if fails again, use DEFAULT_PLAN |
| Confidence < 0.6 | Check `plan.confidence` field | Use default template plan per TTHCSpec category |
| Qwen3-Max API timeout (>10s) | `asyncio.TimeoutError` | Retry once; if fails, use DEFAULT_PLAN + log warning |
| Qwen3-Max returns unknown task names | Validate against `KNOWN_TASK_NAMES` set | Strip unknown tasks, log warning |
| GDB write fails | Gremlin exception | Retry once with backoff; if fails, mark case as `planning_failed` |
| Circular dependency in DAG | Topological sort check post-generation | Reject plan, use DEFAULT_PLAN |

## 10. Test Scenarios

### Test 1: Standard CPXD case (5 documents)
**Input:** Case with 5 documents (don de nghi, GCN QSDD, ban ve, cam ket MT, GPKD)
**Expected:** 8 Task vertices created. `doc_analyze` and `security_scan_initial` have no dependencies. `compliance_check` depends on `classify` and `doc_analyze`. `draft_notice_if_gap` has `conditional: "has_gaps"`.
**Verify:** `g.V().has('Case','id',$id).out('PROCESSED_BY').has('agent_name','Planner').count()` == 1

### Test 2: Sensitive case (military keyword in title)
**Input:** Case with title containing "khu vuc quoc phong"
**Expected:** `security_scan_initial` has `priority: "critical"`. Plan `priority` is "critical".
**Verify:** `g.V().has('Task','name','security_scan_initial').has('case_id',$id).values('priority')` == "critical"

### Test 3: Low confidence fallback
**Input:** Ambiguous case with 1 document, no clear TTHC match
**Expected:** Planner returns low confidence. DEFAULT_PLAN used. `plan.fallback_used` == true.
**Verify:** AgentStep output_json contains `"fallback_used": true`

### Test 4: Dependency DAG validation
**Input:** Any valid case
**Expected:** Topological sort of tasks succeeds. No circular DEPENDS_ON edges.
**Verify:** `g.V().has('Task','case_id',$id).out('DEPENDS_ON').out('DEPENDS_ON').out('DEPENDS_ON').simplePath().count()` confirms acyclicity

## 11. Demo Moment

Show the Agent Trace Viewer with Planner's reasoning:
- Planner receives case metadata
- LLM reasoning trace explains: "Ho so co 5 tai lieu lien quan xay dung, co ban ve ky thuat -> CPXD. Vi tri tai KCN -> can security scan priority cao."
- Task DAG renders as animated directed graph in UI
- Nodes light up as agents start executing

**Pitch line:** "Planner la 'nao' cua he thong. No doc ho so, hieu context, va len ke hoach xu ly dong. Khong phai pipeline cung -- moi case co plan rieng."

## 12. Verification

```bash
# 1. Unit test: plan generation
pytest tests/agents/test_planner.py -v

# 2. Integration test: Task vertices written to GDB
python -c "
from graph.client import GremlinClient
g = GremlinClient()
tasks = g.submit('g.V().has(\"Task\",\"case_id\",\"TEST-001\").valueMap()')
assert len(tasks) >= 8
deps = g.submit('g.V().has(\"Task\",\"case_id\",\"TEST-001\").outE(\"DEPENDS_ON\").count()')
assert deps[0] >= 6
"

# 3. Default plan fallback test
python -c "
from agents.planner import PlannerAgent
p = PlannerAgent()
plan = p.DEFAULT_PLANS['xay_dung']
names = {t['name'] for t in plan}
assert 'doc_analyze' in names
assert 'compliance_check' in names
"

# 4. WebSocket event check
# Connect to ws://localhost:8000/ws/trace/TEST-001
# Expect event: {"type": "agent_step", "agent": "Planner", ...}
```
