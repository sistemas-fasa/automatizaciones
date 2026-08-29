#!/usr/bin/env bash
set -euo pipefail

BACKUP="/home/ferreteria/automatizaciones/backups/linux/crontab-20260604-before-dashboard-home-app.txt"
TMP="$(mktemp)"
APP="/home/ferreteria/automatizaciones/apps/dashboard"
PY="/var/www/html/dashboard/venv/bin/python"
RUN="/home/ferreteria/automatizaciones/jobs/run_job.sh"

crontab -l > "$BACKUP"

while IFS= read -r line; do
  case "$line" in
    "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp1 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=1")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp1 bash -lc 'cd $APP && $PY SalesDashboard.py --monthly --empresa-id=1'"
      ;;
    "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp2 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=2")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp2 bash -lc 'cd $APP && $PY SalesDashboard.py --monthly --empresa-id=2'"
      ;;
    "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp3 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=3")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_monthly_emp3 bash -lc 'cd $APP && $PY SalesDashboard.py --monthly --empresa-id=3'"
      ;;
    "05 19 * * 1-5 $RUN sales_dashboard_weekday_daily_emp1 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=1")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_daily_emp1 bash -lc 'cd $APP && $PY SalesDashboard.py --daily --empresa-id=1'"
      ;;
    "05 19 * * 1-5 $RUN sales_dashboard_weekday_daily_emp2_chmod bash -lc '/var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=2 && sudo chmod 777 /var/www/html/informes -R'")
      echo "05 19 * * 1-5 $RUN sales_dashboard_weekday_daily_emp2_chmod bash -lc 'cd $APP && $PY SalesDashboard.py --daily --empresa-id=2 && sudo chmod 777 /var/www/html/informes -R'"
      ;;
    "05 12 * * 6 $RUN sales_dashboard_saturday_daily_emp1 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=1")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_daily_emp1 bash -lc 'cd $APP && $PY SalesDashboard.py --daily --empresa-id=1'"
      ;;
    "05 12 * * 6 $RUN sales_dashboard_saturday_daily_emp2 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --daily --empresa-id=2")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_daily_emp2 bash -lc 'cd $APP && $PY SalesDashboard.py --daily --empresa-id=2'"
      ;;
    "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp1 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=1")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp1 bash -lc 'cd $APP && $PY SalesDashboard.py --monthly --empresa-id=1'"
      ;;
    "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp2 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=2")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp2 bash -lc 'cd $APP && $PY SalesDashboard.py --monthly --empresa-id=2'"
      ;;
    "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp3 /var/www/html/dashboard/venv/bin/python /var/www/html/dashboard/SalesDashboard.py --monthly --empresa-id=3")
      echo "05 12 * * 6 $RUN sales_dashboard_saturday_monthly_emp3 bash -lc 'cd $APP && $PY SalesDashboard.py --monthly --empresa-id=3'"
      ;;
    *)
      echo "$line"
      ;;
  esac
done < "$BACKUP" > "$TMP"

crontab "$TMP"
rm -f "$TMP"

crontab -l | grep -n 'sales_dashboard_'
