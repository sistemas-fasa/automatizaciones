#!/usr/bin/env bash
# Wrapper para actualizar tabla descuent (bonificaciones por cliente).
# - Carga credenciales DB desde .env junto al script (DB_HOST/USER/PASSWORD/NAME)
# - Calcula rango de fechas: ultimos 12 meses hasta hoy
# - Invoca el script Python con --lista T --actualizar
#
# Cron sugerido:
#   30 23 * * * /home/ferreteria/automatizaciones/jobs/run_job.sh actualizar_descuentos \
#                  /home/ferreteria/automatizaciones/jobs/run_descuentos.sh

set -euo pipefail

APP_DIR="/var/www/html/automatizaciones/apps/export_actualizar_descuentos"
PYTHON="/home/ferreteria/automatizaciones/venv/bin/python"
SCRIPT="$APP_DIR/export_actualizar_descuentos.py"

# Respetar override DESCUENTOS_ENV si esta seteado (lo usa el .py para localizar .env)
export DESCUENTOS_ENV="${DESCUENTOS_ENV:-$APP_DIR/.env}"

HASTA="$(date +%F)"
DESDE="$(date -d 'today -12 months' +%F)"

cd "$APP_DIR"
exec "$PYTHON" "$SCRIPT" \
  --desde "$DESDE" \
  --hasta "$HASTA" \
  --lista T \
  --actualizar