#!/usr/bin/env bash
set -euo pipefail

BACKUP="/home/ferreteria/automatizaciones/backups/linux/crontab-20260604-before-remove-salesdashboard-sudo-chmod.txt"
TMP="$(mktemp)"

crontab -l > "$BACKUP"

python3 - "$BACKUP" "$TMP" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text()
text = text.replace(" && sudo chmod 777 /var/www/html/informes -R'", "'")
dst.write_text(text)
PY

crontab "$TMP"
rm -f "$TMP"

crontab -l | grep -n 'sales_dashboard_weekday_daily_emp2'
