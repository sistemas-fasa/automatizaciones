import os
import sys
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

# -----------------------------
# Configuración
# -----------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "ssl_disabled": True,
    "use_pure": True,
}
HISTORICAL_CUTOFF = date.fromisoformat(os.getenv("HISTORICAL_CUTOFF_DATE", "2007-01-01"))

def connect_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise Exception(f"Error al conectar a la base de datos: {e}")

def fetch_movimientos(conn, cliente, fecha_desde, fecha_hasta, empresa=None):
    """Obtiene movimientos actuales y/o históricos según la fecha."""
    cursor = conn.cursor(dictionary=True)

    def call_procedure(proc_name):
        cursor.callproc(proc_name, [cliente, empresa])
        result = []
        for result_set in cursor.stored_results():
            result.extend(result_set.fetchall())
        return result

    movimientos = call_procedure('pa_GetMovixCli_WithEmpresa')

    # Si fecha_desde está antes del límite histórico, incluimos histórico
    if fecha_desde < HISTORICAL_CUTOFF:
        historicos = call_procedure('historico.pa_getMoviXCli')
        movimientos.extend(historicos)

    # Convertir 'neto_neto' a Decimal y ajustar signos según código
    for m in movimientos:
        neto = m.get('neto_neto')
        if neto is None:
            m['neto_neto'] = Decimal('0')
        else:
            m['neto_neto'] = Decimal(str(neto))
            if m['codigo'].startswith('C'):
                m['neto_neto'] *= -1

    # Filtrar por rango de fechas
    return [
        m for m in movimientos
        if fecha_desde <= m['fecha'] <= fecha_hasta and not m['codigo'].startswith('R')
    ]

def fetch_cta_cte(conn, codigo, clase, comp):
    """Simula la llamada a traedatos.ctacte (ajusta según tu lógica real si es necesario)."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT fecha FROM cta_cte
        WHERE codigo = %s AND clase = %s AND comp = %s
        ORDER BY fecha DESC LIMIT 1
    """, (codigo, clase, comp))
    row = cursor.fetchone()
    return row['fecha'] if row else None

def fetch_pagos(conn, pago_id):
    """Simula trae_pagos(pago)."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT tipo, dias1 FROM pagos WHERE pago = %s", (pago_id,))
    row = cursor.fetchone()
    return row['tipo'] if row else '0'  # tipo '0' como fallback

def fetch_stock_venta(conn, cliente, fecha_desde, fecha_hasta):
    """Obtiene el costo de mercadería vendida."""
    cursor = conn.cursor(dictionary=True)

    def call_stock_proc(proc_name):
        cursor.callproc(proc_name, [cliente])
        result = []
        for result_set in cursor.stored_results():
            rows = result_set.fetchall()
            # Normalizamos las claves a minúsculas
            for row in rows:
                normalized_row = {key.lower(): value for key, value in row.items()}
                result.append(normalized_row)
        return result

    stock = call_stock_proc('pa_getStockVeXCli')
    if fecha_desde < HISTORICAL_CUTOFF:
        stock_hist = call_stock_proc('historico.pa_getStockVeXCli')
        stock.extend(stock_hist)

    total_costo = Decimal('0')
    for s in stock:
        costo = s.get('costo')
        if costo is None:
            costo = Decimal('0')
        else:
            costo = Decimal(str(costo))
            if s.get('codigo', '').startswith('C'):
                costo *= -1

        fecha_mov = s.get('fecha')
        if fecha_mov is not None and fecha_desde <= fecha_mov <= fecha_hasta:
            total_costo += costo

    return total_costo

def fetch_cheques_devueltos(conn, cliente):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT tipo, repuesto
        FROM devuelto
        WHERE cliente = %s
    """, (cliente,))
    return cursor.fetchall()

def fetch_cheques_entregados(conn, cliente):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT interno, tipo
        FROM cajamov
        WHERE cliente = %s AND tipo IN ('02', '03')
    """, (cliente,))
    return cursor.fetchall()

def fetch_valor_pendiente(conn, cliente):
    """Calcula el valor pendiente del cliente (ingresos - egresos de pendient)."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            ROUND(SUM(p.ingresa * s.precio1), 2) as ingresa,
            ROUND(SUM(p.egresa * s.precio1), 2) as egresa
        FROM fasa.pendient p
        LEFT OUTER JOIN fasa.stock s ON p.articulo = s.clave
        WHERE p.cliente = %s
        GROUP BY p.cliente
    """, (cliente,))
    row = cursor.fetchone()

    if row:
        ingresa = Decimal(str(row['ingresa'])) if row['ingresa'] is not None else Decimal('0')
        egresa = Decimal(str(row['egresa'])) if row['egresa'] is not None else Decimal('0')
        return ingresa - egresa
    return Decimal('0')

def fetch_margen_minimo_cta_cte(conn):
    """Obtiene el margen_minimo_cta_cte desde la tabla paramsist."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT Valor
        FROM paramsist
        WHERE Parametro = 'margen_minimo_cta_cte'
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row and row['Valor']:
        try:
            return Decimal(str(row['Valor']))
        except (ValueError, TypeError):
            print(f"[WARN] Valor invalido para margen_minimo_cta_cte: {row['Valor']}, usando 0")
            return Decimal('0')
    print("[WARN] No se encontro margen_minimo_cta_cte en paramsist, usando 0")
    return Decimal('0')

def actualizar_credito_cliente(conn, cliente, credito):
    """Actualiza el campo 'credito' en la tabla clientes."""
    cursor = conn.cursor()
    try:
        # Extraer zona (1 carácter) y cliente (4 caracteres) del código completo
        # Ejemplo: "Z1234" -> zona="Z", cliente="1234"
        if len(cliente) >= 5:
            zona = cliente[0]  # Primer carácter
            cliente_code = cliente[1:5]  # Siguientes 4 caracteres
        else:
            print(f"[WARN] Formato de cliente invalido: {cliente} (debe tener al menos 5 caracteres)")
            return

        cursor.execute("""
            UPDATE clientes
            SET credito = %s
            WHERE zona = %s AND cliente = %s
        """, (float(credito), zona, cliente_code))
        conn.commit()
        print(f"[OK] Campo 'credito' actualizado para cliente {cliente} (zona={zona}, cliente={cliente_code}): {credito}")
    except Error as e:
        conn.rollback()
        print(f"[ERROR] Error al actualizar credito para cliente {cliente}: {e}")
    finally:
        cursor.close()

def resetear_credito_todos_los_clientes(conn):
    """Pone en 0 el campo credito para todos los clientes."""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE clientes SET credito = 0")
        conn.commit()
        print("[OK] Campo 'credito' reseteado a 0 para todos los clientes.")
    except Error as e:
        conn.rollback()
        raise Exception(f"Error al resetear credito de clientes: {e}")
    finally:
        cursor.close()

# -----------------------------
# Función principal
# -----------------------------
def analizar_cliente(cliente, fecha_desde, fecha_hasta):
    conn = connect_db()
    try:
        movs = fetch_movimientos(conn, cliente, fecha_desde, fecha_hasta, empresa=1) # Asumiendo empresa=1, ajustar según sea necesario

        total_vta = Decimal('0')
        tot_cred = Decimal('0')
        tot_cdo = Decimal('0')
        tot_cta_cte = Decimal('0')
        fc_fvenc = 0
        fc_2venc = 0
        fc_1venc = 0
        dias_fvenc = 0

        # Agrupar por mes para promedio
        meses = set()
        for m in movs:
            meses.add((m['fecha'].year, m['fecha'].month))
            total_vta += m['neto_neto']
            if m['codigo'].startswith('C'):
                tot_cred += m['neto_neto']

            # Simular lógica de pagos y cta_cte
            tipo_pago = fetch_pagos(conn, m['pago'])
            if tipo_pago == '1':
                tot_cdo += m['neto_neto']
            elif tipo_pago == '2':
                if m['codigo'].startswith('F'):
                    fecha_cta = fetch_cta_cte(conn, m['codigo'], m['clase'], m['comp'])
                    if fecha_cta:
                        if fecha_cta > m['fechaven']:
                            fc_fvenc += 1
                            dias_fvenc += (fecha_cta - m['fechaven']).days
                        elif fecha_cta > m['fecha1venc']:
                            fc_2venc += 1
                        else:
                            fc_1venc += 1
                    else:
                        dias_fvenc += (date.today() - m['fechaven']).days
                        fc_fvenc += 1
                tot_cta_cte += m['neto_neto']
            else:
                tot_cta_cte += m['neto_neto']

        # Cálculos finales
        prom_vtas = tot_cta_cte / len(meses) if meses else Decimal('0')
        prom_dias = Decimal(dias_fvenc) / fc_fvenc if fc_fvenc > 0 else Decimal('0')

        # Costo de mercadería
        costo_total = fetch_stock_venta(conn, cliente, fecha_desde, fecha_hasta)
        dif_cost_vta = total_vta - costo_total

        # Cheques devueltos
        devueltos = fetch_cheques_devueltos(conn, cliente)
        cheq_dev_02 = sum(1 for d in devueltos if d['tipo'] == '02')
        cheq_no_rep_02 = sum(1 for d in devueltos if d['tipo'] == '02' and d['repuesto'])
        cheq_dev_03 = sum(1 for d in devueltos if d['tipo'] == '03')
        cheq_no_rep_03 = sum(1 for d in devueltos if d['tipo'] == '03' and d['repuesto'])

        # Cheques entregados
        entregados = fetch_cheques_entregados(conn, cliente)
        che_ent_02 = sum(1 for e in entregados if e['tipo'] == '02')
        che_ent_03 = sum(1 for e in entregados if e['tipo'] == '03')

        # Valor pendiente
        valor_pendiente = fetch_valor_pendiente(conn, cliente)

        # Redondear a 2 decimales
        round2 = lambda x: x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Calcular margen_cta_cte
        margen_cta_cte = round(prom_vtas / Decimal('2'))

        # Obtener margen mínimo y usarlo como crédito final
        margen_minimo = fetch_margen_minimo_cta_cte(conn)
        credito_final = margen_minimo

        # Guardar en clientes.credito el margen mínimo requerido
        actualizar_credito_cliente(conn, cliente, margen_minimo)

        return {
            "cliente": cliente,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "total_venta": round2(total_vta),
            "total_credito": round2(tot_cred),
            "total_contado": round2(tot_cdo),
            "total_cta_cte": round2(tot_cta_cte),
            "promedio_ventas": round2(prom_vtas),
            "diferencia_costo_venta": round2(dif_cost_vta),
            "costo_total": round2(costo_total),
            "fc_fvenc": fc_fvenc,
            "fc_2venc": fc_2venc,
            "fc_1venc": fc_1venc,
            "promedio_dias_vencimiento": round2(prom_dias),
            "cheq_dev_02": cheq_dev_02,
            "cheq_no_rep_02": cheq_no_rep_02,
            "cheq_dev_03": cheq_dev_03,
            "cheq_no_rep_03": cheq_no_rep_03,
            "che_ent_02": che_ent_02,
            "che_ent_03": che_ent_03,
            "valor_pendiente": round2(valor_pendiente),
            "margen_cta_cte": margen_cta_cte,
            "credito_final": credito_final
        }

    finally:
        conn.close()

def fetch_pagos_cliente(conn, cliente):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT clientes.pago
        FROM fasa.clientes
        WHERE CONCAT(clientes.zona, clientes.cliente) = %s
    """, (cliente,))
    row = cursor.fetchone()
    if row:
        pago_id = row['pago']
        cursor.execute("SELECT tipo, dias1 FROM pagos WHERE pago = %s", (pago_id,))
        pago_row = cursor.fetchone()
        return pago_row['dias1'] if pago_row else 0
    return 0

def crear_tabla_resumen_si_no_existe():
    """Crea la tabla resumen_cliente en la base de datos 'estadisticas' si no existe."""
    db_config_estadisticas = DB_CONFIG.copy()
    db_config_estadisticas["database"] = "estadisticas"

    try:
        conn = mysql.connector.connect(**db_config_estadisticas)
        cursor = conn.cursor()

        create_query = """
        CREATE TABLE IF NOT EXISTS resumen_cliente (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cliente VARCHAR(50) NOT NULL,
            fecha_desde DATE NOT NULL,
            fecha_hasta DATE NOT NULL,
            total_venta DECIMAL(18,2) DEFAULT 0,
            total_credito DECIMAL(18,2) DEFAULT 0,
            total_contado DECIMAL(18,2) DEFAULT 0,
            total_cta_cte DECIMAL(18,2) DEFAULT 0,
            promedio_ventas DECIMAL(18,2) DEFAULT 0,
            diferencia_costo_venta DECIMAL(18,2) DEFAULT 0,
            costo_total DECIMAL(18,2) DEFAULT 0,
            fc_fvenc INT DEFAULT 0,
            fc_2venc INT DEFAULT 0,
            fc_1venc INT DEFAULT 0,
            promedio_dias_vencimiento DECIMAL(10,2) DEFAULT 0,
            cheq_dev_02 INT DEFAULT 0,
            cheq_no_rep_02 INT DEFAULT 0,
            cheq_dev_03 INT DEFAULT 0,
            cheq_no_rep_03 INT DEFAULT 0,
            che_ent_02 INT DEFAULT 0,
            che_ent_03 INT DEFAULT 0,
            valor_pendiente DECIMAL(18,2) DEFAULT 0,
            margen_cta_cte DECIMAL(18,2) DEFAULT 0,
            credito_final DECIMAL(18,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_cliente_fechas (cliente, fecha_desde, fecha_hasta)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cursor.execute(create_query)
        conn.commit()
        print("[OK] Tabla 'resumen_cliente' verificada/creada en base 'estadisticas'.")
    except Error as e:
        raise Exception(f"Error al crear la tabla en 'estadisticas': {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def guardar_resumen_cliente(resultado):
    """Guarda (o actualiza) el resumen en la tabla resumen_cliente de la base 'estadisticas'."""
    db_config_estadisticas = DB_CONFIG.copy()
    db_config_estadisticas["database"] = "estadisticas"

    conn = mysql.connector.connect(**db_config_estadisticas)
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO resumen_cliente (
        cliente, fecha_desde, fecha_hasta,
        total_venta, total_credito, total_contado, total_cta_cte,
        promedio_ventas, diferencia_costo_venta, costo_total,
        fc_fvenc, fc_2venc, fc_1venc, promedio_dias_vencimiento,
        cheq_dev_02, cheq_no_rep_02, cheq_dev_03, cheq_no_rep_03,
        che_ent_02, che_ent_03, valor_pendiente, margen_cta_cte, credito_final
    ) VALUES (
        %(cliente)s, %(fecha_desde)s, %(fecha_hasta)s,
        %(total_venta)s, %(total_credito)s, %(total_contado)s, %(total_cta_cte)s,
        %(promedio_ventas)s, %(diferencia_costo_venta)s, %(costo_total)s,
        %(fc_fvenc)s, %(fc_2venc)s, %(fc_1venc)s, %(promedio_dias_vencimiento)s,
        %(cheq_dev_02)s, %(cheq_no_rep_02)s, %(cheq_dev_03)s, %(cheq_no_rep_03)s,
        %(che_ent_02)s, %(che_ent_03)s, %(valor_pendiente)s, %(margen_cta_cte)s, %(credito_final)s
    )
    ON DUPLICATE KEY UPDATE
        total_venta = VALUES(total_venta),
        total_credito = VALUES(total_credito),
        total_contado = VALUES(total_contado),
        total_cta_cte = VALUES(total_cta_cte),
        promedio_ventas = VALUES(promedio_ventas),
        diferencia_costo_venta = VALUES(diferencia_costo_venta),
        costo_total = VALUES(costo_total),
        fc_fvenc = VALUES(fc_fvenc),
        fc_2venc = VALUES(fc_2venc),
        fc_1venc = VALUES(fc_1venc),
        promedio_dias_vencimiento = VALUES(promedio_dias_vencimiento),
        cheq_dev_02 = VALUES(cheq_dev_02),
        cheq_no_rep_02 = VALUES(cheq_no_rep_02),
        cheq_dev_03 = VALUES(cheq_dev_03),
        cheq_no_rep_03 = VALUES(cheq_no_rep_03),
        che_ent_02 = VALUES(che_ent_02),
        che_ent_03 = VALUES(che_ent_03),
        valor_pendiente = VALUES(valor_pendiente),
        margen_cta_cte = VALUES(margen_cta_cte),
        credito_final = VALUES(credito_final),
        created_at = CURRENT_TIMESTAMP;
    """

    try:
        cursor.execute(insert_query, resultado)
        conn.commit()
        print(f"[OK] Resumen guardado para cliente {resultado['cliente']} ({resultado['fecha_desde']} - {resultado['fecha_hasta']})")
    except Error as e:
        conn.rollback()
        raise Exception(f"Error al guardar resumen: {e}")
    finally:
        cursor.close()
        conn.close()

def obtener_clientes_cta_cte(conn):
    """Obtiene lista de clientes cuyo método de pago es tipo '2' (cuenta corriente) y están activos."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT
            CONCAT(clientes.zona, clientes.cliente) AS cliente_completo,
            clientes.zona,
            clientes.cliente
        FROM clientes
        INNER JOIN pagos ON clientes.pago = pagos.pago
        WHERE pagos.tipo = '2'
          AND COALESCE(clientes.inhabilita, '0000-00-00') = '0000-00-00'  -- Solo clientes activos (sin fecha de inhabilitación)
        ORDER BY clientes.zona, clientes.cliente
    """)
    filas = cursor.fetchall()
    # Normalizamos claves a minúsculas (por consistencia)
    return [{k.lower(): v for k, v in fila.items()} for fila in filas]

def procesar_todos_clientes_cta_cte(fecha_desde, fecha_hasta):
    """Procesa todos los clientes con cuenta corriente y guarda su resumen."""
    # Conexión a la base de datos operativa (donde están clientes, pagos, etc.)
    conn_operativa = connect_db()
    try:
        clientes = obtener_clientes_cta_cte(conn_operativa)
        total = len(clientes)
        print(f"[INFO] Se encontraron {total} clientes con cuenta corriente (tipo = 2).")

        if total == 0:
            print("[WARN] No hay clientes con cuenta corriente.")
            return

        # Aseguramos que la tabla de resumen exista
        crear_tabla_resumen_si_no_existe()

        # Primero reseteamos todos los creditos y luego asignamos por cliente
        resetear_credito_todos_los_clientes(conn_operativa)

        procesados = 0
        errores = 0

        print(f"[INICIO] Iniciando procesamiento de {total} clientes...")

        for idx, cliente_info in enumerate(clientes, start=1):
            cliente_id = cliente_info['cliente_completo']  # Ej: "Z01C12345"

            # Mostrar progreso cada 10 clientes o en puntos clave
            if idx == 1 or idx % 10 == 0 or idx == total:
                print(f"[PROGRESO] {idx}/{total} ({(idx/total*100):.1f}%) - Cliente {cliente_id}")

            try:
                resultado = analizar_cliente(cliente_id, fecha_desde, fecha_hasta)
                guardar_resumen_cliente(resultado)
                procesados += 1
            except Exception as e:
                print(f"[ERROR] Cliente {cliente_id}: {str(e)[:100]}")
                errores += 1
                # Continuar con el siguiente cliente

        print(f"\n[RESUMEN] Procesados: {procesados}, Errores: {errores}, Total: {total}")

    finally:
        conn_operativa.close()

# -----------------------------
# Ejecución de ejemplo
# -----------------------------
if __name__ == "__main__":
    # Obtener rango de fechas desde argumentos o usar últimos 12 meses por defecto
    if len(sys.argv) >= 3:
        desde = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        hasta = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    else:
        hasta = date.today()
        desde = hasta - relativedelta(months=12)

    print("[INICIO] Iniciando procesamiento masivo de clientes con cuenta corriente...")
    print(f"[INFO] Rango de fechas: {desde} a {hasta}")
    procesar_todos_clientes_cta_cte(desde, hasta)
    print("[FIN] Proceso finalizado.")
