# Artifact Inventory — Cross-cut reference

> **What this is:** the single source of truth mapping **system artifacts** (outputs produced by the 10 agents + pipeline) to **UI surfaces** (where they appear) to **demo moments** (when judges see them on screen).
>
> **Why it exists:** "Judges see artifacts of system processing" is a first-class demo requirement. Without this cross-cut doc, every screen spec risks drifting from the narrative — a gap detected in Compliance might never surface in the citizen's view, a consult opinion might be written to the graph but never visualized. This inventory is the contract: if a row is here, the UI team builds it and the pitch team scripts it.
>
> **Update rule:** when you add a new WebSocket event type to [realtime-interactions.md §event types](./realtime-interactions.md#event-types), add a row to Table 1 of this file BEFORE updating `screen-catalog.md`. When you add a new agent to [agent-catalog.md](../03-architecture/agent-catalog.md), audit its outputs against Tables 1 and 2.

**Read alongside:**
- [screen-catalog.md](./screen-catalog.md) — screen definitions referenced by column 3
- [realtime-interactions.md](./realtime-interactions.md) — WS event types in column 2
- [design-tokens.md](./design-tokens.md) — animation durations/easings in column 5
- [07-pitch/demo-video-storyboard.md](../07-pitch/demo-video-storyboard.md) — demo scenes in column 6

---

## Table 1 — Artifact × Screen × Visual treatment

Primary cross-cut. One row per system artifact. Reading left-to-right: "what the system produces → what event carries it → where it shows up → what the user sees → how it animates in → when in the demo video."

| # | Artifact | Source event type | Produced by | Screens surfacing | Visual component | Animation (see [design-tokens.md §4](./design-tokens.md#4-motion--material-3-duration--easing-scale)) | Demo timestamp |
|---|---|---|---|---|---|---|---|
| 1 | **OCR progress per file** | `agent_step_start` (DocAnalyzer) + periodic `agent_step` progress chunks | DocAnalyzer (Qwen3-VL) | Intake UI | Row-level shimmer + per-file progress chip ("OCR 40%") | stagger 100ms entry, shimmer loop 1.5s linear, exit fade 200ms `--ease-standard` | Scene 2 @ 0:28-0:36 |
| 2 | **Document label** (e.g. "Đơn đề nghị", "GCN QSDĐ") | `agent_step_end` (DocAnalyzer) → `graph_update` adds Document vertex property | DocAnalyzer | Intake UI (row label), Compliance WS (doc list), Document Viewer (sidebar) | Text label + classification icon | fade-in 250ms `--ease-emphasized` | Scene 2 @ 0:32-0:38 |
| 3 | **ExtractedEntity** (diện tích, số GCN, con dấu, vị trí) | `graph_update` added_vertices | DocAnalyzer | Intake UI (entity chips), Compliance WS (info panel), Agent Trace Viewer (graph node), Document Viewer (hover popup) | `<EntityChip>` pill, `<EntityNode>` graph node, `<EntityHighlight>` PDF overlay | slide-in 250ms, 50ms stagger per entity | Scene 2 @ 0:32-0:40 |
| 4 | **TTHC classification** (e.g. "Cấp phép XD matched 1.004415") | `graph_update` added_edge `MATCHES_TTHC` + `case_status_change` | Classifier | Agent Trace Viewer (edge draw), Intake UI (dropdown auto-set), Compliance WS (header badge) | Animated edge, auto-selected dropdown, header badge | edge dashoffset draw 500ms `--ease-standard`, badge fade 250ms | Scene 3 @ 0:52-0:55 |
| 5 | **Classification level** (Unclassified/Confidential/Secret/Top Secret) | `case_classified` (SecurityOfficer agent_step_end) | SecurityOfficer | Agent Trace Viewer (graph node), Security Console (filter), Document Viewer (banner + badge), Citizen Portal (badge on tracking) | `<ClassificationBanner>` sticky top+bottom, `<ClassificationBadge>` inline | banner fade 200ms on mount, badge fade 250ms | Scene 7 @ 2:02-2:04 |
| 6 | **Gap vertex** (e.g. "thiếu Văn bản thẩm duyệt PCCC") | `gap_found` + `graph_update` added_vertex Gap + added_edge `HAS_GAP` | Compliance | Intake UI (alert callout + missing row), Compliance WS (checklist item amber), Agent Trace Viewer (GapNode + edge), Citizen Portal tracking (plain-language notice), Document Viewer (summary tab) | `<AlertCallout>`, `<ChecklistItem status="warning">`, `<GapNode>`, `<CitizenNotice>` | fade-in 250ms + amber pulse 600ms `--ease-emphasized` + camera auto-pan | Scene 3 @ 1:03, Scene 4 @ 1:10 |
| 7 | **Gremlin query text** (visible proof of graph traversal) | `agent_step` detail payload (Compliance) | Compliance | Agent Trace Viewer detail pane only | `<pre class="text-mono-13">` text overlay in step detail panel | fade 250ms on step click; syntax highlight on mount | Scene 3 @ 0:58-1:02 |
| 8 | **Citation vertex** ("NĐ 136/2020 Điều 13.2.b") | `citation_resolved` sub-event in `graph_update` | LegalLookup | Compliance WS (legal panel, clickable), Agent Trace Viewer (graph node + edge to Gap), Document Viewer (legal tab), KG Explorer (highlight), Citizen Portal (plain-language refs) | `<CitationLink>` clickable chip, `<CitationNode>` graph node, `<CitationEdge>` animated edge | edge draw 500ms `--ease-standard` + target node glow 600ms | Scene 3 @ 1:02-1:05 |
| 9 | **Article text excerpt** (full legal text of cited article) | on-demand fetch triggered by citation click | LegalLookup + KG read | KG Explorer (right panel), Document Viewer (legal tab expanded), Compliance WS (popover on citation hover) | `<ArticleText>` Source Serif 4 16/26 rendered block | slide-in 300ms `--ease-emphasized` (right panel), fade 250ms (popover) | (interactive only — not in video) |
| 10 | **Compliance score** (e.g. 80% → 100% after gap closed) | `compliance_computed` + `compliance_score_changed` | Compliance | Intake UI (bar), Compliance WS (big number + bar), Department Inbox (card badge), Leadership Dashboard (queue row), Document Viewer (info panel), Citizen Portal tracking | `<ComplianceBar>` progress bar + `<AnimatedCounter>` percentage | counter lerp 400ms `--ease-emphasized` + bar width transition 400ms | Scene 2 @ 0:38, Scene 5 @ 1:40 |
| 11 | **SLA countdown** (7d remaining → 2d → overdue) | derived from case timestamps (no WS, client-side tick) | — (computed) | Department Inbox (card badge), Leadership Dashboard (header metric + per-case row), Citizen Portal (tracking status), Document Viewer (header) | `<SLABadge>` with color transition + live countdown | color transition 400ms on threshold cross (green→amber→red) + counter every 60s | always on |
| 12 | **ConsultRequest vertex** | `consult_request` + `graph_update` added_vertex | Consult | Consult Inbox (list item + unread badge), Compliance WS (outgoing consult indicator + slide panel confirmation), Agent Trace Viewer (new node) | `<ConsultRequestCard>` in inbox, `<OutgoingConsultChip>` in Compliance WS, graph node | pulse 600ms + counter animate on inbox badge | (Q&A only — not in main video) |
| 13 | **Opinion vertex** (pháp chế/quy hoạch response) | `opinion_received` + `graph_update` added_vertex | Consult (human-in-the-loop) | Consult Inbox (status: replied), Compliance WS (Legal panel new line), Agent Trace Viewer (graph node), Document Viewer (audit tab) | `<OpinionCard>`, new line in legal panel with slide-in, graph node | pulse 600ms glow + stagger entry in legal panel | Scene 5 @ 1:28-1:32 |
| 14 | **Routing decision** (case ASSIGNED_TO dept/user) | `graph_update` added_edge `ASSIGNED_TO` + `case_status_change` | Router | Department Inbox (new card slides into column), Agent Trace Viewer (edge to Organization node), user notification bell | Card slide-in to Kanban column, graph edge, toast + bell increment | Kanban card slide-in 300ms `--ease-emphasized`, bell pulse 600ms | Scene 5 @ 1:22-1:26 |
| 15 | **AgentStep node** (per-step reasoning trace) | `agent_step_start` + `agent_step_end` | all 10 agents | Agent Trace Viewer (primary home — timeline + graph + detail pane) | `<AgentStepNode>` graph node, `<AgentStepRow>` timeline row, `<AgentStepDetail>` bottom panel | fade + glow 400ms `--ease-emphasized` on appear, pulse 600ms on complete | Scene 3 continuous (0:40-1:05) |
| 16 | **Summary variants** (executive / staff / citizen) | `agent_step_end` (Summarizer) | Summarizer | Document Viewer (3 tabs), Compliance WS (summary tab), Citizen Portal (plain-language version), Leadership Dashboard (card preview) | `<SummaryTabs>` with 3 variants, `<SummaryCard>` | tab content fade 200ms, card mount fade 250ms | Scene 5 @ 1:36-1:42 |
| 17 | **Draft document** (pre-publish VB) | `draft_generated` + `graph_update` added_vertex Draft | Drafter | Document Viewer (draft state variant — yellow "DRAFT" ribbon), Leadership Dashboard (preview in approve queue) | `<PDFPreview>` with `<DraftRibbon>` overlay, preview card | fade 250ms + ribbon pulse 600ms on generate | Scene 6 @ 1:45-1:52 |
| 18 | **PublishedDoc** (signed PDF + QR) | `published` + `graph_update` added_vertex PublishedDoc | Drafter (post-sign) | Document Viewer (published state — green seal + QR), Citizen Portal tracking (download button + QR), Leadership Dashboard (status: published) | `<PDFPreview>` with `<PublishedSeal>`, `<QRVerification>` | seal stamp animation 600ms `--ease-decelerate`, QR fade 300ms | Scene 6 @ 1:55-2:00 |
| 19 | **Decision** (approve/deny) | `decision_made` + `case_status_change` | (human) | Leadership Dashboard (button → state change), Document Viewer (header), Agent Trace Viewer (decision node) | Big button → success toast + state badge transition, graph DecisionNode | button glow pulse 600ms + state transition color 400ms | Scene 5 @ 1:42-1:45 |
| 20 | **PermissionDenied — Tier 1 (SDK Guard)** | `permission_denied` with `tier: "sdk_guard"` | SDK runtime | Security Console (audit log row red), toast on any screen where denied action was attempted | `<AuditLogRow status="denied">` + red flash, `<PermissionDeniedToast>` | shake 200ms + red flash 400ms + toast slide-in 300ms | Scene 7 @ 2:05-2:08 |
| 21 | **PermissionDenied — Tier 2 (GDB RBAC)** | `permission_denied` with `tier: "gdb_rbac"` | GDB server | Security Console (audit log row red), graph edge write failure visible in Agent Trace Viewer | `<AuditLogRow>` + `<FailedEdgeIndicator>` | shake 200ms + red flash | Scene 7 @ 2:08-2:11 |
| 22 | **Classification mask applied** (property redacted) | `mask_applied` (client-side render) + server returns `[REDACTED]` for no-clearance properties | SDK Guard (property mask) | Document Viewer, Compliance WS (doc preview), any PDF view | `<Redacted>` solid bar with rounded corners (NOT blur per [design-system.md classification section](./design-system.md)) | solid bar static; content crossfade 250ms on elevation reveal | Scene 7 @ 2:11-2:15 |
| 23 | **AuditEvent** (every read/write/deny) | `audit_written` (batched) | SecurityOfficer | Security Console (live log primary), Document Viewer (audit tab), Case audit panel | `<AuditLogRow>` | slide-in 200ms `--ease-emphasized`, stagger 50ms if batch | Scene 7 continuous |
| 24 | **Anomaly alert** ("12 denied access in 10 min by user xyz") | `anomaly_detected` | SecurityOfficer | Security Console (prominent banner), Leadership Dashboard (warning card) | `<AnomalyBanner>` + `<AnomalyCard>` | fade + slide-down 300ms + red pulse 600ms | (live Q&A only) |
| 25 | **Case status change** (generic transition) | `case_status_change` | Router / Compliance / Drafter | Timeline on Citizen Portal, status badge on every case view, Department Inbox (column move) | Timeline step fill, badge color morph, Kanban card animated column move | fill 400ms, badge morph 400ms, Kanban move 300ms | Scene 4 @ 1:15, Scene 5 @ 1:28, Scene 6 @ 1:55 |
| 26 | **Notification** (in-app bell + push) | `notification` | any agent | All internal screens (bell in header), Citizen Portal (tracking page auto-update on push) | `<NotificationBell>` with counter, toast, `<NotificationPopover>` | bell pulse + counter animate + toast spring entry (1 of 2 spring uses — user-actor pattern) | Scene 4 @ 1:06 (push on phone) |
| 27 | **Consult pre-analyzed context** (case summary, legal refs, precedents auto-populated by Consult agent for Dũng) | pre-computed on `consult_request` creation | Consult + LegalLookup + Summarizer | Consult Inbox detail panel | `<PreAnalyzedContext>` with collapsible sections | fade 250ms on selection | — |
| 28 | **Precedent cases** (semantic similarity via Hologres Proxima) | on-demand fetch on case load | semantic search | Document Viewer (related cases cards), Compliance WS (precedent tab), Consult Inbox | `<PrecedentCaseCard>` mini | fade 250ms + stagger 50ms | — |
| 29 | **Law subgraph** (amendment chain, related articles) | on-demand Cytoscape load | KG read | KG Explorer (primary), Compliance WS (inline mini on citation hover) | Full Cytoscape canvas, mini graph popover | cytoscape cola layout animate 600ms on load, popover fade 250ms | (Q&A only) |
| 30 | **AI Weekly Brief** (Hologres AI Function → Qwen inline) | on-demand button click | Hologres AI Function | Leadership Dashboard | `<WeeklyBriefModal>` with streaming Qwen response | token streaming at ~40 tokens/sec + cursor blink | (optional bonus — Scene 8 B-roll) |

**Row count:** 30 artifacts. Every WebSocket event type in [realtime-interactions.md §event types](./realtime-interactions.md#event-types) maps to at least one row. Any new event type requires a new row here first.

---

## Table 2 — Screen × Artifacts visible (inverse view, acceptance criteria)

For each screen, the artifacts that MUST surface (in **bold**), SHOULD surface (regular), and MAY surface conditionally (italic). Use this as the build acceptance check: if a screen ships without a MUST artifact, it is incomplete.

### 1. Citizen Portal (home + tracking)

- **MUST:** Case status change (#25), Gap vertex plain-language notice (#6), Published doc with QR download (#18), SLA countdown (#11), Notification push (#26)
- SHOULD: Classification badge (#5), Citation refs in plain language (#8), Draft doc (#17 — only if "being prepared" status)
- *MAY:* Decision state (#19 — shown as "approved/denied" in tracking only)

### 2. Intake UI

- **MUST:** OCR progress per file (#1), Document label (#2), ExtractedEntity chips (#3), TTHC classification auto-fill (#4), Compliance score bar (#10), Gap vertex alert (#6)
- SHOULD: Classification level preview (#5), SLA countdown on successful intake (#11)
- *MAY:* Notification confirmation (#26 — post-intake)

### 3. Agent Trace Viewer (signature)

- **MUST:** AgentStep nodes for all 10 agents (#15), Gremlin query text in detail pane (#7), Graph update events live (#3, #4, #6, #8, #14), Gap vertex + edge (#6), Citation node + edge (#8), PermissionDenied indication if any (#20, #21), Routing edge (#14)
- SHOULD: ExtractedEntity nodes (#3), Document nodes (#2), Decision node (#19), Draft node (#17)
- *MAY:* Published node (#18), Opinion node (#13 — if case has consult)

### 4. Compliance Workspace

- **MUST:** Document labels + previews (#2), ExtractedEntity info panel (#3), Compliance score (#10), Gap checklist (#6), Citation legal panel clickable (#8), Summary tabs (#16), Consult dialog + slide panel (#12), Opinion receipt in legal panel (#13)
- SHOULD: Classification banner (#5), SLA countdown header (#11), Audit trail tab (#23), Precedent cases (#28)
- *MAY:* AI Weekly Brief link (#30)

### 5. Department Inbox (Kanban)

- **MUST:** Case cards with compliance score (#10), SLA countdown (#11), Classification badge (#5), Status change animations (#25), Routing decision (new cards arriving) (#14)
- SHOULD: Gap indicator on cards (#6), Consult status (#12, #13)
- *MAY:* Anomaly alerts banner (#24 — if any)

### 6. Leadership Dashboard

- **MUST:** 4 KPI metrics with counter animate (#10, #11, and derived), SLA by TTHC chart (#11), Processing time trend, Approve queue with compliance scores (#10), Decision buttons (#19), Published status (#18)
- SHOULD: Draft preview in approve queue (#17), Summary card preview (#16), AI Weekly Brief button (#30), Anomaly warning (#24)
- *MAY:* Citation quick view on hover (#8)

### 7. Security Console

- **MUST:** AuditEvent live log (#23), PermissionDenied Tier 1 (#20), PermissionDenied Tier 2 (#21), Classification mask demo (#22), Anomaly alerts (#24), Classification filter (#5)
- SHOULD: Forensic replay of case → Agent Trace Viewer (#15), Policy editor (not in inventory — static config)
- *MAY:* User management (static config)

### 8. Document Viewer

- **MUST:** PDF with ExtractedEntity highlights (#3), Document label sidebar (#2), Classification banner sticky top+bottom (#5), Compliance score in info panel (#10), Summary tabs × 3 (#16), Citation legal tab (#8), AuditEvent audit tab (#23), SLA countdown header (#11), Decision buttons if authorized (#19), Draft ribbon if draft state (#17), Published seal + QR if published (#18)
- SHOULD: Precedent cases (#28), Classification mask on PII (#22), Opinion history (#13)
- *MAY:* Article text excerpt popover on citation hover (#9)

### 9. Consult Inbox (NEW)

- **MUST:** ConsultRequest list items (#12), Pre-analyzed context in detail panel (#27), Citation pre-loaded refs (#8), Opinion input + submission (#13), Precedent cases (#28), SLA countdown (#11), Classification badge (#5)
- SHOULD: Document preview of referenced case (#2, #3), Summary preview (#16)
- *MAY:* Notification bell highlights new requests (#26)

### 10. KG Explorer (NEW)

- **MUST:** Law subgraph cola layout (#29), Article text in right panel (#9), Citation navigation (#8), Classification filter (#5), SUPERSEDED_BY amendment chain highlighting
- SHOULD: TTHC → Article `REQUIRES` edges, search/filter, saved views
- *MAY:* Mini version embeddable in Compliance WS

---

## Table 3 — Demo video timeline × Artifact first-reveal

Synchronizes [07-pitch/demo-video-storyboard.md](../07-pitch/demo-video-storyboard.md) scenes with concrete artifact reveals. Pitch team uses this to verify voiceover matches on-screen visuals. Frontend team uses it to verify animations land at the right beats.

| Scene | Timestamp | Voiceover anchor (VN) | Artifact first revealed | UI state | Screen |
|---|---|---|---|---|---|
| **1. Hook** | 0:00-0:15 | "50 triệu hồ sơ/năm, Anh Minh đi 3 lần..." | — (no UI, title cards only) | — | — |
| **2. Intake** | 0:15-0:20 | "Anh Minh mở Citizen Portal, đăng nhập VNeID..." | — (nav only) | Empty home page, login button | Citizen Portal |
| 2 | 0:20-0:28 | "upload 5 tài liệu..." | Upload drop zone, 5 file rows | Upload in progress with progress bars | Intake path via Citizen Portal wizard |
| 2 | 0:28-0:32 | "Qwen3-VL nhận diện từng loại..." | **#1 OCR progress** + **#2 Document label** | Green checks appear per row + labels slide in | Intake UI (or citizen wizard preview) |
| 2 | 0:32-0:40 | "extract metadata thời gian thực — diện tích, vị trí, con dấu" | **#3 ExtractedEntity chips** + **#10 Compliance score** (preview starts filling) | 3 chips per file slide-in, compliance bar animates 0%→80% | Intake UI |
| **3. Agent Trace** | 0:40-0:50 | "Planner Agent phân tích, chia pipeline 3 nhánh..." | **#15 AgentStep Planner node** + edge to Case | Planner fades in, edge draws | Agent Trace Viewer |
| 3 | 0:50-0:58 | "DocAnalyzer extract, Classifier match..." | **#4 TTHC classification** edge (MATCHES_TTHC) + 3 parallel agent nodes | Multiple nodes fade in, classification edge draws | Agent Trace Viewer |
| 3 | 0:58-1:02 | "Compliance Agent chạy Gremlin traversal trên Alibaba Cloud GDB..." | **#7 Gremlin query text** overlay in detail pane | Query text fades into detail panel below graph | Agent Trace Viewer |
| 3 | 1:02-1:05 | "LegalLookup Agent dùng Agentic GraphRAG... trả về NĐ 136/2020 Điều 13.2.b" | **#6 Gap vertex** (amber) + **#8 Citation** + edge to Article | Gap appears with pulse, citation edge draws to Article node | Agent Trace Viewer |
| **4. Citizen Feedback** | 1:05-1:10 | "Trong vòng 30 giây, Drafter Agent sinh thông báo..." | **#26 Notification push** on phone | Phone push notification animation | Citizen Portal (mobile view) |
| 4 | 1:10-1:20 | "không phải đi lại 3 lần để biết..." | **#6 Gap plain-language notice** + **#8 Citation plain refs** | Tracking page shows clear "Bạn cần bổ sung: Văn bản PCCC..." with reason, location, time | Citizen Portal tracking |
| **5. Processing continues** | 1:20-1:25 | "8 ngày sau, anh Minh upload..." | — (file upload UI + time-skip title card) | Upload, then cut | Citizen Portal |
| 5 | 1:25-1:32 | "Router chuyển hồ sơ, Consult Agent auto xin ý kiến..." | **#14 Routing edge** + **#12 ConsultRequest** + **#13 Opinion** (stream in) | Cards move in Kanban, consult + opinion nodes appear in Agent Trace mini view | Department Inbox + Agent Trace mini |
| 5 | 1:32-1:42 | "Chị Hương mở Leadership Dashboard, thấy tóm tắt executive 3 dòng với compliance 100%..." | **#16 Summary card** + **#10 Compliance 100%** + **#19 Decision button** primed | Dashboard approve queue, summary card, big green button | Leadership Dashboard |
| 5 | 1:42-1:45 | "phê duyệt chỉ 1 click" | **#19 Decision made** | Button glow pulse + state badge transition to "Đang duyệt cuối" | Leadership Dashboard / Document Viewer |
| **6. Drafter + Publish** | 1:45-1:52 | "Drafter Agent sinh Giấy phép XD theo NĐ 30/2020..." | **#17 Draft document** with DRAFT ribbon + clickable citations | Draft PDF preview appears with ribbon, citations are underlined/clickable | Document Viewer (draft state) |
| 6 | 1:52-1:55 | "Chị Hương review, ký số, publish" | Sign animation + **#25 Case status change** | Signature animation on draft, status transitions | Document Viewer |
| 6 | 1:55-2:00 | "Anh Minh nhận thông báo, download giấy phép có mã QR xác thực" | **#18 PublishedDoc** seal + QR + **#26 Push notification** | Green seal stamp + QR fade-in on phone | Citizen Portal + Document Viewer split |
| **7. Security wow** | 2:00-2:05 | "SecurityOfficer tự động flag Confidential..." | **#5 Classification level** Confidential banner | Sticky top+bottom Confidential banner appears | Security Console |
| 7 | 2:05-2:08 | "Tier 1 SDK Guard reject agent out-of-scope" | **#20 PermissionDenied Tier 1** | Audit row flashes red + shake + toast | Security Console |
| 7 | 2:08-2:11 | "Tier 2 GDB native RBAC reject cross-agent violation" | **#21 PermissionDenied Tier 2** | Same pattern with different reason string | Security Console |
| 7 | 2:11-2:15 | "Tier 3 Property Mask redact PII... khi user cấp clearance cao hơn, mask gradually reveal" | **#22 Classification mask** solid bar → content crossfade | Solid bars on fields → crossfade to revealed content on elevation | Document Viewer (via Security Console run-demo button) |
| **8. Impact + Ask** | 2:15-2:30 | "700 tỉ VND TAM, 9 văn bản pháp luật..." | — (numbers + logo only) | Impact card + team slogan | — |

**Continuous artifacts throughout scenes 2-7** (not first-reveal but always present where applicable):
- #11 SLA countdown (visible on every case header)
- #15 AgentStep timeline (continuous in Scene 3)
- #23 AuditEvent rows (continuous in Scene 7)

---

## Artifact coverage sanity checks

Run these before considering docs refactor complete:

1. **Agent coverage check:** each of the 10 agents in [agent-catalog.md](../03-architecture/agent-catalog.md) has at least one artifact row in Table 1.
   - Planner → #15
   - DocAnalyzer → #1, #2, #3
   - Classifier → #4
   - Compliance → #6, #7, #10
   - LegalLookup → #8, #9
   - Router → #14
   - Consult → #12, #13, #27
   - Summarizer → #16, #28
   - Drafter → #17, #18
   - SecurityOfficer → #5, #20, #21, #22, #23, #24

2. **WS event coverage check:** each event type in [realtime-interactions.md:41-56](./realtime-interactions.md) maps to ≥1 row.
   - `agent_step_start/end` → #15
   - `graph_update` → #3, #4, #6, #8, #14 (multiple)
   - `case_status_change` → #25
   - `gap_found` → #6
   - `permission_denied` → #20, #21
   - `sla_alert` → #11
   - `consult_request` → #12
   - `opinion_received` → #13
   - `decision_made` → #19
   - `published` → #18
   - `notification` → #26

3. **Persona journey check:** each of 6 personas touches artifacts through defined screens:
   - **Minh (citizen):** #25, #6 (plain lang), #18, #26, #11 on Citizen Portal → complete
   - **Lan (intake):** #1, #2, #3, #4, #10, #6 on Intake UI → complete
   - **Tuấn (compliance):** #2, #3, #6, #7, #8, #10, #12, #13, #16 on Compliance WS + Agent Trace → complete
   - **Hương (leadership):** #10, #11, #16, #17, #18, #19 on Leadership Dashboard + Document Viewer → complete
   - **Quốc (security):** #5, #20, #21, #22, #23, #24 on Security Console → complete
   - **Dũng (pháp chế):** #12, #13, #27, #28, #8, #9 on Consult Inbox + KG Explorer → complete (after new screens ship)

4. **Demo video sync check:** each voiceover line in [07-pitch/demo-video-storyboard.md](../07-pitch/demo-video-storyboard.md) Scenes 2-7 has at least one Table 3 row at its timestamp. No "I said X but nothing on screen" moments.

If all four checks pass, the artifact inventory is complete and the demo narrative is locked to UI state.

---

## How to update this file

- **Adding a new agent** (not expected for hackathon, but post-PoC): audit its outputs → add new rows to Table 1 → add entries to Table 2 for each screen where outputs surface → update coverage check §1.
- **Adding a new WS event type**: add the row to Table 1 FIRST, then update `realtime-interactions.md`, then update consuming screen specs. Reverse order causes drift.
- **Adding a new screen**: add a new row to Table 2 listing its MUST/SHOULD/MAY artifacts from Table 1. If it introduces a new artifact, add it to Table 1 first.
- **Changing an animation duration**: update the row in Table 1. Verify it still matches the token in [design-tokens.md §4](./design-tokens.md).
- **Reworking the demo storyboard**: regenerate Table 3 to match new scenes. Keep this file as the sync contract.

**Owner:** whoever last touched [realtime-interactions.md:41-56](./realtime-interactions.md) event list. If in doubt, this doc is co-owned by UX lead + pitch lead.
