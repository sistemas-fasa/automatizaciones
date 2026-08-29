#!/usr/bin/env bash
set -euo pipefail

BACKUP="/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2048-before-0200-wrapper.txt"
TMP="$(mktemp)"

mkdir -p "$(dirname "$BACKUP")"
crontab -l > "$BACKUP"

while IFS= read -r line; do
  case "$line" in
    "0 2 * * * /var/www/mi-app/scripts/backup-db.sh >> /var/www/mi-app/backups/backup.log 2>&1")
      echo "0 2 * * * /home/ferreteria/automatizaciones/jobs/run_job.sh backup_db /var/www/mi-app/scripts/backup-db.sh"
      ;;
    "0 2 * * * cd /home/ferreteria/ventas_automation && source env/bin/activate && python scripts/ventas_diarias.py >> output/cron.log 2>&1")
      echo "0 2 * * * /home/ferreteria/automatizaciones/jobs/run_job.sh ventas_diarias bash -lc 'cd /home/ferreteria/ventas_automation && source env/bin/activate && python scripts/ventas_diarias.py'"
      ;;
    *)
      echo "$line"
      ;;
  esac
done < "$BACKUP" > "$TMP"

crontab "$TMP"
rm -f "$TMP"

echo "--- migrated 0200 lines ---"
crontab -l | grep -n -E 'backup_db|ventas_diarias|backup-db.sh|ventas_automation'
