# Script + Voiceover — Final Text

Full text for recording. Vietnamese primary + English subtitle version. Time-marked to fit 2:30 demo + 3-minute pitch.

## Full demo video script (2:30)

### Scene 1 — Hook (0:00–0:15)

**[VN]**
> Mỗi năm, Việt Nam có 50 triệu hồ sơ thủ tục hành chính công. Luật quy định cấp phép xây dựng 15 ngày. Thực tế: 1 đến 3 tháng. Anh Minh đây đã đi lại 3 lần trong tháng này cho một bộ hồ sơ.

**[EN subtitle]**
> Every year, Vietnam processes 50 million public admin cases. Construction permit law: 15 days. Reality: 1 to 3 months. Anh Minh here has made 3 trips this month for one case.

### Scene 2 — Intake (0:15–0:40)

**[VN]**
> Anh Minh mở GovFlow Citizen Portal, đăng nhập bằng VNeID, upload 5 tài liệu. Qwen3-VL nhận diện từng loại tài liệu, extract metadata thời gian thực — số giấy chứng nhận, diện tích, vị trí, con dấu đỏ đầy đủ.

**[EN subtitle]**
> Anh Minh opens GovFlow Citizen Portal, logs in via VNeID, uploads 5 documents. Qwen3-VL identifies each document type and extracts metadata in real-time — certificate number, area, location, red stamps, all detected.

### Scene 3 — Agent Trace (0:40–1:05)

**[VN]**
> Planner Agent phân tích, chia pipeline thành 3 nhánh chạy song song. DocAnalyzer extract từng tài liệu. Classifier match mã thủ tục. Compliance Agent chạy Gremlin traversal trên Alibaba Cloud GDB, phát hiện thiếu Văn bản thẩm duyệt PCCC. LegalLookup Agent dùng Agentic GraphRAG trả về Nghị định 136/2020 Điều 13 Khoản 2 Điểm b.

**[EN subtitle]**
> Planner agent analyzes and splits the pipeline into 3 parallel branches. DocAnalyzer extracts entities. Classifier matches the procedure code. Compliance agent runs Gremlin traversal on Alibaba Cloud GDB, detects missing fire safety approval. LegalLookup agent uses Agentic GraphRAG to return Decree 136/2020 Article 13 Clause 2 Point b as citation.

### Scene 4 — Citizen Feedback Loop (1:05–1:20)

**[VN]**
> Trong vòng 30 giây, Drafter Agent sinh thông báo ngôn ngữ đời thường cho anh Minh — không phải đi lại 3 lần để biết, mà biết ngay trên điện thoại. Anh Minh không cần quay lại Bộ phận Một cửa.

**[EN subtitle]**
> Within 30 seconds, Drafter agent generates a plain-language notification for anh Minh. Instead of making 3 trips to find out what's missing, he knows immediately on his phone. No extra trips needed.

### Scene 5 — Processing Continues (1:20–1:45)

**[VN]**
> 8 ngày sau, anh Minh có văn bản PCCC, upload vào hệ thống. Processing tiếp tục không cần bắt đầu lại — Router chuyển hồ sơ đến Phòng Quản lý XD, Consult Agent auto xin ý kiến Pháp chế và Quy hoạch, phản hồi về trong vài phút. Chị Hương — Phó Giám đốc Sở — mở Leadership Dashboard, thấy tóm tắt executive 3 dòng với compliance score 100 phần trăm, và phê duyệt chỉ 1 click.

**[EN subtitle]**
> 8 days later, anh Minh has his PCCC approval and uploads it. Processing continues without restart — Router assigns to the Construction Management department, Consult agent auto-requests opinions from Legal and Planning, responses come back in minutes. Chị Hương, the Deputy Director, opens the Leadership Dashboard, sees the 3-line executive summary with 100 percent compliance, approves in one click.

### Scene 6 — Drafter + Publish (1:45–2:00)

**[VN]**
> Drafter Agent sinh Giấy phép XD theo đúng thể thức Nghị định 30/2020 — quốc hiệu, số hiệu, trích yếu, căn cứ với citations clickable về từng điều luật gốc. Chị Hương review, ký số, publish. Anh Minh nhận thông báo, download giấy phép có mã QR xác thực. Tổng cộng: 10 ngày, 1 chuyến đi, không cần quay lại nhiều lần.

**[EN subtitle]**
> Drafter agent generates the construction permit in the exact format of Decree 30/2020 — national header, document number, subject, legal basis with clickable citations. Chị Hương reviews, digitally signs, publishes. Anh Minh receives the notification, downloads the permit with a QR verification code. Total: 10 days, 1 trip, no back-and-forth.

### Scene 7 — Security Wow Moment (2:00–2:15)

**[VN]**
> Nhưng với hồ sơ nhạy cảm — ví dụ công trình gần khu quân sự — SecurityOfficer Agent tự động flag Confidential. Permission engine 3 tầng bảo vệ: Tier 1 SDK Guard reject agent out-of-scope, Tier 2 GDB native RBAC reject cross-agent violation, Tier 3 Property Mask redact PII. Khi user cấp clearance cao hơn, mask gradually dissolve — đúng nguyên tắc need-to-know của Luật Bảo vệ bí mật nhà nước 2018.

**[EN subtitle]**
> For sensitive cases — say a project near a military zone — SecurityOfficer agent automatically flags Confidential. The 3-tier permission engine protects: Tier 1 SDK Guard rejects out-of-scope, Tier 2 GDB native RBAC rejects cross-agent violations, Tier 3 Property Mask redacts PII. When users gain higher clearance, masks gradually dissolve — enforcing need-to-know per Vietnam's State Secrets Law 2018.

### Scene 8 — Impact + Ask (2:15–2:30)

**[VN]**
> GovFlow: 1 Sở Xây dựng tiết kiệm 600 nghìn ngày doanh nghiệp mỗi năm. 63 tỉnh nhân nhiều Sở. Backed by Alibaba Cloud và Shinhan InnoBoost. Compliance với 9 văn bản pháp luật Việt Nam. Pattern Agentic GraphRAG 2026. Team sẵn sàng ship PoC 3 tháng với 1 Sở ngay sau hackathon. Cảm ơn Qwen AI Build Day.

**[EN subtitle]**
> GovFlow: one Construction Department saves 600 thousand business days per year. 63 provinces times multiple departments. Backed by Alibaba Cloud and Shinhan InnoBoost. Compliant with 9 Vietnamese laws. 2026 Agentic GraphRAG pattern. Team ready to ship a 3-month PoC with one department right after this hackathon. Thank you Qwen AI Build Day.

---

## Live pitch script (3 minutes — if only 3 min allowed)

This version compresses the video into a shorter narration + live intro + Q&A prep.

### Opening (0:00–0:20) — spoken live

> "Chào các anh chị judges. Em đến từ GovFlow.
>
> Mỗi năm, Việt Nam có 50 triệu hồ sơ thủ tục hành chính công. Trung bình mỗi hồ sơ chờ gấp 2 đến 6 lần so với thời hạn luật định. Đây không phải là câu chuyện của văn thư nội bộ — đây là toàn bộ TTHC công, theo cơ chế một cửa liên thông trong Nghị định 61/2018."

### Big idea (0:20–0:50)

> "GovFlow là **graph-native agentic system**. Chúng em không build một pipeline AI thông thường. Chúng em build một **Knowledge Graph pháp luật Việt Nam** cộng với **Context Graph động cho mỗi hồ sơ**, và 10 agent Qwen3 phối hợp với phân quyền tại mức node và edge.
>
> Đây là pattern 2026 theo GraphRAG cộng MCP. Research AGENTiGraph từ tháng 8 năm ngoái cho thấy pattern này đạt 95% accuracy so với 83% của GPT-4 zero-shot. Không đội nào khác trong hackathon này kịp build."

### Demo (0:50–2:50) — play video

Play 2:00 minute abbreviated demo video (cut from 2:30 version by trimming Scene 5 and Scene 7 to essentials).

### Close (2:50–3:00)

> "GovFlow: 1 Sở tiết kiệm 600 nghìn ngày doanh nghiệp mỗi năm. TAM Việt Nam 700 tỉ. Full Alibaba Cloud. Compliance 9 văn bản. PoC 3 tháng qua Shinhan InnoBoost. Cảm ơn. Em xin lắng nghe câu hỏi."

---

## Voiceover recording tips

### Tone
- **Confident, not arrogant.** "Chúng em build" not "Chúng em là số 1."
- **Clear articulation.** Slow enough for international judges.
- **Emotional beats:** pause after big numbers, pick up energy at the ask.

### Recording setup
- **Quiet room,** close door, fabric around if possible
- **External USB mic** (Blue Yeti, Shure MV7) — not laptop mic
- **Pop filter** to reduce plosives
- **Record multiple takes**, pick best sentences

### Post-processing
- **Noise reduction** (very light touch)
- **Slight compression** for consistent volume
- **Normalize to -14 LUFS** (standard for spoken content)

### Backup options
- **If team can't record VN voiceover,** use Qwen's voice (if available) or ElevenLabs
- **If EN voiceover needed,** use a native speaker or AI voice

---

## Subtitles

### Format
- Burned-in subtitles (baked into video file)
- Both Vietnamese + English visible (top = Vietnamese, bottom = English)
- Or: alternate (only EN shown for EN audience, VN for VN audience)
- Font: Inter or Arial, 24pt, white with subtle black outline
- Position: bottom-safe area

### Timing
- Match audio exactly
- 2 lines max per frame
- Max ~42 characters per line
- Break at natural pauses

### QA checklist
- [ ] No typos
- [ ] Vietnamese accents correct (á ả ã à ạ etc.)
- [ ] English translations accurate
- [ ] Timing matches audio within 200ms
- [ ] Readable on large projector at 10m distance
- [ ] No overlap with key UI elements
- [ ] Classification colors visible behind subtitles
- [ ] Music doesn't drown out subtitles on playback

---

## Alternative versions

### 90-second teaser cut
For social media + pre-event sharing:
- Scene 1 (hook) 15s
- Scene 3 (agent trace) 30s
- Scene 7 (security) 20s
- Scene 8 (ask) 15s
- Quick title slides connecting

### 5-minute extended version
For internal Shinhan proposal + deep-dive meetings:
- Full 2:30 demo
- Plus 2:30 of architecture + business case explanation
- Use only if 5-min slot given

### Silent version
For hackathon venue where audio might not play:
- Keep same visuals
- Replace audio with text callouts
- Slightly slower pacing

## Final QA

Before shipping final video:
- [ ] Plays correctly on target laptop (test!)
- [ ] Audio levels consistent
- [ ] No clipping or distortion
- [ ] Subtitles readable
- [ ] Colors consistent with brand
- [ ] Length exactly 2:30 (or specified)
- [ ] File format mp4, H.264, ≤50MB for fast loading
- [ ] Backup file on USB + cloud
