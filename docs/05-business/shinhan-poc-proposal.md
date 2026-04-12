# Shinhan InnoBoost PoC Proposal — Draft

Document này là bản nháp proposal để submit/discuss với Shinhan InnoBoost 2026 program nếu GovFlow được chọn là track winner.

## Executive summary

**GovFlow** là graph-native agentic platform cho thủ tục hành chính công Việt Nam, chạy trên Qwen3 + Alibaba Cloud. Chúng tôi đang tìm **200,000,000 VND PoC funding** từ Shinhan InnoBoost để triển khai production PoC tại 1 Sở cấp tỉnh trong 3 tháng.

**Expected outcome:** Working production system xử lý 1 TTHC flagship (Cấp phép xây dựng) cho 1 Sở XD tỉnh (đề xuất: Bình Dương hoặc Đồng Nai), với metrics rõ ràng về cost/time savings + citizen NPS + legal compliance.

**Why Shinhan:** Shinhan có mảng banking B2G mạnh + quan tâm digital governance. GovFlow là strategic entry vào value chain CĐS khu vực công VN với expected ARR 50+ tỉ VND trong 3 năm.

## Problem statement

Thủ tục hành chính công Việt Nam đang ở giai đoạn chuyển đổi số (Đề án 06, Cổng DVC Quốc gia), nhưng **backend vẫn chạy thủ công**. Kết quả:
- SLA vi phạm phổ biến (CPXD luật quy định 15 ngày, thực tế 1–3 tháng)
- Công dân phải đi lại 3–5 lần cho 1 hồ sơ
- Cán bộ quá tải, xử lý thủ công
- Không audit được lifecycle hồ sơ

Thị trường ~ 50M hồ sơ TTHC/năm × giá trị ~150 nghìn tỉ VND chi phí cơ hội.

## Solution — GovFlow

**Graph-native agentic platform**:
- 10 agents Qwen3 phối hợp trên Knowledge Graph pháp luật + Context Graph per case
- 3-tier permission engine cho multi-level security
- End-to-end 6-step workflow theo NĐ 61/2018
- Full Alibaba Cloud stack (GDB, Hologres, Model Studio, OSS)
- Compliance với 9 văn bản pháp luật Việt Nam

**Evidence:** GovFlow thắng track Public Sector của Qwen AI Build Day 2026 với working prototype.

## PoC scope

### Customer target
**1 Sở Xây dựng của 1 tỉnh progressive** — đề xuất:
- Bình Dương (gần HCMC, có IT budget, lãnh đạo open)
- Đồng Nai
- Long An
- Vĩnh Phúc

### TTHC flagship
**Cấp giấy phép xây dựng (mã 1.004415)** — tiêu biểu vì:
- Khối lượng lớn (5,000–10,000 hồ sơ/năm/Sở)
- SLA gap lớn (15 ngày luật vs 1–3 tháng thực tế)
- Multi-document bundle
- Cross-reference nhiều luật
- Dễ đo outcome

### Duration
**3 tháng** (12 weeks):
- **Week 1–2:** Legal setup, MoU, requirements confirmation
- **Week 3–6:** Deployment + data migration + integration
- **Week 7–10:** Production use (supervised)
- **Week 11–12:** Measurement + review + next steps

### Deliverables
1. Working production system at customer Sở
2. Integration with existing hệ thống một cửa (via API adapter)
3. Custom KG build với 5+ luật liên quan CPXD
4. 10 user accounts (chuyên viên + lãnh đạo)
5. Training + handover documentation
6. Monthly progress reports
7. Final PoC report with metrics

### Success criteria
- **Quantitative:**
  - ≥ 50% reduction in average processing time
  - ≥ 90% SLA hit rate
  - ≥ 95% compliance check accuracy
  - Zero security incidents
- **Qualitative:**
  - ≥ 80% chuyên viên satisfaction (survey)
  - ≥ 70% citizen NPS (satisfied)
  - Lãnh đạo willing to publicly endorse

## Budget breakdown (200M VND)

| Item | Amount (VND) | % |
|---|---|---|
| Alibaba Cloud infrastructure (3 months) | 50M | 25% |
| Legal + contract setup | 20M | 10% |
| Customer integration + adapter | 30M | 15% |
| Training + on-site deployment | 30M | 15% |
| Custom KG content build | 20M | 10% |
| Team time (3 engineers × 3 months, partial) | 40M | 20% |
| Contingency + insurance | 10M | 5% |
| **Total** | **200M** | **100%** |

**Note:** Team salaries not fully covered — founders take reduced compensation for 3 months. Shinhan funds cover infrastructure + integration + deployment.

## Milestones + payment schedule

| Milestone | Timing | Amount | Status Check |
|---|---|---|---|
| Signed MoU + technical spec | Week 2 | 40M | Legal + scope |
| Infrastructure deployed + KG built | Week 6 | 60M | Demo to Shinhan |
| Production go-live | Week 8 | 50M | Working system |
| Final measurement + report | Week 12 | 50M | Success criteria met |

If milestones missed → pause + review, no further disbursement until unblocked.

## Team + qualifications

(To be filled with founder background)

- **Tech lead:** background in graph databases, multi-agent systems, Vietnamese NLP
- **Product/design:** background in gov tech, UX for public sector
- **Business:** background in enterprise sales, gov relations
- **Legal advisor (part-time):** Vietnamese administrative law expertise

External advisors:
- Former cán bộ từ Sở XD (domain expertise)
- Alibaba Cloud solution architect (technical guidance)
- Former Shinhan executive (business guidance)

## Why GovFlow will succeed

1. **Track-winning prototype** — proved technical capability at Qwen AI Build Day
2. **Graph-native architecture** — moat vs competitors, research-backed
3. **Alibaba Cloud partnership** — infrastructure + ecosystem aligned
4. **Compliance ready** — 9-law mapping, not retrofit
5. **Clear customer ROI** — 180× return on subscription cost
6. **Strategic alignment** — Đề án 06, national CĐS priority
7. **Experienced team** — (founder credentials)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Customer procurement delay | Shinhan sponsorship bypasses RFP |
| Technical issues in production | Fallback to human review, graceful degradation |
| LLM cost overrun | Alibaba Cloud infrastructure credits + caching |
| Team capacity | Shinhan funds unlock hiring 1 more engineer |
| Customer ↔ GovFlow fit issues | Weekly sync + clear success criteria |

## After PoC success — expansion plan

### Month 4–6
- Replicate at 2–3 more Sở within same tỉnh (different TTHCs)
- Case study + testimonial publication

### Month 7–12
- Expand to 2 more tỉnh
- Land 1 Bộ pilot
- Raise Seed round ($1–2M) to scale team + marketing

### Year 2
- 10–15 Sở, 2–3 Bộ
- ARR ~10 tỉ VND
- Series A exploration

## Benefit to Shinhan

Beyond the 200M VND PoC:

1. **Portfolio logo** — GovFlow as InnoBoost 2026 success story
2. **Banking upside** — if GovFlow succeeds, Shinhan has first-mover relationship with a high-growth gov-tech platform
3. **Strategic alignment** — Shinhan's B2G banking + GovFlow's TTHC platform create potential bundling opportunities
4. **Network effect** — GovFlow deployments open doors to other Shinhan portfolio companies
5. **Thought leadership** — joint case studies, conference presence, PR

## Ask

**200,000,000 VND PoC funding** with milestone-based disbursement.
**6-month engagement** with Shinhan InnoBoost mentorship.
**Introduction to 1 flagship Sở customer** (Shinhan has gov banking relationships).

In return, GovFlow provides:
- Regular progress reports (bi-weekly)
- Transparent metrics
- Success case study + testimonials rights
- First right of refusal for follow-on investment (Seed round)

## Timeline

- **Day 0:** Win Qwen AI Build Day Public Sector track
- **Day 1–7:** Formal Shinhan InnoBoost application
- **Day 8–14:** Shinhan review + pitch presentation
- **Day 15–21:** Contract negotiation
- **Day 22:** Kickoff PoC
- **Day 22 + 84 (12 weeks):** PoC completion

## Contact

[Founder contact info to be filled]

## Appendix

- Qwen AI Build Day submission + demo video
- Technical architecture deep-dive: see GovFlow docs
- Reference letters (if available)
- LOIs from potential Sở customers (to be gathered)
- Alibaba Cloud partnership letter (if possible)

---

**This document is a draft for internal use. Will be refined and submitted if GovFlow is selected as track winner at Qwen AI Build Day 2026.**
