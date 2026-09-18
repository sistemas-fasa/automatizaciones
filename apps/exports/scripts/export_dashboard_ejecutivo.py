"""
Script para generar automáticamente el reporte ejecutivo mensual.
Consolida datos de múltiples fuentes y genera archivos JSON para el dashboard ejecutivo.
"""

import os
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json
from decimal import Decimal
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

# Configuración de la base de datos
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "use_pure": True,
}

def decimal_default(obj):
    """Convertidor JSON para tipos Decimal y date."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Tipo {type(obj)} no es serializable")

def cero_si_none(value):
    """Normaliza agregados SQL vacios a cero."""
    return 0 if value is None else value

def connect_db(database=None):
    """Conectar a la base de datos."""
    try:
        config = DB_CONFIG.copy()
        if database:
            config["database"] = database
        return mysql.connector.connect(**config)
    except Error as e:
        raise Exception(f"Error al conectar a la base de datos: {e}")

def obtener_resumen_cliente(fecha_desde, fecha_hasta):
    """Obtiene el resumen consolidado de clientes desde la tabla resumen_cliente."""
    conn = connect_db(database="estadisticas")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                COUNT(DISTINCT cliente) as total_clientes,
                SUM(total_venta) as ventas_totales,
                SUM(diferencia_costo_venta) as margen_total,
                AVG(promedio_dias_vencimiento) as dias_vencimiento_promedio,
                SUM(fc_fvenc) as facturas_fuera_vencimiento,
                SUM(fc_1venc) as facturas_al_dia,
                SUM(valor_pendiente) as total_pendiente
            FROM resumen_cliente
            WHERE fecha_desde >= %s AND fecha_hasta <= %s
        """, (fecha_desde, fecha_hasta))

        resultado = cursor.fetchone()
        return resultado if resultado else {}
    finally:
        conn.close()

def obtener_compras_proveedores(fecha_desde, fecha_hasta):
    """Obtiene el resumen de compras por proveedor."""
    conn = connect_db(database="fasa")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                PROVEEDOR,
                NOMBRE,
                SUM(neto) as total_comprado,
                COUNT(DISTINCT comprobante) as cantidad_comprobantes,
                AVG(neto) as promedio_compra
            FROM compras_proveedores
            WHERE periodo >= %s AND periodo <= %s
            GROUP BY PROVEEDOR, NOMBRE
            ORDER BY total_comprado DESC
            LIMIT 20
        """, (fecha_desde, fecha_hasta))

        return cursor.fetchall()
    finally:
        conn.close()

def obtener_porcentaje_listas():
    """Obtiene los porcentajes y márgenes de las listas de precios."""
    conn = connect_db(database="estadisticas")
    try:
        cursor = conn.cursor(dictionary=True)
        # Obtener promedios sobre toda la tabla sin filtrar por fecha ni periodo
        cursor.execute("""
            SELECT
                AVG(Lista1) as lista1_promedio,
                AVG(Lista4) as lista4_promedio,
                AVG(MargenL1) as margen_l1,
                AVG(MargenL4) as margen_l4,
                AVG(Promedio) as promedio_general
            FROM porcentajelista
        """)
        resultado = cursor.fetchone()
        return resultado if resultado else {}
    finally:
        conn.close()

def obtener_ventas_dia_semana(fecha_desde, fecha_hasta):
    """Obtiene el análisis de ventas por día de la semana."""
    conn = connect_db(database="estadisticas")
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT
                    dia_semana,
                    SUM(total_neto) as total_ventas,
                    SUM(cantidad_total) as cantidad_operaciones,
                    AVG(total_neto) as promedio_dia
                FROM ventas_dia_semana
                WHERE fecha >= %s AND fecha <= %s
                GROUP BY dia_semana
                ORDER BY FIELD(dia_semana, 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')
            """, (fecha_desde, fecha_hasta))
            return cursor.fetchall()
        except mysql.connector.errors.ProgrammingError as e:
            # Table may not exist in the DB; intentar fallback cargando JSON local
            print(f"[WARN] Consulta ventas_dia_semana falló: {e}. Intentando fallback con archivo local ventas_dia_semana.json")
            try:
                web_dir = os.getenv("EXPORTS_WEB_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                json_path = os.path.join(web_dir, 'ventas_dia_semana.json')
                with open(json_path, 'r', encoding='utf-8') as fh:
                    datos = json.load(fh)

                # Agregar por dia de la semana
                agregados = {}
                for row in datos:
                    dia = row.get('dia_semana')
                    total = float(row.get('total_neto', 0) or 0)
                    cantidad = float(row.get('cantidad_total', 0) or 0)
                    if dia not in agregados:
                        agregados[dia] = {'total_ventas': 0.0, 'cantidad_operaciones': 0.0, 'contador': 0}
                    agregados[dia]['total_ventas'] += total
                    agregados[dia]['cantidad_operaciones'] += cantidad
                    agregados[dia]['contador'] += 1

                # Construir lista con promedio
                orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                resultado = []
                for d in orden:
                    if d in agregados:
                        a = agregados[d]
                        promedio = (a['total_ventas'] / a['contador']) if a['contador'] > 0 else 0
                        resultado.append({
                            'dia_semana': d,
                            'total_ventas': a['total_ventas'],
                            'cantidad_operaciones': a['cantidad_operaciones'],
                            'promedio_dia': promedio
                        })
                return resultado
            except FileNotFoundError:
                print(f"[WARN] Archivo local ventas_dia_semana.json no encontrado en {json_path}. Continuando con ventas_por_dia vacío.")
                return []
    finally:
        conn.close()

def obtener_top_clientes(fecha_desde, fecha_hasta, limite=20):
    """Obtiene los top clientes por volumen de ventas."""
    conn = connect_db(database="estadisticas")
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                cliente,
                total_venta,
                diferencia_costo_venta,
                promedio_ventas,
                fc_fvenc,
                fc_1venc,
                valor_pendiente,
                credito_final,
                CASE
                    WHEN fc_fvenc > 0 THEN 'Con retraso'
                    WHEN valor_pendiente > credito_final * 0.8 THEN 'Límite cercano'
                    ELSE 'Normal'
                END as estado_cartera
            FROM resumen_cliente
            WHERE fecha_desde >= %s AND fecha_hasta <= %s
            ORDER BY total_venta DESC
            LIMIT %s
        """, (fecha_desde, fecha_hasta, limite))

        return cursor.fetchall()
    finally:
        conn.close()

def calcular_kpis_ejecutivos(fecha_desde, fecha_hasta):
    """Calcula los KPIs principales para el dashboard ejecutivo."""
    print("[INFO] Calculando KPIs ejecutivos...")

    # Obtener datos de múltiples fuentes
    resumen = obtener_resumen_cliente(fecha_desde, fecha_hasta)
    compras = obtener_compras_proveedores(fecha_desde, fecha_hasta)
    listas = obtener_porcentaje_listas()
    ventas_semana = obtener_ventas_dia_semana(fecha_desde, fecha_hasta)
    top_clientes = obtener_top_clientes(fecha_desde, fecha_hasta)

    # Calcular totales de compras
    total_compras = sum(Decimal(str(c['total_comprado'])) for c in compras) if compras else Decimal('0')

    # Calcular métricas clave
    ventas_totales = Decimal(str(resumen.get('ventas_totales', 0))) if resumen.get('ventas_totales') else Decimal('0')
    margen_total = Decimal(str(resumen.get('margen_total', 0))) if resumen.get('margen_total') else Decimal('0')
    margen_porcentaje = (margen_total / ventas_totales * 100) if ventas_totales > 0 else Decimal('0')
    total_clientes = cero_si_none(resumen.get('total_clientes', 0))

    # Construir el reporte ejecutivo
    reporte = {
        "metadata": {
            "fecha_generacion": datetime.now().isoformat(),
            "periodo_inicio": fecha_desde.isoformat(),
            "periodo_fin": fecha_hasta.isoformat(),
            "meses_analizados": (fecha_hasta.year - fecha_desde.year) * 12 + fecha_hasta.month - fecha_desde.month + 1
        },
        "kpis_principales": {
            "ventas_totales": float(ventas_totales),
            "compras_totales": float(total_compras),
            "margen_bruto": float(margen_total),
            "margen_porcentaje": float(margen_porcentaje),
            "clientes_activos": total_clientes,
            "ticket_promedio": float(ventas_totales / total_clientes) if total_clientes > 0 else 0
        },
        "indicadores_listas": {
            "lista1_promedio": float(listas.get('lista1_promedio', 0)) if listas.get('lista1_promedio') else 0,
            "lista4_promedio": float(listas.get('lista4_promedio', 0)) if listas.get('lista4_promedio') else 0,
            "margen_l1": float(listas.get('margen_l1', 0)) if listas.get('margen_l1') else 0,
            "margen_l4": float(listas.get('margen_l4', 0)) if listas.get('margen_l4') else 0
        },
        "cartera": {
            "facturas_al_dia": cero_si_none(resumen.get('facturas_al_dia', 0)),
            "facturas_vencidas": cero_si_none(resumen.get('facturas_fuera_vencimiento', 0)),
            "dias_vencimiento_promedio": float(resumen.get('dias_vencimiento_promedio', 0)) if resumen.get('dias_vencimiento_promedio') else 0,
            "total_pendiente": float(resumen.get('total_pendiente', 0)) if resumen.get('total_pendiente') else 0
        },
        "top_proveedores": [
            {
                "proveedor": p['PROVEEDOR'],
                "nombre": p['NOMBRE'],
                "total_comprado": float(p['total_comprado']),
                "cantidad_comprobantes": p['cantidad_comprobantes'],
                "promedio_compra": float(p['promedio_compra'])
            } for p in compras[:10]
        ] if compras else [],
        "ventas_por_dia": [
            {
                "dia": v['dia_semana'],
                "total_ventas": float(v['total_ventas']),
                "cantidad_operaciones": v['cantidad_operaciones'],
                "promedio": float(v['promedio_dia'])
            } for v in ventas_semana
        ] if ventas_semana else [],
        "top_clientes": [
            {
                "cliente": c['cliente'],
                "total_venta": float(c['total_venta']),
                "margen": float(c['diferencia_costo_venta']),
                "promedio_mensual": float(c['promedio_ventas']),
                "estado_cartera": c['estado_cartera'],
                "facturas_vencidas": c['fc_fvenc'],
                "valor_pendiente": float(c['valor_pendiente']),
                "credito_disponible": float(c['credito_final'])
            } for c in top_clientes
        ] if top_clientes else []
    }

    return reporte

def generar_insights(reporte):
    """Genera insights automáticos basados en los datos del reporte."""
    insights = []
    kpis = reporte['kpis_principales']
    cartera = reporte['cartera']

    # Insight de margen
    if kpis['margen_porcentaje'] < 20:
        insights.append({
            "tipo": "warning",
            "categoria": "rentabilidad",
            "mensaje": f"Margen bruto bajo ({kpis['margen_porcentaje']:.1f}%). Revisar estructura de costos y precios."
        })
    elif kpis['margen_porcentaje'] > 35:
        insights.append({
            "tipo": "success",
            "categoria": "rentabilidad",
            "mensaje": f"Excelente margen bruto ({kpis['margen_porcentaje']:.1f}%). Mantener estrategia comercial."
        })

    # Insight de cartera
    total_facturas = cartera['facturas_al_dia'] + cartera['facturas_vencidas']
    if total_facturas > 0:
        porcentaje_vencido = (cartera['facturas_vencidas'] / total_facturas) * 100
        if porcentaje_vencido > 20:
            insights.append({
                "tipo": "alert",
                "categoria": "cobranza",
                "mensaje": f"Alto nivel de morosidad ({porcentaje_vencido:.1f}%). Intensificar gestión de cobranza."
            })
        elif porcentaje_vencido < 10:
            insights.append({
                "tipo": "success",
                "categoria": "cobranza",
                "mensaje": f"Excelente nivel de cobranza ({100-porcentaje_vencido:.1f}% al día)."
            })

    # Insight de días promedio de vencimiento
    if cartera['dias_vencimiento_promedio'] > 30:
        insights.append({
            "tipo": "warning",
            "categoria": "cobranza",
            "mensaje": f"Días promedio de vencimiento elevados ({cartera['dias_vencimiento_promedio']:.0f} días). Revisar políticas de crédito."
        })

    # Insight de ticket promedio
    if kpis['ticket_promedio'] > 0:
        insights.append({
            "tipo": "info",
            "categoria": "ventas",
            "mensaje": f"Ticket promedio de ${kpis['ticket_promedio']:,.2f} por cliente."
        })

    reporte['insights'] = insights
    return reporte

def main():
    """Función principal para ejecutar la exportación del dashboard ejecutivo."""
    print("=" * 70)
    print("[INICIO] Exportación Dashboard Ejecutivo")
    print(f"[FECHA] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        # Obtener rango de fechas desde argumentos o usar últimos 12 meses por defecto
        if len(sys.argv) >= 3:
            fecha_desde = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
            fecha_hasta = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
        else:
            fecha_hasta = date.today()
            fecha_desde = fecha_hasta - relativedelta(months=12)

        print(f"[INFO] Período de análisis: {fecha_desde} a {fecha_hasta}")

        # Calcular KPIs
        reporte = calcular_kpis_ejecutivos(fecha_desde, fecha_hasta)

        # Generar insights
        reporte = generar_insights(reporte)

        # Determinar ruta de salida
        script_dir = os.path.dirname(os.path.abspath(__file__))
        web_dir = os.path.dirname(script_dir)
        output_file = os.path.join(web_dir, "dashboard_ejecutivo_data.json")

        # Guardar archivo JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False, default=decimal_default)

        print(f"[OK] Archivo generado: {output_file}")
        print(f"[INFO] KPIs principales:")
        print(f"       - Ventas Totales: ${reporte['kpis_principales']['ventas_totales']:,.2f}")
        print(f"       - Margen Bruto: {reporte['kpis_principales']['margen_porcentaje']:.2f}%")
        print(f"       - Clientes Activos: {reporte['kpis_principales']['clientes_activos']}")
        print(f"       - Insights generados: {len(reporte['insights'])}")

        print("=" * 70)
        print("[ÉXITO] Exportación completada")
        print("=" * 70)

        return 0

    except Exception as e:
        print("=" * 70)
        print(f"[ERROR] {str(e)}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
