# Pitch Deck Outline — 10 slides

Target duration: **3 minutes** (hackathon default) or **5 minutes** (extended). Script adapts.

## Slide structure

### Slide 1 — Hook (0:00–0:20)

**Title:** "1–3 months. 15 days. Every business in Vietnam knows this gap."

**Visual:** Split screen. Left: anh Minh (persona 1) standing at one-stop desk with stack of papers, frustrated face. Right: GovFlow Citizen Portal clean UI with "Hồ sơ đã được cấp phép" message.

**Voiceover:**
> "Mỗi năm, Việt Nam có 50 triệu hồ sơ thủ tục hành chính công. Luật quy định cấp phép xây dựng 15 ngày. Thực tế trung bình 1 đến 3 tháng. 63 tỉnh, hàng nghìn loại thủ tục, và backend vẫn chạy bằng tay."

**Key metric on slide:** "50M hồ sơ/năm • SLA gap 2–6×"

### Slide 2 — Problem (0:20–0:45)

**Title:** "Đây không phải văn thư. Đây là toàn bộ thủ tục hành chính công."

**Visual:**
- 6-step workflow (from PDF) with friction icons at each step
- Small inset: 6 personas (citizen, one-stop cán bộ, chuyên viên, lãnh đạo, pháp chế, CIO)
- Legal framework logos: NĐ 61, 107, 45, 30, Đề án 06

**Voiceover:**
> "PDF đề bài không nói về văn thư nội bộ. Cái flow 6 bước — Tiếp nhận, Vào sổ, Chuyển, Thẩm định, Xin ý kiến, Trả kết quả — là khung chung của toàn bộ TTHC công Việt Nam theo Nghị định 61/2018. Đây là vùng đau lớn nhất mà Đề án 06 và loạt nghị định chuyển đổi số đang push, nhưng chưa ai làm được."

**Key messages:**
- Scope: TTHC công, không phải văn thư
- 6 nhóm stakeholder bị đau
- Legal framework anchor

### Slide 3 — Big Idea (0:45–1:10)

**Title:** "GovFlow — Agentic GraphRAG cho TTHC công Việt Nam"

**Visual:**
- Large screenshot: Agent Trace Viewer với graph visualization
- 3 levers as icons: Graph-native / Security / VN-first
- "10 agents" highlighted

**Voiceover:**
> "GovFlow là graph-native agentic system. Không phải 'AI xử lý văn bản' — mà là **AI điều hành bộ máy hành chính trên một đồ thị sống**. 10 agent Qwen3 phối hợp trên Knowledge Graph pháp luật Việt Nam + Context Graph động cho mỗi hồ sơ, với phân quyền tại mức node/edge. Đây là pattern 2026 theo GraphRAG + MCP — không đội nào khác trong hackathon kịp build."

**Key messages:**
- Graph-native (not pipeline)
- 10 agents with permissions
- 2026 pattern

### Slide 4 — How: Dual Graph Architecture (1:10–1:35)

**Title:** "Knowledge Graph + Context Graph — đồ thị LÀ case file, audit trail, và reasoning trace"

**Visual:** Split diagram from §5.1 of plan — KG (left, static) + CG (right, dynamic) with cross-graph edges. Show sample nodes and edges.

**Voiceover:**
> "KG là bộ não dài hạn — tất cả luật Việt Nam, bộ TTHC quốc gia, cơ cấu tổ chức, với quan hệ AMENDED_BY, SUPERSEDED_BY, REFERENCES. Context Graph là bộ nhớ ngắn hạn — mỗi case là subgraph grow theo runtime khi các agent làm việc. Cạnh CITES nối case sang KG tạo traceability pháp lý đầy đủ. Research AGENTiGraph 2025 cho thấy pattern này đạt 95% accuracy vs 83% của GPT-4 zero-shot."

**Key messages:**
- KG + CG design
- Research backing
- Traceability

### Slide 5 — How: Agent-level Permissions (1:35–1:55)

**Title:** "3-tier ABAC-on-Graph — permission tại mức node/edge"

**Visual:** Diagram of 3 tiers: SDK Guard → GDB RBAC → Property Mask. Table showing 10 agents with different scopes.

**Voiceover:**
> "Mọi access đi qua 3 tầng phòng thủ: Agent SDK Guard parse Gremlin AST reject out-of-scope query, Alibaba Cloud GDB native RBAC cho per-agent DB user, và Property Mask middleware redact PII trước khi trả. Mỗi agent có scope riêng. DocAnalyzer đọc raw content, nhưng Summarizer bị mask CCCD. SecurityOfficer có Top Secret cap, others có Confidential cap. Đây là best practice 2026 không ai khác có."

**Key messages:**
- 3 tiers defense in depth
- Agent-level, not just user
- Best practice

### Slide 6 — How: Qwen @ 8 roles (1:55–2:15)

**Title:** "Qwen3 ở 8 vai trò khác nhau — không phải wrapper mỏng"

**Visual:** Diagram showing 8 boxes với Qwen logo in each, labeled:
1. Graph-native orchestration (MCP)
2. Planner DAG generation
3. GraphRAG legal reasoning
4. Qwen3-VL multimodal OCR
5. Compliance reasoning
6. Classifier with taxonomy grounding
7. Role-aware summarizer
8. Drafter with NĐ 30 guardrail

**Voiceover:**
> "GovFlow dùng Qwen3 ở 8 vai trò. Không phải 1 prompt → output. Qwen3-Max làm orchestrator với MCP để expose graph tools. Qwen3-VL làm multimodal document understanding. LegalLookup agent dùng Agentic GraphRAG — vector recall qua Hologres Proxima, graph traversal qua Alibaba Cloud GDB để lấy điều luật có hiệu lực. Drafter sinh VB đúng thể thức NĐ 30/2020. Mỗi vai trò show được Qwen3 đang làm đúng flagship capability."

**Key messages:**
- Qwen3 used deeply
- 8 distinct roles
- MCP + GraphRAG

### Slide 7 — Demo Video (2:15–4:45)

**Content:** Play 2:30 demo video (see [`demo-video-storyboard.md`](demo-video-storyboard.md))

Video shows:
1. Anh Minh uploads CPXD bundle
2. Agents process in realtime
3. Compliance finds missing PCCC
4. Citizen receives plain-language notification
5. Uploads missing, processing continues
6. Leadership approves
7. Drafter generates giấy phép
8. Anh Minh downloads

Plus 3 permission scenes:
A. SDK Guard reject
B. GDB RBAC violation
C. Property mask elevation

### Slide 8 — Security & Compliance (4:45–5:05)

**Title:** "9 văn bản pháp luật Việt Nam — compliance by design"

**Visual:** Grid of 9 law logos/names with feature→law mapping arrows

**Voiceover:**
> "GovFlow tuân thủ 9 văn bản cốt lõi: NĐ 61/2018 + 107/2021 cho một cửa liên thông, NĐ 45/2020 + 42/2022 cho TTHC điện tử, NĐ 30/2020 cho thể thức văn bản, Đề án 06 cho VNeID, Luật BVBMNN 2018 cho 4 cấp mật, Luật ANM + NĐ 53/2022 cho data residency, Luật BVDLCN + NĐ 13/2023 cho xử lý dữ liệu cá nhân. Mỗi feature có legal anchor cụ thể. Qwen3 open-weight Apache 2.0 cho phép triển khai on-prem — đây là giải pháp duy nhất vừa dùng được LLM hàng đầu vừa tuân thủ đầy đủ luật Việt Nam."

**Key messages:**
- 9 laws mapped
- Qwen open-weight advantage
- Data residency

### Slide 9 — Impact & Business Case (5:05–5:25)

**Title:** "1 Sở XD tiết kiệm 600,000 ngày doanh nghiệp/năm"

**Visual:** Big numbers + simple chart
- Before vs After comparison
- 63 tỉnh × N Sở
- TAM: 700 tỉ VND ARR
- 180× customer ROI

**Voiceover:**
> "1 Sở Xây dựng trung bình xử lý 10,000 hồ sơ/năm. Tiết kiệm 60 ngày mỗi hồ sơ = 600,000 ngày doanh nghiệp/năm/Sở. Giá trị kinh tế ~120 tỉ VND/năm/Sở. Nhân 63 tỉnh × 5 Sở target = hàng chục triệu ngày, hàng chục nghìn tỉ VND giá trị. GovFlow pricing 500M/năm/Sở — customer ROI 180×. TAM Việt Nam: 700 tỉ VND ARR, first-mover, backed by Alibaba Cloud và Shinhan."

**Key messages:**
- Massive impact
- Huge ROI
- Big market

### Slide 10 — Ask (5:25–5:40)

**Title:** "PoC 3 tháng với 1 Sở. Shinhan InnoBoost 200M VND. Team sẵn sàng ship."

**Visual:** 3-month PoC timeline. Team photo (if allowed). Contact info.

**Voiceover:**
> "Chúng em đang sẵn sàng triển khai PoC 3 tháng với 1 Sở Xây dựng cấp tỉnh, qua Shinhan InnoBoost 200 triệu VND. Mục tiêu: chứng minh 50% giảm thời gian xử lý + 90% SLA hit rate. Sau đó scale 5 Sở năm 1, 15 Sở năm 2, quốc gia năm 3. Alibaba Cloud + Shinhan + GenAI Fund + Tasco CVC — chúng em có đủ ecosystem. Sẵn sàng lắng nghe câu hỏi. Cảm ơn Qwen AI Build Day đã cho cơ hội."

**Call to action:**
- Ready for Q&A
- Contact info for follow-up

## Slide design principles

- **Large text** — readable from back of room
- **Minimal bullets** — max 3 per slide
- **Big visuals** — screenshots, diagrams, numbers
- **Classification colors** consistently — blue for brand, green for savings, red for pain
- **Dark theme** — matches the "serious gov tech" vibe
- **Vietnamese + English subtitles** — judge panel is mixed

## Timing flexibility

### If 3 minutes:
- Slide 1 (10s) → 2 (15s) → 3 (15s) → 4+5+6 combined (40s) → Demo short cut (60s) → 8+9 combined (20s) → 10 (20s)
- **Total: 3 minutes**

### If 5 minutes:
- Full version as outlined above
- **Total: ~5:40** — adjust demo trim to 2:00 instead of 2:30

### If Q&A time given:
- Aim for 3:30 pitch + 1:30 Q&A
- Prep 10 Q&A scenarios (see [`qa-preparation.md`](qa-preparation.md))

## Speaker delivery

- **Start slow, build momentum** — first 15 seconds are crucial
- **One message per slide** — don't try to say everything
- **Pause after big numbers** — let them sink in
- **Eye contact with different judges** — rotate
- **Confident, not arrogant** — "We built" not "We're the best"
- **Use Vietnamese for impact, English for precision** — mix naturally
- **End on a call-to-action, not a summary**

## Rehearsal protocol

- Rehearse solo 5×
- Rehearse with team mock-judge 3×
- Rehearse with stranger (non-technical) 2×
- Record yourself, watch back, note issues
- Time every rehearsal
- Practice transitions between slides
