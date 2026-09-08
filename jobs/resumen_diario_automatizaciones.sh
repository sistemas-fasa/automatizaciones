#!/usr/bin/env bash
set -u
# Resumen diario de todas las tareas ejecutadas por el scheduler
# Envía un email con: tareas OK, tareas FALLIDAS, y por qué fallaron

BASE="/opt/automatizaciones"
LOG_DIR="/data/logs/linux"
LOCK_FILE="/data/locks/resumen_diario_automatizaciones.lock"
EMAIL_ENV="/run/secrets/informes-diarios.env"

mkdir -p /data/logs/linux/resumen_diario_automatizaciones

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date --iso-8601=seconds) SKIPPED resumen_diario_automatizaciones already_running" >> "$LOG_DIR/resumen_diario_automatizaciones/resumen-$(date +%Y%m%d).log"
  exit 0
fi

echo "$(date --iso-8601=seconds) START resumen_diario_automatizaciones" >> "$LOG_DIR/resumen_diario_automatizaciones/resumen-$(date +%Y%m%d).log"

# Recolectar resultados de los últimos 2 días (o hoy según cron)
RESULTS_FILE="/tmp/resumen_automatizaciones_$(date +%Y%m%d).txt"
echo "Resumen de Automatizaciones - $(date '+%Y-%m-%d %H:%M')" > "$RESULTS_FILE"
echo "========================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "=== TAREAS EJECUTADAS ===" >> "$RESULTS_FILE"
for job_dir in $LOG_DIR/*/; do
  [ -d "$job_dir" ] || continue
  job_name=$(basename "$job_dir")
  # Buscar el log más reciente
  latest_log=$(find "$job_dir" -maxdepth 1 -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
  if [ -n "$latest_log" ]; then
    # Extraer START, END y EXIT_CODE
    start_line=$(grep -m1 "START" "$latest_log" 2>/dev/null || echo "N/A")
    end_line=$(grep -m1 "END" "$latest_log" 2>/dev/null || echo "N/A")
    exit_code=$(echo "$end_line" | grep -oP 'exit_code=\K[0-9]+' || echo "?")
    # No marcar como falla si es el sábado (último log puede ser viejo por horario)
    if [[ "$job_name" == *"saturday"* ]] || [ "$exit_code" = "0" ]; then
      status="OK"
    else
      status="FALLÓ (exit=$exit_code)"
    fi
    echo "$job_name | $status | $end_line" >> "$RESULTS_FILE"
  fi
done

echo "" >> "$RESULTS_FILE"
echo "=== FALLAS DETECTADAS ===" >> "$RESULTS_FILE"
# Buscar errores en los últimos logs
for job_dir in $LOG_DIR/*/; do
  [ -d "$job_dir" ] || continue
  job_name=$(basename "$job_dir")
  latest_log=$(find "$job_dir" -maxdepth 1 -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
  if [ -n "$latest_log" ]; then
    error_lines=$(grep -iE "ERROR|FAIL|exception|Traceback" "$latest_log" 2>/dev/null | tail -3 || true)
    if [ -n "$error_lines" ]; then
      echo "$job_name: $error_lines" >> "$RESULTS_FILE"
    fi
  fi
done

echo "" >> "$RESULTS_FILE"
echo "=== FIN RESUMEN ===" >> "$RESULTS_FILE"

# Generar versión HTML bonita
HTML_FILE="/tmp/resumen_automatizaciones_$(date +%Y%m%d)_html.html"
cat > "$HTML_FILE" << 'HTMLEOF'
<html>
<head><style>
body{font-family:Arial,sans-serif;background:#f8f9fa;padding:20px;color:#333}
.container{max-width:700px;margin:auto;background:#fff;padding:25px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
h2{color:#1565c0;border-bottom:3px solid #1565c0;padding-bottom:10px}
h3{color:#c62828}
.table{width:100%;border-collapse:collapse;margin-top:10px}
.table th{background:#1565c0;color:#fff;padding:8px;text-align:left}
.table td{padding:8px;border-bottom:1px solid #ddd}
.ok{color:#2e7d32;font-weight:bold}
.fail{color:#c62828;font-weight:bold}
.tag{display:inline-block;padding:4px 8px;border-radius:4px;color:#fff;font-size:12px}
.tag-ok{background:#2e7d32}
.tag-fail{background:#c62828}
</style></head>
<body>
<div class="container">
<h2>Resumen de Automatizaciones</h2>
<p><strong>Fecha:</strong> $(date '+%Y-%m-%d %H:%M')</p>
<h3>Estado de tareas</h3>
<table class="table">
<tr><th>Job</th><th>Estado</th><th>Último log</th></tr>
HTMLEOF

# Construir filas de la tabla con datos reales
for job_dir in $LOG_DIR/*/; do
  [ -d "$job_dir" ] || continue
  job_name=$(basename "$job_dir")
  latest_log=$(find "$job_dir" -maxdepth 1 -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
  if [ -n "$latest_log" ]; then
    end_line=$(grep -m1 "END" "$latest_log" 2>/dev/null || echo "N/A")
    exit_code=$(echo "$end_line" | grep -oP 'exit_code=\K[0-9]+' || echo "?")
    if [ "$exit_code" = "0" ]; then
      status_class="ok"
      status_text="OK"
    else
      status_class="fail"
      status_text="FALLÓ (exit=$exit_code)"
    fi
    echo "<tr><td>$job_name</td><td><span class='tag tag-$status_class'>$status_text</span></td><td>$(basename $latest_log)</td></tr>" >> "$HTML_FILE"
  fi
done

cat >> "$HTML_FILE" << 'HTMLEOF'
</table>
<h3>Errores detectados</h3>
<div style="background:#fff3f3;padding:10px;border-left:4px solid #c62828;border-radius:4px">
HTMLEOF

# Agregar errores
errors_found=0
for job_dir in $LOG_DIR/*/; do
  [ -d "$job_dir" ] || continue
  job_name=$(basename "$job_dir")
  latest_log=$(find "$job_dir" -maxdepth 1 -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
  if [ -n "$latest_log" ]; then
    error_lines=$(grep -iE "ERROR|FAIL|exception|Traceback" "$latest_log" 2>/dev/null | tail -3 || true)
    if [ -n "$error_lines" ]; then
      errors_found=1
      echo "<p><strong>$job_name:</strong><br><pre style='font-family:monospace;background:#f5f5f5;padding:8px;border-radius:4px'>$error_lines</pre></p>" >> "$HTML_FILE"
    fi
  fi
done

if [ "$errors_found" = "0" ]; then
  echo "<p><strong>Sin errores detectados.</strong></p>" >> "$HTML_FILE"
fi

cat >> "$HTML_FILE" << 'HTMLEOF'
</div>
<p style="font-size:12px;color:#777;margin-top:20px;border-top:1px solid #ddd;padding-top:10px">Enviado automáticamente por el sistema de automatizaciones.</p>
</div>
</body>
</html>
HTMLEOF

echo "=== FIN RESUMEN ===" >> "$RESULTS_FILE"

# Intentar enviar por email si hay env configurado
if [ -f "$EMAIL_ENV" ]; then
  # Usar python para enviar con la config de informes_diarios
  python3 << 'PYEOF'
import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Cargar env básico
with open('/run/secrets/informes-diarios.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k,v = line.strip().split('=',1)
            os.environ[k] = v

to_emails = ['oscarvogel@gmail.com']
from_email = os.getenv('SMTP_USER','sistemas@ferreteriaavenida.com.ar')
subject = f"Resumen Automatizaciones - {os.popen('date +%Y-%m-%d').read().strip()}"

with open('/tmp/resumen_automatizaciones_{}_html.html'.format(os.popen('date +%Y%m%d').read().strip()), 'r') as f:
    body = f.read()

msg = MIMEMultipart()
msg['From'] = from_email
msg['To'] = ', '.join(to_emails)
msg['Subject'] = subject
msg.attach(MIMEText(body, 'html'))

try:
    server = smtplib.SMTP_SSL(os.getenv('SMTP_SERVER','smtp.gmail.com'), int(os.getenv('SMTP_PORT',465)))
    server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
    server.sendmail(from_email, to_emails, msg.as_string())
    server.quit()
    with open('/data/logs/linux/resumen_diario_automatizaciones/resumen-{}.log'.format(os.popen('date +%Y%m%d').read().strip()), 'a') as f:
        f.write(f"{os.popen('date --iso-8601=seconds').read().strip()} RESUMEN ENVIADO OK\n")
except Exception as e:
    with open('/data/logs/linux/resumen_diario_automatizaciones/resumen-{}.log'.format(os.popen('date +%Y%m%d').read().strip()), 'a') as f:
        f.write(f"{os.popen('date --iso-8601=seconds').read().strip()} ERROR ENVIANDO RESUMEN: {e}\n")
PYEOF
fi

# Limpiar archivos temporales antiguos
find /tmp -maxdepth 1 -name 'resumen_automatizaciones_*.txt' -mtime +2 -delete 2>/dev/null || true

echo "$(date --iso-8601=seconds) END resumen_diario_automatizaciones" >> "$LOG_DIR/resumen_diario_automatizaciones/resumen-$(date +%Y%m%d).log"
exit 0
