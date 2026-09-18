"""
Detecta remitos duplicados (mismo `comp`) y notifica por email a sistemas@ferreteriaavenida.com.ar

Uso: python export_remitos_duplicados.py

Se basa en las convenciones de los otros scripts del directorio:
- carga variables desde .env
- usa mysql.connector
- envía email con plantilla HTML moderna cuando se detectan duplicados
"""

import os
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)


# ---------- Configuración desde .env ----------
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'raise_on_warnings': True,
    'use_pure': True,
}

SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER')
SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Destinatario solicitado por el usuario
EMAIL_TO_OVERRIDE = 'sistemas@ferreteriaavenida.com.ar'


QUERY = """
SELECT comp, COUNT(*) AS cantidad
FROM remitos
WHERE facturado = 'N' AND tipo IN ('X','C')
GROUP BY comp
HAVING cantidad > 1
ORDER BY cantidad DESC
"""


def connect_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise Exception(f"Error al conectar a la base de datos: {e}")


def fetch_duplicates(conn):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(QUERY)
    rows = cursor.fetchall()
    # Normalizar a tipos primitivos
    for r in rows:
        if 'cantidad' in r and r['cantidad'] is not None:
            r['cantidad'] = int(r['cantidad'])
    return rows


def build_html_message(duplicates, generated_at=None):
    generated_at = generated_at or datetime.now()
    total = len(duplicates)

    rows_html = ""
    for d in duplicates:
        rows_html += f"<tr><td style=\"padding:8px;border-bottom:1px solid #eee;\">{d['comp']}</td><td style=\"padding:8px;border-bottom:1px solid #eee;\">{d['cantidad']}</td></tr>"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background:#f6f7fb; color:#111827; margin:0; padding:20px; }}
        .card {{ max-width:800px; margin:0 auto; background:white; border-radius:12px; box-shadow:0 6px 20px rgba(17,24,39,0.08); overflow:hidden; }}
        .header {{ padding:20px 24px; background:linear-gradient(90deg,#0ea5a4 0%,#06b6d4 100%); color:#fff; }}
        .header h1 {{ font-size:18px; margin:0 0 6px 0; }}
        .header p {{ margin:0; opacity:0.95; font-size:13px; }}
        .content {{ padding:20px 24px; }}
        table {{ width:100%; border-collapse:collapse; margin-top:12px; }}
        th {{ text-align:left; padding:10px 8px; color:#374151; font-size:13px; border-bottom:2px solid #f3f4f6; }}
        td {{ font-size:13px; color:#111827; }}
        .footer {{ padding:16px 24px; font-size:12px; color:#6b7280; background:#fbfcfd; }}
        .badge {{ display:inline-block; padding:6px 10px; background:#ef4444; color:#fff; border-radius:999px; font-weight:600; font-size:12px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>Remitos Duplicados Detectados</h1>
          <p>Se encontraron remitos con el mismo <strong>comp</strong> sin facturar (tipo X/C).</p>
        </div>
        <div class="content">
          <p><strong>Total</strong>: <span class="badge">{total}</span></p>
          <table>
            <thead>
              <tr><th>Comp</th><th>Cantidad</th></tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
          <p style="margin-top:12px;color:#374151;font-size:13px;">Este reporte se generó el {generated_at.strftime('%d/%m/%Y %H:%M:%S')}.</p>
        </div>
        <div class="footer">Sistema de alertas - Automatizaciones Ferretería Avenida</div>
      </div>
    </body>
    </html>
    """

    return html_body


def send_email(subject, html_body, to_addr=EMAIL_TO_OVERRIDE):
    if not all([SMTP_SERVER, EMAIL_FROM, EMAIL_PASSWORD, to_addr]):
        print("[ADVERTENCIA] Configuración de email incompleta. Revisar .env variables.")
        return False

    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_FROM
    msg['To'] = to_addr
    msg['Subject'] = subject

    part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_FROM, [to_addr], msg.as_string())
        print(f"[OK] Email enviado a {to_addr}")
        return True
    except Exception as e:
        print(f"[ERROR] Envío de email falló: {e}")
        return False


def main():
    print("=" * 70)
    print("EXPORT REMITOS DUPLICADOS")
    print(f"FECHA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Conectar DB y ejecutar consulta
    try:
        conn = connect_db()
    except Exception as e:
        print(f"[ERROR] {e}")
        return 2

    try:
        duplicates = fetch_duplicates(conn)
    except Exception as e:
        print(f"[ERROR] Fallo al ejecutar consulta: {e}")
        conn.close()
        return 3

    # Guardar resultado en JSON para trazabilidad
    output_file = 'remitos_duplicados.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(duplicates, f, indent=2, ensure_ascii=False)
        print(f"[OK] Resultados guardados en: {output_file}")
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo guardar JSON: {e}")

    if not duplicates:
        print("[INFO] No se encontraron remitos duplicados. No se enviará email.")
        conn.close()
        return 0

    # Construir y enviar email
    html = build_html_message(duplicates)
    subject = f"⚠ Remitos duplicados detectados: {len(duplicates)}"
    sent = send_email(subject, html)

    conn.close()
    return 0 if sent else 4


if __name__ == '__main__':
    exit_code = main()
    raise SystemExit(exit_code)
