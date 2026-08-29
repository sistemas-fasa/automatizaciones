#!/usr/bin/env bash
# backup_fg_db.sh - Backup de la DB fg + notificacion por mail
# Llamado por run_job.sh backup_fg_db /path/backup_fg_db.sh [am|pm]
# Tambien se puede llamar directo: backup_fg_db.sh [am|pm]
set -euo pipefail

# --- Cargar env (MySQL + SMTP) ---
ENV_FILE=/srv/env/registro_produccion/mavis_ro.env
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: no existe $ENV_FILE"
  exit 1
fi
# shellcheck disable=SC1090
set -a
. "$ENV_FILE"
set +a

# --- Determinar am/pm (argumento o por hora) ---
SUFFIX=${1:-}
if [ -z "$SUFFIX" ]; then
  HOUR=$(date +%H)
  if [ "$HOUR" -lt 12 ]; then
    SUFFIX=am
  else
    SUFFIX=pm
  fi
fi

TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=${BACKUP_DIR:-/var/backups/registro_produccion/db}
BACKUP_FILE=$BACKUP_DIR/fg_${SUFFIX}.sql.gz
MAIL_SCRIPT=/home/ferreteria/automatizaciones/jobs/send_backup_mail.py
mkdir -p "$BACKUP_DIR" || { echo "ERROR: no se puede crear $BACKUP_DIR (permisos?)"; exit 1; }

# --- Hacer el dump ---
START_TS=$(date +%s)
echo "[$(date -Iseconds)] INICIO backup fg $SUFFIX"

DUMP_OK=0
if mysqldump \
    -h "$MAVIS_MYSQL_HOST" \
    -P "$MAVIS_MYSQL_PORT" \
    -u root -pfasca \
    --single-transaction --routines --triggers --events \
    --default-character-set=utf8mb4 \
    "$MAVIS_MYSQL_DB" 2>/tmp/backup_fg_err.log | gzip > "$BACKUP_FILE.tmp"; then
  mv "$BACKUP_FILE.tmp" "$BACKUP_FILE"
  DUMP_OK=1
fi

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

if [ "$DUMP_OK" = "1" ]; then
  SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
  echo "[$(date -Iseconds)] OK backup $BACKUP_FILE ($SIZE) en ${DURATION}s"
  # Mandar mail OK
  STATUS=ok
  SUBJECT="[OK] Backup fg $SUFFIX $(date +%Y-%m-%d)"
  BODY="Backup fg $SUFFIX realizado correctamente.

Archivo:    $BACKUP_FILE
Tamano:     $SIZE
Duracion:   ${DURATION}s
Server:     $(hostname)
Hora:       $(date -Iseconds)"
else
  ERR=$(cat /tmp/backup_fg_err.log 2>/dev/null || echo "error desconocido")
  echo "[$(date -Iseconds)] ERROR backup (rc=$?): $ERR"
  STATUS=error
  SUBJECT="[ERROR] Backup fg $SUFFIX $(date +%Y-%m-%d)"
  BODY="Backup fg $SUFFIX FALLO.

Error: $ERR
Ver: /home/ferreteria/automatizaciones/logs/linux/backup_fg_db/
Hora: $(date -Iseconds)"
fi

# --- Mandar mail ---
if [ -f "$MAIL_SCRIPT" ]; then
  SMTP_HOST="$SMTP_HOST" \
  SMTP_PORT="$SMTP_PORT" \
  SMTP_USER="$SMTP_USER" \
  SMTP_PASSWORD="$SMTP_PASSWORD" \
  SMTP_SECURITY="$SMTP_SECURITY" \
  SMTP_FROM="$SMTP_FROM" \
  SMTP_TO="$SMTP_TO" \
  SMTP_TIMEOUT="$SMTP_TIMEOUT" \
  python3 "$MAIL_SCRIPT" --status "$STATUS" --subject "$SUBJECT" --body "$BODY" \
    || echo "[$(date -Iseconds)] mail fallo (no afecta el backup)"
fi

[ "$DUMP_OK" = "1" ] || exit 1
exit 0
