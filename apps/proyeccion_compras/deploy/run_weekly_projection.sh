#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/fasa/automation-src-incoming-20260829/apps/proyeccion_compras"
ENV_FILE="$APP_DIR/.env"
PYTHON="/usr/bin/python3"
PUBLIC_DIR="${PUBLIC_DIR_OVERRIDE:-/srv/fasa-data/data/informes/proyeccion-compras}"

cd "$APP_DIR"
set -a
source "$ENV_FILE"
set +a

exec "$PYTHON" "$APP_DIR/weekly_job.py" --public-dir "$PUBLIC_DIR" "$@"
