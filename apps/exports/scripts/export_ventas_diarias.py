#!/usr/bin/env python3
# scripts/ventas_diarias.py

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
import sys
import pandas as pd
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime

# Cargar variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'raise_on_warnings': True,
    'use_pure': True
}

# Validar que las variables críticas estén presentes
required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Faltan variables en el archivo .env: {', '.join(missing_vars)}")

OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{OUTPUT_DIR}/ejecucion.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# === FUNCIONES ===
def run_query_to_json(query, filename):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        df = pd.read_sql(query, connection)
        connection.close()

        # Limpieza para JSON
        for col in df.select_dtypes(include=['datetime64']).columns:
            df[col] = df[col].astype(str)
        df = df.where(pd.notnull(df), None)

        filepath = f"{OUTPUT_DIR}/{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        df.to_json(filepath, orient='records', indent=2)
        logging.info(f"[OK] {filename}.json generado exitosamente")
        return True, filepath
    except Exception as e:
        logging.error(f"[ERROR] Error en {filename}: {e}")
        return False, str(e)


def enviar_correo(informe, archivos=None):
    try:
        # Cargar variables
        smtp_server = os.getenv('EMAIL_SMTP_SERVER') or os.getenv('SMTP_SERVER')
        smtp_port = os.getenv('EMAIL_SMTP_PORT') or os.getenv('SMTP_PORT')
        email_from = os.getenv('EMAIL_FROM')
        email_pass = os.getenv('EMAIL_PASSWORD') or os.getenv('EMAIL_PASS')
        email_to = os.getenv('EMAIL_TO')

        # Validar que las variables de correo estén configuradas
        if not all([smtp_server, smtp_port, email_from, email_pass, email_to]):
            logging.warning("[ADVERTENCIA] Variables de correo no configuradas en .env - omitiendo envío de email")
            return

        smtp_port = int(smtp_port)

        # Crear mensaje multiparte (texto y HTML)
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = f"[VENTAS DIARIAS] Reporte de ejecucion - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Construir detalle de archivos generados
        if archivos:
            archivos_info = "<br>".join([
                f"[ARCHIVO] <code>{os.path.basename(archivo)}</code> ({os.path.getsize(archivo) // 1024} KB)"
                for archivo in archivos if os.path.isfile(archivo)
            ])
        else:
            archivos_info = "No se generaron nuevos archivos."

        # Cuerpo en HTML con enlace clickeable
        html_body = f"""
        <html>
          <body>
            <p>Informe de ejecución del script de generación de reportes de ventas:</p>
            <pre style="background-color: #f4f4f4; padding: 15px; border: 1px solid #ccc; font-family: monospace; font-size: 14px;">
{informe}
            </pre>
            <p><strong>[DASHBOARD] Accede al dashboard aqui:</strong><br>
            <a href="http://192.168.0.195:8080" target="_blank" style="font-size: 16px; color: #007BFF; text-decoration: underline;">
              Ver dashboard
            </a></p>
            <p><strong>Archivos generados:</strong><br>
            {archivos_info}
            </p>
            <hr>
            <p><em>Este es un mensaje automatico generado por el sistema.<br>
            Directorio de salida: {OUTPUT_DIR}</em></p>
          </body>
        </html>
        """

        # Adjuntar HTML
        part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part)

        # Conectar y enviar
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            try:
                server.starttls()
            except smtplib.SMTPException:
                pass
        server.login(email_from, email_pass)
        server.sendmail(email_from, email_to, msg.as_string().encode('utf-8'))
        server.quit()

        logging.info("[OK] Correo enviado exitosamente (con enlace clickeable)")

    except Exception as e:
        logging.error(f"[ERROR] Fallo al enviar correo: {e}")

# === Consulta: Ventas por Sucursal ===
QUERY_SUCURSAL = """
SELECT
    CONCAT(YEAR(stock_ve.fecha), LPAD(MONTH(stock_ve.FECHA), 2, '0')) AS periodo,
    stock_ve.clave,
    stock_ve.nota,
    movi.pagoant,
    stock_ve.REPARTO,
    sucursales.nombre AS sucursal,
    grupos.nombre AS grupo,
    SUM(
        CASE WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -stock_ve.cantidad ELSE stock_ve.cantidad END
    ) AS cantidad,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -((stock_ve.CANTIDAD * stock_ve.UNITARIO) / ((stock_ve.IVA / 100) + 1))
            ELSE ((stock_ve.CANTIDAD * stock_ve.UNITARIO) / ((stock_ve.IVA / 100) + 1))
        END
    ) AS total
FROM stock_ve
    INNER JOIN grupos ON SUBSTR(stock_ve.clave, 1, 3) = grupos.CODIGO
    INNER JOIN stock ON stock_ve.clave = stock.clave
    INNER JOIN movi ON CONCAT(SUBSTR(movi.codigo, 1, 1), movi.CLASE, movi.comp) = CONCAT(SUBSTR(stock_ve.codigo, 1, 1), stock_ve.clase, stock_ve.comp)
    INNER JOIN sucursales ON movi.SUCURSAL = sucursales.id_sucursal
WHERE stock_ve.fecha >= 20250101
    AND movi.empresa_id = 1
GROUP BY periodo, stock_ve.clave, stock_ve.nota, movi.PAGOANT, stock_ve.reparto, sucursales.nombre, grupos.nombre;
"""

# --- VENTAS POR RANGO DE 15 MINUTOS ---
QUERY_VENTAS_15MIN = """
SELECT
    CONCAT(YEAR(stock_ve.fecha), LPAD(MONTH(stock_ve.FECHA), 2, '0')) AS periodo,
    stock_ve.clave,
    stock_ve.nota,
    movi.pagoant,
    stock_ve.REPARTO,
    sucursales.nombre AS sucursal,
    grupos.nombre AS grupo,
    vendedor.NOM_VEN AS vendedor,
    CASE
        WHEN MINUTE(movi._HORA) < 15 THEN CONCAT(LPAD(HOUR(movi._HORA), 2, '0'), ':00 - ', LPAD(HOUR(movi._HORA), 2, '0'), ':14')
        WHEN MINUTE(movi._HORA) < 30 THEN CONCAT(LPAD(HOUR(movi._HORA), 2, '0'), ':15 - ', LPAD(HOUR(movi._HORA), 2, '0'), ':29')
        WHEN MINUTE(movi._HORA) < 45 THEN CONCAT(LPAD(HOUR(movi._HORA), 2, '0'), ':30 - ', LPAD(HOUR(movi._HORA), 2, '0'), ':44')
        ELSE CONCAT(LPAD(HOUR(movi._HORA), 2, '0'), ':45 - ', LPAD(HOUR(movi._HORA), 2, '0'), ':59')
    END AS rango_15min,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -stock_ve.cantidad
            ELSE stock_ve.cantidad
        END
    ) AS cantidad,
    stock.peso,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -((`stock_ve`.`CANTIDAD` * `stock_ve`.`UNITARIO`) / ((`stock_ve`.`IVA` / 100) + 1))
            ELSE ((`stock_ve`.`CANTIDAD` * `stock_ve`.`UNITARIO`) / ((`stock_ve`.`IVA` / 100) + 1))
        END
    ) AS total
FROM stock_ve
    INNER JOIN grupos ON SUBSTR(stock_ve.clave, 1, 3) = grupos.CODIGO
    INNER JOIN stock ON stock_ve.clave = stock.clave
    INNER JOIN movi ON CONCAT(SUBSTR(movi.codigo, 1, 1), movi.CLASE, movi.comp) = CONCAT(SUBSTR(stock_ve.codigo, 1, 1), stock_ve.clase, stock_ve.comp)
    INNER JOIN sucursales ON movi.SUCURSAL = sucursales.id_sucursal
    INNER JOIN vendedor ON movi.VENDEDOR = vendedor.VENDEDOR
WHERE stock_ve.fecha >= 20250101
    AND movi.empresa_id = 1
GROUP BY
    periodo,
    rango_15min,
    stock_ve.clave,
    stock_ve.nota,
    movi.PAGOANT,
    stock_ve.reparto,
    sucursales.nombre,
    grupos.nombre,
    vendedor.NOM_VEN,
    stock.peso;
"""
# ventas por cliente
QUERY_VENTAS_CLIENTES = """
SELECT
    CONCAT(YEAR(dr.fecha), LPAD(MONTH(dr.FECHA), 2, '0')) AS periodo,
    dr.articulo,
    dr.DETALLE,
    dr.UNIDAD,
    dr.PAGOANT,
    dr.REPARTO,
    l.NOMBRE AS localidad,
    CONCAT(r.zona, r.cliente) AS cliente,
    c.NOMBRE,
    c.lista,
    g.nombre AS grupo,
    SUM(dr.cantidad) AS cantidad,
    s.peso,
    SUM((dr.CANTIDAD * dr.UNITARIO) / ((dr.IVA / 100) + 1)) AS total
FROM detaremi dr
FORCE INDEX (fecha)  -- Forzar uso del índice de fecha
INNER JOIN grupos g ON dr.articulo LIKE CONCAT(SUBSTR(g.CODIGO, 1, 3), '%')
INNER JOIN stock s ON dr.articulo = s.clave
INNER JOIN remitos r ON r.tipo = dr.tipo AND r.comp = dr.comp
INNER JOIN localidad l ON r.LOCALIDAD = l.CODIGO
INNER JOIN clientes c ON r.zona = c.ZONA AND r.cliente = c.CLIENTE
WHERE dr.fecha BETWEEN 20240101 AND curdate()
    AND r.tipo = 'N'
    AND r.empresa_id = 1
GROUP BY
    periodo,
    dr.articulo,
    dr.detalle,
    dr.PAGOANT,
    dr.reparto,
    l.nombre,
    cliente,
    g.nombre,
    s.peso
union all
SELECT
    CONCAT(YEAR(stock_ve.fecha), LPAD(MONTH(stock_ve.FECHA), 2, '0')) AS periodo,
    stock_ve.clave,
    stock_ve.nota,
    stock_ve.UNIDAD,
    movi.pagoant,
    stock_ve.REPARTO,
    LOCALIDAD.NOMBRE localidad,
    concat(movi.zona, movi.cliente) cliente,
    clientes.NOMBRE,
    clientes.lista,
    grupos.nombre AS grupo,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -stock_ve.cantidad
            ELSE stock_ve.cantidad
        END
    ) AS cantidad,
    stock.peso,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -((`stock_ve`.`CANTIDAD` * `stock_ve`.`UNITARIO`) / ((`stock_ve`.`IVA` / 100) + 1))
            ELSE ((`stock_ve`.`CANTIDAD` * `stock_ve`.`UNITARIO`) / ((`stock_ve`.`IVA` / 100) + 1))
        END
    ) AS total
FROM stock_ve
    INNER JOIN grupos ON SUBSTR(stock_ve.clave, 1, 3) = grupos.CODIGO
    INNER JOIN stock ON stock_ve.clave = stock.clave
    INNER JOIN movi ON CONCAT(SUBSTR(movi.codigo, 1, 1), movi.CLASE, movi.comp) = CONCAT(SUBSTR(stock_ve.codigo, 1, 1), stock_ve.clase, stock_ve.comp)
    INNER JOIN localidad ON movi.LOCALIDAD = LOCALIDAD.CODIGO
    INNER JOIN clientes on concat(movi.zona, movi.cliente) = concat(clientes.ZONA, clientes.CLIENTE)
WHERE stock_ve.fecha between 20240101 and curdate()
    AND movi.empresa_id = 1
GROUP BY
    periodo,
    stock_ve.clave,
    stock_ve.nota,
    movi.PAGOANT,
    stock_ve.reparto,
    LOCALIDAD.nombre,
    cliente,
    grupos.nombre,
    stock.peso
"""

# ---ventas por localidad
QUERY_VENTAS_LOCALIDAD = """
SELECT
    CONCAT(YEAR(stock_ve.fecha), LPAD(MONTH(stock_ve.FECHA), 2, '0')) AS periodo,
    stock_ve.clave,
    stock_ve.nota,
    movi.pagoant,
    stock_ve.REPARTO,
    LOCALIDAD.NOMBRE localidad,
    grupos.nombre AS grupo,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -stock_ve.cantidad
            ELSE stock_ve.cantidad
        END
    ) AS cantidad,
    stock.peso,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -((`stock_ve`.`CANTIDAD` * `stock_ve`.`UNITARIO`) / ((`stock_ve`.`IVA` / 100) + 1))
            ELSE ((`stock_ve`.`CANTIDAD` * `stock_ve`.`UNITARIO`) / ((`stock_ve`.`IVA` / 100) + 1))
        END
    ) AS total
FROM stock_ve
    INNER JOIN grupos ON SUBSTR(stock_ve.clave, 1, 3) = grupos.CODIGO
    INNER JOIN stock ON stock_ve.clave = stock.clave
    INNER JOIN movi ON CONCAT(SUBSTR(movi.codigo, 1, 1), movi.CLASE, movi.comp) = CONCAT(SUBSTR(stock_ve.codigo, 1, 1), stock_ve.clase, stock_ve.comp)
    INNER JOIN localidad ON movi.LOCALIDAD = LOCALIDAD.CODIGO
WHERE stock_ve.fecha between 20240101 and curdate()
    AND movi.empresa_id = 1
GROUP BY
    periodo,
    stock_ve.clave,
    stock_ve.nota,
    movi.PAGOANT,
    stock_ve.reparto,
    LOCALIDAD.nombre,
    grupos.nombre,
    stock.peso;
"""

# === Ejecutar consultas ===
if __name__ == "__main__":
    resultados = []
    archivos_generados = []
    logging.info("[INICIO] Iniciando proceso de generacion de reportes de ventas")

    # Ejecutar consulta por sucursal
    exito1, salida1 = run_query_to_json(QUERY_SUCURSAL, "ventas_sucursal")
    resultados.append(f"Ventas por sucursal: {'[OK]' if exito1 else '[ERROR]'}")
    # Ejecutar consulta por hora
    exito2, salida2 = run_query_to_json(QUERY_VENTAS_15MIN, "ventas_hora")
    resultados.append(f"Ventas por hora: {'[OK]' if exito2 else '[ERROR]'}")
    # Ejecutar consulta por cliente
    exito3, salida3 = run_query_to_json(QUERY_VENTAS_CLIENTES, "ventas_clientes")
    resultados.append(f"Ventas por cliente: {'[OK]' if exito3 else '[ERROR]'}")
    # Ejecutar consulta por localidad
    exito4, salida4 = run_query_to_json(QUERY_VENTAS_LOCALIDAD, "ventas_localidad")
    resultados.append(f"Ventas por localidad: {'[OK]' if exito4 else '[ERROR]'}")

    # Adjuntar solo archivos generados
    if exito1 and isinstance(salida1, str): archivos_generados.append(salida1)
    if exito2 and isinstance(salida2, str): archivos_generados.append(salida2)
    if exito3 and isinstance(salida3, str): archivos_generados.append(salida3)
    if exito4 and isinstance(salida4, str): archivos_generados.append(salida4)
    informe = "\n".join(resultados)
    logging.info("[EMAIL] Enviando correo con el informe de resultados")

    # Enviar correo
    enviar_correo(informe, archivos=archivos_generados)

    # Salir con código de error si falló algo
    if not (exito1 and exito2 and exito3 and exito4):
        sys.exit(1)
