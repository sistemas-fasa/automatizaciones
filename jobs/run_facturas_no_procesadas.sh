#!/usr/bin/env bash
set -u

BASE="/opt/automatizaciones"
APP_DIR="$BASE/apps/informes_diarios"
PYTHON="${AUTOMATIZACIONES_PYTHON:-python3}"

cd "$APP_DIR" || exit 1
exec "$BASE/jobs/run_job.sh" facturas_no_procesadas "$PYTHON" "$APP_DIR/facturas_no_procesadas.py"
