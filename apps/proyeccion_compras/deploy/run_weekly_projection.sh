#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/ferreteria/automatizaciones/apps/proyeccion_compras"
ENV_FILE="$APP_DIR/.env"
PYTHON="/home/ferreteria/automatizaciones/venv/bin/python"
PUBLIC_DIR="/var/www/html/informes/proyeccion-compras"

cd "$APP_DIR"
set -a
source "$ENV_FILE"
set +a

exec "$PYTHON" "$APP_DIR/weekly_job.py" --public-dir "$PUBLIC_DIR" "$@"
