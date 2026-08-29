#!/usr/bin/env bash
set -euo pipefail

BACKUP="/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2052-before-salesdashboard-wrapper.txt"
TMP="$(mktemp)"
RUN="/home/ferreteria/automatizaciones/jobs/run_job.sh"
PY="/var/www/html/dashboard/venv/bin/python"
SCRIPT="/var/www/html/dashboard/SalesDashboard.py"

mkdir -p "$(dirname "$BACKUP")"
crontab -l > "$BACKUP"

while IFS= read -r line; do
  case "$line" in
    "05 19 * * 1-5 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=1 > /home/ferreteria/sales_dashboard.log")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp1 $PY $SCRIPT --monthly --empresa-id=1"
      ;;
    "05 19 * * 1-5 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=2 > /home/ferreteria/sales_dashboard.log")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp2 $PY $SCRIPT --monthly --empresa-id=2"
      ;;
    "05 19 * * 1-5 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=3 > /home/ferreteria/sales_dashboard.log")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp3 $PY $SCRIPT --monthly --empresa-id=3"
      ;;
    "05 19 * * 1-5 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=1 > /home/ferreteria/sales_dashboard.log")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_daily_emp1 $PY $SCRIPT --daily --empresa-id=1"
      ;;
    "05 19 * * 1-5 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=2 > /home/ferreteria/sales_dashboard.log && sudo chmod 777 /var/www/html/informes -R")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_daily_emp2_chmod bash -lc '$PY $SCRIPT --daily --empresa-id=2 && sudo chmod 777 /var/www/html/informes -R'"
      ;;
    "05 12 * * 6 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=1 > /home/ferreteria/sales_dashboard.log")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_daily_emp1 $PY $SCRIPT --daily --empresa-id=1"
      ;;
    "05 12 * * 6 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=2 > /home/ferreteria/sales_dashboard.log")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_daily_emp2 $PY $SCRIPT --daily --empresa-id=2"
      ;;
    "05 12 * * 6 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=1")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp1 $PY $SCRIPT --monthly --empresa-id=1"
      ;;
    "05 12 * * 6 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=2")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp2 $PY $SCRIPT --monthly --empresa-id=2"
      ;;
    "05 12 * * 6 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=3")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp3 $PY $SCRIPT --monthly --empresa-id=3"
      ;;
    *)
      echo "$line"
      ;;
  esac
done < "$BACKUP" > "$TMP"

crontab "$TMP"
rm -f "$TMP"

echo "--- SalesDashboard cron ---"
crontab -l | grep -n 'SalesDashboard.py'
