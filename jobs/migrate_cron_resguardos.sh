#!/usr/bin/env bash
set -euo pipefail

BACKUP="/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2059-before-resguardos-wrapper.txt"
TMP="$(mktemp)"
RUN="/home/ferreteria/automatizaciones/jobs/run_job.sh"
DIR="/media/discoh/disco/resguardo/script"

mkdir -p "$(dirname "$BACKUP")"
crontab -l > "$BACKUP"

while IFS= read -r line; do
  case "$line" in
    "30 20 * * * /media/discoh/disco/resguardo/script/alldb.sh")
      echo "30 20 * * * $RUN resguardo_alldb $DIR/alldb.sh"
      ;;
    "30 20 * * * /media/discoh/disco/resguardo/script/alldbserver.sh")
      echo "30 20 * * * $RUN resguardo_alldbserver_2030 $DIR/alldbserver.sh"
      ;;
    "30 12 * * * /media/discoh/disco/resguardo/script/alldbserver.sh")
      echo "30 12 * * * $RUN resguardo_alldbserver_1230 $DIR/alldbserver.sh"
      ;;
    "30 20 * * * /media/discoh/disco/resguardo/script/alldbdattatec.sh")
      echo "30 20 * * * $RUN resguardo_alldbdattatec $DIR/alldbdattatec.sh"
      ;;
    "30 08 * * * /media/discoh/disco/resguardo/script/alldbfelix.sh")
      echo "30 08 * * * $RUN resguardo_alldbfelix $DIR/alldbfelix.sh"
      ;;
    "30 20 * * * /media/discoh/disco/resguardo/script/backupfolder.sh")
      echo "30 20 * * * $RUN resguardo_backupfolder $DIR/backupfolder.sh"
      ;;
    "30 20 * * * /media/discoh/disco/resguardo/script/backupapps.sh")
      echo "30 20 * * * $RUN resguardo_backupapps $DIR/backupapps.sh"
      ;;
    "30 20 * * * /media/discoh/disco/resguardo/script/backupdocumentos.sh")
      echo "30 20 * * * $RUN resguardo_backupdocumentos $DIR/backupdocumentos.sh"
      ;;
    "00 00 * * * /media/discoh/disco/resguardo/script/alldattatec.sh")
      echo "00 00 * * * $RUN resguardo_alldattatec $DIR/alldattatec.sh"
      ;;
    *)
      echo "$line"
      ;;
  esac
done < "$BACKUP" > "$TMP"

crontab "$TMP"
rm -f "$TMP"

echo "--- resguardos cron ---"
crontab -l | grep -n 'resguardo_'
