import os
import shutil
import json
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime, date, time, timedelta
from decimal import Decimal

# Cargar variables de entorno
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

def crear_conexion():
    """Crea conexión a la base de datos MySQL usando variables de entorno"""
    try:
        conexion = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT', 3306),
            charset='utf8mb4',
            collation='utf8mb4_general_ci',
            use_unicode=True,
            use_pure=True,
            autocommit=True
        )
        return conexion
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def convertir_para_json(obj):
    """Convierte objetos Python a tipos compatibles con JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.strftime('%H:%M:%S')
    elif isinstance(obj, timedelta):
        return str(obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def ejecutar_consulta_presupuestos(conexion):
    """Ejecuta la consulta SQL y devuelve los resultados"""
    consulta_sql = """
    SELECT
        comp as numero_presupuesto,
        ARTICULO,
        fecha,
        cliente_completo,
        nombre,
        vendedor,
        DETALLE,
        cantidad_presupuestada,
        cantidad_facturada,
        pendiente_facturar,
        estado_articulo,
        ROUND(cantidad_facturada / NULLIF(cantidad_presupuestada, 0) * 100, 2) as porcentaje_cantidad_facturada,
        COUNT(*) OVER (PARTITION BY comp) as total_articulos_presupuesto,
        SUM(cantidad_presupuestada) OVER (PARTITION BY comp) as cantidad_total_presupuestada,
        SUM(cantidad_facturada) OVER (PARTITION BY comp) as cantidad_total_facturada,
        SUM(pendiente_facturar) OVER (PARTITION BY comp) as cantidad_total_pendiente,
        ROUND(SUM(cantidad_facturada) OVER (PARTITION BY comp) /
              NULLIF(SUM(cantidad_presupuestada) OVER (PARTITION BY comp), 0) * 100, 2) as porcentaje_total_facturado,
        CASE
            WHEN estado_articulo = 'Baja' THEN 'Artículo de Baja'
            WHEN SUM(cantidad_facturada) OVER (PARTITION BY comp) = 0 THEN 'No Facturado'
            WHEN SUM(cantidad_facturada) OVER (PARTITION BY comp) = SUM(cantidad_presupuestada) OVER (PARTITION BY comp) THEN 'Totalmente Facturado'
            WHEN SUM(cantidad_facturada) OVER (PARTITION BY comp) < SUM(cantidad_presupuestada) OVER (PARTITION BY comp) THEN 'Parcialmente Facturado'
            ELSE 'Sobrefacturado'
        END as estado_presupuesto,
        motivo_baja
    FROM presupuestos_facturacion_estado
    ORDER BY comp, ARTICULO
    """

    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(consulta_sql)
        resultados = cursor.fetchall()
        cursor.close()

        # Convertir todos los valores a tipos compatibles con JSON
        resultados_convertidos = []
        for fila in resultados:
            fila_convertida = {}
            for key, value in fila.items():
                try:
                    fila_convertida[key] = convertir_para_json(value)
                except:
                    fila_convertida[key] = str(value)  # Como último recurso, convertir a string
            resultados_convertidos.append(fila_convertida)

        return resultados_convertidos
    except Error as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None

def exportar_a_json(datos, nombre_archivo=None):
    """Exporta los datos a un archivo JSON"""
    if nombre_archivo is None:
        nombre_archivo = f"presupuestos_estado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(nombre_archivo, 'w', encoding='utf-8') as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False, default=convertir_para_json)
        print(f"Datos exportados exitosamente a: {nombre_archivo}")

        # Copiar al servidor de informes
        copiar_a_servidor(nombre_archivo)

        return True
    except Exception as e:
        print(f"Error al exportar a JSON: {e}")
        # Intentar método alternativo
        return exportar_a_json_alternativo(datos, nombre_archivo)

def copiar_a_servidor(archivo_local):
    """Copia el archivo JSON al servidor de informes"""
    try:
        server_path = os.getenv("EXPORTS_WEB_DIR", "")
        if os.path.exists(server_path):
            dest_file = os.path.join(server_path, os.path.basename(archivo_local))
            shutil.copy2(archivo_local, dest_file)
            print(f"[OK] Archivo copiado al servidor: {dest_file}")
        else:
            print(f"[ADVERTENCIA] No se puede acceder al servidor: {server_path}")
    except Exception as e:
        print(f"[ADVERTENCIA] Error al copiar al servidor: {e}")

def exportar_a_json_alternativo(datos, nombre_archivo):
    """Método alternativo para exportar a JSON"""
    try:
        # Convertir manualmente cada fila
        datos_serializables = []
        for fila in datos:
            fila_serializable = {}
            for key, value in fila.items():
                if isinstance(value, (datetime, date)):
                    fila_serializable[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    fila_serializable[key] = float(value)
                elif isinstance(value, (int, float, str, bool, type(None))):
                    fila_serializable[key] = value
                else:
                    fila_serializable[key] = str(value)
            datos_serializables.append(fila_serializable)

        with open(nombre_archivo, 'w', encoding='utf-8') as archivo:
            json.dump(datos_serializables, archivo, indent=2, ensure_ascii=False)

        print(f"Datos exportados (método alternativo) a: {nombre_archivo}")

        # Copiar al servidor de informes
        copiar_a_servidor(nombre_archivo)

        return True
    except Exception as e:
        print(f"Error en método alternativo: {e}")
        return False

def exportar_por_partes(datos, tamano_lote=1000):
    """Exporta los datos en lotes para evitar problemas de memoria"""
    try:
        nombre_base = f"presupuestos_estado_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        for i in range(0, len(datos), tamano_lote):
            lote = datos[i:i + tamano_lote]
            nombre_archivo = f"{nombre_base}_parte_{i//tamano_lote + 1}.json"

            with open(nombre_archivo, 'w', encoding='utf-8') as archivo:
                json.dump(lote, archivo, indent=2, ensure_ascii=False, default=convertir_para_json)

            print(f"Lote {i//tamano_lote + 1} exportado: {len(lote)} registros")

        return True
    except Exception as e:
        print(f"Error al exportar por partes: {e}")
        return False

def procesar_datos_para_json(datos):
    """Procesa los datos para una estructura JSON más organizada"""
    if not datos:
        return []

    presupuestos_organizados = {}

    for fila in datos:
        comp = fila['numero_presupuesto']

        if comp not in presupuestos_organizados:
            presupuestos_organizados[comp] = {
                'numero_presupuesto': comp,
                'fecha': fila['fecha'],
                'cliente_completo': fila['cliente_completo'],
                'nombre': fila['nombre'],
                'vendedor': fila['vendedor'],
                'total_articulos': fila['total_articulos_presupuesto'],
                'cantidad_total_presupuestada': fila['cantidad_total_presupuestada'],
                'cantidad_total_facturada': fila['cantidad_total_facturada'],
                'cantidad_total_pendiente': fila['cantidad_total_pendiente'],
                'porcentaje_total_facturado': fila['porcentaje_total_facturado'],
                'estado_presupuesto': fila['estado_presupuesto'],
                'motivo_baja': fila.get('motivo_baja', ''),
                'articulos': []
            }

        articulo = {
            'articulo': fila['ARTICULO'],
            'detalle': fila['DETALLE'],
            'cantidad_presupuestada': fila['cantidad_presupuestada'],
            'cantidad_facturada': fila['cantidad_facturada'],
            'pendiente_facturar': fila['pendiente_facturar'],
            'porcentaje_cantidad_facturada': fila['porcentaje_cantidad_facturada'],
            'estado_articulo': fila['estado_articulo']
        }

        presupuestos_organizados[comp]['articulos'].append(articulo)

    return list(presupuestos_organizados.values())

def main():
    """Función principal"""
    print("Conectando a la base de datos...")
    conexion = crear_conexion()

    if not conexion:
        print("No se pudo conectar a la base de datos")
        return

    try:
        print("Ejecutando consulta...")
        datos = ejecutar_consulta_presupuestos(conexion)

        if datos:
            print(f"Se encontraron {len(datos)} registros")

            # Intentar exportación normal
            if not exportar_a_json(datos, "presupuestos_estado_plano.json"):
                print("Intentando exportación por partes...")
                exportar_por_partes(datos)

            # Procesar datos organizados
            try:
                datos_organizados = procesar_datos_para_json(datos)
                exportar_a_json(datos_organizados, "presupuestos_estado_organizado.json")
            except Exception as e:
                print(f"Error al procesar datos organizados: {e}")

            # Mostrar resumen
            print(f"\nResumen:")
            print(f"- Total de registros: {len(datos)}")

            # Contar presupuestos únicos
            presupuestos_unicos = len(set(fila['numero_presupuesto'] for fila in datos))
            print(f"- Total de presupuestos únicos: {presupuestos_unicos}")

        else:
            print("No se obtuvieron datos de la consulta")

    except Exception as e:
        print(f"Error durante el proceso: {e}")

    finally:
        if conexion and conexion.is_connected():
            conexion.close()
            print("\nConexión cerrada")

if __name__ == "__main__":
    main()
