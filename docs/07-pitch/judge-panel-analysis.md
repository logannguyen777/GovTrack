# Judge Panel Analysis — Per-judge adaptation

## Judge roster

Based on public information for Qwen AI Build Day 2026:

| Judge | Role | Organization | Priority signals |
|---|---|---|---|
| **Mark Khaw** | Solution Architect | Alibaba Cloud | Tech depth, Alibaba stack usage, scalability |
| **Febria R.** | Global Program Manager | Alibaba Cloud | Program fit, partnership potential, market relevance |
| **Phong Nguyen** | Corporate VC | Tasco JSC | Gov tech market, Vietnamese commercial viability |
| **Laura Nguyen** | Partner | GenAI Fund | Investment thesis, technical moat, team |
| **Kai Yong Kang** | Partner | GenAI Fund | Unit economics, scalability, differentiation |
| **Jean-Francois LEGOURD** | Operator | Elfie | UX quality, execution polish, product craft |
| **Anh Dao** | Operator | Elfie | Product-market fit, go-to-market execution |

## Per-judge strategy

### Mark Khaw (Alibaba Cloud SA)

**What he cares about:**
- Technical architecture depth
- Use of Alibaba Cloud products (GDB, Hologres, Model Studio)
- Scalability patterns
- Best practices (GraphRAG, MCP, agentic design)

**What to emphasize in pitch:**
- Slide 4 (Dual Graph Architecture on Alibaba Cloud GDB) — his sweet spot
- Slide 5 (3-tier permissions) — technical depth
- Slide 6 (Qwen @ 8 roles + MCP) — Alibaba product showcase
- Hologres AI Functions (LLM inline in SQL) — will impress him

**Questions he might ask:**
- "Why GDB not Neo4j?" → "Alibaba Cloud native, Gremlin compatible, production path, enterprise ACL"
- "How do you handle Gremlin complexity with LLM?" → "Template Library + SDK Guard validation"
- "Scaling strategy?" → "Polyglot persistence, ACK + PAI-EAS for production, multi-tenant graph partitioning"

**How to win him over:**
- Show real code running on real GDB
- Mention specific Alibaba Cloud products with depth (not just names)
- Acknowledge trade-offs thoughtfully

---

### Febria R. (Alibaba Cloud GPM)

**What she cares about:**
- Is this a good program fit for Qwen AI Build Day narrative?
- Can this be a success story for Alibaba in Vietnam?
- Partnership potential
- Market reach

**What to emphasize:**
- Slide 9 (Impact + Market) — large VN market
- Slide 10 (Ask + partnership) — Alibaba Cloud as infrastructure partner
- Alibaba Cloud Marketplace potential (Year 3)
- Joint case study + PR opportunity

**Questions she might ask:**
- "Can this become a showcase for Alibaba in VN gov?" → "Absolutely. First Qwen3 agentic platform for Vietnamese gov. Joint case study + conference talks."
- "How can Alibaba help you grow?" → "Marketplace listing, co-sell with Alibaba Cloud sales team, joint PR"

**How to win her over:**
- Position as mutual success (not just taking from Alibaba)
- Express genuine enthusiasm for the partnership
- Mention strategic alignment with Alibaba Cloud's gov push in VN

---

### Phong Nguyen (Tasco CVC)

**What he cares about:**
- Vietnamese market expertise
- Gov sector fit
- Commercial viability with realistic timelines
- Team's ability to execute

**What to emphasize:**
- Slide 2 (Vietnamese scope — NĐ 61, Đề án 06)
- Slide 8 (compliance with 9 VN laws)
- Personas 1–6 (grounded in Vietnamese reality)
- 5 TTHC flagship (CPXD, GCN, ĐKKD, LLTP, GPMT — familiar to him)
- GTM strategy focused on Vietnamese tỉnh

**Questions he might ask:**
- "Bạn hiểu gov procurement VN không?" → "Có, Shinhan PoC bypass RFP, tỉnh progressive first, system integrator partner"
- "Quan hệ với lãnh đạo tỉnh như thế nào?" → honest answer about current state + plan to build
- "Tasco có quan tâm đầu tư không?" → "Em muốn nghe thêm về Tasco's thesis — có phù hợp không?"

**How to win him over:**
- Vietnamese language for key phrases (shows cultural fit)
- Concrete Vietnamese examples (not generic)
- Honest about challenges + specific mitigation plans
- Show deep understanding of Vietnamese admin system

---

### Laura Nguyen + Kai Yong Kang (GenAI Fund)

**What they care about:**
- Investment thesis fit
- Technical moat (is this defensible?)
- Team quality
- Scalability beyond VN

**What to emphasize:**
- Slide 4 + 5 (technical moat via graph-native + 3-tier permissions)
- Slide 9 (unit economics + 180× customer ROI)
- Research backing (AGENTiGraph 95%, Neo4j GraphRAG)
- International expansion possibility (similar gov structures in SE Asia)

**Questions they might ask:**
- "What's your defensible moat?" → "Graph-native architecture + data moat of KG + compliance depth + customer integration. Summary: 6–12 months for competitor to replicate."
- "LTV/CAC?" → "25× at Sở level. Payback 4 months. Based on 35% gross margin Year 1, 65% Year 3."
- "Internatiional expansion?" → "Cambodia, Laos have similar admin structures. Year 4–5 exploratory."
- "How do you hire in VN?" → ask about their network for this

**How to win them over:**
- Numbers, not adjectives
- Acknowledge risks, show mitigations
- Show awareness of investor frameworks (LTV/CAC, payback, etc.)
- Mention their portfolio companies in related space (if relevant)

---

### Jean-Francois LEGOURD (Elfie operator)

**What he cares about:**
- Product craft + UX quality
- Execution polish
- User journey design
- Does the product actually work well?

**What to emphasize:**
- Slide 3 (big idea with screenshot of Agent Trace Viewer — visual polish)
- Demo video (Scene 4 — Citizen Feedback Loop + Scene 7 — Security wow)
- 8 screens catalog (breadth of product)
- Personas-driven design

**Questions he might ask:**
- "How did you design the Citizen Portal?" → user journey + specific UX decisions
- "What's your accessibility strategy?" → WCAG AA, keyboard nav, VN subtitle
- "How do you handle errors?" → mandatory 6 states per screen, graceful degradation
- "What's the experience like on mobile?" → Citizen Portal mobile-first

**How to win him over:**
- Walk through user journey like a real user
- Show actual screenshots not mockups
- Talk about small details (microinteractions, empty states)
- Mention specific design references (Linear, Vercel, Arcade)

---

### Anh Dao (Elfie operator)

**What she cares about:**
- Product-market fit validation
- Go-to-market execution
- Customer success stories (in-progress is OK)
- Operational excellence

**What to emphasize:**
- Slide 10 (GTM with Shinhan PoC framework)
- Journey for real personas (anh Minh, chị Lan, chị Hương)
- Customer success metrics (SLA, NPS, time saved)
- Execution plan detail (not vague "we'll figure it out")

**Questions she might ask:**
- "How do you validate product-market fit?" → "Anh Minh scenario is grounded in real painpoints from Vietnamese admin. PoC measures 4 KPIs: processing time, SLA hit, user NPS, compliance accuracy."
- "What happens in month 2 of PoC?" → specific milestone + risk mgmt
- "How do you keep chuyên viên engaged?" → change management, training, super-user program

**How to win her over:**
- Show concrete operational plans
- Mention metrics, not just direction
- Acknowledge the non-technical side (change management, customer success)

---

## Combined strategy

### Pitch structure adapts to cover all interests:

**Tech depth (Mark, Laura, Kai):**
- Slides 4, 5, 6 — dual graph, permissions, Qwen 8 roles
- Research backing references
- Alibaba Cloud stack specifics

**Business case (Phong, Laura, Kai, Febria):**
- Slides 9, 10 — impact, market, ask
- Unit economics
- GTM strategy

**UX + execution (Jean-Francois, Anh Dao):**
- Demo video — actual product in action
- Screenshots showing polish
- Persona-driven user journey narration

**Vietnamese market (Phong, Febria):**
- Vietnamese language for key moments
- Specific VN examples (anh Minh CPXD, NĐ 61)
- Vietnamese regulatory depth

## Practice scenarios

### Scenario A: Tech-focused Q&A
Pair with team member playing Mark + Laura. Focus 80% of questions on technical architecture, scalability, code.

### Scenario B: Business-focused Q&A
Pair with Phong + Kai roles. Focus on market, competition, pricing, unit economics, GTM.

### Scenario C: Product-focused Q&A
Pair with Jean-Francois + Anh Dao roles. Focus on UX, personas, user journeys, operational details.

### Scenario D: Mixed hostile
All 4 question types rapid-fire, with skeptical tone. Practice staying calm.

## Post-pitch follow-up

If judge asks for specific follow-up:
- **Tech deep-dive:** offer 1-hour architecture walkthrough
- **Business case:** send business plan PDF
- **Customer intro:** ask for their network help
- **Investment interest:** "Happy to schedule separate call"

Always follow up within 24 hours with thank you + specific resources.
