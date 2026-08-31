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

# Consulta SQL para ventas por vendedor, hora (15 min), grupo y tipo
query = """
SELECT
  CASE r.tipo
    WHEN 'Z' THEN 'Presupuesto'
    WHEN 'C' THEN 'Pedidos'
    WHEN 'T' THEN 'Detalle Mostrador'
    WHEN 'X' THEN 'Remito'
    WHEN 'O' THEN 'Orden de entrega'
    WHEN 'U' THEN 'Entrega Interna'
    WHEN 'P' THEN 'Pedido de sucursal'
    ELSE 'Sin Determinar'
  END AS tipo,
  r.facturado,
  r.fecha,
  d.cliente,
  r.nombre,
  d.articulo,
  d.detalle,
  d.cantidad,
  v.NOM_VEN AS vendedor,
  g.nombre AS grupos,
  CONCAT(
      LPAD(HOUR(r._HORA), 2, '0'),
      ':',
      LPAD(FLOOR(MINUTE(r._HORA) / 15) * 15, 2, '0'),
      '-',
      LPAD(
          CASE
              WHEN (FLOOR(MINUTE(r._HORA) / 15) * 15) + 15 >= 60 THEN (HOUR(r._HORA) + 1) % 24
              ELSE HOUR(r._HORA)
          END,
          2,
          '0'
      ),
      ':',
      LPAD(
          CASE
              WHEN (FLOOR(MINUTE(r._HORA) / 15) * 15) + 15 >= 60 THEN '00'
              ELSE (FLOOR(MINUTE(r._HORA) / 15) * 15) + 15
          END,
          2,
          '0'
      )
  ) AS intervalo_15min,
  ((d.CANTIDAD * d.UNITARIO) / ((d.IVA / 100) + 1)) AS neto
FROM remitos r
INNER JOIN detaremi d ON r.tipo = d.tipo AND r.comp = d.comp
INNER JOIN vendedor v ON r.VENDEDOR = v.VENDEDOR
INNER JOIN grupos g ON SUBSTR(d.ARTICULO, 1, 3) = g.codigo
WHERE r.fecha >= 20250101
    and concat(r.zona, r.cliente) not in ('50000', '00004', '00006')
    and r.empresa_id = 1
"""

def main():
    try:
        # Conexión a la base de datos
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(dictionary=True)

        # Ejecutar consulta
        cursor.execute(query)
        resultados = cursor.fetchall()

        # Convertir campos numéricos a float/int para JSON (por seguridad)
        for row in resultados:
            # 'cantidad' suele ser DECIMAL o FLOAT
            if row.get('cantidad') is not None:
                row['cantidad'] = float(row['cantidad'])
            # 'neto' también es DECIMAL
            if row.get('neto') is not None:
                row['neto'] = float(row['neto'])
            # 'fecha' puede ser DATE → convertir a string si es necesario
            if row.get('fecha') is not None and hasattr(row['fecha'], 'strftime'):
                row['fecha'] = row['fecha'].strftime('%Y-%m-%d')

        # Nombre del archivo de salida
        output_file = 'ventas_vendedor_hora_grupo.json'

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
