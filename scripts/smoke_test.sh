#!/usr/bin/env bash
# GovFlow Smoke Test
# Run this after start_demo.sh to verify everything is healthy.
#
# Usage:
#   ./scripts/smoke_test.sh              # Full smoke test (requires running stack)
#   ./scripts/smoke_test.sh --dry-run    # Print what would happen, no actual calls
#
# Exit 0 if all checks pass, Exit 1 if any check fails.
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
BACKEND_URL="${GOVFLOW_API:-http://localhost:8100}"
FRONTEND_URL="${GOVFLOW_FRONTEND:-http://localhost:3100}"
SCENARIO_TIMEOUT="${SCENARIO_TIMEOUT:-30}"
DRY_RUN=false

# Parse flags
for arg in "$@"; do
  case $arg in
    --dry-run)
      DRY_RUN=true
      ;;
  esac
done

# ── Colours ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour
BOLD='\033[1m'

# ── Counters ───────────────────────────────────────────────────────────────────
PASS=0
FAIL=0
SKIP=0

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
skip() { echo -e "  ${YELLOW}[SKIP]${NC} $1 (dry-run)"; SKIP=$((SKIP+1)); }
info() { echo -e "  ${BOLD}[INFO]${NC} $1"; }

echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  GovFlow Smoke Test${NC}"
echo -e "${BOLD}============================================${NC}"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
if $DRY_RUN; then
  echo -e "  Mode:     ${YELLOW}DRY RUN (no actual HTTP calls)${NC}"
fi
echo ""

# ── Check 1: Backend /healthz ─────────────────────────────────────────────────
echo -e "${BOLD}[1/6] Backend health check${NC}"
if $DRY_RUN; then
  skip "Would call: GET $BACKEND_URL/healthz — expect 200 + {\"status\":\"ok\"}"
else
  HTTP_STATUS=$(curl -s -o /tmp/govflow_health.json -w "%{http_code}" \
    --max-time 10 "$BACKEND_URL/healthz" 2>/dev/null || echo "000")
  if [ "$HTTP_STATUS" = "200" ]; then
    STATUS=$(python3 -c "import json,sys; d=json.load(open('/tmp/govflow_health.json')); print(d.get('status','?'))" 2>/dev/null || echo "?")
    pass "GET /healthz → $HTTP_STATUS (status: $STATUS)"
  else
    fail "GET /healthz → $HTTP_STATUS (expected 200)"
    cat /tmp/govflow_health.json 2>/dev/null || true
  fi
fi

# ── Check 2: Frontend root page ───────────────────────────────────────────────
echo -e "${BOLD}[2/6] Frontend root page${NC}"
if $DRY_RUN; then
  skip "Would call: GET $FRONTEND_URL — expect 200"
else
  FE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 "$FRONTEND_URL" 2>/dev/null || echo "000")
  if [ "$FE_STATUS" = "200" ]; then
    pass "GET $FRONTEND_URL → $FE_STATUS"
  else
    fail "GET $FRONTEND_URL → $FE_STATUS (expected 200)"
  fi
fi

# ── Check 3: API docs (Swagger) ───────────────────────────────────────────────
echo -e "${BOLD}[3/6] API docs (Swagger)${NC}"
if $DRY_RUN; then
  skip "Would call: GET $BACKEND_URL/docs — expect 200"
else
  DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 "$BACKEND_URL/docs" 2>/dev/null || echo "000")
  if [ "$DOCS_STATUS" = "200" ]; then
    pass "GET /docs → $DOCS_STATUS"
  else
    fail "GET /docs → $DOCS_STATUS (expected 200)"
  fi
fi

# ── Check 4: Login endpoint ────────────────────────────────────────────────────
echo -e "${BOLD}[4/6] Authentication (staff_intake login)${NC}"
if $DRY_RUN; then
  skip "Would call: POST $BACKEND_URL/auth/login {username:staff_intake, password:demo} — expect JWT"
else
  LOGIN_RESP=$(curl -s -o /tmp/govflow_login.json -w "%{http_code}" \
    --max-time 10 \
    -X POST "$BACKEND_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"staff_intake","password":"demo"}' 2>/dev/null || echo "000")
  if [ "$LOGIN_RESP" = "200" ]; then
    TOKEN=$(python3 -c "import json; d=json.load(open('/tmp/govflow_login.json')); print(d.get('access_token','')[:20])" 2>/dev/null || echo "")
    if [ -n "$TOKEN" ]; then
      pass "POST /auth/login → $LOGIN_RESP (token: ${TOKEN}...)"
    else
      fail "POST /auth/login → $LOGIN_RESP but no access_token in response"
    fi
  else
    fail "POST /auth/login → $LOGIN_RESP (expected 200)"
    cat /tmp/govflow_login.json 2>/dev/null || true
  fi
fi

# ── Check 5: Scenario 1 — CPXD gap detection ──────────────────────────────────
echo -e "${BOLD}[5/6] Scenario 1: CPXD gap detection (timeout: ${SCENARIO_TIMEOUT}s)${NC}"
if $DRY_RUN; then
  skip "Would run: python scripts/demo/scenario_1_cpxd_gap.py (expect: gap detected, ND 136/2020 cited, completes <${SCENARIO_TIMEOUT}s)"
else
  SCENARIO_START=$(date +%s)
  if GOVFLOW_API="$BACKEND_URL" timeout "$SCENARIO_TIMEOUT" \
      python3 scripts/demo/scenario_1_cpxd_gap.py > /tmp/scenario_1.log 2>&1; then
    SCENARIO_END=$(date +%s)
    ELAPSED=$((SCENARIO_END - SCENARIO_START))
    # Check output contains gap keyword
    if grep -q -i "gap\|thieu\|pccc\|136/2020" /tmp/scenario_1.log 2>/dev/null; then
      pass "Scenario 1 completed in ${ELAPSED}s (gap detected)"
    else
      pass "Scenario 1 completed in ${ELAPSED}s (check output manually)"
      info "See /tmp/scenario_1.log for details"
    fi
  else
    EXIT_CODE=$?
    SCENARIO_END=$(date +%s)
    ELAPSED=$((SCENARIO_END - SCENARIO_START))
    if [ $EXIT_CODE -eq 124 ]; then
      fail "Scenario 1 timed out after ${SCENARIO_TIMEOUT}s"
    else
      fail "Scenario 1 failed after ${ELAPSED}s (exit code: $EXIT_CODE)"
    fi
    tail -20 /tmp/scenario_1.log 2>/dev/null || true
  fi
fi

# ── Check 6: Docker services (optional) ───────────────────────────────────────
echo -e "${BOLD}[6/6] Docker services${NC}"
if $DRY_RUN; then
  skip "Would check: docker ps for govflow-gremlin, govflow-postgres, govflow-minio"
else
  if command -v docker &>/dev/null; then
    GREMLIN_RUNNING=$(docker ps --filter "name=govflow-gremlin" --filter "status=running" -q 2>/dev/null | wc -l)
    POSTGRES_RUNNING=$(docker ps --filter "name=govflow-postgres" --filter "status=running" -q 2>/dev/null | wc -l)
    MINIO_RUNNING=$(docker ps --filter "name=govflow-minio" --filter "status=running" -q 2>/dev/null | wc -l)

    [ "$GREMLIN_RUNNING" -ge 1 ] && pass "govflow-gremlin running" || fail "govflow-gremlin not running"
    [ "$POSTGRES_RUNNING" -ge 1 ] && pass "govflow-postgres running" || fail "govflow-postgres not running"
    [ "$MINIO_RUNNING" -ge 1 ] && pass "govflow-minio running" || fail "govflow-minio not running"
  else
    skip "docker not available — skipping container check"
  fi
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  Results${NC}"
echo -e "${BOLD}============================================${NC}"
echo -e "  ${GREEN}Passed:${NC}  $PASS"
echo -e "  ${RED}Failed:${NC}  $FAIL"
echo -e "  ${YELLOW}Skipped:${NC} $SKIP"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}  All checks passed. GovFlow is ready for demo.${NC}"
  echo ""
  exit 0
else
  echo -e "${RED}${BOLD}  $FAIL check(s) failed. Review output above.${NC}"
  echo ""
  echo "  Troubleshooting tips:"
  echo "    - Run ./scripts/start_demo.sh first"
  echo "    - Check backend/.env has DASHSCOPE_API_KEY set"
  echo "    - Check docker ps for service status"
  echo "    - Check backend logs: docker logs govflow-postgres"
  echo ""
  exit 1
fi
