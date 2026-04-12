# Scope Guardrails — What's IN, what's OUT

## IN — must-have for submission

### Core features
- ✅ **5 TTHC flagship** fully supported (CPXD, GCN QSDĐ, ĐKKD, LLTP, GPMT)
- ✅ **10 agents** all working with clear roles
- ✅ **Dual Graph** (KG + Context Graph) on Alibaba Cloud GDB
- ✅ **3-tier Permission Engine** (SDK Guard + GDB RBAC + Property Mask)
- ✅ **Agentic GraphRAG** for legal reasoning (Hologres Proxima + GDB traversal)
- ✅ **8 screens** fully built:
  1. Citizen Portal
  2. Intake UI
  3. Agent Trace Viewer
  4. Compliance Workspace
  5. Department Inbox
  6. Leadership Dashboard
  7. Security Console
  8. Document Viewer
- ✅ **3 permission demo scenes** (SDK Guard, GDB RBAC, Property Mask elevation)
- ✅ **WebSocket realtime** streaming of agent steps
- ✅ **Hologres AI Functions** (at least 1 working query calling Qwen in SQL)
- ✅ **Full Alibaba Cloud stack** (GDB, Hologres, Model Studio, OSS)
- ✅ **Demo video 2:30** with voiceover + subtitles

### Infrastructure
- ✅ Alibaba Cloud Model Studio integration (Qwen3-Max + Qwen3-VL + Qwen3-Embedding)
- ✅ MCP tool exposure for graph queries
- ✅ JWT auth with clearance claims
- ✅ Gremlin Template Library (~30 templates)
- ✅ Audit trail via AgentStep + AuditEvent vertices

### Compliance
- ✅ NĐ 30/2020 format Drafter output
- ✅ 4 classification levels (Unclassified → Top Secret)
- ✅ Data retention policies
- ✅ 9 laws referenced in KG + citations

### Polish
- ✅ Dark + light mode
- ✅ Keyboard navigation
- ✅ ⌘K command palette
- ✅ Micro-interactions (Framer Motion)
- ✅ 6 states per component
- ✅ Responsive 1440 + 1920
- ✅ Accessibility WCAG AA

## OUT — explicitly NOT included

### Features not in scope
- ❌ **Real VNeID integration** (production credentials not available for hackathon) — mock only
- ❌ **Real Cổng DVC integration** (API adapter not in scope for PoC) — simulated
- ❌ **Real digital signature** (PKI setup complex) — visual representation only
- ❌ **Multi-tenant deployment** (single tenant for demo)
- ❌ **Production on-prem deployment** (roadmap only, not hackathon)
- ❌ **Mobile native app** (Citizen Portal responsive web only)
- ❌ **SMS notifications** (push + email only)
- ❌ **Multi-language support** (Vietnamese + English only)
- ❌ **Law update pipeline** (static KG for hackathon)
- ❌ **Automated KG refresh** (manual rebuild)
- ❌ **CI/CD pipeline production-grade** (local Docker + manual deploy)
- ❌ **Load testing at scale** (smoke test only)
- ❌ **Advanced anomaly detection ML** (rule-based for demo)
- ❌ **Internationalization i18n framework** (hardcoded strings OK for hackathon)
- ❌ **Real customer integration APIs** (simulated)
- ❌ **Enterprise SSO** (mock SSO for demo)
- ❌ **Enterprise SLAs** (no customer contracts yet)

### Features beyond flagship TTHC
- ❌ Additional 50+ TTHCs (5 is enough for hackathon)
- ❌ Provincial variation of TTHCs (one size for demo)
- ❌ Historical case database (new cases only)
- ❌ Precedent search (lightweight implementation only)

### Production-grade features
- ❌ Backup + DR strategy (hackathon only)
- ❌ Monitoring dashboards (SLS logs only)
- ❌ On-call rotation (N/A for hackathon)
- ❌ SOC 2 / ISO 27001 (future state)
- ❌ Penetration testing
- ❌ Bug bounty program

## "Nice to have if time permits"

These are valuable but not blocking if cut:

- **Precedent search UI** (Document Viewer tab) — basic version OK
- **Weekly AI brief via Hologres** (pitch-worthy demo feature) — 1 query enough
- **Analytics dashboard** with fancy charts — basic version OK
- **Forensic timeline replay** in Security Console — basic version OK
- **Light mode polish** (dark mode is primary) — both supported but dark is default
- **Mobile view for Citizen Portal** — responsive CSS, not native

## Cut order if time slips

If forced to cut due to time constraints, cut in this order:

1. **First cuts (day 16):**
   - Light mode polish (keep functional, not pixel-perfect)
   - Analytics dashboard advanced features (keep basic charts)
   - Forensic timeline replay (keep basic audit log)
   - Precedent search (keep simple semantic search)

2. **Second cuts (day 17 morning if needed):**
   - Advanced animations (keep essential ones)
   - Keyboard shortcuts beyond ⌘K (keep just the palette)
   - Dark mode alternative colors (standard dark only)

3. **NEVER cut — dealbreakers:**
   - 10 agents end-to-end
   - 3 permission demo scenes
   - Agent Trace Viewer with graph viz
   - Demo video
   - 5 TTHCs at least basic working
   - Compliance with 9 laws mapped
   - Alibaba Cloud stack (GDB + Hologres + Model Studio)

## Post-hackathon TODO (for PoC)

Not in hackathon scope but needed for PoC deployment:

- [ ] Real VNeID integration
- [ ] Customer hệ thống một cửa integration
- [ ] Production Qwen3 deployment option (PAI-EAS)
- [ ] Production-grade auth + SSO
- [ ] Multi-tenant architecture
- [ ] Monitoring + alerting
- [ ] Backup + DR strategy
- [ ] Law update pipeline
- [ ] Additional 20+ TTHCs
- [ ] Change management + training materials

## Scope review discipline

**Every day at 8am standup:**
- Is anyone adding scope unofficially?
- Is anyone building something not in IN list?
- If yes, stop and validate against this guardrail doc

**Every day at 6pm review:**
- Did we make progress on IN items?
- Any IN items at risk of slipping?
- Any OUT items that accidentally got built?

**Every major decision:**
- "Does this serve the 8 capabilities or 3 levers?"
- If yes → proceed
- If no → defer to post-hackathon

## Why scope guardrails matter

Hackathon failure mode #1: trying to do too much. Teams lose focus, ship half-done everything instead of focused excellent.

GovFlow's commitment: **do 10 agents + 3 permission scenes + 5 TTHCs + 8 screens EXCELLENTLY**, not 20 agents + 10 scenes + 20 TTHCs poorly.

Quality > quantity. That's the deal.
