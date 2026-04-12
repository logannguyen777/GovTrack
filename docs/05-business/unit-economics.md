# Unit Economics

## Per case processed

### Revenue
- **Average revenue per case:** ~10,000 VND (blended across tiers)

### Cost breakdown
| Cost | Amount (VND) | % of revenue |
|---|---|---|
| LLM tokens (Qwen3-Max + Qwen3-VL) | 4,500 | 45% |
| Graph DB + vector search compute | 500 | 5% |
| Storage (OSS + Hologres) | 300 | 3% |
| Compute (ECS + processing) | 500 | 5% |
| Support + ops (amortized) | 700 | 7% |
| **Total COGS** | **6,500** | **65%** |
| **Gross profit** | **3,500** | **35%** |

### LLM cost calculation

Per case, Qwen3 usage:
- Planner: ~500 tokens
- DocAnalyzer (Qwen3-VL): ~5,000 tokens (multimodal images)
- Classifier: ~800 tokens
- Compliance: ~3,000 tokens
- LegalLookup: ~4,000 tokens (with context)
- Router: ~500 tokens
- Consult: ~1,500 tokens
- Summarizer: ~2,000 tokens (3 versions)
- Drafter: ~3,000 tokens
- SecurityOfficer: ~800 tokens
- **Total: ~21,100 tokens per case**

Alibaba Cloud Model Studio pricing (approximate Vietnam region):
- Qwen3-Max input: ~$0.004 / 1k tokens
- Qwen3-Max output: ~$0.008 / 1k tokens
- Qwen3-VL: similar

Average: ~$0.006 / 1k tokens × 21 = **$0.126 per case** (~3,000 VND)

With Qwen3 function calling overhead + retries: ~$0.18 per case (~4,500 VND)

### At scale — cost optimization
- **Prompt caching:** Qwen3 supports prompt caching → 40% cost reduction after warm-up
- **Smaller models for simple tasks:** use Qwen3-Turbo cho Classifier, Router → another 20% savings
- **Batch processing:** off-peak batch processing → lower rates
- **Target at scale: ~2,500 VND per case for LLM**

### Target margins
- **Year 1 (hackathon pricing, non-optimized):** 35% gross margin
- **Year 2 (after optimization):** 55% gross margin
- **Year 3 (at scale):** 65% gross margin

### Compare with SaaS benchmarks
- Typical SaaS: 75–85% gross margin
- AI-native SaaS: 40–65% gross margin
- **GovFlow:** 35% → 65% (within normal AI SaaS range)

## Per customer (1 Sở deployment)

### Revenue
- **Professional tier: 500M VND/year**
- Plus overages and add-ons: ~100M VND/year
- **Total: ~600M VND ARR per Sở**

### Cost attribution
- **COGS per Sở:** ~10k cases × 6,500 VND = 65M VND
- **Customer Success:** 50M VND/year (part of CSM salary)
- **Support:** 20M VND/year
- **Infrastructure allocation:** 30M VND/year
- **Total direct cost: ~165M VND/year**

### Gross margin per Sở
- 600M - 165M = **435M VND/year (72%)**

### Customer Acquisition Cost (CAC)
- Sales effort: ~2 months × founder time × 30M/month = 60M VND
- Marketing allocation: 30M VND
- Legal + contract: 20M VND
- Onboarding (free hours): 30M VND
- **Total CAC: 140M VND per Sở**

### Payback period
- **Month to payback: 140M / (435M/12) = ~4 months**
- Very healthy for enterprise SaaS (target is usually <18 months)

### Lifetime Value (LTV)
Assumptions:
- Average customer lifespan: 5 years (gov customers are sticky)
- Annual gross profit: 435M VND
- Year-over-year expansion: +15% (more TTHCs, more users)
- **Cumulative GP over 5 years:** ~3.5 tỉ VND
- **LTV:** 3.5 tỉ VND per Sở

### LTV/CAC ratio
- **3,500M / 140M = 25×**
- World-class ratio (healthy SaaS is 3×, good is 5×, great is 10×)

## At scale (Year 3)

### 100 Sở deployments + 5 Bộ + 10 Enterprise
- Sở ARR: 100 × 500M = 50 tỉ VND
- Bộ ARR: 5 × 2 tỉ = 10 tỉ VND
- Enterprise: 10 × 500M = 5 tỉ VND
- **Total ARR: 65 tỉ VND**

### Cost structure
- COGS: ~30% of revenue = 19.5 tỉ VND
- R&D: ~25% = 16 tỉ VND
- S&M: ~20% = 13 tỉ VND
- G&A: ~10% = 6.5 tỉ VND
- **Total opex: 55 tỉ VND**

### Net income (Year 3 target)
- **65 tỉ - 55 tỉ = 10 tỉ VND profit (15% net margin)**
- Path to profitability in Year 3 (typical for enterprise SaaS)

## Funding requirements

### Pre-seed (now)
- **Shinhan InnoBoost 200M VND** (if selected) + founder capital
- Runway: 2–3 months
- Milestone: working MVP + 1 Sở PoC started

### Seed ($1–2M USD ≈ 25–50 tỉ VND)
- Post-Shinhan PoC success
- Team: 5 → 12 people
- Runway: 18 months
- Milestone: 5 Sở + 1 Bộ pilot + ARR 3 tỉ VND

### Series A ($5–10M USD ≈ 125–250 tỉ VND)
- Year 2
- Team: 12 → 30 people
- Runway: 24 months
- Milestone: 20 Sở + 3 Bộ + ARR 15 tỉ VND

### Series B (optional, Year 3–4)
- Only if national expansion + international
- $10–20M USD
- Team: 30 → 60 people

## Sensitivity analysis

### Scenario: lower capture rate
If we only reach 50% of target Sở:
- ARR Year 3: 32.5 tỉ VND instead of 65
- Still profitable (thinner margin but yes)

### Scenario: LLM cost doubles
If Qwen3 pricing goes up 2×:
- COGS per case: 11,500 VND (revenue: 10,000)
- Gross margin: -15%
- Need to raise prices by 20% (still <200× ROI for customer)
- Or optimize to smaller models + caching

### Scenario: customer churn higher than expected
If churn is 20%/year instead of 5%:
- LTV drops to 1.5 tỉ VND
- LTV/CAC = 10.7× (still very healthy)
- Need to invest more in customer success

## Red flags to watch

1. **COGS creeping above 50%** → check LLM usage per case
2. **CAC over 300M per Sở** → sales process broken
3. **Payback over 12 months** → pricing too low
4. **Churn over 15%** → product-market fit issues
5. **Net Revenue Retention below 100%** → not expanding within accounts

## Financial discipline

**Rule:** before spending money, ask:
- Does this directly drive ARR?
- Does this reduce COGS significantly?
- Is this legal/compliance required?

If none → defer.

Founder salaries kept modest until Series A. Investors funds go to building product and acquiring customers, not fancy offices.

## Bottom line

- **Positive unit economics from PoC**
- **Gross margin improving from 35% → 65%** as scale kicks in
- **LTV/CAC 25× at Sở level**
- **Path to profitability in Year 3**
- **Fundable at each stage**

This is a real business, not a grant project.
