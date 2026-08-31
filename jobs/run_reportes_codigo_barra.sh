#!/usr/bin/env bash
set -u

BASE="${AUTOMATIZACIONES_ROOT:-/opt/automatizaciones}"
PYTHON="${AUTOMATIZACIONES_PYTHON:-python3}"
load_env_file() {
  local file="$1" line
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in
      ''|\#*) continue ;;
      *=*) export "$line" ;;
    esac
  done < "$file"
}
load_env_file /run/secrets/exports.env
load_env_file /run/secrets/legacy-dashboard.env
# reporte_remitos usa nombres de correo históricos; el secreto nuevo usa EMAIL_SMTP_*.
export EMAIL_HOST="${EMAIL_HOST:-${EMAIL_SMTP_SERVER:-}}"
export EMAIL_PORT="${EMAIL_PORT:-${EMAIL_SMTP_PORT:-587}}"
export EMAIL_USER="${EMAIL_USER:-${EMAIL_FROM:-${SMTP_USER:-}}}"
export EMAIL_PASSWORD="${EMAIL_PASSWORD:-${EMAIL_SMTP_PASSWORD:-${SMTP_PASSWORD:-}}}"
export EMAIL_TO="${EMAIL_TO:-${EMAIL_TO_EMAILS:-${TO_EMAILS_DAILY:-}}}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export EXPORTS_OUTPUT_DIR="${EXPORTS_OUTPUT_DIR:-/data/exports-work}"
export EXPORTS_WEB_DIR="${EXPORTS_WEB_DIR:-/data/mis-dashboards}"
LOG_DIR="${REPORTES_CODIGO_BARRA_LOG_DIR:-/data/logs/linux/reportes_codigo_barra}"
LOCK_FILE="${REPORTES_CODIGO_BARRA_LOCK_FILE:-/data/locks/reportes_codigo_barra.lock}"
LOG_FILE="$LOG_DIR/reportes_codigo_barra-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")" "$EXPORTS_OUTPUT_DIR" "$EXPORTS_WEB_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
  exit 0
fi

run_step_in_dir() {
  local dir="$1"
  local name="$2"
  shift 2
  echo "$(date --iso-8601=seconds) START_STEP $name dir=$dir command=$*" >> "$LOG_FILE"
  (cd "$dir" && "$@") >> "$LOG_FILE" 2>&1
  local exit_code=$?
  echo "$(date --iso-8601=seconds) END_STEP $name exit_code=$exit_code" >> "$LOG_FILE"
  return "$exit_code"
}

echo "$(date --iso-8601=seconds) START reportes_codigo_barra" >> "$LOG_FILE"
rc=0

run_step_in_dir "$BASE/apps/reporte_remitos" reporte_remitos "$PYTHON" "$BASE/apps/reporte_remitos/reporte.py" || rc=1
run_step_in_dir "$BASE/apps/dashboard" ventas_vendedor "$PYTHON" "$BASE/apps/dashboard/VentasVendedor.py" || rc=1
run_step_in_dir "$BASE/apps/informes_diarios" facturas_no_procesadas "$PYTHON" "$BASE/apps/informes_diarios/facturas_no_procesadas.py" || rc=1
run_step_in_dir "$BASE/apps/exports" run_all_exports "$PYTHON" "$BASE/apps/exports/scripts/run_all_exports.py" || rc=1

find "$LOG_DIR" -type f -name "reportes_codigo_barra-*.log" -mtime +30 -delete 2>/dev/null || true
echo "$(date --iso-8601=seconds) END reportes_codigo_barra exit_code=$rc" >> "$LOG_FILE"
exit "$rc"
