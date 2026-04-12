# Competitive Landscape — Deep dive

See also [`../02-solution/differentiation.md`](../02-solution/differentiation.md) for pitch-level summary. This is the detail version for business plan + investor discussions.

## Direct competitors — Vietnamese gov-tech DMS/OCR

### FPT IS AKAMINDS + FPT.AI

**Company:** FPT Information System — largest Vietnamese IT services company, ~18,000 employees

**Products:**
- AKAMINDS — AI-powered document processing suite
- FPT.AI — Vietnamese NLP + OCR + chatbot
- FPT Cloud — IaaS

**Strengths:**
- Established relationships with all ministries and large tỉnh
- Deep pocket, proven delivery
- Native Vietnamese language models
- On-prem deployment capability
- Existing OCR + document classification tech

**Weaknesses (from GovFlow PoV):**
- Product is pipeline + rule-based, not agentic
- No graph-native reasoning
- No cross-reference legal RAG
- No multi-agent architecture
- No fine-grained agent permissions
- Focus on văn thư internal, not TTHC công end-to-end
- Big company, slow to innovate

**Risk to GovFlow:** they could add AI features over 12–18 months. But rebuilding graph-native architecture would take much longer.

**Our response:** speed + depth in graph-native. Ship v1 while they're still planning.

### Viettel AI / Viettel Intellect

**Company:** Viettel Group — largest telecom, subsidiary Viettel AI

**Products:**
- Viettel Intellect — AI contact center + back-office automation
- Viettel MCV — voice biometrics
- Viettel Ecosystem — various B2G services

**Strengths:**
- Strong gov relationships (state-owned enterprise with military roots)
- Large data sets from telecom
- Good Vietnamese NLP
- Can bundle with telecom services

**Weaknesses:**
- Mixed AI capability (outsourced from various vendors)
- No graph-native approach
- Focus on customer service ops, not document intelligence
- Slow innovation cycles

**Risk:** could pivot into this space via acquisitions.

**Our response:** partner rather than compete — Viettel could be a channel partner for national rollout.

### VNPT iGate

**Company:** VNPT Group — state telecom + IT

**Products:**
- VNPT iGate — Cổng DVC platform (citizen-facing portal)
- VNPT CDS — digital transformation consulting

**Strengths:**
- Actually powers many tỉnh Cổng DVC deployments
- Gov backing (SOE)
- Established in gov tech

**Weaknesses:**
- Portal/frontend focus, weak backend intelligence
- No AI reasoning on top of their portal data
- Legacy codebase

**Risk:** low direct competition — they're the frontend, we're the backend intelligence. Could be a perfect partner.

**Our response:** integration partner. GovFlow plugs into VNPT iGate portals as the "smart brain" behind the scenes.

### Misa AMIS

**Company:** Misa — SME software leader in VN

**Products:**
- AMIS — ERP + HR + accounting suite
- Some gov sector modules

**Strengths:**
- Strong SME customer base
- Good product UX
- Public company, stable

**Weaknesses:**
- SME focus, weak gov presence
- No AI infrastructure
- No gov compliance depth

**Risk:** low — different segment focus.

**Our response:** potential distribution partner for SME ERP integration.

## Indirect competitors — system integrators

### CMC, HPT, Sao Bắc Đẩu, CEH

These are local system integrators who:
- Deploy other people's software for gov customers
- Do custom development on top
- Maintain ongoing support

**Relationship:** potential partners, not competitors. GovFlow licenses its platform, SI deploys + integrates.

## Foreign platforms — blocked by compliance

### Microsoft Dynamics for Government
- Strong product but **cannot legally serve Vietnamese gov with cloud LLMs** (data residency)
- Limited Vietnamese language
- Restricted in VN

### Salesforce Gov Cloud
- US product, data residency issue
- No Vietnamese presence
- Not applicable

### ServiceNow
- Strong workflow platform but restricted by compliance
- Not optimized for Vietnamese legal system

**Implication:** Foreign platforms are essentially absent from the Vietnamese gov market. This is a protected market for Vietnamese + friendly-region (e.g., Alibaba Cloud) vendors.

## Alibaba Cloud competitive position

Alibaba Cloud is:
- GovFlow's infrastructure partner
- Not a competitor (doesn't sell application-layer products)
- Potentially a distribution channel (Alibaba Cloud Marketplace)
- Strategic aligned (want more Qwen adoption in VN)

**This is a huge asymmetric advantage:** infrastructure-layer backing without competitive tension.

## International analogs (for inspiration, not direct competition)

### GovAI (UK)
- Research-focused, not productized
- Not in Asian markets

### Kira Systems (acquired by Litera)
- Legal contract review AI — similar graph-ish approach
- Not gov-focused, not in VN

### v7 Labs
- Document intelligence platform
- SaaS only, not in VN

**Lesson:** graph-native legal reasoning is an emerging pattern globally. GovFlow being first-to-market in VN is a moat.

## Moat analysis

### Moat 1 — Knowledge graph data
Over time, GovFlow's KG becomes more valuable as:
- More laws are added
- More TTHCs are catalogued
- More precedent cases are included (anonymized)

This is a **data moat** — hard for competitors to replicate quickly.

### Moat 2 — Customer integration
Once deployed at a Sở, switching costs are high:
- Integration with existing systems
- Trained users
- Configured workflows
- Historical case data

Typical gov enterprise software has **90%+ retention** after 2 years of successful deployment.

### Moat 3 — Compliance + legal expertise
Deep knowledge of Vietnamese legal framework is:
- Hard to acquire
- Maintained through ongoing legal monitoring
- Codified in our KG schema

### Moat 4 — Technical paradigm
Graph-native agentic architecture is:
- Research-grounded (backed by 2025–2026 papers)
- Different from existing products (not an add-on, core architecture)
- 6–12 months to replicate even for well-funded competitor

### Moat 5 — Alibaba Cloud partnership
Unique ecosystem backing:
- Qwen3 relationship
- Alibaba Cloud VN market access
- Marketplace listing potential

### Network effects
More Sở using GovFlow → more data → better AI → more value → more Sở join.

## SWOT

### Strengths
- First-mover in agentic GraphRAG for VN gov
- Strong technical architecture
- Deep compliance understanding
- Alibaba Cloud + Shinhan partnerships
- Experienced founding team (assumed)

### Weaknesses
- No production deployment yet
- Small team vs competitors
- Unproven at scale
- Depends on LLM providers (supply risk)

### Opportunities
- Đề án 06 national push
- Gov digital transformation budget cycle
- Vietnamese gov tech underserved
- International expansion (Cambodia, Laos, similar structures)

### Threats
- FPT or Viettel adding similar features
- Changing gov priorities
- LLM cost increases
- Regulatory changes on AI

## Strategy summary

1. **Speed of execution** — ship before competitors wake up
2. **Depth in graph-native** — create hard-to-replicate tech moat
3. **Customer success obsession** — turn first Sở into national reference
4. **Strategic partners** — Alibaba Cloud + Shinhan + system integrators
5. **Compliance as a moat** — make it really hard for foreign vendors to compete
6. **Data + network effects** — accumulate KG + customer data

## Pitch-ready competitive statements

### For Alibaba Cloud SA judge
> "FPT, Viettel, VNPT đều dùng pipeline architecture. Chúng em là đội duy nhất trong hackathon build graph-native on Alibaba Cloud GDB từ ngày đầu. Đây không phải tech demo — đây là production stack."

### For VC judge
> "Competitive landscape in VN gov-tech: legacy SI (FPT/Viettel) slow to innovate, foreign vendors blocked by data residency. First-mover window là 12–18 tháng trước khi FPT phản ứng. Shinhan InnoBoost + Alibaba partnership cho mình runway để khai thác."

### For operator judge
> "Khác biệt về UX: Citizen Portal của chúng em focus real-time tracking + plain-language explanation, không phải 'another gov portal'. Chuyên viên workspace rút 30 phút down 5 phút per case. Leadership dashboard cho phép ký loạt 10 VB trong 30 giây. Đây là sản phẩm mà người dùng thực tế sẽ yêu."
