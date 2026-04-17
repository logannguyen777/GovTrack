#!/usr/bin/env bash
# Reset the demo environment to a clean state.
#   1. Drop all GDB vertices
#   2. Truncate analytics + audit + notification tables (keeps users, law_chunks,
#      templates_nd30 intact — those are infra seed, not demo state)
#   3. Re-seed demo data
#
# Usage:
#   ./scripts/reset_demo.sh
#
# Env:
#   HOLOGRES_DSN  (default: postgresql://govflow:govflow_dev_2026@localhost:5433/govflow)
set -euo pipefail

cd "$(dirname "$0")/.."

DSN="${HOLOGRES_DSN:-postgresql://govflow:govflow_dev_2026@localhost:5433/govflow}"
PY="${PYTHON:-backend/.venv/bin/python}"

if [ ! -x "$PY" ]; then
  PY=python
fi

echo "[reset] clearing GDB vertices..."
"$PY" <<'PYEOF'
import sys
sys.path.insert(0, "backend")
from src.database import (
    create_gremlin_client, close_gremlin_client, gremlin_submit,
)
create_gremlin_client()
try:
    gremlin_submit("g.V().drop().iterate()")
    remaining = gremlin_submit("g.V().count()")
    print(f"[reset]   vertices remaining: {remaining[0] if remaining else '?'}")
finally:
    close_gremlin_client()
PYEOF

echo "[reset] truncating analytics + audit + notification tables..."
if command -v psql >/dev/null 2>&1; then
  psql "$DSN" -v ON_ERROR_STOP=1 -c "
TRUNCATE analytics_cases, analytics_agents, audit_events_flat, notifications CASCADE;
" >/dev/null
else
  DSN="$DSN" "$PY" - <<'PYEOF'
import asyncio, os, asyncpg
async def main():
    conn = await asyncpg.connect(dsn=os.environ["DSN"])
    await conn.execute(
        "TRUNCATE analytics_cases, analytics_agents, audit_events_flat, notifications CASCADE"
    )
    await conn.close()
asyncio.run(main())
PYEOF
fi

echo "[reset] re-seeding demo data..."
"$PY" scripts/seed_demo.py

echo "[reset] done."
