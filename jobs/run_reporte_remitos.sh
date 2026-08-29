#!/usr/bin/env bash
set -u

BASE="/home/ferreteria/automatizaciones"
APP_DIR="$BASE/apps/reporte_remitos"
PYTHON="$BASE/venv/bin/python"

cd "$APP_DIR" || exit 1
exec "$BASE/jobs/run_job.sh" reporte_remitos "$PYTHON" "$APP_DIR/reporte.py"
