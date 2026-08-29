from datetime import datetime
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
logging.basicConfig(
    filename='dashboard.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.basicConfig()

class EmailSender:
    def __init__(self, smtp_config):
        self.smtp_config = smtp_config

    def send_email(self, html_content, fecha, filename=None, report_type='daily', company_name=None):
        """
        Envía email con el reporte de ventas.
        
        Args:
            html_content: Contenido HTML del reporte
            fecha: Fecha del reporte (YYYY-MM-DD)
            filename: Nombre del archivo HTML generado
            report_type: 'daily' o 'monthly' para determinar destinatarios
        """
        try:
            msg = MIMEMultipart()
            
            # Determinar asunto según tipo de reporte
            if report_type == 'monthly':
                if company_name:
                    msg['Subject'] = f'Dashboard de Ventas MENSUAL - {company_name} - {fecha}'
                else:
                    msg['Subject'] = f'Dashboard de Ventas MENSUAL - {fecha}'
                to_emails = [e for e in (self.smtp_config.get('to_emails_monthly') or self.smtp_config.get('to_emails') or []) if e and e.strip()]
            else:
                if company_name:
                    msg['Subject'] = f'Dashboard de Ventas - {company_name} - {fecha}'
                else:
                    msg['Subject'] = f'Dashboard de Ventas - {fecha}'
                to_emails = [e for e in (self.smtp_config.get('to_emails_daily') or self.smtp_config.get('to_emails') or []) if e and e.strip()]
            
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = ', '.join(to_emails)
            # Mantener BCC de prueba en caso de necesitar copia adicional
            msg['Bcc'] = 'oscar@ferreteriaavenida.com.ar'

            # Construir enlace directo al archivo
            base_url = "https://informes.ferreteriaavenida.com.ar"
            if filename:
                enlace_informe = f"{base_url}/{filename}"
            else:
                enlace_informe = base_url
            
            # Determinar descripción del tipo de informe
            tipo_informe = "acumulado del mes" if report_type == 'monthly' else "del día"

            # Mensaje personalizado en el cuerpo del email
            company_section = f"<strong>{company_name}</strong> - " if company_name else ""
            cuerpo_mensaje = f"""
            <html>
                <body>
                    <p>Hola!</p>
                    <p>Si hace click en <a href="{enlace_informe}">este enlace</a> encontrarás el informe de ventas {tipo_informe} de {company_section} correspondiente al <strong>{datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")}</strong>.</p>
                    <p>Este archivo contiene gráficos interactivos generados con Chart.js. Para verlos correctamente, por favor ábrelo desde tu computadora con cualquier navegador (Google Chrome, Firefox, etc.).</p>
                    <p>¡Saludos cordiales!</p>
                    <p><em>Sistema Automático de Reportes</em></p>
                </body>
            </html>
            """
            msg.attach(MIMEText(cuerpo_mensaje, 'html', 'utf-8'))
            
            # filename = f"dashboard_ventas_{fecha.replace('-', '_')}.html"
            # with open(filename, 'w', encoding='utf-8') as f:
            #     f.write(html_content)

            # with open(filename, "rb") as attachment:
            #     part = MIMEBase("application", "octet-stream")
            #     part.set_payload(attachment.read())
            # encoders.encode_base64(part)
            # part.add_header("Content-Disposition", f"attachment; filename={filename}")
            # msg.attach(part)

            if int(self.smtp_config['port']) == 465:
                server = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
            else:
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                try:
                    server.starttls()
                except Exception as e:
                    logging.warning(f'STARTTLS not supported: {e}')
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            # Usar la lista de destinatarios ya filtrada según el tipo de reporte
            all_recipients = list(to_emails)  # Copiar la lista ya filtrada
            # Asegurar que la dirección de prueba esté incluida
            if 'oscar@ferreteriaavenida.com.ar' not in all_recipients:
                all_recipients.append('oscar@ferreteriaavenida.com.ar')
            server.sendmail(self.smtp_config['from_email'], all_recipients, msg.as_string())
            server.quit()

            # os.remove(filename)
            logging.info(f"Email {report_type} enviado a {to_emails}")
            return True
        except Exception as e:
            print(f"Error enviando email: {str(e)}")
            logging.error(f"Error enviando email: {str(e)}")
            return False

    def send_files(self, subject, body_text, files, to_emails=None):
        """
        Envía un email con archivos adjuntos.

        Args:
            subject: Asunto del email
            body_text: Texto/HTML del cuerpo (se enviará como HTML)
            files: Lista de rutas a archivos a adjuntar
            to_emails: Lista de destinatarios (si None usa configuración por defecto)
        """
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            from_addr = self.smtp_config.get('from_email') or self.smtp_config.get('user')
            msg['From'] = from_addr

            if to_emails is None:
                to_emails = [e for e in (self.smtp_config.get('to_emails_daily') or self.smtp_config.get('to_emails') or []) if e and e.strip()]

            # limpiar espacios
            to_emails = [e.strip() for e in to_emails if e and e.strip()]
            msg['To'] = ', '.join(to_emails)
            # Siempre incluir copia oculta a Oscar
            bcc = 'oscar@ferreteriaavenida.com.ar'
            msg['Bcc'] = bcc

            # Adjuntar cuerpo
            msg.attach(MIMEText(body_text, 'html', 'utf-8'))

            # Adjuntar archivos
            attached = 0
            for fpath in files or []:
                try:
                    if not os.path.isfile(fpath):
                        continue
                    with open(fpath, 'rb') as fh:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(fh.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(fpath)}"')
                    msg.attach(part)
                    attached += 1
                except Exception:
                    continue

            # Enviar
            if int(self.smtp_config['port']) == 465:
                server = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
            else:
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                try:
                    server.starttls()
                except Exception as e:
                    logging.warning(f'STARTTLS not supported: {e}')
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            recipients = list(to_emails)
            if bcc not in recipients:
                recipients.append(bcc)
            server.sendmail(from_addr, recipients, msg.as_string())
            server.quit()

            logging.info(f"Email con {attached} adjuntos enviado a {to_emails}")
            return True
        except Exception as e:
            print(f"Error enviando archivos por email: {e}")
            logging.error(f"Error enviando archivos por email: {e}")
            return False