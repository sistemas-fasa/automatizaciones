import mysql.connector
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import date
import os
import logging

# Configuración del logging
logging.basicConfig(
    filename='reporte.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Cargar variables de entorno
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

EMAIL_CONFIG = {
    'host': os.getenv('EMAIL_HOST'),
    'port': int(os.getenv('EMAIL_PORT')),
    'user': os.getenv('EMAIL_USER'),
    'password': os.getenv('EMAIL_PASSWORD'),
    'to': os.getenv('EMAIL_TO')
}

# Conectar a la base de datos y consultar
def obtener_datos_remitos():
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = """
            SELECT r._usuario usuario, COUNT(DISTINCT r.id_remito) AS cantidad_remitos
            FROM remitos r
            JOIN datos_remito d ON r.id_remito = d.idremito
            WHERE DATE(r.fecha) = curdate() AND d.codigo_barra = 1
            GROUP BY r._usuario
            ORDER BY cantidad_remitos DESC
        """

        cursor.execute(query)
        resultados = cursor.fetchall()
        conn.close()
        logging.info("Consulta de remitos ejecutada con éxito.")
    except mysql.connector.Error as err:
        logging.error(f"Error al conectar a la base de datos: {err}")
        return pd.DataFrame()

    return pd.DataFrame(resultados, columns=['Usuario', 'Remitos con código de barra'])

# Crear el cuerpo del correo
def construir_mensaje_html(df):
    if df.empty:
        return "<p>No se registraron remitos con código de barra hoy.</p>"

    estilo = """
    <style>
        table {
            font-family: Arial, sans-serif;
            border-collapse: collapse;
            width: 100%;
            max-width: 600px;
            margin: 20px auto;
        }
        th {
            background-color: #2c3e50;
            color: white;
            padding: 10px;
            text-align: left;
        }
        td {
            border: 1px solid #ddd;
            padding: 10px;
        }
        tr:nth-child(even) {
            background-color: #f6f8fa;
        }
        tr:hover {
            background-color: #e1ecf4;
        }
        caption {
            caption-side: top;
            font-size: 1.2em;
            margin-bottom: 10px;
            color: #333;
            font-weight: bold;
        }
    </style>
    """

    tabla = df.to_html(
        index=False,
        border=0,
        justify="center",
        classes="reporte"
    )

    return f"{estilo}{tabla}"


# Enviar el correo
def enviar_reporte(df):
    try:
        mensaje = MIMEMultipart()
        mensaje['From'] = EMAIL_CONFIG['user']
        mensaje['To'] = EMAIL_CONFIG['to']
        mensaje['Subject'] = f"Reporte de Remitos - {date.today()}"
        mensaje['Bcc'] = 'oscar@ferreteriaavenida.com.ar'

        html = construir_mensaje_html(df)
        mensaje.attach(MIMEText(html, 'html'))

        if EMAIL_CONFIG['port'] == 465:
            servidor = smtplib.SMTP_SSL(EMAIL_CONFIG['host'], EMAIL_CONFIG['port'])
        else:
            servidor = smtplib.SMTP(EMAIL_CONFIG['host'], EMAIL_CONFIG['port'])
            servidor.ehlo()
            # servidor.starttls()

        servidor.login(EMAIL_CONFIG['user'], EMAIL_CONFIG['password'])
        servidor.send_message(mensaje)
        servidor.quit()
        print("Correo enviado con exito.")
        logging.info("Correo enviado con éxito.")
    except smtplib.SMTPException as e:
        print(f"Error al enviar el correo: {e}")
        logging.error(f"Error al enviar el correo: {e}")
    
# Ejecución principal
if __name__ == "__main__":
    df = obtener_datos_remitos()
    enviar_reporte(df)
