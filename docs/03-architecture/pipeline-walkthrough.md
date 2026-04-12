# Pipeline Walkthrough — 1 Case End-to-End

Follow 1 case từ lúc công dân nộp đến lúc nhận kết quả. Đi qua từng agent, từng graph operation, từng permission check.

## Scenario

**Anh Minh** (Persona 1) nộp hồ sơ cấp giấy phép xây dựng nhà xưởng 500m² qua Citizen Portal. Bundle gồm:

1. Đơn đề nghị cấp GPXD (1 page PDF)
2. Giấy chứng nhận QSDĐ (2 page scan, có dấu đỏ)
3. Bản vẽ thiết kế xây dựng (5 pages PDF)
4. Cam kết bảo vệ môi trường (1 page)
5. Giấy phép kinh doanh (1 page)

**Nhà xưởng nằm tại KCN Mỹ Phước, Bình Dương.**

## Sequence diagram

```
Citizen (Anh Minh)    Portal       FastAPI      Orchestrator    Agents       GDB           OSS
     │                  │             │              │              │            │             │
     │──upload bundle──▶│             │              │              │            │             │
     │                  │──POST /cases─▶            │              │            │             │
     │                  │             │──presigned URLs─────────────────────────▶│
     │                  │◀─URLs───────│              │              │            │             │
     │                  │──PUT blobs──────────────────────────────────────────────▶│
     │                  │             │──create Case─▶│              │──addV(Case)│             │
     │                  │             │◀─case_id─────│              │◀───────────│             │
     │                  │◀─case_id───│              │              │            │             │
     │                  │             │──run(case_id)▶│             │            │             │
     │                  │             │              │              │            │             │
     │                  │             │              │──Planner──▶ ─┼────────────▶│(query TTHC)│
     │                  │             │              │              │◀───────────│             │
     │                  │             │              │              │──addV(Task)▶│             │
     │                  │             │              │◀─task DAG────│            │             │
     │                  │             │              │              │            │             │
     │                  │             │              │──spawn parallel─┐         │             │
     │                  │             │              │  ├──DocAnalyzer▶│──OCR blob──────────────▶│
     │                  │             │              │  ├──Classifier──│            │             │
     │                  │             │              │  └──SecurityOfficer scan──┐ │             │
     │                  │             │              │                           │ │             │
     │                  │◀WebSocket──│◀─agent_step event stream──────────────────┘ │             │
     │                  │             │              │              │            │             │
     │                  │             │              │──Compliance──│            │             │
     │                  │             │              │              │──query missing─▶│         │
     │                  │             │              │              │◀─1 missing───│         │
     │                  │             │              │              │──LegalLookup─▶│         │
     │                  │             │              │              │◀─Citation────│         │
     │                  │             │              │              │──addV(Gap)──▶│         │
     │                  │             │              │              │            │             │
     │                  │             │              │──Drafter citizen notice─▶ │             │
     │                  │             │              │              │──addV(Draft)▶│         │
     │                  │             │              │              │            │             │
     │                  │             │──Notify──────▶ │             │            │             │
     │                  │◀──push notification────────────────────────────────────────            │
     │◀─notif: bổ sung──│            │              │              │            │             │
     │                  │             │              │              │            │             │
     │──upload bổ sung─▶│            │              │              │            │             │
     │                  │──POST /cases/{id}/bundles─▶                │            │             │
     │                  │             │              │              │            │             │
     │                  │             │              │──re-run from Compliance──▶ │            │
     │                  │             │              │              │ ... all OK now ...       │
     │                  │             │              │──Router──────│            │             │
     │                  │             │              │──Consult────│             │             │
     │                  │             │              │──Summarizer─▶│            │             │
     │                  │             │              │              │            │             │
     │                  │             │              │              │            │             │
Chị Hương (lead)       Dashboard    FastAPI      Orchestrator                                   │
     │                  │             │              │              │            │             │
     │──view inbox─────▶│            │              │              │            │             │
     │                  │──GET /leadership/inbox─▶  │              │──query──────▶│            │
     │                  │◀──case list──│              │              │◀───────────│            │
     │                  │◀────────────│              │              │            │             │
     │──click case─────▶│            │              │              │            │             │
     │                  │──GET /cases/{id}─▶        │              │            │             │
     │                  │              ──through property mask──────────────────▶│            │
     │                  │◀──masked case data──│      │              │            │             │
     │──approve────────▶│            │              │              │            │             │
     │                  │──POST /cases/{id}/decision─▶              │            │             │
     │                  │             │              │──Drafter──▶ │            │             │
     │                  │             │              │              │──addV(Draft)▶│         │
     │                  │             │              │              │            │             │
     │──review + sign──▶│            │              │              │            │             │
     │                  │──POST /cases/{id}/publish─▶                │            │             │
     │                  │             │              │              │──addV(PublishedDoc)▶│    │
     │                  │             │              │              │            │             │
     │                  │             │──notify citizen─────────────────────────────────────────▶│
     │◀─result ready────│            │              │              │            │             │
     │──download PDF───▶│            │              │              │            │             │
     │                  │◀─signed URL─│             │              │            │             │
     │◀─PDF─────────────│            │              │              │            │             │
```

---

## Phase-by-phase detail

### Phase 1 — Intake (0–5 seconds)

1. Anh Minh opens Citizen Portal, authenticates via VNeID
2. Selects TTHC: "Cấp giấy phép xây dựng"
3. Portal shows guided wizard: "Required documents: 5 items"
4. Anh Minh uploads 5 files via drag-and-drop
5. Portal requests presigned OSS URLs from FastAPI
6. Files upload directly to OSS (bypass backend for performance)
7. FastAPI creates `Case` vertex:
   ```groovy
   g.addV('Case')
    .property('id', 'C-20260412-0001')
    .property('status', 'intake')
    .property('created_at', now())
   g.addV('Applicant')
    .property('type', 'business')
    .property('vneid_subject', 'VN123456')
    .property('display_name_masked', 'Nguyễn Văn M***')
    .property('national_id_encrypted', encrypted_value)
   g.V().has('Case','id','C-20260412-0001')
    .addE('SUBMITTED_BY').to(applicant_vertex)
   // Create Bundle + Document placeholders
   ```
8. FastAPI calls `Orchestrator.run('C-20260412-0001')` asynchronously
9. Returns `case_id` to Portal, shows tracking page

**Permission checkpoints:**
- Citizen Portal uses public API with anti-abuse rate limiting
- FastAPI uses service account with write permission to `Case, Applicant, Bundle, Document` labels
- Upload path uses OSS signed URLs (time-bounded, no persistent credential)

---

### Phase 2 — Planner (5–8 seconds)

Orchestrator spawns `Planner` agent:

1. Planner reads Case + Bundle metadata:
   ```groovy
   g.V().has('Case','id',$case_id)
    .project('case', 'bundle_size', 'doc_count')
    .by(valueMap())
    .by(__.out('HAS_BUNDLE').out('CONTAINS').count())
   ```

2. Planner queries TTHC catalog (doesn't know yet which TTHC):
   ```groovy
   g.V().hasLabel('TTHCSpec').valueMap('code','name','category')
   ```

3. Planner calls Qwen3-Max with prompt:
   > "Anh Minh submitted a bundle of 5 documents for a construction-related request. Based on doc count and category hints, plan the execution pipeline. Output JSON with tasks and dependencies."

4. Qwen3-Max returns plan:
   ```json
   {
     "tasks": [
       {"name": "doc_analyze", "agent": "DocAnalyzer", "depends_on": []},
       {"name": "security_initial_scan", "agent": "SecurityOfficer", "depends_on": []},
       {"name": "classify", "agent": "Classifier", "depends_on": ["doc_analyze"]},
       {"name": "compliance_check", "agent": "Compliance", "depends_on": ["classify", "doc_analyze"]},
       {"name": "legal_lookup", "agent": "LegalLookup", "depends_on": ["compliance_check"]},
       {"name": "route", "agent": "Router", "depends_on": ["classify"]},
       {"name": "summarize", "agent": "Summarizer", "depends_on": ["compliance_check", "legal_lookup"]},
       {"name": "draft_notice", "agent": "Drafter", "depends_on": ["compliance_check"], "conditional": "has_gaps"}
     ],
     "priority": "normal",
     "human_checkpoints": ["pre_publish_review"]
   }
   ```

5. Planner writes Task vertices + DEPENDS_ON edges to Context Graph
6. Planner writes `AgentStep` vertex with its reasoning
7. WebSocket broadcasts event: `{type:"agent_step", agent:"Planner", case_id, ...}` → UI updates Agent Trace Viewer

**Permission:**
- Planner SDK Guard checks: read labels allowed (Case, Bundle, TTHCSpec), write labels allowed (Task, AgentStep, DEPENDS_ON edges, PROCESSED_BY edges). All ✓.

---

### Phase 3 — Parallel agents (8–25 seconds)

Orchestrator sees 3 tasks ready (no pending deps): `doc_analyze`, `security_initial_scan`. Spawns parallel.

#### DocAnalyzer (heavy, ~15s)

1. Reads Bundle → for each Document blob URL:
2. Downloads blob from OSS
3. Calls Qwen3-VL-Plus with prompt:
   > "This is a Vietnamese administrative document. Identify the document type, extract key fields (document number, date, issuing authority, stamps, signatures), and return structured JSON."
4. For each document, writes Document properties + ExtractedEntity vertices:
   ```groovy
   g.V().has('Document','id',$doc_id)
    .property('type','gcn_qsdd')
    .property('confidence', 0.94)
    .property('pages', 2)
    .property('has_red_stamp', true)

   g.addV('ExtractedEntity')
    .property('field_name', 'gcn_number')
    .property('value', 'BK 123456')
    .property('confidence', 0.98)
   g.V().has('Document','id',$doc_id).as('d')
    .V().has('ExtractedEntity','id',$entity_id)
    .addE('EXTRACTED').from('d')
   ```

5. For bản vẽ thiết kế: Qwen3-VL recognizes it's technical drawing + extracts: công trình loại C, diện tích 500m², chiều cao 8m.

6. For GCN QSDĐ: Qwen3-VL reads map + owner + location → extracts: thửa đất 1234, diện tích 800m², KCN Mỹ Phước, Bình Dương.

**Permission:**
- DocAnalyzer has Top Secret cap (needs to see raw) — but only this agent has that cap. Output is immediately processed by SecurityOfficer next.

#### SecurityOfficer initial scan (light, ~3s, runs parallel with DocAnalyzer)

1. Reads Case metadata only (no content yet because DocAnalyzer still running)
2. Check for red flags in metadata: none
3. Waits for DocAnalyzer to finish, then re-runs:
4. Reads ExtractedEntity with location = "KCN Mỹ Phước, Bình Dương"
5. Cross-checks with sensitivity zones: **KCN Mỹ Phước is near area with classified infrastructure** (hypothetical)
6. Classification decision: **Confidential** (due to location sensitivity)
7. Writes `Classification` vertex + `CLASSIFIED_AS` edge:
   ```groovy
   g.addV('Classification')
    .property('level', 'Confidential')
    .property('reasoning', 'Location within 5km of sensitive zone X')
    .property('decided_by', 'SecurityOfficer')
   g.V().has('Case','id',$case_id)
    .addE('CLASSIFIED_AS').to(classification_vertex)
   ```
8. Updates `Case.current_classification = 'Confidential'`

From this point, any access to this case requires clearance ≥ Confidential.

---

### Phase 4 — Classifier (25–28 seconds)

Depends on `doc_analyze` being done.

1. Classifier reads Case + Document types + key entities
2. Calls Qwen3-Max with few-shot prompt containing 5 TTHC taxonomies
3. Qwen3-Max returns: `TTHC code = 1.004415, confidence = 0.97`
4. Classifier grounds by checking TTHCSpec vertex exists in KG — yes
5. Writes `MATCHES_TTHC` cross-graph edge:
   ```groovy
   g.V().has('Case','id',$case_id).as('c')
    .V().hasLabel('TTHCSpec').has('code','1.004415')
    .addE('MATCHES_TTHC').from('c')
    .property('confidence', 0.97)
   ```
6. AgentStep written, WebSocket broadcasts

---

### Phase 5 — Compliance + LegalLookup (28–40 seconds)

Depends on `classify` + `doc_analyze`.

1. Compliance runs Gremlin Template `case.find_missing_components`:
   ```groovy
   g.V().has('Case','id',$case_id)
    .out('MATCHES_TTHC').out('REQUIRES').as('req')
    .where(__.not(
      __.in('SATISFIES').out('EXTRACTED_FROM').in('CONTAINS').has('id',$case_id)
    )).values('name')
   ```

2. Result: `["Văn bản thẩm duyệt PCCC"]` — thiếu 1 item

3. For each missing component, Compliance calls LegalLookup:
   - Query: "requirement for văn bản thẩm duyệt PCCC, construction project nhà xưởng 500m² tại KCN"
   - LegalLookup does GraphRAG: vector recall → graph traversal → returns Citation

4. LegalLookup returns:
   ```json
   {
     "articles": [
       {"law_code": "136/2020/ND-CP", "num": 13, "clause": 2, "point": "b",
        "text": "Công trình thuộc nhóm II, khu công nghiệp, diện tích trên 300m² phải được thẩm duyệt PCCC"}
     ],
     "still_effective": true
   }
   ```

5. Compliance writes:
   ```groovy
   g.addV('Gap')
    .property('reason', 'Thiếu văn bản thẩm duyệt PCCC')
    .property('severity', 'blocker')
    .property('fix_suggestion', 'Nộp văn bản thẩm duyệt PCCC tại Cảnh sát PCCC tỉnh Bình Dương')

   g.V().has('Case','id',$case_id).addE('HAS_GAP').to(gap_vertex)

   g.addV('Citation')
    .property('text_excerpt', 'Công trình thuộc nhóm II...')
   g.V().has('Gap','id',$gap_id).addE('HAS_CITATION').to(citation_vertex)

   g.V().has('Citation','id',$citation_id)
    .V().hasLabel('Article').has('law_code','136/2020/ND-CP').has('num',13)
    .addE('CITES_FROM').from(citation_vertex)  // cross-graph to KG
   ```

6. Compliance score: `1 blocker / 5 required = 80% complete`

---

### Phase 6 — Draft Citizen Notice (40–45 seconds)

Because `has_gaps=true`, Drafter is triggered immediately (before route).

1. Drafter reads Gap + Citation
2. Calls Qwen3-Max with prompt:
   > "Generate a plain-language notification for a Vietnamese SME business about missing document. Explain what's missing, why, and where to get it. Friendly tone, specific, actionable. Reference the law article."

3. Qwen3-Max output:
   > "Anh Minh,
   >
   > Hồ sơ cấp phép xây dựng của anh còn thiếu **Văn bản thẩm duyệt PCCC** theo NĐ 136/2020 Điều 13 (vì công trình trên 300m² tại khu công nghiệp).
   >
   > Anh vui lòng liên hệ **Phòng Cảnh sát PCCC Công an tỉnh Bình Dương** để xin thẩm duyệt.
   >
   > Thời gian thẩm duyệt: khoảng 10 ngày làm việc.
   >
   > Sau khi có văn bản, anh upload vào hồ sơ hiện tại qua [link]. Hồ sơ sẽ tiếp tục xử lý mà không cần nộp lại từ đầu.
   >
   > [Link hướng dẫn chi tiết]"

4. Drafter writes `Draft` vertex with this content
5. Notify service picks up Draft → sends push notification to anh Minh's phone

---

### Phase 7 — Wait for citizen (hours to days)

Case status → `waiting_citizen`. SLA clock paused. Leadership Dashboard shows this case with yellow badge "Đang chờ công dân".

Anh Minh receives push, click notification → opens Citizen Portal → sees detailed explanation → calls Cảnh sát PCCC → đi xin văn bản → trở lại portal → upload file → status updates.

---

### Phase 8 — Resume processing (after citizen returns)

1. New bundle upload triggers re-run from Compliance phase
2. Compliance re-checks `case.find_missing_components` — now returns `[]` (no gaps)
3. Case.status → `processing`
4. Router runs
5. Router queries KG: `Organization AUTHORIZED_FOR TTHC 1.004415`
6. Returns: Sở XD Bình Dương → Phòng Quản lý XD
7. Writes `ASSIGNED_TO` edge
8. Consult agent identifies consult targets: Phòng Pháp chế (routine), Phòng Quy hoạch (auto-flagged vì location trong KCN)
9. Writes `ConsultRequest` vertices

---

### Phase 9 — Cross-dept consult (async, ~minutes in demo)

1. Consult auto-drafts request with pre-analyzed context (Gap resolved, Citation, location details)
2. Phòng Pháp chế (Anh Dũng - Persona 5) opens Consult Inbox
3. Sees pre-analyzed case with TL;DR + LegalLookup findings
4. Submits opinion: "Phù hợp NĐ 15/2021. OK cấp phép."
5. Phòng Quy hoạch similar
6. Both opinions aggregated as `Opinion` vertices

---

### Phase 10 — Summarization (30 seconds)

Summarizer generates 3 summaries:

**Executive** (for Chị Hương):
> "Cấp phép XD cho N** Văn M*** (DN-XXX1234). Nhà xưởng 500m² tại KCN Mỹ Phước. Compliance 100%. Pháp chế + Quy hoạch đã duyệt. Đề xuất: Approve. SLA còn 8 ngày."

**Staff** (for Anh Tuấn):
> "Hồ sơ CPXD C-20260412-0001:
> - Công trình: Nhà xưởng sản xuất điện tử, 500m², cấp C
> - Vị trí: Lô X, KCN Mỹ Phước, P.Mỹ Phước, TX.Bến Cát, Bình Dương
> - Chủ đầu tư: Công ty TNHH ABC (DN-XXX1234)
> - Thành phần hồ sơ: 6/6 (sau bổ sung PCCC)
> - Căn cứ pháp lý: Luật XD 2014 Điều 95, NĐ 15/2021 Điều 41, NĐ 136/2020 Điều 13
> - Pháp chế opinion: OK
> - Quy hoạch opinion: OK (không xung đột quy hoạch)
> - SLA: 8 ngày còn lại (đã dùng 7 ngày)
> - Classification: Confidential (do gần vùng nhạy cảm)"

**Citizen** (for anh Minh when ready):
> "Hồ sơ của bạn đã hoàn thiện và đang được duyệt. Dự kiến có giấy phép trong 3–5 ngày tới. Chúng tôi sẽ thông báo khi sẵn sàng."

---

### Phase 11 — Leadership review + approve

1. Chị Hương opens Leadership Dashboard
2. Sees 15 cases to review. This case shows compliance score 100%, consult OK, all green.
3. Clicks → Document Viewer opens with:
   - Executive summary top
   - All entities highlighted
   - Citations clickable (jump to law article)
   - Audit trail tab
4. Clicks "Approve" → confirmation dialog
5. Writes `Decision` vertex:
   ```groovy
   g.addV('Decision')
    .property('type', 'approve')
    .property('decided_by_user_id', 'user:chi_huong')
    .property('decided_at', now())
    .property('reasoning', 'Compliance 100%, opinions OK')
   g.V().has('Case','id',$case_id).addE('HAS_DECISION').to(decision_vertex)
   ```

---

### Phase 12 — Drafter generates final VB (30 seconds)

1. Drafter picks Template for CPXD approval + Decision + Case data + Opinion
2. Calls Qwen3-Max with structured output per NĐ 30/2020 template
3. Output markdown:

```
ỦY BAN NHÂN DÂN       CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
TỈNH BÌNH DƯƠNG       Độc lập - Tự do - Hạnh phúc
SỞ XÂY DỰNG

Số: XXX/GPXD-SXD    Bình Dương, ngày 20 tháng 4 năm 2026

                    GIẤY PHÉP XÂY DỰNG

Căn cứ Luật Xây dựng ngày 18 tháng 6 năm 2014, Luật sửa đổi, bổ sung
một số điều của Luật Xây dựng ngày 17 tháng 6 năm 2020;
Căn cứ Nghị định số 15/2021/NĐ-CP ngày 03 tháng 3 năm 2021 của Chính phủ;
Căn cứ Nghị định số 136/2020/NĐ-CP ngày 24 tháng 11 năm 2020 của Chính phủ;
Xét đề nghị của Phòng Quản lý Xây dựng,

Giấy phép số: XXX/GPXD-SXD
Cấp cho: Công ty TNHH ABC
...
[theo đúng thể thức NĐ 30/2020]
```

4. Writes Draft vertex
5. Validator checks NĐ 30/2020 compliance: ✓
6. Status: awaiting human sign-off

---

### Phase 13 — Human review + publish (minutes)

1. Chị Hương reviews draft on screen
2. Minor edit (optional)
3. Clicks "Ký số + Phát hành"
4. Digital signature applied (Vietnamese PKI)
5. PublishedDoc vertex written
6. PDF generated, stored in OSS with signed URL
7. Case.status → `published`
8. Notify service sends push to anh Minh: "Giấy phép của bạn đã sẵn sàng"

---

### Phase 14 — Citizen receives result (seconds)

1. Anh Minh receives notification
2. Opens Citizen Portal
3. Clicks download → signed OSS URL returns PDF
4. PDF contains QR code for verification (scan anywhere, opens portal to verify authenticity)
5. Status → `closed`

---

## Timing summary

| Phase | Duration | Cumulative |
|---|---|---|
| 1. Intake + create case | 3–5s | 0–5s |
| 2. Planner | 3s | 5–8s |
| 3. Parallel (DocAnalyzer + Sec initial) | 15s | 8–23s |
| 4. Classifier | 3s | 23–26s |
| 5. Compliance + LegalLookup | 10s | 26–36s |
| 6. Drafter notice (if gap) | 5s | 36–41s |
| **7. Wait for citizen** | **hours to days** | |
| 8. Re-run from Compliance | 5s | +5s |
| 9. Router + Consult auto | parallel | +varies |
| 9b. Human consult response | minutes to hours (optional) | |
| 10. Summarizer | 3s | |
| 11. Leadership review | seconds to minutes | |
| 12. Drafter final VB | 5s | |
| 13. Sign + publish | seconds | |

**Total automated processing: ~60 seconds (vs current 1–3 months).**

**Only human-dependent time: citizen back-and-forth + leadership review + optional consult.**

## Audit trail — what gets logged

Every phase writes to graph:
- Each `AgentStep` with full input/output/latency/tokens
- Each graph read/write creates `AuditEvent`
- Each permission check (allow or deny) logged
- Each human action (approve, sign, view) logged

For this 1 case, estimated:
- ~150 AgentSteps (10 agents × ~15 steps each)
- ~500 AuditEvents (reads + writes + permission checks)
- ~40 ExtractedEntities
- ~10 Task vertices
- ~5 Opinion + Summary + Decision + Draft + PublishedDoc vertices

**Total ~700 vertices + ~1500 edges for 1 completed case.** Entire case file + audit trail + reasoning trace is 1 subgraph.

## Replay capability

Anyone with Security Console access can "replay" this case:
```groovy
g.V().has('Case','id','C-20260412-0001')
 .out('PROCESSED_BY')
 .order().by('timestamp')
 .valueMap('agent_name','tool_used','input_json','output_json','latency_ms','timestamp')
```

Result: step-by-step playback of every agent action + timing. Forensic-grade traceability.
