#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
DATA_ROOT="$TMP" "$ROOT/scheduler-entrypoint.sh" bash -c '
  set -Eeuo pipefail
  for job in sales_dashboard_weekday_monthly_emp{1,2,3} sales_dashboard_weekday_daily_emp{1,2} sales_dashboard_saturday_daily_emp{1,2} sales_dashboard_saturday_monthly_emp{1,2,3}; do
    test -d "$DATA_ROOT/logs/linux/$job"
  done
  test "${1:-}" = marker
' bash marker
echo 'scheduler entrypoint test: PASS'
