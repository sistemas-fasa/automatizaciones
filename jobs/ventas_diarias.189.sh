#!/usr/bin/env bash
set -u

NAME="ventas_diarias"
BASE="${AUTOMATIZACIONES_ROOT:-/data}"
APP_DIR="/home/ferreteria/ventas_automation"
SCRIPT="$APP_DIR/scripts/ventas_diarias.py"
LOG_DIR="$BASE/logs/linux/$NAME"
LOCK_FILE="$BASE/locks/$NAME.lock"
TIMEOUT="50m"

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")"
LOG_FILE="$LOG_DIR/${NAME}-$(date +%Y%m%d-%H%M%S).log"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
  exit 0
fi

echo "$(date --iso-8601=seconds) START script=$SCRIPT" >> "$LOG_FILE"
cd "$APP_DIR" || {
  echo "$(date --iso-8601=seconds) ERROR cannot_cd app_dir=$APP_DIR" >> "$LOG_FILE"
  exit 1
}

if [ -f /run/secrets/ventas-diarias.env ]; then
  set -a
  . /run/secrets/ventas-diarias.env
  set +a
fi

timeout "$TIMEOUT" python3 "$SCRIPT" >> "$LOG_FILE" 2>&1
exit_code=$?

echo "$(date --iso-8601=seconds) END exit_code=$exit_code" >> "$LOG_FILE"
exit "$exit_code"
