#!/usr/bin/env bash
set -u

NAME="actualiza_lista_reventa"
BASE="/home/ferreteria/automatizaciones"
APP_DIR="/var/www/html/utiles"
PYTHON="$APP_DIR/venv/bin/python"
SCRIPT="$APP_DIR/ActualizaListaReventa.py"
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

timeout "$TIMEOUT" "$PYTHON" "$SCRIPT" >> "$LOG_FILE" 2>&1
exit_code=$?

find "$LOG_DIR" -type f -name "${NAME}-*.log" -mtime +30 -delete 2>/dev/null || true
echo "$(date --iso-8601=seconds) END exit_code=$exit_code" >> "$LOG_FILE"
exit "$exit_code"
