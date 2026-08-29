#!/usr/bin/env bash
set -euo pipefail

APP="/home/ferreteria/automatizaciones/apps/dashboard"
PY="/var/www/html/dashboard/venv/bin/python"

cd "$APP"

"$PY" -m py_compile \
  SalesDashboard.py \
  ReportGenerator.py \
  DatabaseManager.py \
  DataProcessor.py \
  EmailSender.py \
  VentasVendedor.py

"$PY" - <<'PY'
import SalesDashboard
import ReportGenerator
import DatabaseManager
import EmailSender
print("IMPORT_DASHBOARD_OK")
PY

echo "--- crontab dashboard ---"
crontab -l | grep -n 'sales_dashboard_'

echo "--- reportes wrapper dashboard line ---"
grep -n 'ventas_vendedor\|dashboard' /home/ferreteria/automatizaciones/jobs/run_reportes_codigo_barra.sh
