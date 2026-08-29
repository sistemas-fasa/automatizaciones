#!/usr/bin/env bash
set -euo pipefail

LINE="30 5 * * 1 /home/ferreteria/automatizaciones/jobs/run_job.sh proyeccion_compras_weekly /home/ferreteria/automatizaciones/apps/proyeccion_compras/deploy/run_weekly_projection.sh"
MARKER="# FASA_AUTOMATIZACIONES proyeccion_compras_weekly"
CURRENT="$(mktemp)"
trap 'rm -f "$CURRENT"' EXIT

crontab -l 2>/dev/null \
  | grep -vF "$MARKER" \
  | grep -vF "run_job.sh proyeccion_compras_weekly" \
  > "$CURRENT" || true

printf '\n%s\n%s\n' "$MARKER" "$LINE" >> "$CURRENT"
crontab "$CURRENT"
