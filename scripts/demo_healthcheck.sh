#!/usr/bin/env bash
# Pre-demo health check.
# Verifies: backend :8100, frontend :3100, Gremlin :8182, Postgres, cache entry
# count, analytics_cases row count, and new AI assistant / document endpoints.
#
# Usage:
#   ./scripts/demo_healthcheck.sh
# Exits non-zero if any check fails.
set -u

cd "$(dirname "$0")/.."

DSN="${HOLOGRES_DSN:-postgresql://govflow:govflow_dev_2026@localhost:5433/govflow}"
CACHE_DIR="${DEMO_CACHE_DIR:-.cache/llm_responses}"

RC=0
ok()  { echo "[OK]   $1"; }
warn(){ echo "[WARN] $1"; }
bad() { echo "[FAIL] $1"; RC=1; }

# --- Services ---
if curl -sf http://localhost:8100/health >/dev/null 2>&1; then
  ok "Backend  :8100"
else
  bad "Backend  :8100 — is uvicorn running?"
fi

if curl -sf http://localhost:3100 >/dev/null 2>&1; then
  ok "Frontend :3100"
else
  warn "Frontend :3100 — is npm run dev running? (not fatal for scenarios)"
fi

if (exec 3<>/dev/tcp/localhost/8182) 2>/dev/null; then
  exec 3<&- 3>&-
  ok "Gremlin  :8182"
else
  bad "Gremlin  :8182 — docker compose up?"
fi

PY="${PYTHON:-backend/.venv/bin/python}"
[ -x "$PY" ] || PY=python

# Postgres check — prefer psql if available, else fall back to asyncpg
if command -v psql >/dev/null 2>&1 && psql "$DSN" -c "SELECT 1" >/dev/null 2>&1; then
  ok "Postgres :5433"
elif "$PY" - <<PYEOF >/dev/null 2>&1
import asyncio, os
import asyncpg
async def check():
    conn = await asyncpg.connect(dsn=os.environ["DSN"])
    await conn.fetchval("SELECT 1"); await conn.close()
asyncio.run(check())
PYEOF
then
  ok "Postgres :5433"
else
  bad "Postgres :5433 — check DSN $DSN"
fi

# --- Data ---
CACHE_COUNT=0
if [ -d "$CACHE_DIR" ]; then
  CACHE_COUNT=$(find "$CACHE_DIR" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
fi
echo "[INFO] LLM cache entries: $CACHE_COUNT  (dir: $CACHE_DIR)"
if [ "${CACHE_COUNT:-0}" -ge 15 ]; then
  ok "LLM cache"
else
  warn "LLM cache (<15) — run: python scripts/warm_cache.py"
fi

if command -v psql >/dev/null 2>&1; then
  CASE_COUNT=$(psql "$DSN" -tAc "SELECT count(*) FROM analytics_cases" 2>/dev/null | tr -d ' ' || echo 0)
else
  CASE_COUNT=$( "$PY" - <<'PYEOF' 2>/dev/null || echo 0
import asyncio, os
import asyncpg
async def q():
    conn = await asyncpg.connect(dsn=os.environ["DSN"])
    n = await conn.fetchval("SELECT count(*) FROM analytics_cases")
    await conn.close(); print(n)
asyncio.run(q())
PYEOF
  )
fi
CASE_COUNT="${CASE_COUNT:-0}"
echo "[INFO] analytics_cases rows: $CASE_COUNT"
if [ "$CASE_COUNT" -ge 5 ]; then
  ok "Seed data"
else
  bad "Seed data (<5) — run: python scripts/seed_demo.py"
fi

# --- GDB data ---
GDB_V=$( (
  PY="${PYTHON:-backend/.venv/bin/python}"
  [ -x "$PY" ] || PY=python
  "$PY" <<'PYEOF' 2>/dev/null
import sys
sys.path.insert(0, "backend")
from src.database import create_gremlin_client, close_gremlin_client, gremlin_submit
create_gremlin_client()
try:
    r = gremlin_submit("g.V().count()")
    print(r[0] if r else 0)
finally:
    close_gremlin_client()
PYEOF
) || echo 0 )
GDB_V="${GDB_V:-0}"
echo "[INFO] GDB vertex count: $GDB_V"
if [ "$GDB_V" -ge 5 ]; then
  ok "GDB vertices"
else
  warn "GDB vertices (<5) — run: python scripts/seed_demo.py"
fi

# --- New AI assistant endpoints ---

echo "[INFO] Checking /api/public/tthc..."
TTHC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8100/api/public/tthc 2>/dev/null || echo 0)
if [ "$TTHC_STATUS" = "200" ]; then
  ok "/api/public/tthc"
else
  warn "/api/public/tthc => HTTP $TTHC_STATUS (backend may be starting)"
fi

echo "[INFO] Checking /api/assistant/intent (POST)..."
INTENT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8100/api/assistant/intent \
  -H "Content-Type: application/json" \
  -d '{"text":"Tôi muốn xin giấy phép xây dựng"}' \
  2>/dev/null || echo 0)
if [ "$INTENT_STATUS" = "200" ]; then
  ok "/api/assistant/intent"
elif [ "$INTENT_STATUS" = "422" ]; then
  warn "/api/assistant/intent => 422 (schema mismatch — check request body)"
else
  warn "/api/assistant/intent => HTTP $INTENT_STATUS"
fi

echo "[INFO] Checking /api/assistant/chat SSE (5 lines)..."
CHAT_OUTPUT=$(curl -s -N -X POST http://localhost:8100/api/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Xin chào","context":{"type":"portal"}}' \
  --max-time 10 2>/dev/null | head -5 || echo "")
if echo "$CHAT_OUTPUT" | grep -q "data:"; then
  ok "/api/assistant/chat SSE"
else
  warn "/api/assistant/chat SSE — no data: lines in first 5 lines"
fi

echo "[INFO] Checking /api/documents/extract endpoint exists..."
EXTRACT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8100/api/documents/extract \
  -F "file_url=https://example.com/sample.jpg" \
  2>/dev/null || echo 0)
if [ "$EXTRACT_STATUS" = "200" ] || [ "$EXTRACT_STATUS" = "422" ]; then
  ok "/api/documents/extract (route exists, HTTP $EXTRACT_STATUS)"
else
  warn "/api/documents/extract => HTTP $EXTRACT_STATUS"
fi

# --- Frontend key pages ---
if curl -sf http://localhost:3100 >/dev/null 2>&1; then
  PORTAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3100/portal 2>/dev/null || echo 0)
  DASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3100/dashboard 2>/dev/null || echo 0)
  echo "[INFO] Frontend /portal => HTTP $PORTAL_STATUS"
  echo "[INFO] Frontend /dashboard => HTTP $DASH_STATUS"
  if [ "$PORTAL_STATUS" = "200" ] || [ "$PORTAL_STATUS" = "307" ]; then
    ok "Frontend /portal"
  else
    warn "Frontend /portal => $PORTAL_STATUS"
  fi
fi

echo
[ $RC -eq 0 ] && echo "[healthcheck] READY" || echo "[healthcheck] FAILED — see above"
exit $RC
