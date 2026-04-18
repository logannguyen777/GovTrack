#!/bin/bash
# Idempotent full re-seed for production demo.
# Run inside backend container OR via `docker exec` when GDB (TinkerGraph, in-memory)
# has been wiped by a container recreate.
#
# Usage (from host):
#   docker cp scripts/ govflow-prod-backend-1:/app/scripts
#   docker cp data/   govflow-prod-backend-1:/app/data
#   docker exec -w /app -e PYTHONPATH=/app govflow-prod-backend-1 bash scripts/full_reseed.sh
set -e

cd /app

echo "[1/9] GDB schema..."
python scripts/create_gdb_schema.py 2>&1 | tail -2

echo "[2/9] Legal KG (10688 verts)..."
python scripts/load_kg_legal.py 2>&1 | tail -2

echo "[3/9] TTHC KG (5 specs + 27 required components)..."
python scripts/load_kg_tthc.py 2>&1 | tail -3

echo "[4/9] Organizations..."
python scripts/seed_organizations.py 2>&1 | tail -2

echo "[5/9] Users..."
python scripts/seed_users.py 2>&1 | tail -2

echo "[6/9] Demo cases (5)..."
python scripts/seed_demo.py 2>&1 | tail -2

echo "[7/9] Stable doc IDs (DOC-001..DOC-041)..."
python /app/scripts/demo_seed/reseed_stable_docs.py 2>&1 | tail -3

echo "[8/9] Happy case documents (link required per TTHC)..."
python /app/scripts/demo_seed/seed_happy.py 2>&1 | tail -2

echo "[9/9] Demo gaps + reset case statuses..."
python /app/scripts/demo_seed/seed_gaps.py 2>&1 | tail -2
python /app/scripts/demo_seed/reset_cases.py 2>&1 | tail -2

echo ""
echo "✓ Full re-seed complete."
