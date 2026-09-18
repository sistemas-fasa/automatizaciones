#!/usr/bin/env bash
set -u

NAME="monitor_puerto_3050"
HOST="${MONITOR_TARGET_HOST:-suevos.ddns.net}"
PORT="${MONITOR_TARGET_PORT:-3050}"
BASE="${AUTOMATIZACIONES_ROOT:-/home/ferreteria/automatizaciones}"
LOG_DIR="${AUTOMATIZACIONES_LOG_ROOT:-$BASE/logs/linux/$NAME}"
LOCK_FILE="${AUTOMATIZACIONES_LOCK_FILE:-$BASE/locks/$NAME.lock}"

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")"
LOG_FILE="$LOG_DIR/${NAME}-$(date +%Y%m%d-%H%M%S).log"

if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
        exit 0
    fi
else
    : > "$LOCK_FILE"
    LOCK_DIR="${LOCK_FILE}.d"
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
        exit 0
    fi
    trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
fi

echo "$(date --iso-8601=seconds) START host=$HOST port=$PORT" >> "$LOG_FILE"
if timeout 15 bash -c "</dev/tcp/$HOST/$PORT" >/dev/null 2>&1; then
    echo "$(date --iso-8601=seconds) OK port_open host=$HOST port=$PORT" >> "$LOG_FILE"
    exit_code=0
else
    exit_code=$?
    error_line="$(date --iso-8601=seconds) ERROR port_closed_or_timeout host=$HOST port=$PORT exit_code=$exit_code"
    echo "$error_line" >> "$LOG_FILE"
    echo "$error_line log=$LOG_FILE" >&2
fi

find "$LOG_DIR" -type f -name "${NAME}-*.log" -mtime +30 -delete 2>/dev/null || true
echo "$(date --iso-8601=seconds) END exit_code=$exit_code" >> "$LOG_FILE"
exit "$exit_code"
