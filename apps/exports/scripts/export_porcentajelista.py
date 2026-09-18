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

# Consulta SQL
query = """
SELECT * FROM estadisticas.porcentajelista
"""

def main():
    try:
        # Conexión a la base de datos
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(dictionary=True)  # Devuelve filas como diccionarios

        # Ejecutar la consulta
        cursor.execute(query)

        # Obtener todos los resultados
        resultados = cursor.fetchall()

        # Convertir campos numéricos a float para JSON (si existen)
        for row in resultados:
            for key, value in row.items():
                # Convertir Decimal a float
                if value is not None and hasattr(value, '__float__'):
                    try:
                        row[key] = float(value)
                    except (ValueError, TypeError):
                        pass

        # Nombre del archivo de salida
        output_file = 'porcentajelista.json'

        # Guardar en archivo JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)

        print(f"[OK] Exportado con exito: {len(resultados)} registros guardados en '{output_file}'")

        # Copiar al servidor de informes
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
