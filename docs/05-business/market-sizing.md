# Market Sizing — TAM / SAM / SOM cho GovFlow

## Context

Vietnamese public administrative services market — đây là thị trường ngách nhưng rất lớn và chưa được khai thác bởi AI platform. Shinhan InnoBoost, GenAI Fund, Tasco CVC đang tìm startup giải bài toán này → GovFlow positioning đúng thị hiếu investor.

## TAM (Total Addressable Market) — Việt Nam gov-tech

### Dimension 1: Số đơn vị
- **63 tỉnh/thành phố** trực thuộc trung ương
- **~700 quận/huyện/thị xã**
- **~10,500 xã/phường/thị trấn**
- **~30 Bộ/cơ quan ngang Bộ + 8 cơ quan thuộc Chính phủ**
- **~1,200 cơ quan đơn vị cấp Sở/Ban/Ngành** ở các tỉnh
- **Tổng: ~12,500 đơn vị hành chính**

### Dimension 2: Khối lượng hồ sơ TTHC
- **~53,000 TTHC** được công bố trên Cổng DVC Quốc gia
- **~2,000 TTHC phổ biến** (chiếm 80% khối lượng)
- **~50–80 triệu hồ sơ TTHC/năm** trên toàn quốc (ước tính)

### Dimension 3: Giá trị kinh tế
- Tiết kiệm thời gian cho doanh nghiệp + công dân: **~150,000 tỉ VND/năm** chi phí cơ hội
- Giảm công suất cán bộ: **~15,000 tỉ VND/năm** có thể reallocate
- **TAM kinh tế: ~165,000 tỉ VND/năm**

### TAM platform revenue (nếu capture 1%)
- Software platform: **~200–500 tỉ VND ARR TAM** ở Việt Nam
- Plus expansion vào doanh nghiệp lớn có TTHC nội bộ: **+500 tỉ VND**
- **TAM total: ~700–1,000 tỉ VND ARR** (~$30–40M USD)

Tiny by global standards, but **underserved** — không ai làm tốt.

## SAM (Serviceable Addressable Market) — 3 năm đầu

GovFlow không thể target tất cả đơn vị. SAM = các đơn vị realistic sẽ mua trong 3 năm:

### Target segments
1. **~100 Sở trọng điểm** — Sở Xây dựng, TN&MT, KH&ĐT, Tư pháp ở 20 tỉnh lớn nhất (có IT budget + nhu cầu)
2. **~15 Bộ** có TTHC công khối lượng cao (Bộ XD, TN&MT, KH&ĐT, Tư pháp, Y tế, Giáo dục, Tài chính, Công thương...)
3. **~50 doanh nghiệp lớn** (VN30 + major FDI) có nhu cầu TTHC nội bộ

### SAM ARR estimate
- 100 Sở × 500M VND/năm = **50 tỉ VND**
- 15 Bộ × 2 tỉ VND/năm = **30 tỉ VND**
- 50 enterprise × 300M VND/năm = **15 tỉ VND**
- **SAM total: ~95 tỉ VND ARR** (~$4M USD)

## SOM (Serviceable Obtainable Market) — realistic capture

Với Shinhan InnoBoost + Alibaba Cloud backing + first-mover advantage:

### Year 1 (2026–2027)
- **PoC 1 Sở** (via Shinhan InnoBoost 200M VND)
- **Replicate 2–5 Sở** trong cùng tỉnh (after PoC success)
- **Pilot 1 Bộ** (via gov partnership)
- **ARR: ~1.5–3 tỉ VND**

### Year 2 (2027–2028)
- **Expand 5–10 tỉnh** với 3–5 Sở mỗi tỉnh
- **Pilot 2 doanh nghiệp lớn**
- **ARR: ~10–15 tỉ VND**

### Year 3 (2028–2029)
- **20+ tỉnh** có deployment
- **5–10 Bộ** có deployment
- **5–10 enterprise**
- **ARR: ~30–50 tỉ VND**

### Year 5 target
- **50+ tỉnh** coverage
- **15 Bộ** coverage
- **20 enterprise**
- **ARR: ~100 tỉ VND** (~$4M USD) ≈ SAM saturation

**Valuation at Year 5:** 10× ARR = ~1,000 tỉ VND (~$40M USD) — fundable outcome

## Competitive landscape positioning

### Direct competitors (gov DMS / OCR)
- FPT IS AKAMINDS — document mgmt + OCR
- Viettel AI Intellect — AI ops platform
- VNPT iGate — Cổng DVC frontend
- Misa AMIS — SME suite, limited gov

**Gap:** Không ai có agentic GraphRAG end-to-end cho TTHC công.

### Indirect (gov tech advisory + build)
- System integrators: CMC, HPT, Sao Bắc Đẩu, CEH
- Build internal IT teams of ministries
- Foreign vendors (SAP, Oracle, Salesforce) — restricted by data residency

**Gap:** Build is slow + expensive. Foreign vendors can't meet compliance.

### Platform competitors from abroad
- Microsoft Dynamics Gov — not available/restricted in VN
- Salesforce Gov Cloud — not in VN
- Google Workspace for Gov — data residency issue
- ServiceNow — data residency issue

**Gap:** None of them can legally serve Vietnamese gov with LLM.

**GovFlow's unique position:** first agentic GraphRAG platform for TTHC công, Vietnamese-first, Alibaba Cloud + Qwen native, compliance-ready from day 1.

## Unit economics

### Per case processed
- **Subscription pricing:** 5,000–20,000 VND per case (varies by complexity)
- **Cost of goods:**
  - LLM tokens: ~5,000 VND per case (Qwen3-Max pricing)
  - Storage + compute: ~500 VND
  - Support + ops: ~1,000 VND
- **Gross margin: ~50–75% per case**

### Per deployment (1 Sở)
- **Setup cost:** 200M VND (one-time, waived with Shinhan PoC)
- **Annual subscription:** 500M VND/year
- **Customer savings:** ~120 tỉ VND/year (time saved × rate)
- **ROI for customer: 240×** — no-brainer

### Burn rate (for GovFlow team)
- 5-person team × 50M VND/month = 250M VND/month (~$10k/month)
- Infrastructure: ~50M VND/month
- Marketing + sales: ~100M VND/month
- **Burn: ~400M VND/month** (~$16k/month)
- **Shinhan 200M covers ~2 weeks** → need additional funding after PoC

### Funding strategy
- **Pre-seed:** Shinhan InnoBoost 200M VND + founder savings → MVP + PoC
- **Seed ($1–2M):** after PoC success → expand 5 Sở
- **Series A ($5–10M):** after 20 Sở → national expansion
- Exit: acquisition by system integrator or IPO (5–7 year horizon)

## Why Vietnamese gov-tech is actually attractive

Common objection: "Gov market is slow, bureaucratic, unreliable."

Rebuttal:
1. **Đề án 06 + Chương trình CĐS Quốc gia** — gov is pushing hard for digital transformation
2. **Budget available** — most Sở have IT modernization budget allocated annually
3. **Pain is real** — SLA violations have political cost, leadership wants solutions
4. **Competitive pressure** — tỉnh nào chuyển đổi số trước, kéo được đầu tư
5. **Alibaba + Shinhan backing** — GovFlow có ecosystem partners, không phải đi một mình
6. **First-mover** — không đội nào làm graph-native agentic platform cho TTHC

## Red flags + mitigation

### Slow sales cycle
- **Risk:** gov procurement có thể 6–12 tháng
- **Mitigation:** start with Shinhan PoC framework — fast-track via InnoBoost

### Political dependency
- **Risk:** thay đổi chính sách có thể ảnh hưởng
- **Mitigation:** alignment với Đề án 06, NĐ 61, NĐ 30 — these are stable long-term frameworks

### Custom per deployment
- **Risk:** mỗi tỉnh có TTHC + quy trình khác nhau
- **Mitigation:** GovFlow architecture là platform, customization qua config (agent profiles, KG content) — không rebuild code

### Integration with existing systems
- **Risk:** phải integrate với Cổng DVC + hệ thống một cửa tỉnh
- **Mitigation:** OpenAPI spec từ đầu, integration adapters per system

## Conclusion

**TAM:** ~700 tỉ VND ARR, underserved, first-mover position, backed by Shinhan + Alibaba Cloud.
**SAM:** ~95 tỉ VND ARR — realistic 5-year target.
**SOM:** 100 tỉ VND ARR by Year 5 — fundable outcome.

**Bottom line for VC pitch:** *"Market đủ lớn ($30–40M USD), underserved, first-mover, backed by strategic partners, high gross margin (50–75%), unit economics positive from PoC, exit path clear."*
