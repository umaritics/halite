#!/usr/bin/env bash
# Bounded conflict-analysis backfill against local halite-api (127.0.0.1:8002).
# Requires OPS_TOKEN in backend/.env on the VM. Logs to data/analysis_backfill.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
API="http://127.0.0.1:8002/api/maintenance/analysis/run"
LOG="$ROOT/backend/data/analysis_backfill.log"
BATCH_SIZE="${BATCH_SIZE:-25}"
MAX_ROUNDS="${MAX_ROUNDS:-100}"
SLEEP_SEC="${SLEEP_SEC:-2}"

OPS_TOKEN="$(grep -E '^OPS_TOKEN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r')"
if [[ -z "$OPS_TOKEN" ]]; then
  echo "OPS_TOKEN missing in $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG")"
echo "=== backfill start $(date -Is) batch=$BATCH_SIZE max_rounds=$MAX_ROUNDS ===" | tee -a "$LOG"

for ((round = 1; round <= MAX_ROUNDS; round++)); do
  resp="$(curl -sf -X POST "$API" \
    -H "X-Ops-Token: $OPS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"batch_size\": $BATCH_SIZE}")" || {
    echo "round $round: curl failed" | tee -a "$LOG"
    exit 1
  }
  echo "round $round: $resp" | tee -a "$LOG"
  unscored="$(python3 -c "import json,sys; d=json.load(sys.stdin); print((d.get('analysis_status') or {}).get('unscored', 0))" <<<"$resp")"
  processed="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('processed', 0))" <<<"$resp")"
  if [[ "${processed:-0}" -eq 0 ]]; then
    echo "round $round: nothing processed; stopping" | tee -a "$LOG"
    break
  fi
  if [[ "${unscored:-1}" -eq 0 ]]; then
    echo "round $round: corpus fully scored" | tee -a "$LOG"
    break
  fi
  sleep "$SLEEP_SEC"
done

echo "=== backfill end $(date -Is) ===" | tee -a "$LOG"
curl -sf -H "X-Ops-Token: $OPS_TOKEN" "http://127.0.0.1:8002/api/maintenance/analysis/status" | tee -a "$LOG"