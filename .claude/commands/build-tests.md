You are writing tests for GovFlow. Follow docs/implementation/18-integration-testing.md as the detailed guide.

Task: $ARGUMENTS (scope: e2e, permission, agent, frontend, benchmark, or "all")

## Test Infrastructure

- **Backend**: pytest-asyncio, TinkerGraph in-memory for GDB, SQLite for Hologres (CI fallback)
- **Frontend**: Playwright for E2E, Vitest for component tests
- **Fixtures**: conftest.py with gdb_client (TinkerGraph), hologres_session (SQLite), oss_client (mock), seeded KG data

## Test Categories

### E2E Happy Path (`backend/tests/tthc/`)
5 tests, one per TTHC:

1. **test_cpxd.py**: Submit 5 docs missing PCCC -> Planner -> DocAnalyzer -> Classifier (1.004415) -> Compliance detects PCCC gap -> LegalLookup returns ND 136/2020 Dieu 13.2.b -> Drafter creates citizen notice
2. **test_gcn_qsdd.py**: Submit land bundle -> classify (1.000046) -> route to So TN&MT -> certificate draft
3. **test_dkkd.py**: Submit business docs -> classify (1.001757) -> compliance OK -> route -> GCN DKDN draft
4. **test_lltp.py**: Submit criminal record request -> classify (1.000122) -> route to So Tu phap -> extract
5. **test_gpmt.py**: Submit environmental bundle -> classify (2.002154) -> environmental check -> route

Each test: submit case via API -> wait for orchestrator -> verify GDB has correct vertices/edges.

### Permission Negative (`backend/tests/unit/test_permissions.py`)
20+ scenarios from docs/03-architecture/permission-engine.md:
- SDK Guard read denials (wrong label access)
- SDK Guard write denials (wrong write scope)
- Property Mask redaction at each clearance level
- SecurityOfficer allowed full access
- Each denial produces AuditEvent with correct tier

### Agent Accuracy (`backend/tests/unit/test_agents.py`)
Per agent: 3-5 test inputs with mock DashScope responses, verify:
- Correct vertex/edge types written to graph
- No SDK Guard violations for normal operations
- Confidence thresholds respected

### Latency Benchmark (`scripts/benchmark.py`)
- 25 cases (5 per TTHC)
- Measure: p50/p95 latency per agent, total pipeline time
- Measure: token usage per agent
- Output: CSV + summary table

### Frontend Smoke (`frontend/e2e/`)
Playwright tests for 8 screens:
- citizen-portal.spec.ts: navigate, search TTHC, view tracking page
- agent-trace.spec.ts: open trace viewer, verify graph renders
- permission-demo.spec.ts: trigger 3 scenes, verify UI reactions
- dashboard.spec.ts: verify charts render with data

### Demo Reliability
Run exact demo scenario 5x consecutive -> 100% pass rate required.

## Conventions
- Use pytest markers: @pytest.mark.e2e, @pytest.mark.permission, @pytest.mark.agent
- Mock DashScope in unit tests (no real API calls)
- Integration tests may call real DashScope (mark with @pytest.mark.integration)
- Frontend tests: use data-testid attributes for selectors

## Accuracy Targets
- Classification: > 80% correct TTHC code
- Compliance gap detection: > 90% correct gaps
- Legal citation: > 85% correct article reference
- Demo reliability: 100% pass rate (5/5 runs)

## Verification
```bash
cd backend && pytest tests/unit/ -v --tb=short
cd backend && pytest tests/tthc/ -v --tb=short  # Requires running infra
cd backend && pytest tests/unit/test_permissions.py -v  # 20+ scenarios
cd frontend && npx playwright test
python scripts/benchmark.py --output results.csv
```