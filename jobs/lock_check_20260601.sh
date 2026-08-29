#!/usr/bin/env bash
set -u

echo "--- lock checks ---"
for lock in actualiza_lista_reventa reportes_codigo_barra monitor_puerto_3050; do
  f="/home/ferreteria/automatizaciones/locks/$lock.lock"
  if flock -n "$f" true; then
    echo "$lock LOCK_FREE"
  else
    echo "$lock LOCK_BUSY"
  fi
done

echo "--- running processes ---"
ps -ef | grep -E 'run_reportes_codigo_barra|run_all_exports.py|ActualizaListaReventa.py' | grep -v grep || true
