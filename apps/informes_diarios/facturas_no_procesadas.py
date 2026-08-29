import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error


env_file = Path(
    os.getenv("FACTURAS_ENV_FILE", Path(__file__).with_name(".env"))
)
load_dotenv(env_file)


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_SSL = env_bool("SMTP_USE_SSL")
SMTP_USE_STARTTLS = env_bool("SMTP_USE_STARTTLS", True)
TO_EMAILS = [
    email.strip()
    for email in os.getenv(
        "TO_EMAILS",
        "sistemas@ferreteriaavenida.com.ar,compras@ferreteriaavenida.com.ar",
    ).split(",")
    if email.strip()
]
BCC_EMAILS = [
    email.strip()
    for email in os.getenv(
        "BCC_EMAILS", "oscar@ferreteriaavenida.com.ar"
    ).split(",")
    if email.strip()
]
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

db_config = {
    "host": "192.168.0.150",
    "database": "fasa",
    "user": "root",
    "password": "fasca",
}

smtp_server = SMTP_SERVER
smtp_port = SMTP_PORT
sender_email = SMTP_USER
sender_password = SMTP_PASSWORD
receiver_email = TO_EMAILS
subject = "Reporte de Facturas no procesadas desde el 01/06/2025"


def ejecutar_consulta():
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        query = """
        SELECT
            movi.idmovi id,
            stock_ve.codigo Codigo,
            stock_ve.CLASE Clase,
            stock_ve.comp Comprobante,
            CONCAT(stock_ve.ZONA, stock_ve.cliente) AS Cliente,
            movi.NOMBRE Nombre,
            movi.Fecha Fecha,
            stock_ve.clave Articulo,
            stock_ve.unidad Unidad,
            stock_ve.cantidad Cantidad
        FROM movi
        INNER JOIN stock_ve
            ON CONCAT(SUBSTR(movi.CODIGO, 1,1), movi.clase, movi.comp) = CONCAT(stock_ve.CODIGO, stock_ve.CLASE, stock_ve.COMP)
        WHERE movi.fecha >= 20250601
          AND reparte = 'A'
          AND stock_ve.Procesado = 0
          AND movi.pagoant = 0
        UNION
        SELECT d.IDREMITO id, d.tipo codigo, '' clase,
               d.COMP comprobante, d.cliente,
               r.NOMBRE, r.fecha,
               d.ARTICULO articulo,
               d.UNIDAD, d.cantidad
          FROM detaremi d
          INNER JOIN remitos r ON d.tipo = r.TIPO AND d.comp = r.comp
         WHERE d.procesado = 0
           AND d.tipo = 'X'
           AND d.fecha >= 20250601
           AND d.reparto = 'N'
           AND SUBSTR(d.comp,1,4) IN ('0011', '0013')
        """
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return columns, result
    except Error as error:
        print(f"Error al conectar o ejecutar la consulta: {error}")
        return [], []
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def generar_texto_plano(datos, columnas):
    lineas = [subject, ""]
    lineas.append("\t".join(str(col) for col in columnas))
    for fila in datos:
        lineas.append("\t".join(str(celda) for celda in fila))
    return "\n".join(lineas)


def generar_html_tabla(datos, columnas):
    html = """
    <html>
    <head>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h2>Reporte de Facturas no Procesadas</h2>
        <table>
            <thead>
                <tr>
    """

    html += "".join([f"<th>{col}</th>" for col in columnas])
    html += """
                </tr>
            </thead>
            <tbody>
    """

    for fila in datos:
        html += "<tr>"
        html += "".join([f"<td>{celda}</td>" for celda in fila])
        html += "</tr>"

    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html


def enviar_correo(html_content, texto_plano):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(receiver_email)
    msg.attach(MIMEText(texto_plano, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        smtp_class = smtplib.SMTP_SSL if SMTP_USE_SSL else smtplib.SMTP
        with smtp_class(smtp_server, smtp_port, timeout=30) as server:
            if SMTP_USE_STARTTLS and not SMTP_USE_SSL:
                server.starttls()
                server.ehlo()
            server.login(sender_email, sender_password)
            all_recipients = receiver_email + BCC_EMAILS
            refused = server.sendmail(sender_email, all_recipients, msg.as_string())
            if refused:
                print(
                    "Correo aceptado por el servidor pero rechazado para: "
                    f"{refused}"
                )
            else:
                print(
                    "Correo enviado exitosamente a: " + ", ".join(all_recipients)
                )
    except Exception as error:
        print(
            f"Error al enviar el correo ({smtp_server}:{smtp_port}): {error}"
        )


if __name__ == "__main__":
    columnas, datos = ejecutar_consulta()
    if datos:
        html_tabla = generar_html_tabla(datos, columnas)
        texto_plano = generar_texto_plano(datos, columnas)
        enviar_correo(html_tabla, texto_plano)
    else:
        print("No se encontraron resultados para enviar.")
