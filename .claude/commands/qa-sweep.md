You are orchestrating a full QA sweep of GovFlow before hackathon submission. Spawn 4 specialized sub-agents in parallel, collect their diffs, then validate with lint + type + smoke tests.

## Workflow

### Phase 1 — Parallel auto-fix (spawn all 4 in ONE message with multiple Agent tool calls)

1. **ux-polish-agent** — add quick-fill buttons for intake/dashboard/compliance + 6-state audit + real-time form validation
2. **stub-completer-agent** — complete Compliance workspace split view + KG Explorer + de-hardcode TTHC_NAMES
3. **resilience-agent** — GDB circuit breaker + Hologres asyncpg retry + timeout envelope + HTTP error mapping
4. **agent-stub-filler** — fill build_messages for summarizer/drafter/consult

### Phase 2 — Validate (sequential, after all 4 agents return)

Run in this order, stop on first failure and delegate back to the responsible agent:

```bash
cd /home/logan/GovTrack/backend && ruff check src/
cd /home/logan/GovTrack/backend && mypy src/ --ignore-missing-imports || true   # non-blocking
cd /home/logan/GovTrack/frontend && npx tsc --noEmit
cd /home/logan/GovTrack/frontend && npm run lint
cd /home/logan/GovTrack/backend && pytest -m "not slow and not requires_dashscope and not benchmark" -q
cd /home/logan/GovTrack/frontend && npx playwright test tests/smoke.spec.ts --reporter=list
```

### Phase 3 — Summary

Print a table to the user:

| Agent | Files touched | Status |
|---|---|---|
| ux-polish | N | ✓ |
| stub-completer | N | ✓ |
| resilience | N | ✓ |
| agent-stub-filler | N | ✓ |

Followed by: "Run `/stress-demo` to stress-test 25 cases, then `/ship-check` for pre-submit verification."

## Critical instructions

- Spawn all 4 agents in ONE message (parallel Task calls). Do NOT serialize.
- Each agent has Edit/Write permission — they auto-apply, you do not relay diffs manually
- If Phase 2 fails, re-dispatch to the offending agent with the error output
- Do NOT commit — leave staging clean for user review

## Arguments
$ARGUMENTS — optional scope filter: "ux" | "backend" | "all" (default "all"). Skip agents outside scope.