import os
import shutil
import mysql.connector
import json
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

# Configuración de conexión a MySQL desde variables de entorno
config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME'),
    'raise_on_warnings': True,
    'use_pure': True
}

# Validar que las variables críticas estén presentes
required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Faltan variables en el archivo .env: {', '.join(missing_vars)}")

# Consulta SQL para ventas por hora
query = """
SELECT
    CONCAT(YEAR(stock_ve.fecha), LPAD(MONTH(stock_ve.FECHA), 2, '0')) AS periodo,
    stock_ve.clave,
    stock_ve.nota,
    movi.pagoant,
    stock_ve.REPARTO,
    sucursales.nombre AS sucursal,
    grupos.nombre AS grupo,
    vendedor.NOM_VEN AS vendedor,
    LPAD(HOUR(movi._HORA), 2, '0') AS hora,
    LPAD(FLOOR(MINUTE(movi._HORA) / 15) * 15, 2, '0') AS minuto_inicio,
    CONCAT(
        LPAD(HOUR(movi._HORA), 2, '0'),
        ':',
        LPAD(FLOOR(MINUTE(movi._HORA) / 15) * 15, 2, '0'),
        '-',
        LPAD(
            CASE
                WHEN (FLOOR(MINUTE(movi._HORA) / 15) * 15) + 15 >= 60 THEN (HOUR(movi._HORA) + 1) % 24
                ELSE HOUR(movi._HORA)
            END,
            2,
            '0'
        ),
        ':',
        LPAD(
            CASE
                WHEN (FLOOR(MINUTE(movi._HORA) / 15) * 15) + 15 >= 60 THEN '00'
                ELSE (FLOOR(MINUTE(movi._HORA) / 15) * 15) + 15
            END,
            2,
            '0'
        )
    ) AS intervalo_15min,
    SUM(
        CASE
            WHEN SUBSTR(movi.codigo, 1, 1) = 'C' THEN -stock_ve.cantidad
            ELSE stock_ve.cantidad
        END
    ) AS cantidad,
    stock.peso,
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
    INNER JOIN vendedor ON movi.VENDEDOR = vendedor.VENDEDOR
WHERE stock_ve.fecha >= 20250101
    and concat(movi.zona, movi.cliente) != '50000'
    and movi.empresa_id = 1
GROUP BY
    periodo,
    hora,
    minuto_inicio,
    stock_ve.clave,
    stock_ve.nota,
    movi.PAGOANT,
    stock_ve.reparto,
    sucursales.nombre,
    grupos.nombre,
    stock.peso,
    vendedor.NOM_VEN;
"""

def main():
    try:
        # Conexión a la base de datos
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(dictionary=True)

        # Ejecutar consulta
        cursor.execute(query)
        resultados = cursor.fetchall()

        # Convertir campos numéricos a float para JSON
        numeric_fields = ['cantidad', 'peso', 'total']
        for row in resultados:
            for key in numeric_fields:
                if row.get(key) is not None:
                    row[key] = float(row[key])

        # Nombre del archivo de salida
        output_file = 'ventas_hora.json'

        # Guardar en archivo JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)

        print(f"[OK] Exportado con exito: {len(resultados)} registros guardados en '{output_file}'")

        # Opcional: copiar al servidor de informes
        try:
            server_path = os.getenv("EXPORTS_WEB_DIR", "")
            if os.path.exists(server_path):
                dest_file = os.path.join(server_path, output_file)
                shutil.copy2(output_file, dest_file)
                print(f"[OK] Archivo copiado al servidor: {dest_file}")
            else:
                print(f"[ADVERTENCIA] No se puede acceder al servidor: {server_path}")
        except Exception as e:
            print(f"[ADVERTENCIA] Error al copiar al servidor: {e}")

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
