# Q&A Preparation — 15+ prepped scenarios

## How to handle Q&A

1. **Listen fully** — don't interrupt the judge
2. **Pause 1–2 seconds** before answering (shows thoughtfulness)
3. **Acknowledge** — "Great question" (sincerely, not rote)
4. **Answer directly** — lead with the answer, then support with evidence
5. **Keep it short** — 30 seconds per answer max, leave room for follow-up
6. **If you don't know** — say so honestly, then pivot to what you do know
7. **Defer to team member** — if it's their area of expertise, pass to them

## Top 15 questions

### 1. "Khác gì so với FPT.AI / Viettel / VNPT / Misa — họ đã làm OCR + DMS rồi?"

**Answer:**
> "Em đi thẳng vào. Họ làm OCR + DMS truyền thống với pipeline architecture. GovFlow là graph-native agentic system — Knowledge Graph pháp luật + Context Graph per case + 10 agent với phân quyền node-level. Pattern này đòi hỏi rebuild architecture từ đầu, không thể add vào hệ thống cũ của họ. Và em là đội duy nhất trong hackathon đi full Alibaba Cloud GDB + Hologres từ ngày đầu."

### 2. "Accuracy của classifier + compliance check trên TTHC thật là bao nhiêu?"

**Answer:**
> "Em đã benchmark trên 20 mẫu hồ sơ thật cho 5 TTHC flagship. Classifier TTHC matching đạt [target 92%+], Compliance gap detection đạt [85%+], LegalLookup citation relevance đạt [88%+]. Có edge cases — ví dụ hồ sơ scan rất xấu, DocAnalyzer confidence thấp, hệ thống tự động flag cần người duyệt. Production sẽ fine-tune với dữ liệu thực tế từ Sở triển khai PoC."

### 3. "Làm sao tích hợp vào Cổng DVC Quốc gia và hệ thống một cửa hiện có?"

**Answer:**
> "GovFlow có OpenAPI spec tương thích với chuẩn của Cổng DVC. Chúng em không thay thế — chúng em **augment**. Cổng DVC Quốc gia tiếp tục là frontend công dân, hệ thống một cửa tỉnh tiếp tục là workflow engine, GovFlow là AI brain chạy phía sau — nhận input từ API, sinh output qua API. Deploy như 1 module backend, không disrupt hệ thống cũ. Adapter cho mỗi hệ thống một cửa cấp tỉnh sẽ được build theo tỉnh."

### 4. "Data privacy khi gọi Qwen qua Alibaba Cloud Model Studio — có data residency concern không?"

**Answer:**
> "Câu hỏi quan trọng. Với PoC, em dùng Model Studio Singapore region — data không ra khỏi Đông Nam Á, có DPA với Alibaba Cloud. Với production cho khách hàng có yêu cầu data residency strict, chúng em deploy **Qwen3 open-weight với license Apache 2.0 qua PAI-EAS trên hạ tầng on-prem của khách hàng**. Đây là lời giải duy nhất vừa có LLM mạnh vừa tuân thủ Luật An ninh mạng Điều 26 và NĐ 53/2022. Không phải OpenAI, không phải Gemini — chỉ có Qwen mới làm được."

### 5. "Cán bộ nhà nước có dám tin agent reasoning không?"

**Answer:**
> "Em thiết kế với human-in-the-loop ở mọi điểm quyết định quan trọng — phê duyệt cuối cùng, cấp mật, từ chối. Agent **sinh đề xuất**, không **phát hành**. Drafter sinh draft → human review → publish. SecurityOfficer suggest classification → human security officer confirm cho Secret+. Audit trail đầy đủ — mọi quyết định có reasoning cụ thể + citation luật. Cán bộ vẫn chịu trách nhiệm pháp lý, GovFlow là trợ lý giảm workload + tăng độ chính xác."

### 6. "Roadmap commercial là gì?"

**Answer:**
> "Năm 1: PoC 1 Sở qua Shinhan InnoBoost, sau đó replicate 3–5 Sở cùng tỉnh. ARR ~1.5–3 tỉ VND. Năm 2: expand 5–10 tỉnh, pilot 1–2 Bộ, ARR ~10–15 tỉ VND. Năm 3: 20 tỉnh, 3–5 Bộ, ARR ~30–50 tỉ VND. Target Year 5: 100 tỉ VND ARR saturating SAM. Exit: acquisition bởi system integrator lớn hoặc IPO trong 5–7 năm."

### 7. "Pricing model của các bạn?"

**Answer:**
> "3 tier: Starter cho PoC 1 Sở 1 TTHC — 300M VND/năm, Shinhan sponsor setup. Professional 1 Sở nhiều TTHC — 500M VND/năm. Enterprise cho Bộ — 2 tỉ VND/năm. Plus overages và add-ons. Customer savings là 180× subscription (~120 tỉ VND/năm/Sở so với 500M). Gross margin 35% Year 1, optimize lên 65% Year 3."

### 8. "Team có kinh nghiệm gì với khách hàng gov?"

**Answer:** (customize based on actual founder background)
> "[Founder background]. Chúng em có [domain expertise trong gov / legal / AI]. Quan trọng hơn: chúng em có Shinhan InnoBoost mentor, Alibaba Cloud architect advisor, và planning sẽ hire 1 former cán bộ Sở làm customer success từ Month 2 để deep dive domain."

### 9. "Hallucination của Drafter agent — có nguy hiểm cho gov output không?"

**Answer:**
> "3 lớp bảo vệ. Một: Drafter dùng template Nghị định 30/2020 structured, không sinh free-form — fill template. Hai: Output đi qua validator kiểm tra 9 thành phần thể thức bắt buộc. Ba: **Luôn có human review gate** — cán bộ review draft + ký số + publish. Agent không bao giờ auto-publish. Hallucination nếu có → bị catch ở gate 2 (invalid format) hoặc gate 3 (human notice). Audit trail ghi mọi thay đổi."

### 10. "Qwen3 tiếng Việt tốt không? Compare với GPT-4 / Gemini?"

**Answer:**
> "Qwen3 được train trên 119 ngôn ngữ, tiếng Việt là một trong những ngôn ngữ được cover mạnh. Em đã test trên mẫu TTHC thật — accuracy tương đương GPT-4 cho tiếng Việt hành chính. Quan trọng hơn, Qwen3 có **open-weight Apache 2.0** — cho phép deploy on-prem, điều mà GPT-4 và Gemini không có. Đây là cloud + on-prem hybrid unique cho GovFlow."

### 11. "Gremlin khó sinh bằng LLM — các bạn xử lý thế nào?"

**Answer:**
> "Chúng em có **Gremlin Template Library** với ~30 template prebuilt cho các traversal thông dụng — case.find_missing_components, law.get_effective_article, etc. Qwen3 chỉ pick template name + fill parameters, không sinh raw Gremlin. Khi cần ad-hoc, query đi qua SDK Guard parse AST validate scope trước khi hit GDB. Approach này đạt ~95% correct syntax trong testing."

### 12. "Alibaba Cloud GDB setup chậm + dev loop khó. Làm sao build trong 6 ngày?"

**Answer:**
> "Em dùng hybrid dev strategy. Local: `gremlin-server` với TinkerGraph in-memory cho iteration nhanh — milliseconds. Schema + Template Library phát triển trên local. Day 3 import vào Alibaba Cloud GDB production instance. Code thay đổi minimal vì cả 2 đều là TinkerPop compatible. Setup Alibaba Cloud GDB em đã làm từ Day 1, trong lúc chờ em build local. Architecture slide show production trên GDB."

### 13. "What happens if Alibaba Cloud Model Studio goes down during demo?"

**Answer:**
> "Demo chính là video record trước, không risk network. Live demo chỉ là secondary — có cache Qwen response cho các case demo chính, nếu live fail thì fallback sang video. Production có retry logic + fallback sang rule-based cho case đơn giản. Alibaba Cloud Model Studio uptime 99.9% — risk thấp."

### 14. "How is this different from Microsoft Copilot for Government?"

**Answer:**
> "Microsoft Copilot cho gov (1) không có Vietnamese data residency — bị Luật ANM block, (2) không hiểu legal framework Việt Nam, (3) không phải agentic GraphRAG — là chatbot + document grounding. GovFlow là **platform cho TTHC công Việt Nam**, không phải assistant. Architecture khác fundamentally."

### 15. "Có thực sự production-ready hay chỉ là hackathon prototype?"

**Answer:**
> "Architecture production-ready: full Alibaba Cloud stack từ ngày đầu (GDB + Hologres + Model Studio + OSS), không cần migration. 3-tier permission engine có unit tests. Compliance với 9 văn bản pháp luật mapped chính xác. Human-in-the-loop ở mọi điểm quyết định. Hackathon chỉ là proof of concept với 5 TTHC — production scope cần thêm 50+ TTHC, integration thật với Cổng DVC, VNeID production credentials, và hardening. PoC 3 tháng với 1 Sở sẽ đi tới production-grade cho 1 TTHC flagship."

## Curveball questions

### "Nếu chúng tôi nói 'không, không interested' thì sao?"

**Answer:**
> "Em tôn trọng quyết định. Em sẽ quay lại với updates sau 3 tháng với customer PoC data. Feedback từ anh chị giúp em hiểu gap ở đâu — anh chị có thể share không?"

### "Team nhỏ, làm sao cạnh tranh với FPT 18,000 người?"

**Answer:**
> "Small team + focus = speed. FPT phải di chuyển 18,000 người cùng lúc, rất chậm. Chúng em ship weekly. Plus chúng em là first-mover trong graph-native architecture — FPT phải rebuild. 12–18 tháng window để establish market share trước khi họ react. Đó là reason focus matters."

### "What's your biggest risk?"

**Answer:**
> "Slow gov procurement. Mitigation: dùng Shinhan PoC framework bypass RFP, partner với system integrator có contract sẵn. Và chúng em start với tỉnh progressive (Bình Dương, Đồng Nai) không phải Hà Nội."

### "Có thể bị gov thu lại hoặc copy không?"

**Answer:**
> "Legal: Qwen3 open-weight là Apache 2.0, GovFlow code là IP của chúng em. Gov mua license hoặc subscription, không own source. Chúng em có service agreement bảo vệ IP. Risk copy thấp vì complexity — không thể reverse engineer easily."

## Things NOT to say

- ❌ "Chúng em là số 1" → arrogant
- ❌ "Chắc chắn thành công" → overconfident
- ❌ "Không có competition" → naive
- ❌ "AI sẽ thay thế cán bộ" → scary for gov audience
- ❌ "Easy to build" → diminishes effort
- ❌ Jargon without explanation → loses audience

## Things TO say

- ✓ "Em đã build điều này vì..." (personal conviction)
- ✓ "Customer sẽ thấy giá trị qua..." (customer-centric)
- ✓ "Research backing là..." (evidence-based)
- ✓ "Team sẽ handle risk này bằng..." (risk aware)
- ✓ "Em không biết chính xác, nhưng..." (honest)
- ✓ "Cảm ơn câu hỏi — đây là điểm em đã suy nghĩ nhiều..." (validate)

## Practice drills

1. **Quick-fire:** team member asks 10 questions back-to-back, 30s to answer each
2. **Hostile:** team member plays antagonistic judge trying to poke holes
3. **Confused:** team member plays judge who doesn't understand technical detail
4. **Deep technical:** team member asks super-technical questions on graph architecture
5. **Business focused:** team member asks only about market, pricing, competition

Rotate who's "judge" so multiple team members practice answering.
