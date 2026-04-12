# Verification Rubric — Self-score against judging criteria

## Target: ≥ 38/40

Before submission day 17, self-score GovFlow against the 4 judging criteria. Each criterion 10 points.

## Criterion 1 — Problem Relevance (target ≥ 10/10)

### Questions to verify

- [ ] **Scope is correct** — TTHC công, not just văn thư nội bộ (1 pt)
- [ ] **Cover all 8 future-state capabilities** from PDF page 5 (1 pt)
- [ ] **Cover 3 key challenges** from PDF page 3 (1 pt)
- [ ] **Cover 4 constraints** from PDF page 4 (1 pt)
- [ ] **Cover 3 impact areas** from PDF page 1 (1 pt)
- [ ] **Ghim vào Vietnamese legal framework** (NĐ 61, 107, 45, 30, 42, Đề án 06) (1 pt)
- [ ] **Ghim vào security framework** (Luật BVBMNN, ANM, BVDLCN) (1 pt)
- [ ] **Real Vietnamese TTHC examples** (5 flagship) (1 pt)
- [ ] **6 stakeholder personas** realistic + grounded (1 pt)
- [ ] **Demo 4-level classification** via 3 permission scenes (1 pt)

**Score: ___/10**

### Evidence for ≥ 10:
- Coverage Matrix in [`../02-solution/coverage-matrix.md`](../02-solution/coverage-matrix.md) shows 32/32 items
- 6 stakeholder analysis in [`../01-problem/painpoint-analysis.md`](../01-problem/painpoint-analysis.md)
- 9-law mapping in [`../06-compliance/legal-framework-mapping.md`](../06-compliance/legal-framework-mapping.md)
- Demo video includes Vietnamese regulatory references

---

## Criterion 2 — Solution Quality (target ≥ 9/10)

### Questions to verify

- [ ] **Graph-native architecture** implemented (not just claimed) (2 pts)
- [ ] **10 agents all working** end-to-end (2 pts)
- [ ] **3-tier permission engine** actually enforces (2 pts)
- [ ] **UI 8 screens polished** to "đẳng cấp hàng đầu" bar (2 pts)
- [ ] **Handles edge cases** (scan xấu, hồ sơ thiếu, confidence thấp, denials) (1 pt)
- [ ] **Benchmark data** on ≥ 25 real sample cases (1 pt)

**Score: ___/10**

### Evidence for ≥ 9:
- Architecture docs in [`../03-architecture/`](../03-architecture/)
- Agent catalog in [`../03-architecture/agent-catalog.md`](../03-architecture/agent-catalog.md)
- Permission engine in [`../03-architecture/permission-engine.md`](../03-architecture/permission-engine.md)
- Screen catalog in [`../04-ux/screen-catalog.md`](../04-ux/screen-catalog.md)
- Live demo + benchmark results

### Deductions possible:
- Missing 1–2 screens → -1
- Permission engine only 2 tiers → -1
- < 25 benchmark cases → -1
- UI not polished → -2

---

## Criterion 3 — Use of Qwen (target ≥ 10/10)

### Questions to verify

- [ ] **Qwen used in ≥ 7 distinct roles** (2 pts)
- [ ] **Qwen3-VL for multimodal** (not just text) (1 pt)
- [ ] **Qwen3-Max for reasoning** (agents, not prompts) (1 pt)
- [ ] **Qwen3-Embedding for vector search** (1 pt)
- [ ] **MCP integration** for tool exposure (1 pt)
- [ ] **Agentic GraphRAG** pattern visible (1 pt)
- [ ] **Function calling** with structured outputs (1 pt)
- [ ] **Hologres AI Functions** — Qwen called inline in SQL (1 pt)
- [ ] **Agent reasoning trace visible** in demo (1 pt)

**Score: ___/10**

### Evidence for ≥ 10:
- 8 roles documented in [`../02-solution/vision.md`](../02-solution/vision.md) + pitch slide 6
- MCP integration in [`../03-architecture/mcp-integration.md`](../03-architecture/mcp-integration.md)
- GraphRAG design in [`../03-architecture/graphrag-legal-reasoning.md`](../03-architecture/graphrag-legal-reasoning.md)
- Agent Trace Viewer shows live reasoning
- Hologres AI Functions demo during pitch

### Warnings:
- Simple wrapper → judge will catch, deduct heavily
- Claims not matching demo → worse than not claiming

---

## Criterion 4 — Execution & Demo (target ≥ 9/10)

### Questions to verify

- [ ] **Working prototype end-to-end** (2 pts)
- [ ] **5 TTHCs all processable** (1 pt)
- [ ] **Demo video 2:30 polished** (1 pt)
- [ ] **≥ 2 "wow moments"** in demo (1 pt)
- [ ] **Video backup** ready (1 pt)
- [ ] **Subtitles** VN + EN (0.5 pt)
- [ ] **Pitch timing** within limit (0.5 pt)
- [ ] **Q&A confidence** (1 pt)
- [ ] **Devpost submission complete** (1 pt)
- [ ] **Professional delivery** (1 pt)

**Score: ___/10**

### Evidence for ≥ 9:
- Demo video in repository
- Live demo URL accessible
- Rehearsal count ≥ 8
- Q&A prep in [`../07-pitch/qa-preparation.md`](../07-pitch/qa-preparation.md)

---

## Total score

**Minimum score for strong submission:** 32/40
**Target score:** 38/40
**Maximum possible:** 40/40

**Track record:** AI Build Day track winners typically score 34–38 per public reports.

## Rehearsal test

**Protocol:**
1. 3 people who haven't seen the pitch
2. 1 technical, 1 business, 1 non-technical
3. Play pitch + demo video
4. Ask them to describe in their own words: "What is GovFlow?"

**Pass criteria:** All 3 can explain core idea + 2 differentiators

**If fail:** rewrite hook + big idea, simplify language

## Demo stress test — day 16

- [ ] Run 25 test cases (5 per TTHC) back-to-back
- [ ] Measure: success rate, latency p50/p95, errors
- [ ] Run 5 permission scenarios (all should reject correctly)
- [ ] Run 3 edge cases: very poor scan, missing 2 docs, contradicting entities
- [ ] Record backup video of each scenario
- [ ] Create "restore state" script to reset between demos

**Gates:**
- Success rate ≥ 90% → go
- Success rate 70–89% → fix critical issues, retest
- Success rate < 70% → stop, reassess scope

## Submission checklist

Day 17 before deadline:

- [ ] Devpost submission form filled
- [ ] Project title: "GovFlow — Agentic GraphRAG for Vietnam Public Services"
- [ ] Description 150 words
- [ ] Track: Public Sector (Government)
- [ ] GitHub repo link (code + README)
- [ ] Demo video link (YouTube unlisted or Vimeo)
- [ ] Screenshots (3–5 best screens)
- [ ] Architecture diagram
- [ ] Team members listed
- [ ] Contact info accurate
- [ ] Tested — submission page loads correctly

## Day-of pitch checklist

Day 21/04:
- [ ] Arrive 45 min early
- [ ] Laptop charged + backup battery
- [ ] Demo video on laptop + USB backup
- [ ] Deck on laptop + PDF backup
- [ ] Presenter remote (if using)
- [ ] Water bottle
- [ ] Business cards (if available)
- [ ] Confident outfit
- [ ] Deep breaths before going on
- [ ] **Smile at judges**

## Red flags — stop and review

If any of these happen during build week, pause and review:

- 🚨 Demo fails 3× in a row during testing
- 🚨 Critical feature not working day 16
- 🚨 Team member burns out / leaves
- 🚨 Permission engine has major hole found day 15
- 🚨 Cannot pitch at venue (logistics failure)
- 🚨 Qwen API access blocked

Escalate to team lead immediately.

## Final word

Target: **track winner + Shinhan InnoBoost PoC funding approved.**

Plan B: even if not winner, we ship a real product that can be deployed for a customer PoC. That's still a win.

**Confidence = preparation + execution + calm delivery.**

Rehearse. Prepare. Deliver. Breathe.
