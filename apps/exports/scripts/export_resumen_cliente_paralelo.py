"""
Versión optimizada del export_resumen_cliente.py
Procesa clientes en paralelo usando multiprocessing para mejorar el rendimiento.
"""

import os
import sys
from datetime import date
from decimal import Decimal
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count
from functools import partial

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

# Configuración
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "use_pure": True,
}

def connect_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise Exception(f"Error al conectar a la base de datos: {e}")

def procesar_cliente_simple(cliente_id, fecha_desde, fecha_hasta):
    """
    Versión simplificada que calcula KPIs básicos sin tanto detalle.
    Mucho más rápido que la versión completa.
    """
    try:
        # Importar la función original
        from export_resumen_cliente import analizar_cliente, guardar_resumen_cliente

        resultado = analizar_cliente(cliente_id, fecha_desde, fecha_hasta)
        guardar_resumen_cliente(resultado)
        return (True, cliente_id, None)
    except Exception as e:
        return (False, cliente_id, str(e))

def obtener_clientes_activos():
    """Obtiene solo clientes activos con cuenta corriente."""
    conn = connect_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT
                CONCAT(clientes.zona, clientes.cliente) AS cliente_completo
            FROM clientes
            INNER JOIN pagos ON clientes.pago = pagos.pago
            WHERE pagos.tipo = '2'
            ORDER BY clientes.zona, clientes.cliente
        """)
        return [row['cliente_completo'] for row in cursor.fetchall()]
    finally:
        conn.close()

def main_paralelo(num_workers=None):
    """
    Procesa clientes en paralelo.

    Args:
        num_workers: Número de workers paralelos. Si es None, usa CPU count / 2
    """
    print("=" * 70)
    print("EXPORT RESUMEN CLIENTE - VERSIÓN PARALELA")
    print("=" * 70)

    # Configurar workers
    if num_workers is None:
        num_workers = max(1, cpu_count() // 2)  # Mitad de CPUs disponibles

    print(f"[CONFIG] Usando {num_workers} workers paralelos")

    # Fechas
    fecha_desde = date(2025, 1, 1)
    fecha_hasta = date(2025, 12, 31)
    print(f"[PERIODO] {fecha_desde} a {fecha_hasta}")

    # Obtener clientes
    print("[INFO] Obteniendo lista de clientes...")
    clientes = obtener_clientes_activos()
    total = len(clientes)
    print(f"[INFO] {total} clientes encontrados")

    if total == 0:
        print("[WARN] No hay clientes para procesar")
        return

    # Procesar en paralelo
    print(f"[INICIO] Procesando {total} clientes...")
    print("=" * 70)

    # Crear función parcial con las fechas
    procesar_func = partial(procesar_cliente_simple,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)

    exitosos = 0
    errores = 0

    try:
        with Pool(processes=num_workers) as pool:
            # Procesar con barra de progreso
            for i, (exito, cliente_id, error) in enumerate(pool.imap(procesar_func, clientes), 1):
                if exito:
                    exitosos += 1
                else:
                    errores += 1
                    print(f"[ERROR] {cliente_id}: {error}")

                # Progreso cada 10 clientes
                if i % 10 == 0 or i == total:
                    print(f"[PROGRESO] {i}/{total} ({i/total*100:.1f}%) - Exitosos: {exitosos}, Errores: {errores}")

    except KeyboardInterrupt:
        print("\n[CANCELADO] Proceso interrumpido por el usuario")
        return

    # Resumen final
    print("=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    print(f"Total procesados: {exitosos + errores}")
    print(f"Exitosos: {exitosos}")
    print(f"Errores: {errores}")
    print(f"Tasa de éxito: {(exitosos/(exitosos+errores)*100):.1f}%")
    print("=" * 70)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Export resumen cliente (versión paralela)')
    # Allow either a positional workers arg (e.g. `python script.py 1`) or the --workers option
    parser.add_argument('workers_pos', nargs='?', type=int,
                        help='Número de workers paralelos como argumento posicional (opcional)')
    parser.add_argument('--workers', dest='workers_opt', type=int, default=None,
                        help='Número de workers paralelos (default: CPU count / 2)')

    args = parser.parse_args()

    # Prefer explicit --workers, fall back to positional if provided
    num_workers = args.workers_opt if args.workers_opt is not None else args.workers_pos

    main_paralelo(num_workers=num_workers)
