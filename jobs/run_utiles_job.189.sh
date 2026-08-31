#!/usr/bin/env bash
set -u

NAME="${1:?job name required}"
ENV_FILE="${2:?env file required}"
shift 2
BASE="${AUTOMATIZACIONES_ROOT:-/data}"
APP_DIR="/var/www/html/utiles"
LOG_DIR="$BASE/logs/linux/$NAME"
LOCK_FILE="$BASE/locks/$NAME.lock"
TIMEOUT="${JOB_TIMEOUT:-50m}"

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")"
LOG_FILE="$LOG_DIR/${NAME}-$(date +%Y%m%d-%H%M%S).log"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
  exit 0
fi

load_env_file() {
  local file="$1" line key value
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in
      ''|'#'*) continue ;;
      export\ *) line="${line#export }" ;;
    esac
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      export "$key=$value"
    fi
  done < "$file"
}

echo "$(date --iso-8601=seconds) START env_file=$ENV_FILE command=$*" >> "$LOG_FILE"
if [ -f "$ENV_FILE" ]; then
  load_env_file "$ENV_FILE"
else
  echo "$(date --iso-8601=seconds) ERROR missing_env_file=$ENV_FILE" >> "$LOG_FILE"
  exit 1
fi

cd "$APP_DIR" || {
  echo "$(date --iso-8601=seconds) ERROR cannot_cd app_dir=$APP_DIR" >> "$LOG_FILE"
  exit 1
}
export PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"

timeout "$TIMEOUT" "$@" >> "$LOG_FILE" 2>&1
exit_code=$?
echo "$(date --iso-8601=seconds) END exit_code=$exit_code" >> "$LOG_FILE"
exit "$exit_code"
