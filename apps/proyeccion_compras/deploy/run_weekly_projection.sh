#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${PROYECCION_APP_DIR:-/opt/automatizaciones/apps/proyeccion_compras}"
ENV_FILE="${PROYECCION_ENV_FILE:-/run/secrets/proyeccion-compras.env}"
PYTHON="${PROYECCION_PYTHON:-python3}"
PUBLIC_DIR="${PROYECCION_PUBLIC_DIR:-/var/www/html/informes/proyeccion-compras}"

cd "$APP_DIR"
set -a
source "$ENV_FILE"
set +a

exec "$PYTHON" "$APP_DIR/weekly_job.py" --public-dir "$PUBLIC_DIR" "$@"
