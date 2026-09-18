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

def obtener_query_ventas_dia(fecha_desde, fecha_hasta, empresa_id=1):
    """Genera la consulta SQL con el rango de fechas especificado."""
    # Convertir fechas a formato YYYYMMDD
    fecha_desde_int = int(fecha_desde.strftime('%Y%m%d'))
    fecha_hasta_int = int(fecha_hasta.strftime('%Y%m%d'))

    return f"""
SELECT
    CONCAT(YEAR(movi.fecha), LPAD(MONTH(movi.fecha), 2, '0')) AS periodo,
    CASE WEEKDAY(movi.fecha)
        WHEN 0 THEN 'Lunes'
        WHEN 1 THEN 'Martes'
        WHEN 2 THEN 'Miércoles'
        WHEN 3 THEN 'Jueves'
        WHEN 4 THEN 'Viernes'
        WHEN 5 THEN 'Sábado'
        WHEN 6 THEN 'Domingo'
    END AS dia_semana,
    grupos.nombre AS grupo,
    LOCALIDAD.NOMBRE AS localidad,
    stock_ve.REPARTO,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -stock_ve.cantidad
            ELSE stock_ve.cantidad
        END
    ) AS cantidad_total,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -((stock_ve.CANTIDAD * stock_ve.UNITARIO) / ((stock_ve.IVA / 100) + 1))
            ELSE ((stock_ve.CANTIDAD * stock_ve.UNITARIO) / ((stock_ve.IVA / 100) + 1))
        END
    ) AS total_neto,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -((stock_ve.FLETE + stock_ve.FLETETRANSP) / ((stock_ve.IVA / 100) + 1))
            ELSE ((stock_ve.FLETE + stock_ve.FLETETRANSP) / ((stock_ve.IVA / 100) + 1))
        END
    ) AS flete_neto
FROM stock_ve
    INNER JOIN grupos ON SUBSTR(stock_ve.clave, 1, 3) = grupos.CODIGO
    INNER JOIN stock ON stock_ve.clave = stock.clave
    INNER JOIN movi ON CONCAT(SUBSTR(movi.codigo, 1, 1), movi.CLASE, movi.comp) = CONCAT(SUBSTR(stock_ve.codigo, 1, 1), stock_ve.clase, stock_ve.comp)
    INNER JOIN localidad ON movi.LOCALIDAD = LOCALIDAD.CODIGO
WHERE
    stock_ve.fecha BETWEEN {fecha_desde_int} AND {fecha_hasta_int}
    AND movi.empresa_id = {empresa_id}
GROUP BY
    periodo,
    dia_semana,
    grupos.nombre,
    LOCALIDAD.NOMBRE,
    stock_ve.REPARTO
ORDER BY
    periodo,
    FIELD(dia_semana, 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'),
    grupos.nombre,
    LOCALIDAD.NOMBRE;
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
        cursor = cnx.cursor(dictionary=True)

        # Generar y ejecutar consulta con el rango de fechas
        query = obtener_query_ventas_dia(fecha_desde, fecha_hasta, empresa_id)
        cursor.execute(query)

        # Obtener resultados
        resultados = cursor.fetchall()

        # Asegurar compatibilidad con JSON (convertir Decimals a float)
        for row in resultados:
            for key in ['cantidad_total', 'total_neto', 'flete_neto']:
                if row[key] is not None:
                    row[key] = float(row[key])

        # Determinar la ruta correcta (carpeta padre si estamos en automation)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.getenv("EXPORTS_WEB_DIR", os.path.dirname(script_dir))
        output_file = os.path.join(parent_dir, 'venta_dia_semana.json')

        # Guardar en archivo JSON en la carpeta web
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)
        # Copiar al servidor de informes
        try:
            server_path = os.getenv("EXPORTS_WEB_DIR", "")
            if os.path.exists(server_path):
                dest_file = os.path.join(server_path, 'venta_dia_semana.json')
                shutil.copy2(output_file, dest_file)
                print(f"[OK] Archivo copiado al servidor: {dest_file}")
            else:
                print(f"[ADVERTENCIA] No se puede acceder al servidor: {server_path}")
        except Exception as e:
            print(f"[ADVERTENCIA] Error al copiar al servidor: {e}")

        print(f"[OK] Exportado con exito: {len(resultados)} registros guardados en '{output_file}'")

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
