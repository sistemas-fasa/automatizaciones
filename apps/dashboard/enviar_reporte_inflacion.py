import os
import sys
import logging
from datetime import date
from dotenv import load_dotenv
import shutil

# Add the current directory to sys.path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from DatabaseManager import DatabaseManager
from ReportGenerator import ReportGenerator
from EmailSender import EmailSender

# Load environment variables
load_dotenv()

# Configuration
LOG_FILE = os.path.join(current_dir, 'dashboard.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def main():
    try:
        logging.info("Iniciando envío de reporte de inflación interanual...")

        # 1. Setup Database Connection
        db_config = {
            'host': os.getenv('DB_HOST', '192.168.0.150'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'fasca'),
            'database': os.getenv('DB_NAME', 'fasa'),
            'port': int(os.getenv('DB_PORT', '3306'))
        }

        empresa_id = 1
        db_manager = DatabaseManager(db_config, empresa_id=empresa_id)

        # 2. Prepare data and report
        fecha_consulta = date.today().strftime('%Y-%m-%d')
        logging.info(f"Obteniendo detalles de inflación para {fecha_consulta}")
        inflacion_details = db_manager.get_inflacion_interanual_details(fecha_consulta)

        rep_gen = ReportGenerator()
        company_map = {
            1: {'title': 'Ferreteria Avenida SA', 'color': '#E60000'},
            2: {'title': 'Steffen Hnos SRL', 'color': '#006400'},
            3: {'title': 'Transporte Avenida SRL', 'color': '#FF5722'},
        }
        comp_info = company_map.get(empresa_id, {'title': 'Empresa', 'color': '#1F2937'})

        html_content = rep_gen.generate_inflacion_details_html(inflacion_details, comp_info, fecha_consulta)

        filename = f"inflacion_interanual_{empresa_id}_{fecha_consulta.replace('-', '_')}_reporte.html"
        filepath = os.path.join(current_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logging.info(f"Reporte generado en: {filepath}")

        # Copiar también a la carpeta principal donde están los demás reportes
        try:
            parent_dir = os.path.dirname(current_dir)
            workspace_dest = os.path.join(parent_dir, filename)
            shutil.copy2(filepath, workspace_dest)
            logging.info(f"Reporte copiado a carpeta principal de reportes: {workspace_dest}")
        except Exception as e:
            logging.error(f"No se pudo copiar el reporte a la carpeta principal: {e}")

        # 3. Copiar al servidor si existe la ruta de informes
        copied = False
        try:
            # /var/www/html/informes es mount a /srv/fasa-data/data/informes (195 dado de baja).
            server_path = "/var/www/html/informes"

            if os.path.exists(server_path):
                try:
                    dest_file = os.path.join(server_path, filename)
                    shutil.copy2(filepath, dest_file)
                    logging.info(f"Reporte copiado a servidor: {dest_file}")
                    # copiar archivos de histórico si existen
                    if os.path.exists(os.path.join(current_dir, 'history.json')):
                        shutil.copy2(os.path.join(current_dir, 'history.json'), os.path.join(server_path, 'history.json'))
                    if os.path.exists(os.path.join(current_dir, 'history_viewer.html')):
                        shutil.copy2(os.path.join(current_dir, 'history_viewer.html'), os.path.join(server_path, 'history_viewer.html'))
                    copied = True
                except Exception as e:
                    logging.error(f"Error copiando al servidor: {e}")
            else:
                logging.warning(f"Ruta de servidor no existe: {server_path}")
        except Exception as e:
            logging.error(f"Error verificando/copiando al servidor: {e}")

        # 4. Prepare SMTP config and send EMAIL WITH LINK (not attachment)
        smtp_config = {
            'server': os.getenv('SMTP_SERVER'),
            'port': int(os.getenv('SMTP_PORT', 587)),
            'user': os.getenv('SMTP_USER'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL'),
            'to_emails_daily': [e.strip() for e in os.getenv('TO_EMAILS_INFLATION', 'compras@ferreteriaavenida.com.ar').split(',') if e.strip()],
            'to_emails': [],
            'to_emails_monthly': []
        }

        email_sender = EmailSender(smtp_config)

        # send_email builds the link using the filename and the hardcoded base URL
        sent = email_sender.send_email(html_content=html_content, fecha=fecha_consulta, filename=filename, report_type='daily', company_name=comp_info['title'])

        if sent:
            logging.info("Email enviado exitosamente.")
        else:
            logging.error("Fallo al enviar el email.")

        # 5. Cleanup local temp file
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info("Archivo temporal eliminado.")
        except Exception:
            pass

    except Exception as e:
        logging.error(f"Error crítico en enviar_reporte_inflacion: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
