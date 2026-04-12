# Agent Implementation: Consult (Agent 7)

## 1. Objective

Auto-draft cross-department consultation requests with pre-summarized case context, and aggregate opinions after responses. Replaces the traditional "cong van xin y kien" process that takes 3-7 days with a minutes-long automated flow. The agent reads only case summaries and gaps (never full document content) to enforce information minimization.

## 2. Model

- **Model ID:** `qwen-max-latest`
- **Temperature:** 0.4 (some creativity for natural language drafting)
- **Max tokens:** 2048
- **Response format:** JSON for structured output, text for draft content

## 3. System Prompt

```
Ban la chuyen vien Van phong So, chuyen soan cong van xin y kien va tong hop y kien.
Nhiem vu: soan yeu cau hoi y kien cho phong ban khac, tom tat boi canh ho so, va tong hop phan hoi.

Quy tac:
1. Yeu cau PHAI co: boi canh tom tat, van de can y kien, cau hoi cu the, thoi han tra loi
2. KHONG bao gom noi dung chi tiet tai lieu -- chi tom tat va cac gap da phat hien
3. KHONG bao gom thong tin ca nhan cong dan (CCCD, SDT, dia chi chi tiet)
4. Giu tone chuyen nghiep, ngan gon, hanh chinh
5. Moi yeu cau co 1 cau hoi CHINH va toi da 3 cau hoi PHU
6. Thoi han tra loi mac dinh: 2 ngay lam viec (tru khi khan cap)
7. Khi tong hop y kien: giu nguyen y nghia, trich dan chinh xac, khong suy dien

Output yeu cau: {"context_summary": "...", "main_question": "...", "sub_questions": [...], "deadline": "...", "urgency": "normal|high"}
Output tong hop: {"aggregated_opinion": "...", "consensus": true/false, "dissenting_views": [...], "recommendation": "..."}
```

## 4. Permission Profile YAML

```yaml
agent: Consult
role: consult_drafter
clearance_cap: Confidential

read_scope:
  node_labels:
    - Case            # summary only
    - Gap
    - Citation
    - Summary         # from Summarizer
    - Organization    # consult targets
  edge_types:
    - HAS_GAP
    - CITES
    - HAS_SUMMARY
    - CONSULTED
    - ASSIGNED_TO

write_scope:
  node_labels:
    - ConsultRequest
    - Opinion
    - AgentStep
  edge_types:
    - HAS_CONSULT_REQUEST
    - HAS_OPINION
    - CONSULTED
    - PROCESSED_BY

cannot_read:
  - Document.blob_url
  - Document.content_full
  - Applicant.national_id
  - Applicant.phone
  - Applicant.address_detail

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
| Context Graph | Case | id, urgency, tthc summary |
| Context Graph | Gap | reason, severity, fix_suggestion |
| Context Graph | Citation | text_excerpt, law_code, article_num |
| Context Graph | CONSULTED edge | target org id, reason (from Router) |
| Knowledge Graph | Organization | id, name, department_type |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | ConsultRequest | context_summary, main_question, sub_questions, deadline, status=pending, target_org_id |
| Context Graph | HAS_CONSULT_REQUEST | from Case to ConsultRequest |
| Context Graph | Opinion | content, source_org_id, submitted_at, aggregated=false (later true after aggregation) |
| Context Graph | HAS_OPINION | from ConsultRequest to Opinion |

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `case.get_full_context` | Get case summary + gaps + citations |
| `graph.query_template` | `case.get_consult_targets` | Get CONSULTED edges from Router |
| `graph.create_vertex` | ConsultRequest | Write consult request |
| `graph.create_vertex` | Opinion | Write aggregated opinion after responses |
| `graph.create_edge` | HAS_CONSULT_REQUEST, HAS_OPINION | Wire edges |

## 8. Implementation

```python
# backend/src/agents/consult.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
import json
from datetime import datetime, timedelta

class ConsultAgent(BaseAgent):
    """Auto-draft consult requests and aggregate opinions."""

    AGENT_NAME = "Consult"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/consult.yaml"
    DEFAULT_DEADLINE_DAYS = 2

    async def run(self, case_id: str) -> dict:
        """Draft consult requests for all CONSULTED targets."""
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get case context (summary level only)
        case_context = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_full_context",
            "parameters": {"case_id": case_id}
        })

        # Step 2: Get consult targets from Router
        consult_targets = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_consult_targets",
            "parameters": {"case_id": case_id}
        })

        if not consult_targets:
            self.end_step(step, output={"consult_requests": 0, "reason": "no_consult_targets"})
            return {"consult_requests": []}

        # Step 3: Draft consult request for each target
        requests = []
        for target in consult_targets:
            request = await self._draft_consult_request(case_id, case_context, target)
            requests.append(request)

        self.end_step(step, output={"consult_requests": len(requests)})
        await self.broadcast_ws({
            "type": "agent_step", "agent": self.AGENT_NAME, "case_id": case_id,
            "consult_requests_created": len(requests)
        })

        return {"consult_requests": requests}

    async def _draft_consult_request(self, case_id: str, case_context: dict, target: dict) -> dict:
        """Draft a single consult request for a target department."""
        step = self.begin_step("draft_request", {"target": target["name"]})

        # Build context for LLM (sanitized -- no PII, no full doc content)
        sanitized_context = {
            "tthc_name": case_context.get("tthc_name", ""),
            "gaps": [{"reason": g["reason"], "severity": g["severity"]} for g in case_context.get("gaps", [])],
            "citations": [{"law": c.get("law_code"), "article": c.get("article_num"), "text": c.get("text_excerpt", "")[:200]} for c in case_context.get("citations", [])],
            "urgency": case_context.get("urgency", "normal"),
            "consult_reason": target.get("reason", "")
        }

        # Determine deadline based on urgency
        deadline_days = 1 if case_context.get("urgency") == "critical" else self.DEFAULT_DEADLINE_DAYS
        deadline = (datetime.utcnow() + timedelta(days=deadline_days)).isoformat()

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "target_department": target["name"],
                "target_expertise": target.get("department_type", ""),
                "case_context": sanitized_context,
                "deadline_days": deadline_days,
                "instruction": "Soan yeu cau xin y kien. Tap trung vao van de can y kien tu phong ban nay."
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.4)
        draft = json.loads(response.choices[0].message.content)

        # Write ConsultRequest vertex
        cr_vertex = await self.mcp.call_tool("graph.create_vertex", {
            "label": "ConsultRequest",
            "properties": {
                "context_summary": draft["context_summary"],
                "main_question": draft["main_question"],
                "sub_questions": json.dumps(draft.get("sub_questions", []), ensure_ascii=False),
                "deadline": deadline,
                "status": "pending",
                "target_org_id": target["id"],
                "target_org_name": target["name"],
                "urgency": draft.get("urgency", "normal"),
                "case_id": case_id,
                "created_at": datetime.utcnow().isoformat()
            }
        })

        # Wire HAS_CONSULT_REQUEST edge
        await self.mcp.call_tool("graph.create_edge", {
            "label": "HAS_CONSULT_REQUEST",
            "from_vertex": {"label": "Case", "id": case_id},
            "to_id": cr_vertex["id"]
        })

        self.end_step(step, output={"consult_request_id": cr_vertex["id"]})
        return {"id": cr_vertex["id"], "target": target["name"], "main_question": draft["main_question"]}

    async def aggregate_opinions(self, case_id: str, consult_request_id: str) -> dict:
        """Aggregate opinions after departments respond. Called when all opinions received."""
        step = self.begin_step("aggregate", {"consult_request_id": consult_request_id})

        # Get all opinions for this consult request
        opinions = await self.mcp.call_tool("graph.query_template", {
            "template_name": "consult.get_opinions",
            "parameters": {"consult_request_id": consult_request_id}
        })

        if not opinions:
            self.end_step(step, output={"status": "no_opinions_yet"})
            return {"status": "waiting"}

        # Get original request context
        request = await self.mcp.call_tool("graph.query_template", {
            "template_name": "consult.get_request",
            "parameters": {"consult_request_id": consult_request_id}
        })

        # LLM aggregation
        messages = [
            {"role": "system", "content": "Tong hop y kien tu cac phong ban. Giu nguyen y nghia, neu ro dong thuan hay bat dong."},
            {"role": "user", "content": json.dumps({
                "original_question": request.get("main_question", ""),
                "opinions": [{"source": o.get("source_org_name"), "content": o.get("content")} for o in opinions],
                "instruction": "Tong hop. JSON: {\"aggregated_opinion\": \"...\", \"consensus\": true/false, \"dissenting_views\": [...], \"recommendation\": \"...\"}"
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.2)
        aggregation = json.loads(response.choices[0].message.content)

        # Write aggregated Opinion vertex
        opinion_vertex = await self.mcp.call_tool("graph.create_vertex", {
            "label": "Opinion",
            "properties": {
                "content": aggregation["aggregated_opinion"],
                "consensus": aggregation.get("consensus", True),
                "recommendation": aggregation.get("recommendation", ""),
                "aggregated": True,
                "opinion_count": len(opinions),
                "consult_request_id": consult_request_id,
                "created_at": datetime.utcnow().isoformat()
            }
        })

        # Wire HAS_OPINION edge
        await self.mcp.call_tool("graph.create_edge", {
            "label": "HAS_OPINION",
            "from_id": consult_request_id,
            "to_id": opinion_vertex["id"]
        })

        # Update consult request status
        await self.mcp.call_tool("graph.query_template", {
            "template_name": "vertex.update_property",
            "parameters": {"vertex_id": consult_request_id, "property": "status", "value": "completed"}
        })

        self.end_step(step, output=aggregation)
        return aggregation
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| No consult targets from Router | Empty `consult_targets` | Skip consult step entirely, proceed to next pipeline stage |
| Draft contains PII | Post-generation scan for CCCD/SDT patterns | Strip PII patterns, regenerate if needed |
| Opinion deadline passed without response | Cron job checks pending ConsultRequests | Auto-escalate: notify supervisor, allow pipeline to continue without opinion |
| Conflicting opinions | `consensus: false` in aggregation | Include all views in Opinion vertex, let human reviewer decide |
| LLM produces inappropriate question | Manual review of first few requests during testing | System prompt constraints + output validation |

## 10. Test Scenarios

### Test 1: Consult Phong Phap che for legal complexity
**Input:** Case C-001 with 2 gaps. Router set CONSULTED edge to Phong Phap che.
**Expected:** ConsultRequest vertex created with context_summary referencing gaps, main_question about legal requirements, deadline in 2 days.
**Verify:** `g.V().has('Case','id','C-001').out('HAS_CONSULT_REQUEST').has('target_org_name','Phong Phap che').count()` == 1

### Test 2: Urgent case -- shortened deadline
**Input:** Case with urgency="critical". CONSULTED edge to Phong Quy hoach.
**Expected:** ConsultRequest with deadline = 1 day, urgency = "high".
**Verify:** ConsultRequest vertex deadline is within 24 hours.

### Test 3: Opinion aggregation with consensus
**Input:** 2 opinions: Phong Phap che "OK", Phong Quy hoach "Phu hop quy hoach".
**Expected:** Aggregated opinion with `consensus: true`, recommendation = positive.
**Verify:** Opinion vertex has `aggregated: true`, `consensus: true`.

### Test 4: Opinion aggregation with dissent
**Input:** 2 opinions: one approves, one raises concerns about zoning.
**Expected:** `consensus: false`, `dissenting_views` includes the concern.
**Verify:** Opinion vertex captures both views.

## 11. Demo Moment

Show Consult Inbox screen (Persona 5 -- Anh Dung):
1. ConsultRequest arrives with pre-summarized context
2. Anh Dung sees: TL;DR of case, specific question, legal citations already found
3. Anh Dung types opinion in structured form
4. Submit -> Opinion vertex written -> aggregator runs -> pipeline continues
5. Total time: 2 minutes (vs traditional 3-7 day cong van process)

**Pitch line:** "Consult agent thay the quy trinh cong van xin y kien mat 3-7 ngay. Tu dong soan yeu cau voi boi canh da phan tich, phong ban nhan duoc 'ready-to-answer' thay vi 'start-from-scratch'."

## 12. Verification

```bash
# 1. Unit test: consult request drafting
pytest tests/agents/test_consult.py -v

# 2. ConsultRequest vertex in GDB
python -c "
from graph.client import GremlinClient
g = GremlinClient()
reqs = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").out(\"HAS_CONSULT_REQUEST\").valueMap()')
assert len(reqs) >= 1
for req in reqs:
    assert 'main_question' in req
    assert 'context_summary' in req
    assert req.get('status') == 'pending'
"

# 3. No PII in consult requests
python -c "
from graph.client import GremlinClient
g = GremlinClient()
reqs = g.submit('g.V().hasLabel(\"ConsultRequest\").valueMap()')
import re
cccd_pattern = re.compile(r'\\d{9,12}')
for req in reqs:
    for field in ['context_summary', 'main_question']:
        text = req.get(field, '')
        assert 'CCCD' not in text
        assert 'SDT' not in text
"

# 4. Opinion aggregation test
# Submit 2 opinions, trigger aggregation, verify Opinion vertex with consensus field
```
