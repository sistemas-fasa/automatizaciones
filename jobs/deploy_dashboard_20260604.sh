#!/usr/bin/env bash
set -euo pipefail

BASE="/home/ferreteria/automatizaciones"
TS="20260604-1626"
ARCHIVE="$BASE/backups/linux/dashboard-20260604-source.tgz"
APP="$BASE/apps/dashboard"

mkdir -p "$BASE/apps" "$BASE/backups/linux"

if [ -d "$APP" ]; then
  mv "$APP" "$BASE/backups/linux/dashboard-$TS-before-update-dir"
fi

tar -xzf "$ARCHIVE" -C "$BASE/apps"

cp /var/www/html/dashboard/.env "$APP/.env"
cp /var/www/html/dashboard/fasa.ini "$APP/fasa.ini"

chmod -R u+rwX,go+rX "$APP"

find "$APP" -maxdepth 2 -type f | sort | sed -n '1,120p'
