import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import mysql.connector


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta variable requerida: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def split_emails(name: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, "").split(",") if value.strip()]


def main() -> int:
    db = mysql.connector.connect(
        host=required("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=required("DB_USER"),
        password=required("DB_PASSWORD"),
        database=required("DB_NAME"),
    )
    try:
        cursor = db.cursor()
        try:
            hoy = datetime.now().strftime("%m-%d")
            query = (
                "SELECT concat(zona,cliente) codigo, nombre, correo, fecha_nacimiento "
                "FROM clientes WHERE DATE_FORMAT(fecha_nacimiento, '%m-%d') = %s"
            )
            cursor.execute(query, (hoy,))
            clientes = cursor.fetchall()
        finally:
            cursor.close()
    finally:
        db.close()

    if not clientes:
        print("No hay clientes que cumplan años hoy.")
        return 0

    tabla_clientes = """
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;">
  <thead><tr style="background-color: #f2f2f2;">
    <th style="text-align:left;">Nombre</th>
    <th style="text-align:left;">Email</th>
    <th style="text-align:left;">Fecha de Nacimiento</th>
    <th style="text-align:left;">Edad</th>
  </tr></thead><tbody>
"""
    for codigo, nombre, email, fecha_nac in clientes:
        edad = datetime.now().year - fecha_nac.year
        tabla_clientes += f"""
    <tr>
      <td>{escape(f'{codigo} - {nombre}')}</td>
      <td>{escape(email or '')}</td>
      <td>{fecha_nac.strftime('%d/%m/%Y')}</td>
      <td>{edad}</td>
    </tr>
"""
    tabla_clientes += "</tbody></table>"

    cuerpo_html = f"""
<html><body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
  <div style="max-width: 800px; margin: auto; background-color: #fff; border-radius: 8px; padding: 20px;">
    <h2 style="color: #e67e22;">Clientes que cumplen años hoy</h2>
    <p>Estos son los clientes que celebran su cumpleaños el día de hoy:</p>
    {tabla_clientes}
    <br><p><strong>Por favor, contactarlos vía WhatsApp o por otros medios con salutaciones personalizadas.</strong></p>
    <p>Saludos cordiales,<br><strong>Ferretería Avenida Sa</strong></p>
  </div>
</body></html>
"""

    smtp_server = required("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("FROM_EMAIL", smtp_user).strip()
    to_emails = split_emails("TO_EMAILS")
    bcc_emails = split_emails("BCC_EMAILS")
    recipients = to_emails + bcc_emails
    if not recipients:
        raise RuntimeError("No hay destinatarios configurados")

    mensaje = MIMEMultipart()
    mensaje["From"] = from_email
    if to_emails:
        mensaje["To"] = ", ".join(to_emails)
    if bcc_emails:
        mensaje["Bcc"] = ", ".join(bcc_emails)
    mensaje["Subject"] = "🎂 Clientes que cumplen años hoy - Ferretería Avenida Sa"
    mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    timeout = float(os.getenv("SMTP_TIMEOUT", "30"))
    if env_bool("SMTP_USE_SSL", smtp_port == 465):
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=timeout)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=timeout)
    try:
        if env_bool("SMTP_USE_STARTTLS", not env_bool("SMTP_USE_SSL", smtp_port == 465)):
            server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.sendmail(from_email, recipients, mensaje.as_string())
    finally:
        server.quit()
    print(f"Correo enviado a {len(recipients)} destinatarios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
