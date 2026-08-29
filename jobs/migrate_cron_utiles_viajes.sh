#!/usr/bin/env bash
set -euo pipefail

BACKUP="/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2056-before-utiles-viajes-wrapper.txt"
TMP="$(mktemp)"
RUN="/home/ferreteria/automatizaciones/jobs/run_job.sh"

mkdir -p "$(dirname "$BACKUP")"
crontab -l > "$BACKUP"

while IFS= read -r line; do
  case "$line" in
    "0 6 * * 1-6 /var/www/html/utiles/venv/bin/python3 /var/www/html/utiles/utiles/cron_envio_compensables.py")
      echo "0 6 * * 1-6 $RUN cron_envio_compensables /var/www/html/utiles/venv/bin/python3 /var/www/html/utiles/utiles/cron_envio_compensables.py"
      ;;
    "0 6 * * 6 cd /var/www/html/utiles && /var/www/html/utiles/run_enviar_ofertas.sh >> /var/www/html/utiles/enviar_ofertas.cron.log 2>&1")
      echo "0 6 * * 6 $RUN enviar_ofertas bash -lc 'cd /var/www/html/utiles && /var/www/html/utiles/run_enviar_ofertas.sh'"
      ;;
    "0 6 * * 1-5 /var/www/html/utiles/venv/bin/python /var/www/html/utiles/utiles/envio_resumen_ctacte.py -t vencidas")
      echo "0 6 * * 1-5 $RUN envio_resumen_ctacte_vencidas /var/www/html/utiles/venv/bin/python /var/www/html/utiles/utiles/envio_resumen_ctacte.py -t vencidas"
      ;;
    "0 6 * * 1-5 /var/www/html/utiles/venv/bin/python /var/www/html/utiles/utiles/envio_resumen_ctacte.py -t primer_vencimiento")
      echo "0 6 * * 1-5 $RUN envio_resumen_ctacte_primer_vencimiento /var/www/html/utiles/venv/bin/python /var/www/html/utiles/utiles/envio_resumen_ctacte.py -t primer_vencimiento"
      ;;
    "0 6 * * 1-5 /var/www/html/utiles/venv/bin/python /var/www/html/utiles/utiles/envio_resumen_ctacte.py -t vencimiento_final")
      echo "0 6 * * 1-5 $RUN envio_resumen_ctacte_vencimiento_final /var/www/html/utiles/venv/bin/python /var/www/html/utiles/utiles/envio_resumen_ctacte.py -t vencimiento_final"
      ;;
    "15 7 * * * cd /var/www/html/django/viajesfg/backend && ./venv/bin/python scripts/send_daily_log_summary.py --days 1 --limit 10 >> /home/ferreteria/viajesfg-daily-log-summary.log 2>&1")
      echo "15 7 * * * $RUN viajesfg_daily_log_summary bash -lc 'cd /var/www/html/django/viajesfg/backend && ./venv/bin/python scripts/send_daily_log_summary.py --days 1 --limit 10'"
      ;;
    *)
      echo "$line"
      ;;
  esac
done < "$BACKUP" > "$TMP"

crontab "$TMP"
rm -f "$TMP"

echo "--- utiles/viajes cron ---"
crontab -l | grep -n -E 'cron_envio_compensables|enviar_ofertas|envio_resumen_ctacte|viajesfg_daily_log_summary|send_daily_log_summary'
