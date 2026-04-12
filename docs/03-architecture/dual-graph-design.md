# Dual Graph Design — Knowledge Graph + Context Graph

GovFlow vận hành trên **2 đồ thị liên kết**. Đây là triết lý kiến trúc cốt lõi — xem [`../02-solution/why-graph-native.md`](../02-solution/why-graph-native.md) để hiểu *tại sao*.

## Summary

| Graph | Lifecycle | Write frequency | Purpose |
|---|---|---|---|
| **Knowledge Graph (KG)** | Build offline, near read-only | Rare updates (new laws) | Bộ não dài hạn của hệ thống — luật, TTHC, tổ chức |
| **Context Graph (CG)** | Per-case, runtime grown | High writes during processing | Case file + audit trail + reasoning trace |

Hai đồ thị tồn tại trong **cùng 1 Alibaba Cloud GDB instance**, phân biệt bằng label namespace (`KG:Law` vs `CG:Case`). Các cross-graph edge như `MATCHES_TTHC` nối CG vertices sang KG vertices.

---

## Knowledge Graph (KG) — Static

### Purpose
Bộ não dài hạn của hệ thống. Biểu diễn:
1. Cơ sở dữ liệu pháp luật Việt Nam với quan hệ tham chiếu chéo
2. Bộ thủ tục hành chính quốc gia
3. Cơ cấu tổ chức nhà nước
4. Taxonomy (loại VB, cấp mật, nhóm TTHC)
5. Templates VB output

### Vertex labels

#### Legal corpus
- **`Law`** — Luật (Luật XD, Luật Đất đai, Luật DN...)
  - `code` (string, unique) — e.g. "50/2014/QH13"
  - `name`
  - `issued_date`
  - `effective_date`
  - `classification` (Unclassified | Confidential | Secret | Top Secret)
  - `status` ("effective" | "amended" | "repealed")

- **`Decree`** — Nghị định (NĐ 61/2018, NĐ 15/2021...)
  - `code` — e.g. "15/2021/ND-CP"
  - `name`, `issued_date`, `effective_date`, `classification`, `status`

- **`Circular`** — Thông tư
- **`Decision`** — Quyết định (of Thủ tướng, Bộ...)

- **`Article`** — Điều
  - `law_code` (foreign ref)
  - `num` (int) — số điều
  - `title`
  - `text` (full text)
  - `classification`
  - `effective_date`

- **`Clause`** — Khoản (sub of Article)
- **`Point`** — Điểm (sub of Clause)

#### TTHC catalog
- **`TTHCSpec`** — một thủ tục hành chính công
  - `code` — e.g. "1.004415" (CPXD)
  - `name` — "Cấp giấy phép xây dựng"
  - `category` — e.g. "Xây dựng"
  - `authority_level` — Sở | Bộ | UBND huyện | UBND xã
  - `sla_days_law` — theo luật
  - `sla_days_typical` — thực tế
  - `fee_vnd`

- **`RequiredComponent`** — thành phần hồ sơ
  - `name` — e.g. "Văn bản thẩm duyệt PCCC"
  - `is_required` (bool)
  - `condition` — e.g. "when project_nature includes flammable materials"
  - `original_or_copy` — "original" | "copy" | "both"

- **`ProcedureCategory`** — nhóm TTHC
  - `name` — e.g. "Xây dựng", "Đất đai", "Kinh doanh"

#### Organization
- **`Organization`** — cơ quan nhà nước
  - `name` — "Sở Xây dựng Bình Dương"
  - `level` — "Bộ" | "Tỉnh" | "Huyện" | "Xã"
  - `parent_id`
  - `scope_regions` (array) — tỉnh/huyện/xã phụ trách

- **`Position`** — chức danh
  - `title` — "Phó Giám đốc Sở"
  - `authority_level`
  - `reports_to_position_id`

#### Templates
- **`Template`** — mẫu VB đầu ra
  - `doc_type` — "QuyetDinh", "CongVan", "ThongBao"
  - `tthc_code` — for which TTHC
  - `body_template` (Jinja template string)
  - `compliance_rules_nd30` (JSON)

#### Reference data
- **`ClassificationLevel`** — 4 cấp mật (Unclassified, Confidential, Secret, Top Secret)
- **`Precedent`** — case lịch sử đã xử lý (anonymized), optional cho demo

### Edge types (KG)

```
(Law)         -[:CONTAINS]->      (Article)
(Decree)      -[:CONTAINS]->      (Article)
(Article)     -[:HAS_CLAUSE]->    (Clause)
(Clause)      -[:HAS_POINT]->     (Point)

(Article)     -[:AMENDED_BY]->    (Article)       // lịch sử sửa đổi
(Article)     -[:SUPERSEDED_BY]-> (Article)       // bị thay thế
(Article)     -[:REPEALED_BY]->   (Decree)        // bị bãi bỏ
(Article)     -[:REFERENCES]->    (Article)       // tham chiếu chéo

(TTHCSpec)    -[:BELONGS_TO]->    (ProcedureCategory)
(TTHCSpec)    -[:REQUIRES]->      (RequiredComponent)
(TTHCSpec)    -[:GOVERNED_BY]->   (Article)       // luật chi phối
(TTHCSpec)    -[:RESULT_TEMPLATE]-> (Template)

(Organization)  -[:PARENT_OF]->    (Organization)  // hierarchy
(Organization)  -[:AUTHORIZED_FOR]->(TTHCSpec)     // thẩm quyền xử lý
(Position)      -[:BELONGS_TO]->   (Organization)
(Position)      -[:REPORTS_TO]->   (Position)
```

### Example KG fragment

```
(Law{code:'50/2014/QH13', name:'Luật Xây dựng'})
  -[:CONTAINS]-> (Article{num:95, law_code:'50/2014/QH13', text:'...'})
  -[:AMENDED_BY]-> (Article{num:95, law_code:'62/2020/QH14', text:'...'})

(Decree{code:'15/2021/ND-CP', name:'NĐ 15/2021'})
  -[:CONTAINS]-> (Article{num:41, text:'Thành phần hồ sơ đề nghị cấp GPXD'})
  -[:REFERENCES]-> (Article{num:13, law_code:'136/2020/ND-CP'})

(TTHCSpec{code:'1.004415', name:'Cấp giấy phép xây dựng'})
  -[:GOVERNED_BY]-> (Article{num:95, law_code:'50/2014/QH13'})
  -[:REQUIRES]-> (RequiredComponent{name:'Đơn đề nghị'})
  -[:REQUIRES]-> (RequiredComponent{name:'GCN QSDĐ'})
  -[:REQUIRES]-> (RequiredComponent{name:'Bản vẽ thiết kế'})
  -[:REQUIRES]-> (RequiredComponent{name:'Văn bản thẩm duyệt PCCC'})
                   -[:GOVERNED_BY]-> (Article{num:13, law_code:'136/2020/ND-CP'})
```

### KG size target (hackathon)

**Original estimate:** ~700 vertices, ~2000 edges

**Actual after ingest (12/04/2026):** Exceeded targets significantly thanks to pre-crawled HuggingFace datasets.

| Vertex label | Count | Source |
|---|---|---|
| Law | 61 | vbpl.vn via HF (15 core + 46 related) |
| Decree | 176 | vbpl.vn via HF |
| Circular | 266 | vbpl.vn via HF |
| Decision | 1,163 | vbpl.vn via HF (QĐ UBND các tỉnh) |
| Resolution | 409 | vbpl.vn via HF |
| Article | 861 | Parsed from 15 core laws |
| Clause | 3,660 | Parsed from core law articles |
| Point | 4,089 | Parsed from clauses |
| TTHCSpec | 5 | Curated from dichvucong.gov.vn |
| RequiredComponent | 27 | Curated per TTHC |
| ProcedureCategory | 5 | 5 nhóm TTHC |
| **Total** | **10,725** | |

| Edge label | Count |
|---|---|
| BASED_ON | 86,889 |
| SUPERSEDED_BY | 2,083 |
| AMENDED_BY | 1,979 |
| REPEALED_BY | 2,072 |
| REFERENCES | 1,680 |
| CONTAINS | 861 |
| HAS_CLAUSE | 3,660 |
| HAS_POINT | 4,089 |
| REQUIRES | 27 |
| GOVERNED_BY | 52 |
| BELONGS_TO | 5 |
| Others | ~1,163 |
| **Total** | **~104,560** |

**Note:** Organizations (~20) and Positions (~50) chưa ingest — cần thêm sau khi pick Sở cụ thể cho demo. Templates (~10) cũng pending.

### KG build strategy
See [`../08-execution/daily-plan.md`](../08-execution/daily-plan.md) — day 12/04 sáng tập trung build KG với Qwen3-Max làm NER + RE để parse luật auto.

---

## Context Graph (CG) — Dynamic

### Purpose
Per-case runtime. Khi công dân nộp hồ sơ, một subgraph mới được tạo ra với root là `Case` node. Subgraph grow khi agents xử lý.

Context Graph là:
- **Case file** — tất cả docs, entities, gaps, decisions
- **Audit trail** — AuditEvent immutable
- **Reasoning trace** — AgentSteps
- **Workflow state** — status, assignments, consults

### Vertex labels

#### Case core
- **`Case`** — gốc của 1 subgraph case
  - `id` (e.g. "C-20260411-0001")
  - `created_at`
  - `status` — "intake" | "processing" | "waiting_citizen" | "decided" | "published" | "closed"
  - `urgency` — "normal" | "urgent" | "critical"
  - `current_classification`
  - `sla_deadline`
  - `current_owner_position_id` (ref to KG)

- **`Applicant`** — người nộp
  - `type` — "citizen" | "business"
  - `vneid_subject` (for citizen — from Đề án 06)
  - `business_id` (for business — mã DN)
  - `display_name_masked` — "N*** Văn A" cho display
  - `national_id_encrypted` (raw, chỉ DocAnalyzer + SecurityOfficer thấy)
  - `contact_phone_masked`, `contact_email`

- **`Bundle`** — 1 bộ hồ sơ trong 1 case
  - `uploaded_at`
  - `source` — "portal" | "one_stop_desk" | "api"
  - `version` (int) — tăng khi công dân bổ sung

#### Documents & entities
- **`Document`** — 1 tài liệu trong bundle
  - `id`
  - `type` — "Đơn", "GCN_QSDĐ", "BanVeThietKe", "VBThamDuyetPCCC"...
  - `detected_by_agent` — "DocAnalyzer"
  - `confidence` (float 0–1)
  - `blob_url` (OSS signed URL)
  - `pages` (int)
  - `content_hash`

- **`ExtractedEntity`** — 1 field extracted từ document
  - `field_name` — e.g. "gcn_number", "area_m2", "location_address"
  - `value`
  - `confidence`
  - `extracted_by_agent` — "DocAnalyzer"
  - `agent_version`

#### Processing state
- **`Task`** — nhiệm vụ Planner sinh
  - `name` — e.g. "classify", "check_compliance"
  - `depends_on_task_ids` (array)
  - `status` — "pending" | "in_progress" | "completed" | "failed"
  - `assigned_to_agent`

- **`Gap`** — thiếu/vi phạm Compliance phát hiện
  - `reason` — "Thiếu văn bản thẩm duyệt PCCC"
  - `severity` — "blocker" | "warning" | "info"
  - `fix_suggestion`

- **`Citation`** — trích dẫn điều luật áp dụng
  - `text_excerpt` — đoạn text cụ thể
  - `article_ref` — edge ra KG Article

- **`Opinion`** — ý kiến consult từ phòng khác
  - `dept_id` (ref KG Organization)
  - `content`
  - `submitted_at`
  - `submitted_by_position_id`

- **`Summary`** — tóm tắt role-aware
  - `role` — "executive" | "staff" | "citizen"
  - `text`
  - `generated_by_agent` — "Summarizer"

- **`Classification`** — cấp mật quyết định bởi SecurityOfficer
  - `level` — "Unclassified" | "Confidential" | "Secret" | "Top Secret"
  - `reasoning` — explanation
  - `decided_by` — "SecurityOfficer" | "human_review"

- **`Decision`** — quyết định cuối
  - `type` — "approve" | "deny" | "request_more"
  - `decided_by_user_id`
  - `decided_at`
  - `reasoning`

- **`Draft`** — VB draft output
  - `type` — "QuyetDinh" | "CongVan" | "ThongBao"
  - `content_markdown`
  - `generated_by_agent` — "Drafter"
  - `human_reviewed_by`
  - `reviewed_at`

- **`PublishedDoc`** — VB đã publish
  - `doc_number` — số hiệu
  - `published_at`
  - `pdf_url` (OSS signed)
  - `citizen_notified_at`

#### Audit + agent trace
- **`AuditEvent`** — every read/write access
  - `actor_id` — user or agent
  - `actor_type` — "user" | "agent"
  - `action` — "read" | "write" | "delete" | "publish"
  - `resource_label`
  - `resource_id`
  - `result` — "allow" | "deny"
  - `reason`
  - `ip`, `user_agent`
  - `timestamp`

- **`AgentStep`** — 1 bước agent chạy
  - `agent_name`
  - `tool_used`
  - `input_json` (masked if sensitive)
  - `output_json` (masked)
  - `latency_ms`
  - `tokens_in`, `tokens_out`
  - `status` — "success" | "error"

### Edge types (CG)

```
(Case)     -[:SUBMITTED_BY]->  (Applicant)
(Case)     -[:HAS_BUNDLE]->    (Bundle)
(Bundle)   -[:CONTAINS]->      (Document)
(Document) -[:EXTRACTED]->     (ExtractedEntity)

(Case)     -[:MATCHES_TTHC]->  (TTHCSpec)        // CROSS-GRAPH to KG
(Case)     -[:HAS_TASK]->      (Task)
(Task)     -[:DEPENDS_ON]->    (Task)

(Case)     -[:HAS_GAP]->       (Gap)
(Gap)      -[:GAP_FOR]->       (RequiredComponent)  // CROSS-GRAPH
(Gap)      -[:CITES]->         (Article)            // CROSS-GRAPH
(Gap)      -[:HAS_CITATION]->  (Citation)

(Case)     -[:ASSIGNED_TO]->   (Organization)       // CROSS-GRAPH
(Case)     -[:CONSULTED]->     (Organization)       // CROSS-GRAPH
(Case)     -[:HAS_OPINION]->   (Opinion)
(Opinion)  -[:FROM_DEPT]->     (Organization)

(Case)     -[:HAS_SUMMARY]->   (Summary)
(Case)     -[:CLASSIFIED_AS]-> (Classification)

(Case)     -[:PROCESSED_BY]->  (AgentStep)          // reasoning trace
(AgentStep)-[:NEXT_STEP]->     (AgentStep)          // sequence

(Case)     -[:HAS_DECISION]->  (Decision)
(Case)     -[:HAS_DRAFT]->     (Draft)
(Draft)    -[:PUBLISHED_AS]->  (PublishedDoc)

(Case)     -[:AUDITS]->        (AuditEvent)         // audit trail
(*)        -[:AUDITS]->        (AuditEvent)         // any vertex can audit
```

### Context Graph growth pattern

Khi case được tạo:
```
t=0s:   Case node created
t=1s:   Applicant + Bundle vertices, CONTAINS edges
t=5s:   Planner writes Task vertices + dependencies
t=10s:  DocAnalyzer writes Document + ExtractedEntity vertices (parallel)
t=15s:  Classifier writes MATCHES_TTHC edge (cross-graph to KG)
t=20s:  SecurityOfficer writes Classification vertex
t=25s:  Compliance writes Gap + Citation vertices
t=30s:  LegalLookup writes more Citations
t=40s:  Router writes ASSIGNED_TO edge
t=50s:  Summarizer writes Summary vertices
t=60s:  Consult (if needed) writes Opinion vertices
...
```

Mỗi write sinh thêm `AgentStep` + `AuditEvent` + `PROCESSED_BY` edges.

Sau khi xong, Context Graph của 1 case có ~50–200 vertices và ~100–500 edges tuỳ độ phức tạp.

## Cross-graph queries — examples

### 1. "Tìm tất cả điều luật có hiệu lực chi phối case X"
```groovy
g.V().has('Case', 'id', 'C-20260411-0001')
 .out('MATCHES_TTHC')       // to TTHCSpec in KG
 .out('GOVERNED_BY')         // to Articles in KG
 .until(__.not(__.out('SUPERSEDED_BY')))
 .repeat(__.out('SUPERSEDED_BY'))
 .valueMap('num', 'law_code', 'text')
```

### 2. "Case X đang thiếu gì?"
```groovy
g.V().has('Case', 'id', 'C-20260411-0001')
 .out('HAS_GAP')
 .project('reason', 'component', 'cited_law')
 .by('reason')
 .by(__.out('GAP_FOR').values('name'))
 .by(__.out('CITES').valueMap('law_code', 'num'))
```

### 3. "Ai có quyền xử lý case X?"
```groovy
g.V().has('Case', 'id', 'C-20260411-0001')
 .out('MATCHES_TTHC')
 .in('AUTHORIZED_FOR')       // to Organizations in KG
 .in('BELONGS_TO')           // to Positions in KG
 .valueMap('title')
```

## Graph size projections

### Hackathon demo
- KG: ~700 vertices, ~2000 edges (fixed)
- CG per case: ~100 vertices, ~250 edges
- Demo data: 25 cases × 100 = 2,500 CG vertices + 6,250 edges
- **Total ~3,200 vertices, ~8,250 edges** — tiny for GDB

### PoC 1 Sở (10k cases/year)
- KG: ~5,000 vertices (expand law corpus), ~15,000 edges
- CG: 10k × 100 = 1M vertices/year + 2.5M edges/year
- **Totally manageable for Alibaba Cloud GDB**

## Implications for build

- Day 12/04 sáng: focus KG build (use Qwen3 NER to parse laws fast)
- Day 12/04 chiều: Context Graph write path + Template Library
- Day 13/04 permission engine + agents

See [`../08-execution/daily-plan.md`](../08-execution/daily-plan.md) for full timeline.
