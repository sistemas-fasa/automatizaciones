#!/usr/bin/env bash
set -u

echo "--- cron central ---"
crontab -l | grep -n -E 'actualiza_lista_reventa|monitor_puerto_3050|reportes_codigo_barra|run_reportes_codigo_barra' || true

echo "--- latest logs ---"
for job in actualiza_lista_reventa monitor_puerto_3050 reportes_codigo_barra; do
  echo "### $job"
  dir="/home/ferreteria/automatizaciones/logs/linux/$job"
  if [ ! -d "$dir" ]; then
    echo "NO_LOG_DIR"
    continue
  fi

  latest="$(find "$dir" -maxdepth 1 -type f -name "$job-*.log" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
  if [ -z "$latest" ]; then
    echo "NO_LOG_FILES"
    continue
  fi

  ls -l "$latest"
  tail -25 "$latest"
done
