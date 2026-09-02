#!/usr/bin/env bash
set -Eeuo pipefail

data_root="${DATA_ROOT:-/data}"
log_root="$data_root/logs/linux"
mkdir -p "$log_root" "$data_root/locks"

jobs=(
  sales_dashboard_weekday_monthly_emp1
  sales_dashboard_weekday_monthly_emp2
  sales_dashboard_weekday_monthly_emp3
  sales_dashboard_weekday_daily_emp1
  sales_dashboard_weekday_daily_emp2
  sales_dashboard_saturday_daily_emp1
  sales_dashboard_saturday_daily_emp2
  sales_dashboard_saturday_monthly_emp1
  sales_dashboard_saturday_monthly_emp2
  sales_dashboard_saturday_monthly_emp3
)
for job in "${jobs[@]}"; do
  mkdir -p "$log_root/$job"
done
