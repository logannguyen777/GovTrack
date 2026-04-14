# Agent Implementation: Summarizer (Agent 8) ✅

## 1. Objective

Generate 3 role-aware summaries for each case: executive (3 lines for leadership), staff (10 lines with legal references for case handlers), and citizen (plain Vietnamese for the applicant). Each summary is tailored to its audience in length, tone, detail level, and information access. The citizen summary MUST NOT contain PII -- enforced by Tier 3 property mask.

## 2. Model

- **Model ID:** `qwen-max-latest`
- **Temperature:** 0.4 (natural language generation)
- **Max tokens:** 2048
- **3 separate LLM calls, one per summary mode**

## 3. System Prompt

```
Ban la chuyen gia truyen thong hanh chinh, chuyen viet tom tat ho so TTHC cho nhieu doi tuong.

EXECUTIVE MODE (cho lanh dao):
- Toi da 3 dong
- Tap trung: quyet dinh can dua, rui ro, diem nghen
- Bao gom: compliance score, y kien phong ban, de xuat xu ly
- Tone: trang trong, data-driven, hanh dong

STAFF MODE (cho chuyen vien):
- Toi da 10 dong
- Bao gom: deadline, tham chieu phap luat, van de con mo, lich su xu ly
- Tone: ky thuat, co cau truc, chi tiet
- Ghi ro cac dieu/khoan/diem phap luat lien quan

CITIZEN MODE (cho cong dan):
- Tieng Viet binh dan, de hieu, than thien
- Giai thich: tinh trang ho so, buoc tiep theo, thoi gian du kien
- TUYET DOI KHONG chua: so CCCD, SDT, dia chi chi tiet, thong tin noi bo
- Tone: than thien, dong cam, huong den hanh dong
- Khong dung thuat ngu phap ly phuc tap

Output JSON: {"summary_text": "...", "mode": "executive|staff|citizen", "word_count": XX}
```

## 4. Permission Profile YAML

```yaml
agent: Summarizer
role: summarizer
clearance_cap: Confidential   # varies by mode; citizen mode = Unclassified

read_scope:
  node_labels:
    - Case
    - Document          # metadata and extracted entities only
    - ExtractedEntity
    - Gap
    - Citation
    - Opinion
    - Decision
    - Summary           # check existing summaries
  edge_types:
    - HAS_BUNDLE
    - CONTAINS
    - EXTRACTED
    - HAS_GAP
    - CITES
    - HAS_OPINION
    - HAS_DECISION
    - HAS_SUMMARY
    - MATCHES_TTHC

write_scope:
  node_labels:
    - Summary
    - AgentStep
  edge_types:
    - HAS_SUMMARY
    - PROCESSED_BY

property_masks:
  Applicant:
    national_id: redact
    phone: redact
    address_detail: redact
  Document:
    blob_url: redact
    content_full: redact
  Case:
    notes_internal: classification_gated:Secret

allowed_tools:
  - graph.query_template
  - graph.create_vertex
  - graph.create_edge
```

## 5. Input

| Source | Vertex/Edge | Fields Used |
|--------|------------|-------------|
| Context Graph | Case | id, status, urgency, compliance_score, tthc_name |
| Context Graph | Document | type, extracted entities (masked) |
| Context Graph | Gap | reason, severity, fix_suggestion |
| Context Graph | Citation | text_excerpt, law_code, article_num |
| Context Graph | Opinion | aggregated content, consensus |
| Context Graph | Decision | type (approve/deny), reasoning |

## 6. Output

| Target | Vertex/Edge | Fields Written |
|--------|------------|----------------|
| Context Graph | Summary (executive) | text, mode="executive", word_count, created_at |
| Context Graph | Summary (staff) | text, mode="staff", word_count, created_at |
| Context Graph | Summary (citizen) | text, mode="citizen", word_count, created_at |
| Context Graph | HAS_SUMMARY | from Case to each Summary |

## 7. MCP Tools Used

| Tool | Template | Purpose |
|------|----------|---------|
| `graph.query_template` | `case.get_full_context` | Get all case data for summarization |
| `graph.create_vertex` | Summary | Write each summary |
| `graph.create_edge` | HAS_SUMMARY | Link Case to Summary |

## 8. Implementation

```python
# backend/src/agents/summarizer.py

from agents.base import BaseAgent
from agents.qwen_client import qwen_chat
import json
import re
from datetime import datetime

class SummarizerAgent(BaseAgent):
    """Generate 3 role-aware summaries: executive, staff, citizen."""

    AGENT_NAME = "Summarizer"
    MODEL = "qwen-max-latest"
    PROFILE_PATH = "agents/profiles/summarizer.yaml"

    MODES = ["executive", "staff", "citizen"]
    PII_PATTERNS = [
        re.compile(r'\b\d{9,12}\b'),           # CCCD/CMND numbers
        re.compile(r'\b0\d{9,10}\b'),           # Phone numbers
        re.compile(r'\b\d{1,4}[\/\-]\d{1,4}\s+(duong|pho|ngo|hem)', re.IGNORECASE),  # Detailed address
    ]

    async def run(self, case_id: str) -> dict:
        step = self.begin_step("run", {"case_id": case_id})

        # Step 1: Get full case context (property-masked per agent profile)
        case_context = await self.mcp.call_tool("graph.query_template", {
            "template_name": "case.get_full_context",
            "parameters": {"case_id": case_id}
        })

        # Step 2: Generate all 3 summaries
        summaries = {}
        for mode in self.MODES:
            summary = await self._generate_summary(case_id, case_context, mode)
            summaries[mode] = summary

        self.end_step(step, output={
            "summaries_generated": len(summaries),
            "word_counts": {mode: s["word_count"] for mode, s in summaries.items()}
        })

        return {"summaries": summaries}

    async def _generate_summary(self, case_id: str, case_context: dict, mode: str) -> dict:
        """Generate a single summary for the given mode."""
        step = self.begin_step(f"generate_{mode}", {"case_id": case_id, "mode": mode})

        # Build mode-specific context
        context_for_llm = self._build_mode_context(case_context, mode)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json.dumps({
                "case_context": context_for_llm,
                "mode": mode,
                "instruction": self._mode_instruction(mode)
            }, ensure_ascii=False)}
        ]

        response = await qwen_chat(
            model=self.MODEL,
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"}
        )

        summary_data = json.loads(response.choices[0].message.content)
        summary_text = summary_data.get("summary_text", "")

        # CRITICAL: PII enforcement for citizen mode
        if mode == "citizen":
            summary_text = self._strip_pii(summary_text)
            if self._has_pii(summary_text):
                self.log_warning(f"PII detected in citizen summary after stripping, regenerating")
                summary_text = await self._regenerate_without_pii(case_context, summary_text)

        # Write Summary vertex
        summary_vertex = await self.mcp.call_tool("graph.create_vertex", {
            "label": "Summary",
            "properties": {
                "text": summary_text,
                "mode": mode,
                "word_count": len(summary_text.split()),
                "case_id": case_id,
                "created_at": datetime.utcnow().isoformat()
            }
        })

        # Wire HAS_SUMMARY edge
        await self.mcp.call_tool("graph.create_edge", {
            "label": "HAS_SUMMARY",
            "from_vertex": {"label": "Case", "id": case_id},
            "to_id": summary_vertex["id"]
        })

        result = {
            "id": summary_vertex["id"],
            "mode": mode,
            "text": summary_text,
            "word_count": len(summary_text.split())
        }
        self.end_step(step, output=result)
        return result

    def _build_mode_context(self, case_context: dict, mode: str) -> dict:
        """Build appropriate context per mode -- citizen gets minimal info."""
        base = {
            "tthc_name": case_context.get("tthc_name", ""),
            "status": case_context.get("status", ""),
            "compliance_score": case_context.get("compliance_score"),
        }

        if mode == "executive":
            base["gap_count"] = len(case_context.get("gaps", []))
            base["gap_severities"] = [g["severity"] for g in case_context.get("gaps", [])]
            base["opinions_summary"] = [o.get("recommendation", "") for o in case_context.get("opinions", [])]
            base["decision"] = case_context.get("decision", {})
            base["sla_remaining_days"] = case_context.get("sla_remaining_days")

        elif mode == "staff":
            base["gaps"] = case_context.get("gaps", [])
            base["citations"] = [
                {"law": c.get("law_code"), "article": c.get("article_num"), "clause": c.get("clause_num"), "text": c.get("text_excerpt", "")[:150]}
                for c in case_context.get("citations", [])
            ]
            base["opinions"] = case_context.get("opinions", [])
            base["entities"] = case_context.get("entities", [])[:20]  # top entities
            base["sla_deadline"] = case_context.get("sla_deadline")

        elif mode == "citizen":
            # Minimal -- no PII, no internal details
            base["gap_descriptions"] = [g.get("fix_suggestion", "") for g in case_context.get("gaps", [])]
            # Do NOT include entities, citations, opinions, internal notes

        return base

    def _mode_instruction(self, mode: str) -> str:
        instructions = {
            "executive": "Viet tom tat 3 dong cho lanh dao. Tap trung quyet dinh, rui ro, de xuat.",
            "staff": "Viet tom tat 10 dong cho chuyen vien. Bao gom deadline, luat, van de mo.",
            "citizen": "Viet tom tat bang tieng Viet binh dan cho cong dan. TUYET DOI KHONG chua thong tin ca nhan."
        }
        return instructions[mode]

    def _strip_pii(self, text: str) -> str:
        """Remove PII patterns from text."""
        for pattern in self.PII_PATTERNS:
            text = pattern.sub("[***]", text)
        return text

    def _has_pii(self, text: str) -> bool:
        """Check if text still contains PII patterns."""
        for pattern in self.PII_PATTERNS:
            if pattern.search(text):
                return True
        return False

    async def _regenerate_without_pii(self, case_context: dict, original: str) -> str:
        """Regenerate citizen summary with explicit PII removal instruction."""
        messages = [
            {"role": "system", "content": "Viet lai doan van sau, LOAI BO hoan toan moi thong tin ca nhan (so CCCD, SDT, dia chi)."},
            {"role": "user", "content": original}
        ]
        response = await qwen_chat(model=self.MODEL, messages=messages, temperature=0.2)
        return response.choices[0].message.content
```

## 9. Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| PII in citizen summary | Regex pattern match post-generation | Strip PII, regenerate if patterns still found |
| Summary too long | Word count check | Re-prompt with stricter length constraint |
| Missing case context (upstream agents failed) | Empty gaps/citations/opinions | Generate partial summary with available data, note "pending" items |
| LLM outputs in wrong mode/tone | Mode field check in output | Regenerate with explicit mode instruction |
| Qwen3-Max API failure | HTTP error | Retry once; if fails, generate minimal template-based summary |

## 10. Test Scenarios

### Test 1: Complete CPXD case -- all 3 summaries
**Input:** Case C-001, compliance 100%, 2 positive opinions, decision = approve.
**Expected:** 3 Summary vertices. Executive: 3 lines with "Approve" recommendation. Staff: 10 lines with ND citations. Citizen: plain Vietnamese, no PII.
**Verify:** `g.V().has('Case','id','C-001').out('HAS_SUMMARY').count()` == 3

### Test 2: Citizen summary PII enforcement
**Input:** Case where applicant data includes CCCD 079123456789, phone 0901234567.
**Expected:** Citizen summary contains ZERO PII. No 9-12 digit sequences. No phone patterns.
**Verify:**
```python
summary = get_citizen_summary('C-001')
assert '079' not in summary.text
assert '0901234567' not in summary.text
assert not re.search(r'\b\d{9,12}\b', summary.text)
```

### Test 3: Case with gaps -- citizen explanation
**Input:** Case C-002 with 1 blocker gap (missing PCCC).
**Expected:** Citizen summary explains what's missing in plain language, what to do next, expected timeline. No legal jargon.
**Verify:** Citizen summary contains actionable guidance without citing specific Dieu/Khoan.

### Test 4: Executive summary brevity
**Input:** Complex case with 3 gaps, 2 opinions, multiple citations.
**Expected:** Executive summary is exactly 3 lines max. Contains compliance score and recommendation.
**Verify:** `len(summary.text.strip().split('\n')) <= 3`

## 11. Demo Moment

Show Leadership Dashboard with executive summary:
> "Cap phep XD cho N** Van M*** (DN-XXX1234). Nha xuong 500m2 tai KCN My Phuoc. Compliance 100%. Phap che + Quy hoach da duyet. De xuat: Approve. SLA con 8 ngay."

Toggle to Staff View with detailed summary including law references.

Toggle to Citizen View showing plain language explanation.

**Pitch line:** "Summarizer sinh 3 phien ban tom tat cho 3 doi tuong khac nhau tu cung 1 bo du lieu. Cong dan nhan thong tin de hieu, chuyen vien nhan chi tiet ky thuat, lanh dao nhan 3 dong de quyet dinh. Va phan cong dan TUYET DOI khong chua thong tin ca nhan -- enforce bang Tier 3 property mask."

## 12. Verification

```bash
# 1. Unit test: all 3 modes
pytest tests/agents/test_summarizer.py -v

# 2. PII enforcement test
python -c "
from graph.client import GremlinClient
import re
g = GremlinClient()
citizen = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").out(\"HAS_SUMMARY\").has(\"mode\",\"citizen\").values(\"text\")')
for text in citizen:
    assert not re.search(r'\b\d{9,12}\b', text), f'PII found in citizen summary: {text}'
    print('Citizen summary PII check PASSED')
"

# 3. Summary count and modes
python -c "
from graph.client import GremlinClient
g = GremlinClient()
modes = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").out(\"HAS_SUMMARY\").values(\"mode\")')
assert set(modes) == {'executive', 'staff', 'citizen'}
"

# 4. Executive summary length check
python -c "
from graph.client import GremlinClient
g = GremlinClient()
exec_text = g.submit('g.V().has(\"Case\",\"id\",\"TEST-001\").out(\"HAS_SUMMARY\").has(\"mode\",\"executive\").values(\"text\")')[0]
lines = [l for l in exec_text.strip().split('\n') if l.strip()]
assert len(lines) <= 3, f'Executive summary too long: {len(lines)} lines'
"
```
