#!/usr/bin/env bash
set -u

BASE="/home/ferreteria/automatizaciones"
PYTHON="$BASE/venv/bin/python"
LOG_DIR="$BASE/logs/linux/reportes_codigo_barra"
LOCK_FILE="$BASE/locks/reportes_codigo_barra.lock"
LOG_FILE="$LOG_DIR/reportes_codigo_barra-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR" "$(dirname "$LOCK_FILE")"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date --iso-8601=seconds) SKIPPED already_running lock=$LOCK_FILE" >> "$LOG_FILE"
  exit 0
fi

run_step() {
  local name="$1"
  shift
  echo "$(date --iso-8601=seconds) START_STEP $name command=$*" >> "$LOG_FILE"
  "$@" >> "$LOG_FILE" 2>&1
  local exit_code=$?
  echo "$(date --iso-8601=seconds) END_STEP $name exit_code=$exit_code" >> "$LOG_FILE"
  return "$exit_code"
}

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

run_step_in_dir "$BASE/apps/reporte_remitos" reporte_remitos "$PYTHON" "$BASE/apps/reporte_remitos/reporte.py"
rc=$?

run_step_in_dir /home/ferreteria/automatizaciones/apps/dashboard ventas_vendedor /var/www/html/dashboard/venv/bin/python /home/ferreteria/automatizaciones/apps/dashboard/VentasVendedor.py
rc=$(( rc || $? ))

run_step_in_dir "$BASE/apps/informes_diarios" facturas_no_procesadas "$PYTHON" "$BASE/apps/informes_diarios/facturas_no_procesadas.py"
rc=$(( rc || $? ))

run_step_in_dir "$BASE/apps/exports" run_all_exports "$PYTHON" "$BASE/apps/exports/scripts/run_all_exports.py"
rc=$(( rc || $? ))

find "$LOG_DIR" -type f -name "reportes_codigo_barra-*.log" -mtime +30 -delete 2>/dev/null || true
echo "$(date --iso-8601=seconds) END reportes_codigo_barra exit_code=$rc" >> "$LOG_FILE"
exit "$rc"
