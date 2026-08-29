#!/usr/bin/env bash
set -u

BASE="/home/ferreteria/automatizaciones"
APP_DIR="$BASE/apps/exports"
PYTHON="$BASE/venv/bin/python"

mkdir -p "$APP_DIR/output"
cd "$APP_DIR" || exit 1
exec "$BASE/jobs/run_job.sh" run_all_exports "$PYTHON" "$APP_DIR/scripts/run_all_exports.py"
