"""
Envía por email los presupuestos NO FACTURADOS cuyo total supera
el valor configurado en paramsist('monto_informa_presupuesto').

Requiere variables en .env:
  EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT, EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

Instalación (si falta):
  pip install python-dotenv pymysql

Uso:
  python export_presupuestos_mayores.py

"""
import os
import sys
import re
import argparse
from datetime import datetime, date
from decimal import Decimal
import traceback
import webbrowser
import tempfile

try:
    import pymysql
except Exception:
    print("Module pymysql no disponible. Instalar: pip install pymysql")
    raise

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv


def cargar_env():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)
    cfg = {
        'smtp_server': os.getenv('EMAIL_SMTP_SERVER'),
        'smtp_port': os.getenv('EMAIL_SMTP_PORT', '587'),
        'email_from': os.getenv('EMAIL_FROM'),
        'email_to': os.getenv('EMAIL_TO'),
        'email_password': os.getenv('EMAIL_PASSWORD'),
        'db_host': os.getenv('DB_HOST'),
        'db_port': int(os.getenv('DB_PORT', '3306')),
        'db_user': os.getenv('DB_USER'),
        'db_password': os.getenv('DB_PASSWORD'),
        'db_name': os.getenv('DB_NAME')
    }
    return cfg


def obtener_monto(cursor):
    cursor.execute("SELECT valor FROM paramsist WHERE parametro = 'monto_informa_presupuesto' LIMIT 1")
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("No se encontró paramsist('monto_informa_presupuesto')")
    # valor puede ser string, convertir a Decimal
    return Decimal(str(row[0]))


def obtener_presupuestos(cursor, monto, empresa_id):
    sql = """
    SELECT p.fecha, p.comp, p.cliente_completo, p.nombre, p.estado_articulo,
      SUM(d.UNITARIO * d.cantidad) AS totalsiva,
      SUM(d.MONTOIVA) AS iva,
      SUM(d.MONTOPERCEP) AS dgr,
            (SUM(d.UNITARIO * d.cantidad) + SUM(d.MONTOIVA) + SUM(d.MONTOPERCEP)) AS total
    FROM presupuestos_facturacion_estado p
      INNER JOIN detaremi d ON p.comp = d.comp AND p.ARTICULO = d.ARTICULO
        WHERE p.estado_articulo = 'No Facturado' AND p.empresa_id = %s
    GROUP BY p.fecha, p.comp, p.cliente_completo, p.nombre, p.estado_articulo
        HAVING total > %s
    ORDER BY total DESC
    """
    cursor.execute(sql, (empresa_id, str(monto)))
    return cursor.fetchall()


def formato_moneda(v):
    try:
        return f"${v:,.2f}"
    except Exception:
        return str(v)


def construir_html(rows, monto):
    # Cabecera y estilo moderno
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    total_count = len(rows)
    html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
                        <style>
                                *{{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif}}
                                html,body{{height:100%;}}
                                body{{background:#f3f4f6;margin:0;padding:16px;color:#0f172a}}
                                .card{{width:100%;max-width:1200px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(2,6,23,0.08)}}
                                .header{{background:linear-gradient(135deg,#0ea5a4 0%,#06b6d4 100%);color:#fff;padding:20px 24px}}
                                .header h1{{margin:0;font-size:20px}}
                                .meta{{padding:12px 16px;border-bottom:1px solid #eef2f7;color:#475569;font-size:13px}}
                                .content{{padding:14px 12px}}
                                .table-wrap{{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}}
                                table{{min-width:720px;width:100%;border-collapse:collapse;font-size:13px}}
                                thead tr{{background:#f8fafc;text-align:left}}
                                th,td{{padding:10px 12px;border-bottom:1px solid #f1f5f9;vertical-align:middle}}
                                th{{color:#0f172a;font-weight:700;font-size:12px}}
                                tr:nth-child(even) td{{background:#fbfdff}}
                                .muted{{color:#64748b;font-size:13px}}
                                .empty{{padding:20px;text-align:center;color:#475569}}
                                .badge{{display:inline-block;background:#fef3c7;color:#92400e;padding:6px 10px;border-radius:999px;font-weight:700}}

                                /* Responsive adjustments */
                                @media (max-width: 820px) {{
                                        .header h1{{font-size:16px}}
                                        th,td{{padding:8px 8px}}
                                        .meta{{font-size:12px}}
                                }}

                                @media (max-width: 520px) {{
                                        body{{padding:10px}}
                                        .card{{border-radius:8px}}
                                        .header{{padding:14px}}
                                        .header h1{{font-size:15px}}
                                        table{{min-width:600px}}
                                        th,td{{padding:8px 6px;font-size:12px}}
                                        .meta{{padding:10px}}
                                }}
                        </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h1>Presupuestos no facturados - Montos mayores a {formato_moneda(monto)}</h1>
                </div>
                <div class="meta">
                    <span class="muted">Generado:</span> {now} &nbsp; • &nbsp; <span class="muted">Total encontrados:</span> <strong>{total_count}</strong>
                </div>
                <div class="content">
        """

    if not rows:
        html += f"<div class=\"empty\">No se encontraron presupuestos mayores a {formato_moneda(monto)}</div>"
    else:
        html += "<div class=\"table-wrap\"><table><thead><tr>"
        headers = ['Fecha','Comp','Cliente','Nombre','TotalSinIVA','IVA','Percep','Total']
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        for r in rows:
            fecha, comp, cliente, nombre, estado_art, totalsiva, iva, dgr, total = r
            # formatear fecha a DD-MM-AAAA
            try:
                if isinstance(fecha, (datetime, date)):
                    fecha_fmt = fecha.strftime('%d-%m-%Y')
                else:
                    s = str(fecha)
                    fecha_fmt = None
                    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%d-%m-%Y'):
                        try:
                            fecha_fmt = datetime.strptime(s, fmt).strftime('%d-%m-%Y')
                            break
                        except Exception:
                            continue
                    if fecha_fmt is None:
                        fecha_fmt = s
            except Exception:
                fecha_fmt = str(fecha)
            html += "<tr>"
            html += f"<td>{fecha_fmt}</td>"
            html += f"<td>{comp}</td>"
            html += f"<td>{cliente}</td>"
            html += f"<td>{nombre}</td>"
            html += f"<td>{formato_moneda(totalsiva or 0)}</td>"
            html += f"<td>{formato_moneda(iva or 0)}</td>"
            html += f"<td>{formato_moneda(dgr or 0)}</td>"
            html += f"<td><strong>{formato_moneda(total or 0)}</strong></td>"
            html += "</tr>"
        html += "</tbody></table></div>"

    html += """
        </div>
      </div>
    </body>
    </html>
    """
    return html


def enviar_email(cfg, html, asunto, recipients=None):
    smtp_server = cfg['smtp_server']
    smtp_port = int(cfg['smtp_port'])
    email_from = cfg['email_from']
    email_password = cfg['email_password']

    # Determinar destinatarios: argumento tiene prioridad, luego .env
    recipients_str = recipients if recipients is not None else cfg.get('email_to')
    if not recipients_str:
        print("[ADVERTENCIA] No hay destinatarios configurados (.env EMAIL_TO o --to)")
        return False

    # Soporta separadores , o ;
    recipients_list = [r.strip() for r in re.split('[,;]', recipients_str) if r.strip()]

    if not all([smtp_server, email_from, email_password]):
        print("[ADVERTENCIA] Variables SMTP incompletas. Revisa .env")
        return False

    msg = MIMEMultipart('alternative')
    msg['From'] = email_from
    msg['To'] = ', '.join(recipients_list)
    msg['Subject'] = asunto

    part1 = MIMEText('Se adjunta el listado de presupuestos no facturados mayores al umbral configurado.', 'plain', 'utf-8')
    part2 = MIMEText(html, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(email_from, email_password)
                server.sendmail(email_from, recipients_list, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_from, email_password)
                server.sendmail(email_from, recipients_list, msg.as_string())
        print("[EMAIL] Enviado a:", recipients_list)
        return True
    except Exception as e:
        print("[EMAIL] Error al enviar:", e)
        traceback.print_exc()
        return False


def parse_args():
    p = argparse.ArgumentParser(description='Exporta presupuestos mayores y envía email opcionalmente')
    p.add_argument('--html-only', action='store_true', help='Generar HTML y no enviar email')
    p.add_argument('--output', '-o', help='Archivo donde guardar HTML (si --html-only). Si no se indica, imprime en stdout')
    p.add_argument('--to', help='Destinatarios del email (separados por coma). Si no se indica usa EMAIL_TO de .env')
    p.add_argument('--subject', help='Asunto del email. Si no se indica se genera uno por defecto')
    p.add_argument('--empresa-id', '-e', type=int, default=1, help='ID de la empresa para filtrar presupuestos (default: 1)')
    return p.parse_args()


def main():
    # Compatibilidad con llamada legacy que pasa empresa_id como argumento posicional
    # Ej: python export_presupuestos_mayores.py 1
    # Buscar cualquier token numérico posicional y convertirlo en --empresa-id <val>
    if len(sys.argv) == 2 and re.match(r'^\d+$', sys.argv[1] or ''):
        # Reemplazar el token legacy por --empresa-id <valor>.
        token = sys.argv[1]
        sys.argv[1] = '--empresa-id'
        sys.argv.insert(2, token)

    args = parse_args()
    cfg = cargar_env()

    # Verificar DB
    if not all([cfg['db_host'], cfg['db_user'], cfg['db_name']]):
        print("[ERROR] Falta configuración de BD en .env (DB_HOST, DB_USER, DB_NAME)")
        return 1

    try:
        conn = pymysql.connect(host=cfg['db_host'], port=cfg['db_port'], user=cfg['db_user'],
                               password=cfg['db_password'], db=cfg['db_name'], charset='utf8mb4',
                               cursorclass=pymysql.cursors.Cursor)
    except Exception as e:
        print("[ERROR] No se pudo conectar a la base de datos:", e)
        return 1

    try:
        with conn.cursor() as cur:
            monto = obtener_monto(cur)
            rows = obtener_presupuestos(cur, monto, args.empresa_id)

        html = construir_html(rows, monto)
        default_subject = f"Presupuestos no facturados > {formato_moneda(monto)} ({len(rows)} encontrados) - Empresa {args.empresa_id}"
        asunto = args.subject if args.subject else default_subject

        if args.html_only:
            # Solo generar HTML: escribir a archivo o stdout
            if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(html)
                    path = os.path.abspath(args.output)
                    print(f"HTML generado en: {path}")
                    try:
                        webbrowser.open(path)
                    except Exception:
                        print("No se pudo abrir el navegador automáticamente. Abre el archivo manualmente.")
            else:
                    # Crear archivo temporal para abrir en navegador
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
                    try:
                        tmp.write(html)
                        tmp.close()
                        print(f"HTML temporal generado en: {tmp.name}")
                        try:
                            webbrowser.open(tmp.name)
                        except Exception:
                            print("No se pudo abrir el navegador automáticamente. Abre el archivo manualmente.")
                    finally:
                        # no eliminar el temporal para que el navegador pueda leerlo
                        pass
            return 0

        # Enviar email, destinatarios pueden venir por argumento
        enviado = enviar_email(cfg, html, asunto, recipients=args.to)
        return 0 if enviado else 2

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Cancelado por usuario")
        sys.exit(1)
