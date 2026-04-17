#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# GovFlow DR Drill Script
# Backs up Hologres to OSS, restores to staging, verifies row counts, cleans up.
#
# Usage:
#   ./scripts/dr_drill.sh [--verify-only] [--staging-db <dsn>]
#
# Required environment variables (or .env file):
#   HOLOGRES_DSN          — source Hologres/PostgreSQL DSN
#   OSS_BUCKET            — destination bucket (e.g. govflow-prod)
#   OSS_ENDPOINT          — Alibaba Cloud OSS endpoint
#   OSS_ACCESS_KEY        — OSS access key ID
#   OSS_SECRET_KEY        — OSS secret key
#   STAGING_DB_NAME       — name for the staging restore database (default: govflow_dr_staging)
#
# Optional:
#   --verify-only         — skip backup/restore, only verify row counts between
#                           HOLOGRES_DSN and STAGING_DB_DSN
#   --staging-db <dsn>    — explicit DSN for staging DB (default: derived from HOLOGRES_DSN)
#
# Exit codes:
#   0 — success
#   1 — step failure or row count mismatch > 5%
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Logging helpers ────────────────────────────────────────────────────────
LOG_FILE="/tmp/govflow_dr_drill_$(date +%Y%m%d_%H%M%S).log"
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

log()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${BOLD}INFO${RESET}  $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARN${RESET}  $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR${RESET} $*" | tee -a "$LOG_FILE" >&2; }
ok()   { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}OK${RESET}    $*" | tee -a "$LOG_FILE"; }

# ── Argument parsing ───────────────────────────────────────────────────────
VERIFY_ONLY=false
STAGING_DB_DSN_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --verify-only)    VERIFY_ONLY=true; shift ;;
    --staging-db)     STAGING_DB_DSN_OVERRIDE="$2"; shift 2 ;;
    *) err "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Load .env if present ───────────────────────────────────────────────────
if [[ -f ".env" ]]; then
  log "Loading .env"
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

# ── Required variables ─────────────────────────────────────────────────────
: "${HOLOGRES_DSN:?HOLOGRES_DSN must be set}"
: "${OSS_BUCKET:?OSS_BUCKET must be set}"

STAGING_DB_NAME="${STAGING_DB_NAME:-govflow_dr_staging}"
BACKUP_DATE="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="/tmp/govflow_hologres_backup_${BACKUP_DATE}.dump"
OSS_BACKUP_KEY="backups/hologres/${BACKUP_DATE}.dump"

# Derive staging DSN if not provided
if [[ -n "$STAGING_DB_DSN_OVERRIDE" ]]; then
  STAGING_DSN="$STAGING_DB_DSN_OVERRIDE"
else
  # Replace database name in DSN for staging
  STAGING_DSN="${HOLOGRES_DSN%/*}/${STAGING_DB_NAME}"
fi

log "DR Drill started — log file: $LOG_FILE"
log "Source DSN: ${HOLOGRES_DSN%%@*}@..."
log "Staging DSN: ${STAGING_DSN%%@*}@..."
log "OSS backup key: oss://${OSS_BUCKET}/${OSS_BACKUP_KEY}"

# ── Track staging DB creation for cleanup ─────────────────────────────────
STAGING_CREATED=false

cleanup() {
  local exit_code=$?
  if [[ "$STAGING_CREATED" == "true" ]]; then
    log "Cleanup: dropping staging database '${STAGING_DB_NAME}'"
    # Extract connection params from source DSN for psql admin connection
    # DSN format: postgresql://user:pass@host:port/dbname
    ADMIN_DSN="${HOLOGRES_DSN%/*}/postgres"
    psql "$ADMIN_DSN" -c "DROP DATABASE IF EXISTS ${STAGING_DB_NAME};" \
      2>>"$LOG_FILE" && log "Staging DB dropped" || warn "Could not drop staging DB — manual cleanup required"
  fi
  if [[ -f "$BACKUP_FILE" ]]; then
    rm -f "$BACKUP_FILE"
    log "Cleanup: removed local backup file"
  fi
  if [[ $exit_code -eq 0 ]]; then
    ok "DR Drill PASSED — exit 0"
  else
    err "DR Drill FAILED — exit $exit_code"
  fi
  exit $exit_code
}
trap cleanup EXIT INT TERM

# ── Dependency checks ──────────────────────────────────────────────────────
for cmd in pg_dump psql python3; do
  if ! command -v "$cmd" &>/dev/null; then
    err "Required command not found: $cmd"
    exit 1
  fi
done

# ── Step 1: Backup source Hologres to local dump ──────────────────────────
if [[ "$VERIFY_ONLY" == "false" ]]; then
  log "Step 1/4: Backing up Hologres → ${BACKUP_FILE}"
  if pg_dump \
      --format=custom \
      --no-password \
      --verbose \
      --file="$BACKUP_FILE" \
      "$HOLOGRES_DSN" \
      >>"$LOG_FILE" 2>&1; then
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    ok "Step 1/4: Backup complete (${BACKUP_SIZE})"
  else
    err "Step 1/4: pg_dump failed"
    exit 1
  fi

  # ── Step 2: Upload dump to OSS ─────────────────────────────────────────
  log "Step 2/4: Uploading backup to OSS (oss://${OSS_BUCKET}/${OSS_BACKUP_KEY})"
  if command -v aliyun &>/dev/null; then
    if aliyun oss cp "$BACKUP_FILE" "oss://${OSS_BUCKET}/${OSS_BACKUP_KEY}" \
        >>"$LOG_FILE" 2>&1; then
      ok "Step 2/4: OSS upload complete"
    else
      err "Step 2/4: OSS upload failed — check aliyun CLI credentials"
      exit 1
    fi
  elif command -v aws &>/dev/null; then
    # Fallback: use AWS CLI with OSS endpoint (S3-compatible)
    if aws s3 cp "$BACKUP_FILE" "s3://${OSS_BUCKET}/${OSS_BACKUP_KEY}" \
        --endpoint-url "${OSS_ENDPOINT:-}" \
        >>"$LOG_FILE" 2>&1; then
      ok "Step 2/4: OSS upload via aws CLI complete"
    else
      warn "Step 2/4: OSS upload failed — backup saved locally at $BACKUP_FILE"
    fi
  else
    warn "Step 2/4: No aliyun or aws CLI found — skipping OSS upload"
    warn "         Local backup retained at: $BACKUP_FILE"
  fi

  # ── Step 3: Restore to staging DB ─────────────────────────────────────
  log "Step 3/4: Creating staging database '${STAGING_DB_NAME}'"
  ADMIN_DSN="${HOLOGRES_DSN%/*}/postgres"
  psql "$ADMIN_DSN" \
    -c "DROP DATABASE IF EXISTS ${STAGING_DB_NAME};" \
    -c "CREATE DATABASE ${STAGING_DB_NAME};" \
    >>"$LOG_FILE" 2>&1 \
    && STAGING_CREATED=true \
    || { err "Step 3/4: Could not create staging DB"; exit 1; }

  log "Step 3/4: Restoring dump to staging DB"
  if pg_restore \
      --format=custom \
      --no-password \
      --verbose \
      --dbname="$STAGING_DSN" \
      "$BACKUP_FILE" \
      >>"$LOG_FILE" 2>&1; then
    ok "Step 3/4: Restore complete"
  else
    # pg_restore exits non-zero for warnings too — check for real errors
    warn "Step 3/4: pg_restore exited non-zero — checking for critical errors"
    if grep -q "ERROR:" "$LOG_FILE"; then
      err "Step 3/4: Restore encountered errors — see $LOG_FILE"
      exit 1
    else
      ok "Step 3/4: Restore completed with warnings (non-critical)"
    fi
  fi
fi  # end VERIFY_ONLY==false

# ── Step 4: Verify row counts ─────────────────────────────────────────────
log "Step 4/4: Verifying row counts (tolerance: 5%)"

VERIFY_SCRIPT=$(cat <<'PYEOF'
import sys
import subprocess
import json

def row_counts(dsn):
    query = """
    SELECT table_name, n_live_tup::bigint AS cnt
    FROM pg_stat_user_tables
    WHERE schemaname = 'public' AND n_live_tup > 0
    ORDER BY table_name;
    """
    result = subprocess.run(
        ["psql", dsn, "-t", "-A", "-F", "\t", "-c", query],
        capture_output=True, text=True, check=True
    )
    counts = {}
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            counts[parts[0]] = int(parts[1])
    return counts

src_dsn, stg_dsn = sys.argv[1], sys.argv[2]
tolerance = 0.05  # 5%

try:
    src_counts = row_counts(src_dsn)
    stg_counts = row_counts(stg_dsn)
except subprocess.CalledProcessError as e:
    print(f"ERROR: psql failed: {e.stderr}", file=sys.stderr)
    sys.exit(1)

if not src_counts:
    print("WARN: source DB appears empty — skipping count comparison")
    sys.exit(0)

failures = []
for table, src_n in src_counts.items():
    stg_n = stg_counts.get(table, 0)
    if src_n == 0:
        continue
    diff_pct = abs(src_n - stg_n) / src_n
    status = "OK" if diff_pct <= tolerance else "FAIL"
    print(f"  {status} {table}: src={src_n} stg={stg_n} diff={diff_pct:.1%}")
    if status == "FAIL":
        failures.append(table)

if failures:
    print(f"FAIL: Row count mismatch > {tolerance:.0%} in tables: {failures}", file=sys.stderr)
    sys.exit(1)
else:
    print(f"OK: All tables within {tolerance:.0%} tolerance")
PYEOF
)

if python3 -c "$VERIFY_SCRIPT" "$HOLOGRES_DSN" "$STAGING_DSN" 2>&1 | tee -a "$LOG_FILE"; then
  ok "Step 4/4: Row count verification passed"
else
  err "Step 4/4: Row count verification failed"
  exit 1
fi

ok "All DR drill steps completed successfully"
log "Full log saved to: $LOG_FILE"
