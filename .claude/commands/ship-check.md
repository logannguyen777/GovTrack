You are the pre-submission gatekeeper for GovFlow. Run every quality gate and produce a SUBMISSION_READY.md report.

## Gates (run sequentially, collect all results)

```bash
cd /home/logan/GovTrack

# 1. Backend lint
cd backend && ruff check src/ && echo "BACKEND_LINT=OK"

# 2. Backend type
cd backend && mypy src/ --ignore-missing-imports && echo "BACKEND_TYPE=OK"

# 3. Backend tests (excluding slow/dashscope/benchmark)
cd backend && pytest -m "not slow and not requires_dashscope and not benchmark" -q && echo "BACKEND_TEST=OK"

# 4. Frontend type
cd frontend && npx tsc --noEmit && echo "FRONTEND_TYPE=OK"

# 5. Frontend lint
cd frontend && npm run lint && echo "FRONTEND_LINT=OK"

# 6. Frontend build
cd frontend && npm run build && echo "FRONTEND_BUILD=OK"

# 7. Playwright smoke (5 fastest tests)
cd frontend && npx playwright test tests/smoke.spec.ts --reporter=list && echo "SMOKE=OK"

# 8. Demo healthcheck (services up, seed applied)
bash scripts/demo_healthcheck.sh && echo "HEALTHCHECK=OK"

# 9. Secret scan
cd /home/logan/GovTrack && command -v gitleaks && gitleaks detect --source . --no-banner --redact && echo "SECRETS=OK" || echo "SECRETS=SKIPPED"

# 10. Git status check (no uncommitted secrets/large files)
cd /home/logan/GovTrack && git status --short | grep -E "\.env$|\.key$|\.pem$" && echo "GIT_CHECK=FAIL" || echo "GIT_CHECK=OK"
```

## Output

Write `/home/logan/GovTrack/SUBMISSION_READY.md`:

```markdown
# GovFlow — Submission Readiness Report

Generated: <ISO timestamp>
Target: Qwen AI Build Day 2026 (submit 17/04/2026)

## Gate results

| # | Gate | Status |
|---|---|---|
| 1 | Backend lint (ruff) | ✅ / ❌ |
| 2 | Backend type (mypy) | ✅ / ❌ |
| 3 | Backend tests (pytest) | ✅ N passed, M skipped |
| 4 | Frontend type (tsc) | ✅ / ❌ |
| 5 | Frontend lint (eslint) | ✅ / ❌ |
| 6 | Frontend build (next build) | ✅ / ❌ |
| 7 | Playwright smoke | ✅ / ❌ |
| 8 | Demo healthcheck | ✅ / ❌ |
| 9 | Secret scan | ✅ / ⚠️ skipped |
| 10 | Git status | ✅ / ❌ |

## Test counts
- Backend: <N> pytest cases
- Frontend: <N> Playwright cases
- Last stress run: <25/25> at <timestamp> (from scripts/benchmark_results.csv)

## Open risks
- <bullet list of anything not green, with the command to rerun>

## Next steps
- [ ] Record demo video (out of scope for QA sweep)
- [ ] Prepare subtitles VN+EN
- [ ] Commit & tag v1.0-qwen-submit
```

If every gate is ✅, end with "**READY TO SUBMIT**". Otherwise end with "**NOT READY — fix items above**" + the exact commands to fix.

## Important
- Do NOT commit or tag automatically. User decides.
- Do NOT skip gates. If a command is not installed (e.g., gitleaks), mark SKIPPED with a note.
- If a gate fails, do NOT dispatch sub-agent to fix — just report. User decides the next /qa-sweep.