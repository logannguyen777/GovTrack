# Agent Catalog — 10 Agents + 1 Orchestrator

Mỗi agent là 1 Python class với role + scope + permission riêng. Mỗi agent có system prompt được tune cho task cụ thể, dùng Qwen3-Max hoặc Qwen3-VL tuỳ task.

---

## Orchestrator (không phải agent, là runtime)

### Role
Điều phối 10 agents. Spawn tasks, handle parallel execution, retry, fallback.

### Implementation
```python
class AgentRuntime:
    def __init__(self, case_id: str, graph: GremlinClient, mcp: MCPServer):
        self.case_id = case_id
        self.graph = graph
        self.mcp = mcp

    async def run(self):
        plan = await Planner(self).run(self.case_id)
        # plan is written to graph as Task vertices with DEPENDS_ON edges
        while self.has_pending_tasks():
            ready = self.get_ready_tasks()  # tasks with no pending deps
            await asyncio.gather(*[self.execute_task(t) for t in ready])
        return self.get_final_state()
```

### Features
- Reads Task vertices from graph, dispatches to appropriate agent
- Parallel execution where `DEPENDS_ON` edges allow
- Retry logic: max 2 retries with exponential backoff per tool call
- Fallback: if agent fails → write `Task.status = failed` + escalate human review
- WebSocket broadcast: every AgentStep write streams to frontend Agent Trace Viewer
- Gremlin Template Library exposed as MCP tools to agents

---

## Agent 1 — Planner

### Role
Đọc case đầu vào, hiểu loại TTHC, lên execution plan động dưới dạng Task DAG trong Context Graph.

### Model
Qwen3-Max với system prompt:
> "Bạn là Phó phòng Một cửa cấp Sở có 20 năm kinh nghiệm tại cơ quan nhà nước Việt Nam. Nhiệm vụ: phân tích bộ hồ sơ và quyết định pipeline xử lý. Output JSON với tasks, dependencies, priority."

### Input
- `case_id` (Case vertex mới tạo)
- Bundle vertices (chưa có Documents extracted — phải tự decide pipeline trước)

### Output
Write Task vertices vào Context Graph:
```
Task{name:"doc_analyze", depends_on:[], priority:"high"}
Task{name:"classify", depends_on:["doc_analyze"], priority:"high"}
Task{name:"security_scan_initial", depends_on:[], priority:"high"}
Task{name:"compliance_check", depends_on:["classify", "doc_analyze"]}
Task{name:"legal_lookup", depends_on:["compliance_check"]}
Task{name:"route", depends_on:["classify"]}
Task{name:"summarize", depends_on:["compliance_check", "legal_lookup"]}
Task{name:"draft_notice_if_gap", depends_on:["compliance_check"]}
```

### Permission scope
- **Read:** Case, Bundle, TTHCSpec catalog (KG)
- **Write:** Task vertices + DEPENDS_ON edges
- **Clearance cap:** Confidential

### Tools (via MCP)
- `graph.query_template("case.get_initial_metadata", case_id)`
- `graph.query_template("tthc.list_common", {})`
- `graph.create_tasks(tasks_json)`

### Why matters
Planner thể hiện "não" của hệ thống. Show reasoning trace cho judge: "Tại sao case này cần SecurityOfficer chạy trước?" → "Vì có từ 'mật' trong title hoặc vị trí là khu quân sự".

### Failure mode
Nếu Planner sai → cascaded downstream. Mitigation: có default plan fallback template cho mỗi TTHCSpec, Planner chỉ customize. Confidence threshold — nếu Planner uncertain → dùng template.

---

## Agent 2 — DocAnalyzer

### Role
Xử lý từng tài liệu trong bundle — OCR, layout understanding, doc type detection, entity extraction, validation thể thức.

### Model
Qwen3-VL-Plus (multimodal). Đây là agent duy nhất có quyền đọc raw image blobs.

### Input
- `case_id`
- Bundle vertices (có blob_url)

### Output
- Update `Document` vertices với `type`, `confidence`
- Create `ExtractedEntity` vertices với field_name, value
- Write validation results vào Document properties (`format_valid`, `signature_detected`)

### Permission scope
- **Read:** Bundle, Document raw, blob OSS
- **Write:** Document properties, ExtractedEntity, EXTRACTED edges
- **Clearance cap:** Top Secret (necessary to see raw content, but output goes through SecurityOfficer classification first)

### Tools
- `ocr_with_layout(blob_url)` — wraps Qwen3-VL
- `detect_doc_type(image, known_types)` — few-shot classifier
- `extract_entities(doc, schema)` — field extraction per doc type
- `detect_stamp_signature(image)` — red stamp + signature detection
- `validate_nd30_format(doc)` — check ND30/2020 thể thức compliance

### Special capabilities
- **Scan quality robust:** Qwen3-VL xử lý được scan xấu, mờ, lệch
- **Vietnamese stamp recognition:** con dấu đỏ, mộc tròn của cơ quan
- **Multi-page:** PDF nhiều trang + continuation logic
- **Mixed language:** Tiếng Việt chính + một ít tiếng Anh/Pháp cho thuật ngữ

### Failure mode
Nếu confidence < 0.7 cho doc type → flag cho human review tại Intake UI. Chuyên viên tiếp nhận confirm/correct manually, feedback loop cải thiện prompt.

---

## Agent 3 — Classifier

### Role
Nhận diện case này thuộc loại TTHC nào trong bộ thủ tục quốc gia. Xác định subject, urgency, suggest classification level.

### Model
Qwen3-Max với few-shot prompt chứa taxonomy của 5+ TTHC flagship.

### Input
- `case_id` + early DocAnalyzer output (document types + key entities)

### Output
- Create `MATCHES_TTHC` edge từ Case sang TTHCSpec vertex trong KG (**cross-graph**)
- Update Case.urgency
- Write initial classification suggestion (will be reviewed by SecurityOfficer)

### Permission scope
- **Read:** Case, Documents metadata (type only, not raw content), TTHCSpec + ProcedureCategory (KG)
- **Write:** MATCHES_TTHC edge, Case.urgency, initial classification draft
- **Clearance cap:** Confidential

### Tools
- `graph.query_template("tthc.find_by_category", category)`
- `classify_tthc(bundle_summary, taxonomy)` — few-shot LLM call
- `suggest_urgency(doc_metadata)` — rule-based + LLM
- `suggest_classification_level(bundle_summary, sensitive_keywords)` — passes to SecurityOfficer

### Grounding constraint
Classifier output *must* match an existing TTHCSpec vertex in KG. If no match → return `unknown_tthc` flag → escalate human. Không bao giờ "invent" TTHC code.

### Few-shot example
```
Example 1:
Bundle: [đơn cấp phép XD, GCN QSDĐ, bản vẽ, cam kết môi trường]
→ TTHC = 1.004415 "Cấp giấy phép xây dựng"

Example 2:
Bundle: [đơn đăng ký kinh doanh, điều lệ, danh sách thành viên, CCCD]
→ TTHC = 1.001757 "Đăng ký thành lập công ty TNHH"
```

---

## Agent 4 — Compliance

### Role
**The heart of GovFlow for legal reasoning.** Check hồ sơ có đủ thành phần không, thoả điều kiện không, có vi phạm quy định không. Gọi LegalLookup cho mỗi item cần tra.

### Model
Qwen3-Max — cần reasoning cao.

### Input
- `case_id` với `MATCHES_TTHC` đã có
- Documents + ExtractedEntities
- KG vertices: TTHCSpec + RequiredComponents + GOVERNED_BY Articles

### Output
- Create `Gap` vertices với `reason`, `severity`, `fix_suggestion`
- Create `HAS_GAP` edges từ Case
- Create `GAP_FOR` edges từ Gap sang RequiredComponent (KG cross-graph)
- Call LegalLookup for each Gap to get Citations
- Write `Compliance.score` on Case

### Permission scope
- **Read:** Case, Documents, ExtractedEntities, TTHCSpec, RequiredComponents, Articles (KG)
- **Write:** Gap, Citation, HAS_GAP, CITES edges
- **Cannot read:** Applicant PII (national_id, phone) — masked by property mask
- **Clearance cap:** Confidential

### Core query (Gremlin template)
```groovy
// case.find_missing_components
g.V().has('Case', 'id', ${case_id})
 .out('MATCHES_TTHC').out('REQUIRES').as('required_comp')
 .where(__.not(
    __.in('SATISFIES')              // assumed edge
       .out('EXTRACTED_FROM')
       .in('CONTAINS')
       .has('id', ${case_id})
 ))
 .valueMap('name', 'is_required', 'condition')
```

Results → for each missing → call LegalLookup → write Gap + Citation + CITES.

### Satisfiability logic
Some RequiredComponents có condition (e.g. "required only if project is nhóm I"). Compliance agent dùng Qwen3 reasoning để check condition apply cho case hiện tại không.

### Output example
```
Gap{
  reason: "Thiếu văn bản thẩm duyệt PCCC",
  severity: "blocker",
  fix_suggestion: "Nộp văn bản thẩm duyệt PCCC tại Cảnh sát PCCC tỉnh Bình Dương. Mẫu theo Phụ lục III NĐ 136/2020."
}
-[:CITES]-> Article{law_code:'136/2020/ND-CP', num:13}
```

---

## Agent 5 — LegalLookup

### Role
Agentic GraphRAG cho legal reasoning. Given một question hoặc required component, tìm điều luật có hiệu lực + cite chính xác.

### Model
Qwen3-Max + Qwen3-Embedding v3 (cho vector recall).

### Input
- Query (text hoặc structured: "find laws governing PCCC requirement for factory 500m²")

### Output
- `Citation` vertices với text_excerpt + article_ref edge sang Article in KG
- Return list of citations with confidence

### Permission scope
- **Read:** Law, Decree, Circular, Article, Clause, Point (KG) — filter by classification ≤ agent.clearance
- **Write:** Citation vertices (in Context Graph)
- **Clearance cap:** Confidential

### Process (GraphRAG pipeline)
1. **Vector recall** (Hologres Proxima): top-10 article candidates by semantic similarity
2. **Graph expansion**: for each candidate, traverse `SUPERSEDED_BY`/`AMENDED_BY` to get current effective version
3. **Relevance filter**: Qwen3-Max reranks candidates by case context
4. **Extract citation**: pick specific điều/khoản/điểm, write Citation vertex
5. **Cross-reference expansion**: follow `REFERENCES` 1 hop to add related articles

### Example query + result

Query: "Requirement văn bản thẩm duyệt PCCC cho nhà xưởng 500m² sản xuất điện tử"

Result:
```
Citation{
  text_excerpt: "Công trình thuộc nhóm II, khu công nghiệp, diện tích trên 300m² phải được thẩm duyệt PCCC",
  article_ref: -> Article{law_code:'136/2020/ND-CP', num:13, clause:2, point:'b'}
}
+
Citation{
  text_excerpt: "Hồ sơ đề nghị thẩm duyệt PCCC theo Phụ lục III",
  article_ref: -> Article{law_code:'136/2020/ND-CP', num:15}
}
```

See [`graphrag-legal-reasoning.md`](graphrag-legal-reasoning.md) for deeper walkthrough.

---

## Agent 6 — Router

### Role
Quyết định phòng ban chuyên môn xử lý chính, phòng consult, cán bộ thụ lý.

### Model
Qwen3-Max + rule engine hybrid.

### Input
- `case_id` với `MATCHES_TTHC` đã xác định
- KG Organization + Position vertices

### Output
- `ASSIGNED_TO` edge từ Case sang Organization
- `CONSULTED` edges (suggested)
- Assignment suggestion cho specific Position

### Permission scope
- **Read:** Case metadata (no PII), Organization, Position (KG)
- **Write:** ASSIGNED_TO, CONSULTED edges
- **Clearance cap:** Confidential

### Logic
1. Rule engine first: match TTHCSpec → AUTHORIZED_FOR → Organization (deterministic)
2. If multiple candidate orgs → Qwen3 reason based on case specifics (location, subject)
3. Workload check: `Position.current_workload` — prefer low workload
4. Consult suggestions: if case complex → suggest Pháp chế / chuyên ngành consult

### Confidence threshold
If confidence < 85% → write task with status "needs_human_review" instead of auto-assigning.

---

## Agent 7 — Consult

### Role
Khi cần xin ý kiến phòng khác (pháp chế, chuyên môn), tự soạn yêu cầu + tổng hợp phản hồi.

### Model
Qwen3-Max.

### Input
- `case_id`
- Consult target org from Router
- Specific question/issue

### Output
- `ConsultRequest` vertex with pre-summarized context
- After response: `Opinion` vertex aggregating responses

### Permission scope
- **Read:** Case summary (from Summarizer), Gap, Citation
- **Write:** ConsultRequest, Opinion, CONSULTED, HAS_OPINION edges
- **Cannot read:** full document content (only summary + specific gaps)
- **Clearance cap:** Confidential

### Replaces
Traditional "công văn xin ý kiến" process. Cắt 3–7 ngày → vài giờ/phút.

### Workflow integration
Consult request → notify target dept → human (anh Dũng persona 5) opens Consult Inbox → reviews pre-analyzed context → submits opinion → aggregator writes Opinion vertex.

---

## Agent 8 — Summarizer

### Role
Sinh 3 phiên bản summary khác nhau cho 3 audiences.

### Model
Qwen3-Max.

### Input
- `case_id` với đầy đủ Documents, Gaps, Citations, Decisions

### Output
- 3 `Summary` vertices: role=executive, staff, citizen
- All with different length + tone + masked appropriately

### Permission scope
- **Read:** Case (redacted view based on requester), Documents (entities masked), Gaps, Citations
- **Write:** Summary vertices
- **Clearance cap:** matches requester role

### 3 modes

**`executive`** (for lãnh đạo):
- 3 dòng + 1 action item + compliance score
- Focus: decision needed, risk, bottleneck
- Language: formal, data-forward

**`staff`** (for chuyên viên):
- 10 dòng + deadlines + legal references + open issues
- Focus: what to do next, what to check
- Language: technical, structured

**`citizen`** (for public):
- Plain Vietnamese, explain what happened, what's next
- Focus: user-facing, empathetic
- Language: simple, hopeful, action-oriented
- **Never contains sensitive info** (property mask enforced)

---

## Agent 9 — Drafter

### Role
Soạn VB output theo thể thức NĐ 30/2020 — quyết định, giấy phép, công văn trả lời, thông báo từ chối.

### Model
Qwen3-Max với structured output + validation loop.

### Input
- `case_id` với Decision, Opinion, Summary, Template

### Output
- `Draft` vertex với content_markdown
- Validated against NĐ 30/2020 rules (structure, header, footer, sign-off)

### Permission scope
- **Read:** Case, Decision, Opinion, Summary, Template (KG), Applicant (masked)
- **Write:** Draft vertex
- **Critical:** Cannot publish — must go through human review gate

### Templates
Stored in KG as `Template` vertices keyed by TTHC + decision type:
- CPXD approve → "Giấy phép xây dựng"
- CPXD deny → "Công văn từ chối cấp phép xây dựng"
- ĐKKD approve → "Giấy chứng nhận đăng ký doanh nghiệp"
- etc.

### Validation rules (NĐ 30/2020)
- Must have: Quốc hiệu + tiêu ngữ + số/ký hiệu + nơi + ngày + trích yếu + nội dung + nơi nhận + người ký
- Chữ ký: phải có position title + full name + placeholder cho digital signature
- Trích yếu ≤ 80 words
- Font: Times New Roman 13 (Vietnamese regulation)

### Citizen-facing variant
For every output, Drafter also generates a plain-language explanation:
- "Vì sao bị từ chối"
- "Cần làm gì tiếp theo"
- "Link hướng dẫn"

Stored as Summary{role:"citizen"}.

---

## Agent 10 — SecurityOfficer

### Role
Quyết định cấp mật cuối cùng. Check mọi access request. Log forensic audit. Can override other agents' classification.

### Model
Qwen3-Max với dedicated security system prompt.

### Input
- `case_id` với all content
- User access requests (intercepted by middleware)

### Output
- `Classification` vertex with level + reasoning
- Override Case.current_classification
- `AuditEvent` vertices for every access check

### Permission scope
- **Read:** Everything (including raw PII, classification metadata)
- **Write:** Classification, AuditEvent, can update Case.current_classification
- **Clearance cap:** Top Secret

### Rules
- **Keyword scan:** quốc phòng, nhân sự cấp cao, ngoại giao, tài chính công, dữ liệu cá nhân CCCD
- **Location sensitivity:** cross-check with geographic sensitive zones
- **Aggregation risk:** multiple low-sensitivity items combined may escalate classification
- **Human escalation:** if uncertain → flag for human security review

### Demo moment
When user without proper clearance tries to access → SecurityOfficer intercepts via Permission Engine → logs AuditEvent + returns deny + writes reasoning trace visible in Security Console.

---

## Agent-level permission summary table

| Agent | Primary Purpose | Read Scope | Write Scope | Clearance Cap |
|---|---|---|---|---|
| Planner | Plan execution | Case, TTHCSpec, Org (KG) | Task, PROCESSED_BY | Confidential |
| DocAnalyzer | OCR + extract | Bundle blobs, Document raw | Document props, ExtractedEntity | Top Secret |
| Classifier | TTHC matching | Case, Doc metadata, TTHC (KG) | MATCHES_TTHC edge | Confidential |
| Compliance | Gap detection | Case, Docs, Entities, TTHC, Articles | Gap, Citation, HAS_GAP, CITES | Confidential |
| LegalLookup | Legal RAG | Law, Decree, Article (filtered) | Citation | Confidential |
| Router | Department routing | Case metadata, Org (KG) | ASSIGNED_TO, CONSULTED | Confidential |
| Consult | Cross-dept opinion | Case summary, Gap | ConsultRequest, Opinion | Confidential |
| Summarizer | Role-aware summary | Case (masked), Docs (redacted) | Summary | varies by role |
| Drafter | Output generation | Case, Decision, Template | Draft | Confidential |
| **SecurityOfficer** | **Classification + access** | **Everything incl. PII** | **Classification, AuditEvent** | **Top Secret** |

## Deliberate design choices

1. **DocAnalyzer has Top Secret cap** — it needs to see raw content to do OCR. But output is immediately classified by SecurityOfficer before other agents read it.
2. **SecurityOfficer is the only agent with unrestricted read** — separation of duties.
3. **Drafter cannot publish** — human-in-the-loop enforced architecturally.
4. **All agents write AuditEvents** — every graph operation is logged.
5. **Clearance caps are hard limits** — an agent cannot exceed its cap even if user requests.
