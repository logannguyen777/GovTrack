#!/usr/bin/env bash
# Start the full GovFlow demo stack.
#   - Brings up docker compose (Gremlin, Postgres, MinIO)
#   - Waits for Postgres + Gremlin to be ready
#   - Resets + seeds demo data
#   - Optionally pre-warms the LLM + embedding cache (--warm / WARM_CACHE=1)
#   - Launches backend (:8100) and frontend (:3100)
#
# Usage:
#   ./scripts/start_demo.sh              # default — cold start (no cache warm)
#   ./scripts/start_demo.sh --warm       # warm cache before starting (recommended for judges)
#   WARM_CACHE=1 ./scripts/start_demo.sh # same as --warm via env var
#
# Why --warm is opt-in
# --------------------
# Cold start is the default so the demo pipeline is exercised end-to-end and
# real DashScope round-trips are visible in the trace UI. Judges who want
# snappier (<3 s) first-run responses should pass --warm; this pre-populates
# the LLM + embedding cache so subsequent scenario runs hit cache instead of
# going to DashScope live.
#
# Env overrides:
#   WARM_CACHE=1                    # equivalent to --warm flag
#   WARM_SCENARIO=N                 # restrict warm to scenario N (1–6)
#   DEMO_CACHE_OFFLINE_ONLY=true    # fail on cache miss (pure offline mode)
#   SKIP_FRONTEND=1                 # only start the backend
set -euo pipefail

cd "$(dirname "$0")/.."

export DEMO_MODE="${DEMO_MODE:-true}"
export DEMO_CACHE_ENABLED="${DEMO_CACHE_ENABLED:-true}"
export DEMO_CACHE_OFFLINE_ONLY="${DEMO_CACHE_OFFLINE_ONLY:-false}"

# Parse --warm flag
DO_WARM="${WARM_CACHE:-0}"
WARM_SCENARIO_ARG=""
for arg in "$@"; do
  case "$arg" in
    --warm) DO_WARM=1 ;;
    --scenario=*) WARM_SCENARIO_ARG="${arg#--scenario=}" ;;
  esac
done

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "[demo] stopping..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[demo] bringing infra up..."
(cd infra && docker compose up -d)

echo "[demo] waiting for Postgres on :5433..."
for i in $(seq 1 30); do
  if docker exec govflow-postgres pg_isready -U govflow -d govflow >/dev/null 2>&1; then
    echo "[demo]   Postgres ready"
    break
  fi
  sleep 1
done

echo "[demo] waiting for Gremlin on :8182..."
for i in $(seq 1 30); do
  if (exec 3<>/dev/tcp/localhost/8182) 2>/dev/null; then
    exec 3<&- 3>&-
    echo "[demo]   Gremlin ready"
    break
  fi
  sleep 1
done

echo "[demo] reset + seed..."
./scripts/reset_demo.sh

# ── Optional cache warm (requires DASHSCOPE_API_KEY) ─────────────────────
if [ "$DO_WARM" = "1" ]; then
  if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
    echo "[demo] WARN: WARM_CACHE=1 requested but DASHSCOPE_API_KEY is not set — skipping warm."
  else
    echo "[demo] warming LLM + embedding cache (this may take ~60 s)..."
    SCENARIO_FLAG=""
    [ -n "$WARM_SCENARIO_ARG" ] && SCENARIO_FLAG="--scenario $WARM_SCENARIO_ARG"
    # Activate the backend venv if present so warm_cache.py can import src.*
    (
      cd backend
      # shellcheck source=/dev/null
      [ -f .venv/bin/activate ] && source .venv/bin/activate
      cd ..
      python scripts/warm_cache.py $SCENARIO_FLAG
    ) && echo "[demo]   Cache warm complete." \
      || echo "[demo]   WARN: cache warm exited non-zero — continuing anyway."
  fi
fi

echo "[demo] starting backend on :8100..."
(
  cd backend
  # shellcheck source=/dev/null
  [ -f .venv/bin/activate ] && source .venv/bin/activate
  DEMO_MODE="$DEMO_MODE" \
    DEMO_CACHE_ENABLED="$DEMO_CACHE_ENABLED" \
    DEMO_CACHE_OFFLINE_ONLY="$DEMO_CACHE_OFFLINE_ONLY" \
    uvicorn src.main:app --host 0.0.0.0 --port 8100 --reload
) &
BACKEND_PID=$!

sleep 3

if [ "${SKIP_FRONTEND:-0}" != "1" ]; then
  echo "[demo] starting frontend on :3100..."
  (cd frontend && npm run dev) &
  FRONTEND_PID=$!
fi

cat <<EOF

============================================
  GovFlow Demo Ready
============================================
  Frontend:  http://localhost:3100
  Backend:   http://localhost:8100
  API docs:  http://localhost:8100/docs
  Gremlin:   ws://localhost:8182
  MinIO:     http://localhost:9101 (minioadmin/minioadmin123)
============================================

Demo users (password: "demo"):
  citizen_demo      — Citizen Portal
  staff_intake      — Intake UI / Compliance
  cv_qldt           — Officer workspace
  ld_phong          — Leadership Dashboard
  legal_expert      — Legal review
  security_officer  — Security Console
  admin             — Full access

Cache warm tip:
  First-run cold-start: ~30 s   (real DashScope calls, visible in trace UI)
  After cache warm:     <3 s    (cache hits, same UX)
  To pre-warm:  ./scripts/start_demo.sh --warm
                WARM_CACHE=1 ./scripts/start_demo.sh
                python scripts/warm_cache.py --dry-run   (preview only)

Press Ctrl+C to stop.
EOF

wait
