#!/usr/bin/env bash
set -u

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 JOB_ID COMMAND [ARGS...]" >&2
  exit 64
fi

JOB_ID="$1"
shift

BASE="/home/ferreteria/automatizaciones"
LOG_DIR="$BASE/logs/linux/$JOB_ID"
LOCK_FILE="$BASE/locks/$JOB_ID.lock"

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")"
LOG_FILE="$LOG_DIR/${JOB_ID}-$(date +%Y%m%d-%H%M%S).log"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
  exit 0
fi

echo "$(date --iso-8601=seconds) START job=$JOB_ID command=$*" >> "$LOG_FILE"
"$@" >> "$LOG_FILE" 2>&1
exit_code=$?
echo "$(date --iso-8601=seconds) END job=$JOB_ID exit_code=$exit_code" >> "$LOG_FILE"

find "$LOG_DIR" -type f -name "${JOB_ID}-*.log" -mtime +30 -delete 2>/dev/null || true
exit "$exit_code"
