# Risk Register

## Risk prioritization

Risks scored on:
- **Likelihood** (L/M/H)
- **Impact** (L/M/H)
- **Severity** = Likelihood × Impact

## Technical risks

### R1 — Alibaba Cloud GDB provision slow / account issues
- **Likelihood:** Medium
- **Impact:** High (blocks everything day 12)
- **Severity:** High
- **Mitigation:**
  - Start provision immediately day 12 morning
  - Parallel local dev with `gremlin-server` TinkerGraph in-memory
  - Schema + Template Library developed locally, import to GDB when ready
  - Backup: Neo4j Aura free tier if GDB fails entirely (compromise on Alibaba SA points)
- **Owner:** Infrastructure lead
- **Status:** Active

### R2 — Gremlin LLM generation failures
- **Likelihood:** High
- **Impact:** High (blocks compliance + legal lookup)
- **Severity:** High
- **Mitigation:**
  - Gremlin Template Library ~30 prebuilt — LLM only picks template + fills params
  - SDK Guard validates all ad-hoc queries before execution
  - Test 50+ query patterns day 12–13
  - Fallback rules for common queries (if LLM uncertain)
- **Owner:** Agent engineer
- **Status:** Active

### R3 — Qwen3-VL OCR accuracy on poor scans
- **Likelihood:** High
- **Impact:** Medium (cascades into classification/compliance errors)
- **Severity:** High
- **Mitigation:**
  - Test on 10+ real scanned docs day 12
  - DocAnalyzer confidence threshold (<0.7 → flag for human)
  - Citizen Portal primarily uses digital uploads (high quality)
  - Only paper scans come through Intake UI (limited volume)
- **Owner:** Agent engineer
- **Status:** Active

### R4 — Agent Permission Engine has hole
- **Likelihood:** Medium
- **Impact:** High (security demo credibility)
- **Severity:** High
- **Mitigation:**
  - 20+ negative permission test scenarios day 13
  - Security review internal day 15
  - Focus on 3 demo scenes reliability (can be tightly scoped)
  - 3-tier architecture provides defense in depth
- **Owner:** Security lead
- **Status:** Active

### R5 — Qwen API rate limits during demo
- **Likelihood:** Medium
- **Impact:** Medium (degraded demo)
- **Severity:** Medium
- **Mitigation:**
  - Pre-record video as primary, live demo backup
  - Cache Qwen responses for demo cases (warm cache day 17)
  - Fallback: abort live demo, play video
  - Alibaba Cloud demo credits for hackathon
- **Owner:** Backend engineer
- **Status:** Active

### R6 — Hologres AI Functions not working as expected
- **Likelihood:** Medium
- **Impact:** Low (nice-to-have feature)
- **Severity:** Low
- **Mitigation:**
  - Test day 12
  - If fails, simulate by calling Qwen in application code + inserting into Hologres
  - Still appears in slides as "Hologres + AI Functions"
- **Owner:** Backend engineer
- **Status:** Active

### R7 — Compliance knowledge base incomplete for 5 TTHCs
- **Likelihood:** Medium
- **Impact:** High (demo shows compliance failures)
- **Severity:** High
- **Mitigation:**
  - Day 12 morning dedicated to 5 TTHCs full spec
  - Qwen3-Max assists parsing law text → graph edges
  - CPXD most detailed (flagship demo), others basic
  - Human QA on specs before demo day
- **Owner:** Domain expert / legal advisor
- **Status:** Active

## Execution risks

### R8 — Scope creep (feature additions)
- **Likelihood:** High
- **Impact:** Medium (eats time)
- **Severity:** High
- **Mitigation:**
  - Lock scope to 8 capabilities + 5 TTHCs + 8 screens + 3 permission scenes
  - Any new feature needs "does it serve 1 of 10 principles?" check
  - Daily standup verifies scope lock
- **Owner:** Product lead
- **Status:** Active

### R9 — UI quality below "đẳng cấp hàng đầu" bar
- **Likelihood:** Medium
- **Impact:** High (execution tiêu chí)
- **Severity:** High
- **Mitigation:**
  - 1.5 day dedicated to polish (day 15.5 + 16)
  - Design references: Linear, Vercel, Arcade
  - 6-state mandatory per component
  - Team UI review day 16 morning
- **Owner:** Frontend lead
- **Status:** Active

### R10 — Team burnout
- **Likelihood:** Medium
- **Impact:** High (day of pitch performance)
- **Severity:** High
- **Mitigation:**
  - Sleep 7+ hours per night
  - Break every 90 min
  - Exercise 20 min/day
  - Real meals, not snacks
  - No all-nighters — if task can't finish today, do tomorrow
- **Owner:** All team members
- **Status:** Active

### R11 — Critical bug discovered day 17
- **Likelihood:** Medium
- **Impact:** High
- **Severity:** High
- **Mitigation:**
  - Full bench day 16
  - Day 17 morning reserved for final fixes
  - Video as demo fallback — doesn't depend on live system
  - Freeze code day 17 afternoon — no new features
- **Owner:** Tech lead
- **Status:** Active

### R12 — Missing pitch day 21
- **Likelihood:** Low
- **Impact:** Dealbreaker
- **Severity:** High
- **Mitigation:**
  - Confirm team member availability today (12/04)
  - Book travel day 18
  - Have 2 team members ready to pitch
  - Pre-event contingency planning
- **Owner:** Founder
- **Status:** **Verify today**

## Pitch risks

### R13 — Live demo fails during pitch
- **Likelihood:** Medium
- **Impact:** Medium
- **Severity:** Medium
- **Mitigation:**
  - Demo video is primary, live is secondary
  - Have fallback slide deck with screenshots
  - Graceful transition: "Let me show the recorded version..."
  - Rehearsal includes failure scenarios
- **Owner:** Pitcher
- **Status:** Active

### R14 — Hostile Q&A — judge tries to poke holes
- **Likelihood:** High
- **Impact:** Medium
- **Severity:** Medium
- **Mitigation:**
  - Prep 15+ Q&A scenarios
  - Practice with hostile mock judge
  - "Pause, breathe, answer" protocol
  - Admit uncertainty rather than fake
- **Owner:** Pitcher
- **Status:** Active

### R15 — Language barrier with international judges
- **Likelihood:** Medium
- **Impact:** Medium
- **Severity:** Medium
- **Mitigation:**
  - English subtitles in demo video
  - English tech terms where needed
  - Slides in English primary, key VN terms italicized
  - Pitcher comfortable switching languages
- **Owner:** Pitcher
- **Status:** Active

## Compliance risks

### R16 — Real PII accidentally used in demo
- **Likelihood:** Low
- **Impact:** High (legal, reputation)
- **Severity:** Medium
- **Mitigation:**
  - Use only template samples from thuvienphapluat.vn (public)
  - Anonymize any sample data
  - Mock VNeID login (no real data)
  - Team compliance check before recording
- **Owner:** Product lead
- **Status:** Active

### R17 — Misrepresenting Alibaba Cloud / Qwen capabilities
- **Likelihood:** Low
- **Impact:** Medium
- **Severity:** Low
- **Mitigation:**
  - Only claim what we actually use
  - Research references factual
  - "Production path" clearly labeled vs "current demo"
- **Owner:** Tech lead
- **Status:** Active

## Business risks (post-hackathon)

### R18 — No track winner
- **Likelihood:** Medium
- **Impact:** Low (still built real system)
- **Severity:** Low
- **Mitigation:**
  - System is production-ready regardless
  - Direct outreach to Shinhan even if not winner
  - Pivot to direct market entry
- **Owner:** Founder
- **Status:** Future

### R19 — Shinhan doesn't approve PoC funding
- **Likelihood:** Medium
- **Impact:** Medium
- **Severity:** Medium
- **Mitigation:**
  - Apply to other accelerators (GenAI Fund, Tasco CVC portfolio)
  - Founder capital to buy runway
  - Direct customer outreach for PoC without funding
- **Owner:** Founder
- **Status:** Future

## Risk monitoring

### Daily standup review
- Highest severity risks reviewed every morning
- Status updates: new/mitigating/resolved
- Any new risks discovered → add to register

### Risk owner responsibilities
- Track mitigation progress
- Escalate if cannot mitigate
- Document lessons learned

## Risk appetite

Team is willing to accept:
- **R2 (Gremlin LLM):** HIGH risk accepted because it's the core differentiator
- **R5 (Qwen rate limits):** MEDIUM risk accepted, has video fallback
- **R8 (scope creep):** MEDIUM risk accepted if feature directly serves judging criteria

Team is NOT willing to accept:
- **R12 (missing pitch):** MUST verify day 1
- **R16 (PII leak):** MUST be zero
- **Permission engine not working:** core differentiator, must work

## Contingency budget

Time buffer in schedule:
- **Day 16 evening:** buffer for critical bug fixes
- **Day 17 morning:** final fixes + polish
- **Day 20:** extra rehearsal day (not production work)

Scope buffer:
- If critical slip → defer in this order:
  1. Security Console polish (keep core, cut dashboard polish)
  2. Leadership Dashboard analytics (keep basic, cut AI Functions)
  3. 1–2 TTHCs edge cases (keep CPXD flagship deep)
  4. **NEVER cut:** agent trace viewer, 3 permission scenes, demo video
