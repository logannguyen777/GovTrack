You are running GovFlow's 25-case stress matrix to verify demo reliability.

## Workflow

1. Invoke `e2e-stress-agent` via Task tool: "Generate or update frontend/tests/stress-matrix.spec.ts with 5 TTHC × 5 variant = 25 Playwright tests. Run the matrix, log results to scripts/benchmark_results.csv. Retry failures once."

2. Parse the agent's report. If 25/25 passed on first attempt → DONE, print summary.

3. If any failed after retry → invoke `frontend-engineer` via Task with the failing test name + stacktrace + this instruction: "Fix the minimum code needed to make this Playwright test pass. Do NOT modify the test itself — fix the product code. If the test is wrong, report that back."

4. Re-run stress-demo (loop at most 2 times). If still failing after 2 loops → stop, surface the blocker to user.

5. Final summary:

```
Stress matrix results (2026-04-16T14:00Z)
  Total: 25
  Passed: 25
  Flaky: 0
  Failed: 0
  CSV: scripts/benchmark_results.csv
```

## Pre-flight

Before invoking the agent, verify:
```bash
curl -fs localhost:3100/api/health && echo "frontend up"
curl -fs localhost:8100/health && echo "backend up"
```

If servers not up, start them via `bash /home/logan/GovTrack/scripts/start_demo.sh` in background, wait 15s, recheck.

## Out of scope
- Modifying non-test files to force green (delegate to frontend-engineer / backend-engineer)
- Changing playwright.config.ts retry count