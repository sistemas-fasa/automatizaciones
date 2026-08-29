import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from config import cfg
from models import ResumenProveedor

logger = logging.getLogger(__name__)


def send_report_email(
    report_path: str | Path,
    public_url: str,
    recipients: list[str],
) -> None:
    path = Path(report_path)
    if not recipients:
        raise ValueError("No hay destinatarios configurados")
    if not path.is_file():
        raise FileNotFoundError(path)
    if not cfg.smtp_server:
        raise ValueError("SMTP_SERVER no está configurado")

    msg = MIMEMultipart()
    msg["From"] = cfg.smtp_from or cfg.smtp_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"Proyección semanal de compras - {datetime.now():%d/%m/%Y}"
    body = (
        "<p>La proyección semanal de compras ya está disponible.</p>"
        f'<p><a href="{public_url}">Abrir informe publicado</a></p>'
        "<p>También se adjunta una copia HTML.</p>"
    )
    msg.attach(MIMEText(body, "html", "utf-8"))

    attachment = MIMEBase("text", "html")
    attachment.set_payload(path.read_bytes())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        'attachment; filename="proyeccion-compras.html"',
    )
    msg.attach(attachment)

    with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port) as server:
        server.starttls()
        if cfg.smtp_user:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.send_message(msg)

    logger.info("Email enviado a %s", ", ".join(recipients))


def build_html_body(resumenes: list[ResumenProveedor]) -> str:
    rows_html = ""
    for prov in resumenes:
        rows_html += f"""
        <tr>
            <td>{prov.codigo}</td>
            <td>{prov.nombre}</td>
            <td style="text-align:right">{prov.cantidad_articulos}</td>
            <td style="text-align:right">{prov.total_stock:,.2f}</td>
            <td style="text-align:right">{prov.total_proyeccion:,.2f}</td>
            <td style="text-align:right">{prov.total_pedido_sugerido:,.2f}</td>
        </tr>"""

    total_arts = sum(p.cantidad_articulos for p in resumenes)
    total_stock = sum(p.total_stock for p in resumenes)
    total_proy = sum(p.total_proyeccion for p in resumenes)
    total_ped = sum(p.total_pedido_sugerido for p in resumenes)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Calibri,Arial,sans-serif;font-size:12px;">
<h2>Proyección de Compras</h2>
<p>Resumen por proveedor - {cfg.proy_meses} meses proyectados.</p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
<tr style="background:#4472C4;color:white;font-weight:bold">
    <td>Proveedor</td><td>Nombre</td><td>Artículos</td><td>Stock Actual</td><td>Proyección</td><td>Pedido Sugerido</td>
</tr>
{rows_html}
<tr style="font-weight:bold;background:#D9E2F3">
    <td colspan="2">TOTAL</td>
    <td style="text-align:right">{total_arts}</td>
    <td style="text-align:right">{total_stock:,.2f}</td>
    <td style="text-align:right">{total_proy:,.2f}</td>
    <td style="text-align:right">{total_ped:,.2f}</td>
</tr>
</table>
<p style="color:#666;font-size:10px;">Generado automáticamente el {__import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
</body>
</html>"""
    return html


def send_email(resumenes: list[ResumenProveedor], excel_path: str | Path | None = None):
    if not cfg.smtp_server:
        logger.warning("SMTP no configurado, omitiendo envío de email")
        return

    msg = MIMEMultipart()
    msg["From"] = cfg.smtp_from
    msg["To"] = cfg.smtp_to
    msg["Subject"] = f"Proyección de Compras - {cfg.proy_meses} meses"

    msg.attach(MIMEText(build_html_body(resumenes), "html", "utf-8"))

    if excel_path:
        path = Path(excel_path)
        if path.exists():
            with open(path, "rb") as f:
                part = MIMEBase(
                    "application",
                    "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{path.name}"',
            )
            msg.attach(part)

    try:
        server = smtplib.SMTP(cfg.smtp_server, cfg.smtp_port)
        server.starttls()
        if cfg.smtp_user:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info("Email enviado a %s", cfg.smtp_to)
    except Exception as e:
        logger.error("Error enviando email: %s", e)
        raise
