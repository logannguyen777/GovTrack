# Daily Plan — 12–17/04/2026

**Today is 12/04/2026.** Day 2 of build period. 6 days to submission, 9 days to pitch.

## Overview

Full scope + 5 TTHC deep + top-tier UI/UX + 3-scene permission demo + full Alibaba Cloud stack. No cuts.

## Day 12/04 — TODAY (build day 2)

### Morning (8am–12pm)

**Infrastructure setup:**
- [ ] Provision Alibaba Cloud GDB instance (small tier, VPC, security group)
- [ ] Provision Hologres instance (compute 4-core, PG-compatible)
- [ ] Provision OSS bucket + IAM + KMS keys
- [ ] Provision ECS Singapore g7.large for backend
- [ ] Setup local dev: Docker Compose with `gremlin-server` TinkerGraph + Postgres + MinIO
- [ ] Create monorepo: `frontend/`, `backend/`, `infra/`, `data/`
- [ ] Setup git + CI skeleton

**Parallel — Data collection:** ✅ COMPLETED (exceeded targets)
- [x] Scrape 5 TTHC flagship spec → curated in `data/tthc_specs/` (37 vertices, 84 edges)
- [x] Download legal corpus → HF `th1nhng0/vietnamese-legal-documents` (153k docs, 897k relationships from vbpl.vn)
- [x] Ingest 15 core laws + 4,966 related docs → `data/legal/processed/` (10,688 vertices, 104,476 edges, 869 law chunks)
- [x] Clone Vietnamese provinces database (63 tỉnh, 3,321 phường/xã) → `data/provinces/`
- [ ] Collect 10+ real sample documents per TTHC → DEFERRED (propose after KG shape finalized)

### Afternoon (1pm–6pm)

**KG build (parallel with infrastructure):**
- [ ] FastAPI skeleton + gremlinpython connector to GDB
- [ ] Gremlin schema definition (30+ vertex labels, 20+ edge types)
- [x] ~~Write KG ingest script~~ → `scripts/ingest_legal.py` done (no Qwen3 NER needed — used pre-crawled data with article parsing)
- [x] ~~Build 5 TTHCSpec vertices~~ → `scripts/ingest_tthc.py` done (37 vertices, 84 edges)
- [x] ~~Cross-reference~~ → 104k edges including AMENDED_BY, REFERENCES, BASED_ON, SUPERSEDED_BY from vbpl.vn
- [x] ~~Validate~~ → 10,725 vertices, 104,560 edges (far exceeds original ~2000/~5000 targets)
- [ ] Load processed data into GDB (requires GDB instance provisioned)
- [ ] Load law_chunks into Hologres (requires Hologres instance + embedding model)

**Parallel — Frontend skeleton:**
- [ ] Next.js 15 App Router project
- [ ] shadcn/ui setup + custom theme (dark + light)
- [ ] Tailwind config + typography + colors per design-theme.md
- [ ] Base layout (nav sidebar + top bar)
- [ ] Auth skeleton (JWT validation, mock login for now)

### Evening (7pm–11pm)

**Agent foundation:**
- [ ] Python class skeleton for all 10 agents
- [ ] DashScope SDK setup + Qwen3-Max/VL client wrapper
- [ ] Agent profile YAML loader (for permissions)
- [ ] First 15 Gremlin Template Library queries implemented + tested on TinkerGraph
- [ ] Qwen3-VL smoke test on 5 sample scan documents

**End-of-day deliverable:**
- [ ] GDB up with KG populated (~2000 vertices)
- [ ] Template Library 15 queries working
- [ ] Backend FastAPI + gremlinpython connector working
- [ ] Frontend skeleton running locally
- [ ] Qwen3-VL smoke test passing

**Sleep by midnight.** Don't burn out on day 1.

---

## Day 13/04 — Permission engine + agents

### Morning

**Agent Permission Engine 3 tiers:**
- [ ] SDK Guard: Gremlin AST parser + scope check
- [ ] GDB RBAC: create 10 agent DB users with privileges
- [ ] Property Mask Middleware: redact sensitive fields
- [ ] Test: 20+ negative permission scenarios
- [ ] Agent profiles for all 10 agents in YAML

### Afternoon

**Core agents working end-to-end:**
- [ ] Planner agent (Qwen3-Max function calling)
- [ ] DocAnalyzer agent (Qwen3-VL OCR + layout + entity extraction)
- [ ] Classifier agent (few-shot TTHC taxonomy matching)
- [ ] Test: process 1 sample CPXD bundle end-to-end

### Evening

**Compliance + LegalLookup:**
- [ ] Compliance agent with Gremlin traversal for missing components
- [ ] LegalLookup agent with Agentic GraphRAG (Hologres Proxima vector + GDB traversal)
- [ ] Test: detect missing PCCC for sample CPXD + return correct citation

**End-of-day deliverable:**
- [ ] Permission engine 3 tiers working
- [ ] 5 agents working end-to-end (Planner, DocAnalyzer, Classifier, Compliance, LegalLookup)
- [ ] 1 complete CPXD case processable with citation

---

## Day 14/04 — All agents + frontend core

### Morning

**Remaining agents:**
- [ ] Router agent (Organization graph traversal)
- [ ] Consult agent (cross-dept consult workflow)
- [ ] Summarizer agent (role-aware — executive/staff/citizen)
- [ ] Drafter agent (NĐ 30/2020 templates + validation)
- [ ] SecurityOfficer agent (classification rules + access check)

### Afternoon

**Orchestrator + end-to-end:**
- [ ] Orchestrator: DAG execution, parallel where possible
- [ ] MCP tool exposure for all template queries
- [ ] WebSocket streaming of agent steps
- [ ] Test: process all 5 TTHCs end-to-end
- [ ] Benchmark: accuracy + latency per TTHC

### Evening

**Frontend core screens:**
- [ ] Citizen Portal home + tracking page
- [ ] Intake UI for Bộ phận Một cửa
- [ ] Agent Trace Viewer with React Flow (graph visualization)
- [ ] WebSocket client + real-time updates

**End-of-day deliverable:**
- [ ] 10 agents complete and working on 5 TTHCs
- [ ] Frontend core 3 screens running
- [ ] End-to-end CPXD flow with graph viz

---

## Day 15/04 — Remaining UI + polish start

### Morning

- [ ] Compliance Workspace screen
- [ ] Department Inbox (Kanban 5 cols)
- [ ] Document Viewer with entity highlights + summary tabs

### Afternoon

- [ ] Leadership Dashboard (SLA heatmap + analytics + Recharts)
- [ ] Integrate Hologres AI Functions for weekly brief demo
- [ ] Security Console (audit log live stream + 3 permission scenes UI)

### Evening

- [ ] UI polish pass 1: animations, transitions, empty states, loading skeletons
- [ ] Keyboard navigation + ⌘K command palette
- [ ] Dark + light mode verification
- [ ] Test on 1440 + 1920 screen sizes

**End-of-day deliverable:**
- [ ] All 8 screens functional
- [ ] 3 permission scenes implemented
- [ ] UI polished to "đẳng cấp hàng đầu" bar

---

## Day 16/04 — Polish + benchmark + video

### Morning

- [ ] UI polish pass 2: microinteractions, hover states, toast notifications
- [ ] Error states + edge case handling
- [ ] Mobile responsive for Citizen Portal
- [ ] Accessibility pass (WCAG AA, keyboard, aria labels)

### Afternoon

- [ ] Benchmark: run 25 test cases (5 per TTHC)
- [ ] Measure: classification accuracy, compliance accuracy, latency p50/p95, agent reasoning quality
- [ ] Fix critical bugs found during benchmark
- [ ] Edge case security demo: location near military zone case

### Evening

- [ ] Record demo video 2:30 (following [`../07-pitch/demo-video-storyboard.md`](../07-pitch/demo-video-storyboard.md))
- [ ] Voiceover recording (Vietnamese + English subtitle)
- [ ] Edit in DaVinci Resolve or CapCut
- [ ] Write pitch deck (10 slides) in Figma or Google Slides

**End-of-day deliverable:**
- [ ] Production polished UI
- [ ] Benchmark data ready for pitch
- [ ] Demo video v1 recorded
- [ ] Pitch deck draft

---

## Day 17/04 — Submission day

### Morning

- [ ] Final bug fixes
- [ ] Video edit pass 2 (polish, subtitles, audio mix)
- [ ] Deck revision + visual polish
- [ ] Write Devpost submission (README, screenshots, architecture diagram, link to video)
- [ ] GitHub repo cleanup + README

### Afternoon

- [ ] **Final submission to Devpost** before deadline
- [ ] Test demo system one more time end-to-end on production URL
- [ ] Cache Qwen responses for demo-critical cases (avoid rate limits during pitch)
- [ ] Backup plan: offline video + screenshot deck if network fails

### Evening

- [ ] Rehearsal 1–2 (solo reading)
- [ ] Team review of submission
- [ ] Early rest — don't pull all-nighter

**End-of-day deliverable:**
- [ ] Submitted to Devpost
- [ ] Demo reliably running
- [ ] Pitch video + deck final
- [ ] Rehearsal started

---

## Days 18–20/04 — Rehearsal + polish

### Day 18
- [ ] Rehearsal 3–4 (from memory, record yourself)
- [ ] Review recording, note issues, iterate script
- [ ] Prepare Q&A per [`../07-pitch/qa-preparation.md`](../07-pitch/qa-preparation.md)

### Day 19
- [ ] Rehearsal 5–6 (team mock with judge roles)
- [ ] Debrief + adjust
- [ ] Prepare pitch day logistics (transport, laptop bag, backup)

### Day 20
- [ ] Rehearsal 7–8 (dress rehearsal with full setup)
- [ ] Final deck tweaks
- [ ] Team meeting: confirm roles + who speaks + backup
- [ ] Early sleep

---

## Day 21/04 — **PITCH DAY**

### Morning
- [ ] Light breakfast
- [ ] Quick verbal run-through
- [ ] Travel to HCMC venue (arrive 45 min early)
- [ ] Setup check + AV test

### Pitch slot
- [ ] Deep breaths
- [ ] Deliver pitch (3:00 or 5:00)
- [ ] Q&A with confidence
- [ ] Thank judges genuinely

### After
- [ ] Stay for other pitches (networking)
- [ ] Eat + hydrate
- [ ] Wait for results

---

## Day 22/04 — Showcase (if top)

If GovFlow is track winner:
- [ ] Showcase at Alibaba Cloud SME AI Growth Day Vietnam
- [ ] Networking + follow-up meetings
- [ ] Shinhan InnoBoost discussion

---

## Critical path items (CAN'T SLIP)

These are the items whose delay blocks everything else:

1. **Day 12 morning: GDB provisioned** — without this, nothing runs
2. **Day 12 afternoon: KG populated** — agents need this
3. **Day 13 morning: Permission engine** — needed before other agents
4. **Day 14 morning: All 10 agents complete** — needed before frontend integration
5. **Day 16 evening: Demo video recorded** — needed for submission
6. **Day 17 afternoon: Devpost submission** — hard deadline

If slipping, rearrange: move polish work later, keep critical path moving.

## Daily standup format

Every morning at 8am (15 min):
1. What did we finish yesterday?
2. What's the plan today?
3. What's blocking us?
4. Who needs help?

Tracker: spreadsheet or Notion board with task status.

## Energy management

- **Sleep 7+ hours per night** — caffeine can't replace this
- **Short breaks** every 90 min (stand up, walk, water)
- **Lunch + dinner** — real food, not snacks
- **Exercise** 20 min per day (walk, stretch)
- **Hand off to teammate** when stuck for 30+ min

Sustained execution > heroic burnout. We have 6 days.

## Risk mitigation

See [`risk-register.md`](risk-register.md) for detailed risks + mitigations.

## When in doubt

Refer to [`../02-solution/solution-principles.md`](../02-solution/solution-principles.md). 10 principles guide every decision.
