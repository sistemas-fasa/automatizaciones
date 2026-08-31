import os
import sys
import shutil
import mysql.connector
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

# Configuración de conexión a MySQL desde variables de entorno
config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST', 'localhost'),  # valor por defecto: localhost
    'database': os.getenv('DB_NAME'),
    'raise_on_warnings': True,
    'use_pure': True
}

# Validar que las variables críticas estén presentes
required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Faltan variables en el archivo .env: {', '.join(missing_vars)}")

def obtener_query_compras(fecha_desde, fecha_hasta, empresa_id=1):
    """Genera la consulta SQL con el rango de fechas especificado."""
    # Convertir fechas a formato YYYYMMDD
    fecha_desde_int = int(fecha_desde.strftime('%Y%m%d'))
    fecha_hasta_int = int(fecha_hasta.strftime('%Y%m%d'))

    return f"""
SELECT
    proveedo.PROVEEDOR,
    proveedo.NOMBRE,
    CONCAT(YEAR(pmovi.fecha), LPAD(MONTH(pmovi.fecha), 2, '0')) AS periodo,
    concat(pmovi.CODIGO, pmovi.clase, pmovi.comp) comprobante,
    SUM(
        CASE
            WHEN pmovi.CODIGO = 'C' THEN -pmovi.neto
            ELSE pmovi.neto
        END
    ) AS neto
FROM pmovi
INNER JOIN proveedo ON pmovi.PROVEEDOR = proveedo.PROVEEDOR
WHERE pmovi.PROVEEDOR IN (
        SELECT DISTINCT movmer.PROVEEDOR
        FROM movmer
        WHERE FECHAEM BETWEEN {fecha_desde_int} AND {fecha_hasta_int}
          AND tipo = 'I'
          AND proveedor NOT IN ('0002', '    ', '1058')
    )
  AND pmovi.FECHA BETWEEN {fecha_desde_int} AND {fecha_hasta_int}
  AND pmovi.codigo IN ('F', 'C', 'D')
  AND pmovi.empresa_id = {empresa_id}
GROUP BY 1, 2, 3, 4
ORDER BY proveedo.NOMBRE;
"""

def main():
    # Obtener rango de fechas desde argumentos o usar últimos 12 meses por defecto
    if len(sys.argv) >= 3:
        fecha_desde = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        fecha_hasta = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    else:
        fecha_hasta = date.today()
        fecha_desde = fecha_hasta - relativedelta(months=12)

    # Obtener empresa_id desde argumentos o usar 1 por defecto
    empresa_id = int(sys.argv[3]) if len(sys.argv) >= 4 else 1

    print(f"[INFO] Rango de fechas: {fecha_desde} a {fecha_hasta}")
    print(f"[INFO] Empresa ID: {empresa_id}")

    try:
        # Conexión a la base de datos
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(dictionary=True)  # Devuelve filas como diccionarios

        # Generar y ejecutar la consulta con el rango de fechas
        query = obtener_query_compras(fecha_desde, fecha_hasta, empresa_id)
        cursor.execute(query)

        # Obtener todos los resultados
        resultados = cursor.fetchall()

        # Convertir a formato JSON serializable
        # (mysql-connector ya devuelve tipos compatibles, pero aseguramos fechas si hubiera)
        for row in resultados:
            # Aseguramos que 'neto' sea float (por si viene como Decimal)
            if 'neto' in row and row['neto'] is not None:
                row['neto'] = float(row['neto'])
            # 'periodo' ya es string por la función CONCAT en SQL

        # Guardar en archivo JSON
        with open('compras_proveedores.json', 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)
        # Copiar al servidor de informes
        try:
            server_path = os.getenv("EXPORTS_WEB_DIR", "")
            if os.path.exists(server_path):
                dest_file = os.path.join(server_path, 'compras_proveedores.json')
                shutil.copy2('compras_proveedores.json', dest_file)
                print(f"[OK] Archivo copiado al servidor: {dest_file}")
            else:
                print(f"[ADVERTENCIA] No se puede acceder al servidor: {server_path}")
        except Exception as e:
            print(f"[ADVERTENCIA] Error al copiar al servidor: {e}")

        print(f"[OK] Exportado con exito: {len(resultados)} registros guardados en 'compras_proveedores.json'")

    except mysql.connector.Error as err:
        print(f"[ERROR] Error de base de datos: {err}")
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()

if __name__ == '__main__':
    main()
