# Demo Video Storyboard — 2:30 frame-by-frame

**Target length:** 2 minutes 30 seconds
**Format:** 1920×1080 mp4, 30fps
**Voiceover:** Vietnamese primary + English subtitles burned in
**Music:** Subtle cinematic background (low volume, non-distracting)

> **Sync contracts (UX spec ↔ narrative):**
> - **Per-frame artifact mapping** → [`../04-ux/artifact-inventory.md` Table 3](../04-ux/artifact-inventory.md#table-3--demo-video-timeline--artifact-first-reveal)
> - **WS event → UI reaction mapping** → [`../04-ux/realtime-interactions.md` Demo moment mapping](../04-ux/realtime-interactions.md#demo-moment-mapping)
> - **Individual screen choreography tables** referenced from each scene below
>
> Any edit to this file must be mirrored in the artifact inventory. They are the three-way contract: `screen spec ↔ artifact inventory ↔ this storyboard`.

## Scene list

1. Hook (0:00–0:15) — 15s
2. Intake (0:15–0:40) — 25s
3. Agent Trace (0:40–1:05) — 25s
4. Citizen Feedback Loop (1:05–1:20) — 15s
5. Processing Continues (1:20–1:45) — 25s
6. Drafter + Publish (1:45–2:00) — 15s
7. Security Wow Moment (2:00–2:15) — 15s
8. Impact + Ask (2:15–2:30) — 15s

---

## Scene 1 — Hook (0:00–0:15)

**Frame 1 (0:00–0:05):** Static split screen
- **Left:** Photo/illustration of anh Minh standing at Bộ phận Một cửa, holding a stack of papers, worried expression
- **Right:** Blank white/dark screen

**Frame 2 (0:05–0:10):** Right side transitions
- Right side fades in to show GovFlow Citizen Portal home page, clean UI
- Title card on left: "Before: 1–3 months, 3–5 trips"
- Title card on right: "After: 1–2 days, 1 trip"

**Frame 3 (0:10–0:15):** Numbers appear
- Large text overlay: "63 tỉnh • 50M hồ sơ/năm • SLA gap 2–6×"

**Voiceover (VN):**
> "Mỗi năm, Việt Nam có 50 triệu hồ sơ thủ tục hành chính công. Luật quy định cấp phép xây dựng 15 ngày. Thực tế: 1–3 tháng. Anh Minh đây đã đi lại 3 lần trong tháng này cho một bộ hồ sơ."

**Subtitle (EN):**
> "Every year, Vietnam processes 50M public admin cases. Construction permits: 15 days by law. Reality: 1–3 months. Anh Minh here has visited the one-stop desk 3 times this month alone for one case."

---

## Scene 2 — Intake on Citizen Portal (0:15–0:40)

> **UI choreography:** [screen-catalog.md §Intake UI Live reveal choreography (t=0 → t=15s)](../04-ux/screen-catalog.md#live-reveal-choreography-t0--t15s)

**Frame 1 (0:15–0:20):** Zoom in on Citizen Portal home
- Anh Minh opens phone
- Taps "Nộp hồ sơ mới" → selects "Cấp giấy phép xây dựng"
- VNeID login button

**Frame 2 (0:20–0:28):** Upload wizard
- Drag-and-drop area
- Anh Minh uploads 5 files (PDF icons appearing)
- Each file shows upload progress
- OCR preview starts

**Frame 3 (0:28–0:40):** DocAnalyzer works in realtime
- Each file gets green check ✓ as Qwen3-VL processes
- Auto-detected labels appear:
  - "Đơn đề nghị"
  - "GCN QSDĐ ✓ (có dấu đỏ)"
  - "Bản vẽ thiết kế"
  - "Cam kết môi trường"
  - "Giấy phép KD"
- Extracted fields appear: "Diện tích: 500m², Vị trí: KCN Mỹ Phước"

**Voiceover (VN):**
> "Anh Minh mở GovFlow Citizen Portal, đăng nhập bằng VNeID, upload 5 tài liệu. Qwen3-VL nhận diện từng loại tài liệu, extract metadata thời gian thực — số GCN, diện tích, vị trí, con dấu đỏ đầy đủ."

**Subtitle (EN):**
> "Anh Minh opens Citizen Portal, logs in via VNeID, uploads 5 documents. Qwen3-VL identifies each document type and extracts metadata in real-time — permit number, area, location, red stamp, all detected."

---

## Scene 3 — Agent Trace live (0:40–1:05)

> **UI choreography:** [screen-catalog.md §Agent Trace Viewer Live build choreography (t=0 → t=30s)](../04-ux/screen-catalog.md#live-build-choreography-t0--t30s) — every frame here has a corresponding row in that table.

**Frame 1 (0:40–0:50):** Cut to Agent Trace Viewer
- Split screen: agent timeline on left + Context Graph visualization on right
- Planner node appears with reasoning bubble: "TTHC = Cấp phép XD, priority = normal, parallel: DocAnalyzer + SecurityOfficer + Classifier"

**Frame 2 (0:50–1:00):** Parallel execution
- 3 agent nodes appear in parallel
- Context Graph nodes grow: Document vertices, ExtractedEntity vertices
- Classifier writes MATCHES_TTHC edge to KG (animated edge drawing)
- Labels: "TTHC matched: 1.004415 Cấp phép XD"

**Frame 3 (1:00–1:05):** Compliance + LegalLookup
- Compliance agent runs Gremlin query (shown as text overlay):
  ```
  g.V().has('Case','id',$cid)
   .out('MATCHES_TTHC').out('REQUIRES')
   .where(not exists satisfied)
  ```
- Result: "1 missing: Văn bản thẩm duyệt PCCC"
- LegalLookup finds citation: "NĐ 136/2020 Điều 13.2.b"
- Gap node appears connected to Case, with Citation edge to Article in KG

**Voiceover (VN):**
> "Planner Agent phân tích, chia pipeline thành 3 nhánh chạy song song. DocAnalyzer extract từng tài liệu. Classifier match mã thủ tục. Compliance Agent chạy Gremlin traversal trên Alibaba Cloud GDB, phát hiện thiếu Văn bản thẩm duyệt PCCC. LegalLookup Agent dùng Agentic GraphRAG — vector recall qua Hologres Proxima, graph traversal qua GDB để lấy điều luật có hiệu lực — trả về Nghị định 136/2020 Điều 13.2.b."

**Subtitle (EN):**
> "Planner agent analyzes and splits the pipeline into 3 parallel branches. DocAnalyzer extracts entities. Classifier matches the TTHC code. Compliance agent runs Gremlin traversal on Alibaba Cloud GDB, detects missing PCCC approval document. LegalLookup agent uses Agentic GraphRAG — vector recall via Hologres Proxima, graph traversal via GDB — and returns NĐ 136/2020 Article 13 Clause 2 Point b as the citation."

---

## Scene 4 — Citizen Feedback Loop (1:05–1:20)

**Frame 1 (1:05–1:10):** Cut to anh Minh's phone
- Push notification appears: "GovFlow: Hồ sơ thiếu giấy. Nhấn để xem"
- Anh Minh taps

**Frame 2 (1:10–1:20):** Tracking page opens
- Clear plain-language notice:
  > "Anh Minh, hồ sơ của anh thiếu **Văn bản thẩm duyệt PCCC**. Vì công trình 500m² tại KCN Mỹ Phước thuộc diện phải thẩm duyệt theo Nghị định 136/2020 Điều 13.
  >
  > Nơi nhận: **Phòng Cảnh sát PCCC Công an tỉnh Bình Dương** — [bản đồ]
  >
  > Thời gian ước tính: ~10 ngày làm việc."
- Button: [Upload khi có]
- Anh Minh smiles, thumbs up

**Voiceover (VN):**
> "Trong vòng 30 giây, Drafter Agent sinh thông báo ngôn ngữ đời thường cho anh Minh — không phải đi lại 3 lần để biết, mà biết ngay trên điện thoại. Anh Minh không cần quay lại Bộ phận Một cửa."

**Subtitle (EN):**
> "Within 30 seconds, Drafter agent generates a plain-language notification. Instead of making 3 trips to find out what's missing, anh Minh knows immediately on his phone. No extra trips needed."

---

## Scene 5 — Processing Continues (1:20–1:45)

**Frame 1 (1:20–1:25):** Time skip title: "8 days later — anh Minh has PCCC approval"
- Anh Minh returns to Citizen Portal
- Uploads PCCC document

**Frame 2 (1:25–1:35):** Processing resumes
- Quick montage of agents running (Router, Consult, Summarizer)
- ConsultRequest sent to Pháp chế + Quy hoạch
- Response received: "OK — đồng ý cấp phép"
- Case.status → "Đang chờ phê duyệt"

**Frame 3 (1:35–1:45):** Cut to Chị Hương (Persona 4) — Leadership Dashboard
- Desktop view of dashboard
- 15 cases awaiting approval
- Chị Hương clicks first one → Document Viewer opens
- Executive summary visible:
  > "Cấp phép XD cho N*** Văn M***. Nhà xưởng 500m² tại KCN Mỹ Phước. Compliance 100%. Pháp chế + Quy hoạch đã duyệt. Đề xuất: Approve."
- Big green button "Phê duyệt"
- Chị Hương clicks

**Voiceover (VN):**
> "8 ngày sau, anh Minh có văn bản PCCC, upload vào hệ thống. Processing tiếp tục không cần bắt đầu lại — Router chuyển hồ sơ đến Phòng Quản lý XD, Consult Agent auto xin ý kiến Pháp chế và Quy hoạch, phản hồi về trong vài phút. Chị Hương — Phó Giám đốc Sở — mở Leadership Dashboard, thấy tóm tắt executive 3 dòng với compliance score 100%, và phê duyệt chỉ 1 click."

**Subtitle (EN):**
> "8 days later, anh Minh has his PCCC approval and uploads it. Processing continues without restart — Router assigns to the Construction Management department, Consult agent auto-requests opinions from Legal and Planning, responses come back in minutes. Chị Hương, Deputy Director, opens the Leadership Dashboard, sees the 3-line executive summary with 100% compliance, approves in one click."

---

## Scene 6 — Drafter + Publish (1:45–2:00)

**Frame 1 (1:45–1:52):** Drafter agent generates VB
- Chị Hương's screen shows generated Giấy phép XD PDF preview
- Standard NĐ 30/2020 format with:
  - Quốc hiệu + tiêu ngữ
  - Số hiệu
  - Trích yếu
  - Căn cứ (with law citations clickable)
  - Nội dung
  - Chữ ký số placeholder
- Chị Hương reviews, clicks "Ký số + Phát hành"
- Digital signature animation

**Frame 2 (1:52–2:00):** Anh Minh receives result
- Cut to anh Minh's phone
- Push notification: "Giấy phép của bạn đã sẵn sàng"
- Anh Minh opens, sees green checkmark + download button
- PDF appears with QR verification code
- Anh Minh smiles, thumbs up

**Voiceover (VN):**
> "Drafter Agent sinh Giấy phép XD theo đúng thể thức Nghị định 30/2020 — quốc hiệu, số hiệu, trích yếu, căn cứ với citations clickable về từng điều luật gốc. Chị Hương review, ký số, publish. Anh Minh nhận thông báo, download giấy phép có mã QR xác thực. Tổng cộng: 10 ngày, 1 chuyến đi, không cần quay lại nhiều lần."

**Subtitle (EN):**
> "Drafter agent generates the construction permit in the exact format of NĐ 30/2020 — national header, document number, subject, legal basis with clickable citations to source articles. Chị Hương reviews, digitally signs, publishes. Anh Minh receives the notification, downloads the permit with a QR verification code. Total: 10 days, 1 trip, no back-and-forth."

---

## Scene 7 — Security Wow Moment (2:00–2:15)

> **UI choreography:** [screen-catalog.md §Security Console Permission demo harness](../04-ux/screen-catalog.md#permission-demo-harness) — 3 scripted scenarios triggered from the top-right button group with keyboard shortcuts D+A, D+B, D+C. Each scene uses **solid-bar redaction with opacity crossfade** — NOT blur (see [design-system.md Redaction section](../04-ux/design-system.md)).

**Frame 1 (2:00–2:05):** Cut to Security Console
- Title card: "Different case: CPXD near sensitive zone"
- SecurityOfficer agent has flagged case as "Confidential" (due to location near military)

**Frame 2 (2:05–2:15):** 3 permission scenes rapid montage

**Scene A (2:05–2:08):** SDK Guard reject
- Summarizer agent attempts to read `Applicant.national_id`
- Red X appears: "❌ Denied at Tier 1: SDK Guard"
- Reason shown: "Property 'national_id' not in read scope"

**Scene B (2:08–2:11):** GDB RBAC violation
- LegalLookup attempts to write Gap (simulated)
- Red X: "❌ Denied at Tier 2: GDB Native RBAC"
- Reason: "agent_legallookup lacks WRITE privilege on label Gap"

**Scene C (2:11–2:15):** Property mask elevation
- User with Unclassified clearance opens case viewer
- Fields show **solid-bar redaction** (rounded black bars, NOT blur): `national_id: ▓▓▓▓▓▓▓▓`, `location: ▓▓▓▓▓▓▓▓`
- User elevates to Confidential via step-up auth modal (1-click security officer grant + OTP)
- Animation: solid bars unmount, revealed content crossfades in (opacity 0→1, 250ms): "079****1234", "Lô X, KCN Mỹ Phước"
- Classification banner at top transitions from UNCLASSIFIED green to CONFIDENTIAL blue
- Further elevation to Secret: location detail reveals "3km from military base"
- **Why solid bar:** blur is cryptographically recoverable and reads as consumer soft-focus. See [design-system.md Redaction](../04-ux/design-system.md) for full rationale.

**Voiceover (VN):**
> "Nhưng với hồ sơ nhạy cảm — ví dụ công trình gần khu quân sự — SecurityOfficer Agent tự động flag Confidential. Permission engine 3 tầng bảo vệ: Tier 1 SDK Guard reject agent out-of-scope, Tier 2 GDB native RBAC reject cross-agent violation, Tier 3 Property Mask redact PII. Khi user cấp clearance cao hơn, mask gradually dissolve — đúng nguyên tắc need-to-know của Luật Bảo vệ bí mật nhà nước 2018."

**Subtitle (EN):**
> "But for sensitive cases — say a project near a military zone — SecurityOfficer agent automatically flags Confidential. Three-tier permission engine protects: Tier 1 SDK Guard rejects out-of-scope, Tier 2 GDB native RBAC rejects cross-agent violations, Tier 3 Property Mask redacts PII. When users gain higher clearance, masks gradually dissolve — enforcing need-to-know per Vietnam's State Secrets Law 2018."

---

## Scene 8 — Impact + Ask (2:15–2:30)

**Frame 1 (2:15–2:22):** Big numbers
- "30 ngày → 10 ngày × 10k hồ sơ/năm = 200,000 ngày tiết kiệm/năm/Sở"
- "× 63 tỉnh × 5 Sở = hàng chục triệu ngày"
- "TAM Việt Nam: 700 tỉ VND ARR"
- "Compliance với 9 văn bản pháp luật"

**Frame 2 (2:22–2:30):** Ask + CTA
- GovFlow logo large
- "Agentic GraphRAG trên Alibaba Cloud + Shinhan InnoBoost 200M VND"
- "PoC 3 tháng với 1 Sở — sẵn sàng triển khai"
- Team slogan: "Cùng xây dựng OS cho bộ máy hành chính Việt Nam"

**Voiceover (VN):**
> "GovFlow: 1 Sở Xây dựng tiết kiệm 600 nghìn ngày doanh nghiệp/năm. 63 tỉnh × nhiều Sở. Backed by Alibaba Cloud và Shinhan InnoBoost. Compliance với 9 văn bản pháp luật Việt Nam. Pattern Agentic GraphRAG 2026. Team sẵn sàng ship PoC 3 tháng với 1 Sở ngay sau hackathon. Cảm ơn Qwen AI Build Day đã cho cơ hội. Sẵn sàng lắng nghe câu hỏi."

**Subtitle (EN):**
> "GovFlow: One Construction Department saves 600,000 business days per year. 63 provinces × multiple departments. Backed by Alibaba Cloud and Shinhan InnoBoost. Compliant with 9 Vietnamese laws. 2026 Agentic GraphRAG pattern. Team ready to ship 3-month PoC with one department right after this hackathon. Thank you Qwen AI Build Day for the opportunity. Ready for questions."

---

## Video production notes

### Recording setup
- **Screen recording:** Use OBS or Loom for UI captures
- **Resolution:** 1920×1080 for final output
- **Framerate:** 30fps (smooth enough, smaller file)
- **Audio:** External mic, not laptop mic, quiet room

### Post-production
- **Editor:** DaVinci Resolve (free + pro-level) or CapCut (fast)
- **Captions:** burned in Vietnamese + English
- **Transitions:** minimal, cuts + fades only
- **Music:** royalty-free cinematic from Pixabay or Epidemic Sound (low volume)
- **Color grading:** slight contrast boost, cool tone for tech feel

### Assets needed
- **Persona illustrations** — anh Minh, chị Hương, anh Tuấn (either photos with permission or stock illustrations)
- **Law document mockups** — sample CPXD, GCN, bản vẽ (from public templates)
- **UI screenshots** — real GovFlow UI, not mockups
- **Graph visualization** — real Agent Trace Viewer in action

### Voiceover
- **Recording:** Vietnamese native speaker, clear diction, professional tone
- **Backup:** record yourself if no other option, post-process
- **AI voiceover:** last resort (Qwen voice or other — may sound unnatural)
- **Subtitles:** manually transcribed for accuracy

### Testing
- **Test on projector:** demo day will be on large screen — check readability
- **Test without sound:** some judges may watch without audio — visual story should stand alone
- **Time it:** must be ≤ 2:30 (or 2:00 if presentation slot is tight)

### Version control
- v1: rough cut day 16 morning
- v2: polished version day 16 afternoon
- v3: final day 17 morning (small tweaks only)
- Backup: uncompressed master file + compressed H.264 for sharing

## Fallback plan

If live demo goes wrong during pitch:
- Have demo video ready to play
- Rehearse transition from "I was about to show live..." → "Let me play the recording instead"
- Graceful, not flustered

## Accessibility

- Captions make it accessible for hearing-impaired judges
- High-contrast UI in video
- Speed not too fast (international judges may find VN pace hard to follow)
