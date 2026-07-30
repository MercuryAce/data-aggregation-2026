#!/usr/bin/env bash
# Run a CryptoDash CLI job from cron with logging and overlap protection.
#
# Usage:
#   scripts/run_cron.sh markets
#   scripts/run_cron.sh sync-platforms
#   scripts/run_cron.sh patch-cmc
#   scripts/run_cron.sh patch-defillama
#   scripts/run_cron.sh trending
#   scripts/run_cron.sh exchanges-categories
#   scripts/run_cron.sh warm-apicache
#
# Override app root:
#   CRYPTODASH_ROOT=/var/www/html/cryptodash scripts/run_cron.sh markets

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="${CRYPTODASH_ROOT:-$ROOT}"
cd "$ROOT"

PYTHON="${ROOT}/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: venv python not found at $PYTHON" >&2
  exit 1
fi

JOB="${1:-}"
if [[ -z "$JOB" ]]; then
  echo "Usage: $0 <markets|sync-platforms|patch-cmc|patch-defillama|trending|exchanges-categories|warm-apicache>" >&2
  exit 1
fi

LOG_DIR="${CRYPTODASH_LOG_DIR:-$HOME/logs/cryptodash}"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/cron.log"
LOCK_DIR="${LOG_DIR}/locks"
mkdir -p "$LOCK_DIR"
LOCK_FILE="${LOCK_DIR}/${JOB}.lock"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

run_locked() {
  local label="$1"
  shift
  (
    flock -n 9 || {
      echo "$(ts) SKIP ${label} (already running)" >>"$LOG_FILE"
      exit 0
    }
    echo "$(ts) START ${label}" >>"$LOG_FILE"
    if "$@" >>"$LOG_FILE" 2>&1; then
      echo "$(ts) OK    ${label}" >>"$LOG_FILE"
    else
      local rc=$?
      echo "$(ts) FAIL  ${label} exit=${rc}" >>"$LOG_FILE"
      exit "$rc"
    fi
  ) 9>"$LOCK_FILE"
}

case "$JOB" in
  markets)
    run_locked "markets" \
      "$PYTHON" scripts/populate_views.py --tables markets --force
    ;;
  sync-platforms)
    run_locked "sync-platforms" \
      "$PYTHON" scripts/populate_views.py --sync-platforms
    ;;
  patch-cmc)
    run_locked "patch-cmc" \
      "$PYTHON" scripts/populate_views.py --patch-cmc
    ;;
  patch-defillama)
    run_locked "patch-defillama" \
      "$PYTHON" scripts/populate_views.py --patch-defillama
    ;;
  trending)
    run_locked "trending" \
      "$PYTHON" scripts/populate_views.py --tables trending --force
    ;;
  exchanges-categories)
    run_locked "exchanges-categories" \
      "$PYTHON" scripts/populate_views.py --tables exchanges,categories --force
    ;;
  warm-apicache)
    run_locked "warm-apicache" \
      "$PYTHON" scripts/sync_coingecko.py --tasks top-coins,ohlc,search,exchange-details --limit 15
    ;;
  *)
    echo "Unknown job: $JOB" >&2
    exit 1
    ;;
esac
