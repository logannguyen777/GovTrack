# Milestones — Definition of Done per day

## Daily DoD gates

Mỗi ngày có Definition of Done rõ ràng. Không "move on" khi chưa đạt.

### Day 12/04 DoD

- [x] **Infra:** Alibaba Cloud GDB + Hologres + OSS provisioned, accessible from dev env
- [x] **KG:** ~2,000 vertices loaded (Law + Article + TTHCSpec + RequiredComponent + Organization)
- [x] **Cross-refs:** 5 TTHCs have GOVERNED_BY edges to ≥ 10 Articles each
- [x] **Template Library:** First 15 Gremlin templates working (tested on TinkerGraph locally + GDB)
- [x] **Backend:** FastAPI skeleton running, gremlinpython connected to GDB
- [x] **Frontend:** Next.js + shadcn theme + base layout running at `localhost:3000`
- [x] **Qwen3-VL smoke test:** successfully OCR + extract fields from 5 sample docs
- [x] **Agents:** 10 Python class skeletons with system prompts + profile YAML files
- [x] **Git:** repo structured, first meaningful commit

**Verification:**
- Can submit a case via API → Case vertex in GDB
- Can query "what TTHCs exist?" via Gremlin template
- Can upload image → Qwen3-VL returns structured JSON

### Day 13/04 DoD

- [ ] **Permission engine:** 3 tiers working (SDK Guard, GDB RBAC simulation, Property Mask)
- [ ] **Test:** 20+ negative permission scenarios all reject correctly
- [ ] **Agent profiles:** all 10 agents have YAML profiles loaded and enforced
- [ ] **Core 5 agents running end-to-end:**
  - Planner
  - DocAnalyzer
  - Classifier
  - Compliance
  - LegalLookup
- [ ] **E2E test:** process 1 sample CPXD bundle → generates Gap + Citation
- [ ] **GraphRAG working:** LegalLookup returns correct NĐ 136/2020 Điều 13.2.b citation for PCCC gap

**Verification:**
- Submit sample bundle → agent trace shows 5 agents running + writing to graph
- Compliance detects missing PCCC → LegalLookup returns correct citation
- Negative permission test: Summarizer cannot read national_id (SDK Guard catches)

### Day 14/04 DoD

- [ ] **All 10 agents complete and tested**
- [ ] **E2E test on all 5 TTHCs:** each produces expected output structure
- [ ] **Orchestrator DAG execution:** parallel branches working
- [ ] **WebSocket streaming:** agent steps streamed to client
- [ ] **MCP tools exposed:** 30+ Gremlin templates callable as MCP tools
- [ ] **Frontend 3 core screens:**
  - Citizen Portal (home + tracking)
  - Intake UI
  - Agent Trace Viewer (with live graph viz)
- [ ] **Benchmark baseline:** record accuracy + latency for each agent on 5 test cases

**Verification:**
- Drag-drop file on Intake UI → full pipeline runs → Agent Trace Viewer shows graph growing
- All 5 TTHCs have at least 1 happy-path case passing
- Agent permission denials still working correctly

### Day 15/04 DoD

- [ ] **Frontend 5 more screens:**
  - Compliance Workspace
  - Department Inbox (Kanban)
  - Document Viewer
  - Leadership Dashboard (with Hologres AI Functions integration)
  - Security Console
- [ ] **3 permission scenes UI:** Scene A (SDK reject), B (RBAC reject), C (mask elevation)
- [ ] **Hologres AI Function demo:** `ai_generate_text` call in SQL returns weekly brief
- [ ] **Polish pass 1:** animations, transitions, empty states, loading skeletons
- [ ] **Keyboard nav + ⌘K working**
- [ ] **Dark + light mode both polished**

**Verification:**
- Click through all 8 screens without errors
- 3 permission scenes trigger correctly with animations
- Responsive at 1440 + 1920 resolutions

### Day 16/04 DoD

- [ ] **Polish pass 2:** all microinteractions, toast feedback, edge cases
- [ ] **Accessibility:** WCAG AA compliance, keyboard complete, ARIA labels
- [ ] **Mobile responsive:** Citizen Portal works on phone viewport
- [ ] **Benchmark final:** 25 test cases (5 per TTHC), metrics documented
- [ ] **Bug count:** < 5 critical bugs remaining
- [ ] **Demo video v1 recorded:** 2:30 following storyboard
- [ ] **Voiceover recorded:** Vietnamese + English subtitle
- [ ] **Pitch deck v1:** 10 slides written

**Verification:**
- Demo video plays end-to-end without issues
- Benchmark metrics show target accuracy
- No critical bugs in main demo paths

### Day 17/04 DoD

- [ ] **All critical bugs fixed**
- [ ] **Demo video v2 final:** polished, subtitled, exported
- [ ] **Pitch deck v2 final:** visual polish, tested on projector-like resolution
- [ ] **GitHub repo polished:** README, architecture diagram, screenshots
- [ ] **Devpost submission complete:** before deadline
- [ ] **Backup plan ready:** offline video, screenshot deck, USB backup
- [ ] **Production demo URL live:** tested from external network
- [ ] **Cache warmed:** Qwen responses for demo cases
- [ ] **Rehearsal 2 completed**

**Verification:**
- Submitted on Devpost
- Demo URL accessible from phone on different network
- Can walk through demo 2× back-to-back without bugs

## Definition of Ready (DoR)

Before starting a task:
- [ ] Task clearly described
- [ ] Acceptance criteria defined
- [ ] Dependencies identified
- [ ] Estimated time
- [ ] Assigned to specific person

## Checkpoint review

At end of each day, team reviews:
1. DoD completion
2. What slipped
3. What's in critical path tomorrow
4. Any blockers

If DoD not met:
- Is it critical? → must-do tomorrow first
- Is it optional? → defer, communicate decision

## Success criteria — Pitch day

**Minimum (must have):**
- Working demo end-to-end
- 5 TTHCs all process correctly
- 3 permission scenes work
- Pitch delivered within time limit
- Answer Q&A confidently

**Target (strong):**
- All DoDs met on schedule
- Polished UI
- Demo video polished
- Rehearsed 8+ times
- Strong Q&A performance

**Stretch (aim for):**
- Track winner selection
- Shinhan InnoBoost PoC funding approval
- Multiple follow-up meetings

## What "done" means for GovFlow

**NOT done:**
- Tests failing
- Partial features merged
- "Works on my machine"
- Polish deferred indefinitely
- TODO comments in critical paths

**Done:**
- Tests passing
- Feature complete per spec
- UI polished to "đẳng cấp" bar
- Demo runs end-to-end reliably
- Audit trail + error handling working

## Quality gates

### Code
- [ ] No linter errors
- [ ] No critical warnings
- [ ] Type check passes
- [ ] Tests > 70% coverage on critical paths

### UI
- [ ] All 6 states (empty/loading/error/hover/focus/disabled)
- [ ] Responsive 1440 + 1920
- [ ] Dark + light mode
- [ ] Keyboard accessible

### Agent
- [ ] System prompt validated
- [ ] Tool scope correct
- [ ] Permission profile loaded
- [ ] End-to-end test passing

### Documentation
- [ ] Code comments for non-obvious logic
- [ ] README updated
- [ ] API docs generated

## Execution principles

From [`../02-solution/solution-principles.md`](../02-solution/solution-principles.md):

1. **Graph-first, not pipeline-first** — all state in graph
2. **Qwen is brain, graph is memory**
3. **Everything auditable, nothing implicit**
4. **Permissions 3-tier, not 1**
5. **Human-in-the-loop at decision points**
6. **Vietnamese-context-first**
7. **Traceability pháp lý = feature**
8. **Alibaba Cloud-first commitment**
9. **Realtime where it matters**
10. **Simplicity at surface, depth underneath**

When faced with a decision, check these principles.

## Never slip these

These are dealbreakers — if they slip, pitch fails:

1. **Demo video ready by day 16 end** — backup plan depends on it
2. **Devpost submission before deadline day 17** — can't submit late
3. **3 permission scenes working** — core differentiation
4. **All 5 TTHCs end-to-end working** — claimed scope
5. **Pitch team member on site day 21** — presence is mandatory

Everything else is optional if cascading cuts are needed (which they shouldn't be with good planning).
