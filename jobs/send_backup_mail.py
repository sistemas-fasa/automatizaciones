#!/usr/bin/env python3
"""send_backup_mail.py - Envia mail de notificacion de backup de fg.

Lee config de env vars:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_SECURITY (ssl|tls|none)
  SMTP_FROM, SMTP_TO, SMTP_TIMEOUT

Argumentos:
  --status   ok|error
  --subject  Asunto del mail
  --body     Cuerpo del mail (texto plano)
"""
import argparse
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--status", choices=("ok", "error"), required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    args = p.parse_args()

    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    smtp_security = os.environ.get("SMTP_SECURITY", "ssl").lower()
    from_email = os.environ["SMTP_FROM"]
    to_emails = [e.strip() for e in os.environ["SMTP_TO"].split(",") if e.strip()]

    color = "#2e7d32" if args.status == "ok" else "#c62828"
    heading = "Backup OK" if args.status == "ok" else "Backup ERROR"
    html_body = f"""\
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
    <div style="max-width: 600px; margin: auto; background-color: #fff; border-left: 6px solid {color}; border-radius: 6px; padding: 20px; box-shadow: 0 0 6px rgba(0,0,0,0.1);">
      <h2 style="color: {color}; margin-top: 0;">{heading}</h2>
      <pre style="font-family: 'Courier New', monospace; background-color: #f9f9f9; padding: 12px; border-radius: 4px; white-space: pre-wrap;">{args.body}</pre>
      <hr>
      <p style="font-size: 12px; color: #888;">Enviado automaticamente por backup_fg_db.sh en {os.uname().nodename}</p>
    </div>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = args.subject
    msg.attach(MIMEText(args.body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    if smtp_security == "ssl":
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=int(os.environ.get("SMTP_TIMEOUT", "30")))
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=int(os.environ.get("SMTP_TIMEOUT", "30")))
        if smtp_security in ("tls", "starttls"):
            server.starttls()

    try:
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_emails, msg.as_string())
        print(f"mail {args.status} enviado a {to_emails}")
    finally:
        server.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR enviando mail: {e}", file=sys.stderr)
        sys.exit(1)
