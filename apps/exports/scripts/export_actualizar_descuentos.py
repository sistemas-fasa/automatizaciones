import argparse
import json
import os
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# Carga .env del directorio raiz del proyecto y sobreescribe variables previas
# para evitar que variables del sistema/sesion tomen prioridad.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "ssl_disabled": True,
    "use_pure": True,
}


def connect_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        host = DB_CONFIG.get("host") or "<sin_host>"
        user = DB_CONFIG.get("user") or "<sin_usuario>"
        dbname = DB_CONFIG.get("database") or "<sin_bd>"
        raise Exception(
            "Error al conectar a la base de datos: "
            f"{e} | host={host} user={user} db={dbname} env={ENV_PATH}"
        )


def ensure_descuent_table_exists(conn):
    query = """
    CREATE TABLE IF NOT EXISTS descuent (
      IDDESCUENT int NOT NULL AUTO_INCREMENT,
      CLIENTE varchar(5) DEFAULT NULL,
      DESDEART varchar(7) DEFAULT NULL,
      HASTAART varchar(7) DEFAULT NULL,
      DESCUENTO decimal(6,2) DEFAULT NULL,
      DETALLE varchar(30) DEFAULT NULL,
      LISTA varchar(1) DEFAULT NULL,
      RANGO varchar(2) DEFAULT NULL,
      RUBRO varchar(9) DEFAULT NULL,
      DESCUENTO1 decimal(5,2) DEFAULT NULL,
      DESCUENTO2 decimal(5,2) DEFAULT NULL,
      DESCUENTO3 decimal(5,2) DEFAULT NULL,
      DESCUENTO4 decimal(5,2) DEFAULT NULL,
      DESCUENTO5 decimal(5,2) DEFAULT NULL,
      CANTIDAD decimal(9,2) DEFAULT NULL,
      DETDES varchar(34) DEFAULT NULL,
      DESCCANT decimal(9,2) DEFAULT NULL,
      PRECIO decimal(12,3) DEFAULT NULL,
      PAGO varchar(2) DEFAULT NULL,
      CANMIN decimal(9,2) DEFAULT NULL,
      CANMAX decimal(9,2) DEFAULT NULL,
      Transferido bit(1) NOT NULL DEFAULT b'0',
      PRIMARY KEY (IDDESCUENT)
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
        print("[OK] Tabla descuent verificada/creada.")
    finally:
        cursor.close()


def parse_lista_range(lista):
    lista = str(lista).strip().upper()
    if lista == "T":
        return "1", "4"
    if lista not in {"1", "2", "3", "4"}:
        raise ValueError("La lista debe ser 1, 2, 3, 4 o T")
    return lista, lista


def decimal_or_zero(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def normalize_bonificacion(value):
    """Garantiza que la bonificacion final no sea nula ni negativa."""
    boni = decimal_or_zero(value)
    return boni if boni > Decimal("0") else Decimal("0")


def fetch_facturas(conn, fecha_desde, fecha_hasta, d_lista, h_lista):
    query = """
    SELECT
        cliente,
        nombre,
        SUM(
            CASE
                WHEN SUBSTR(facturas.codigo, 1, 1) = 'C' THEN facturas.total * -1
                ELSE facturas.total
            END
        ) AS total,
        facturas.lista
    FROM facturas
    WHERE fecha BETWEEN %s AND %s
      AND cliente <> 1
      AND lista BETWEEN %s AND %s
      AND clave >= '000.000'
    GROUP BY cliente, nombre, facturas.lista
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (fecha_desde, fecha_hasta, d_lista, h_lista))
        rows = cursor.fetchall()
        return [{k.lower(): v for k, v in row.items()} for row in rows]
    finally:
        cursor.close()


def fetch_remitos(conn, fecha_desde, fecha_hasta, d_lista, h_lista):
    query = """
    SELECT
        CONCAT(remitos.zona, remitos.cliente) AS cliente,
        remitos.nombre,
        SUM(detaremi.UNITARIO * detaremi.CANTIDAD) + SUM(detaremi.MONTOIVA) AS neto,
        remitos.lista
    FROM remitos
    INNER JOIN detaremi
        ON CONCAT(remitos.TIPO, remitos.COMP) = CONCAT(detaremi.TIPO, detaremi.COMP)
    WHERE SUBSTR(remitos.tipo, 1, 1) IN ('N')
      AND remitos.fecha BETWEEN %s AND %s
      AND remitos.lista BETWEEN %s AND %s
      AND detaremi.ARTICULO >= '000.000'
    GROUP BY CONCAT(remitos.zona, remitos.cliente), remitos.nombre, remitos.lista
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (fecha_desde, fecha_hasta, d_lista, h_lista))
        rows = cursor.fetchall()
        return [{k.lower(): v for k, v in row.items()} for row in rows]
    finally:
        cursor.close()


def fetch_descuento_actual(conn, cliente, lista):
    query = """
    SELECT iddescuent, descuento
    FROM descuent
    WHERE cliente = %s
      AND lista = %s
      AND desdeart = '000.000'
    ORDER BY iddescuent DESC
    LIMIT 1
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (cliente, lista))
        return cursor.fetchone()
    finally:
        cursor.close()


def fetch_bonificacion_calculada(conn, lista, monto_promedio_mensual):
    query = """
    SELECT boni
    FROM boniart
    WHERE lista = %s
      AND monto <= %s
    ORDER BY monto DESC
    LIMIT 1
    """
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (lista, monto_promedio_mensual))
        row = cursor.fetchone()
        return normalize_bonificacion(row["boni"]) if row and row.get("boni") is not None else Decimal("0")
    finally:
        cursor.close()


def resetear_descuentos(conn, d_lista, h_lista):
    query = """
    UPDATE descuent
    SET descuento = 0
    WHERE lista BETWEEN %s AND %s
      AND desdeart = '000.000'
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (d_lista, h_lista))
        conn.commit()
        print(f"[OK] Descuentos reseteados a 0 para listas {d_lista} a {h_lista}.")
    finally:
        cursor.close()


def eliminar_descuentos_duplicados(conn, d_lista, h_lista):
    """Elimina duplicados por cliente/lista/rango de articulo, conservando el ID mayor."""
    query = """
    DELETE d1
    FROM descuent d1
    INNER JOIN descuent d2
      ON d1.cliente = d2.cliente
     AND COALESCE(d1.lista, '') = COALESCE(d2.lista, '')
     AND COALESCE(d1.desdeart, '') = COALESCE(d2.desdeart, '')
     AND COALESCE(d1.hastaart, '') = COALESCE(d2.hastaart, '')
     AND d1.iddescuent < d2.iddescuent
    WHERE COALESCE(d1.lista, '') BETWEEN %s AND %s
      AND COALESCE(d2.lista, '') BETWEEN %s AND %s
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (d_lista, h_lista, d_lista, h_lista))
        eliminados = cursor.rowcount
        conn.commit()
        print(
            f"[OK] Duplicados eliminados en descuent (listas {d_lista}-{h_lista}): {eliminados}"
        )
        return eliminados
    finally:
        cursor.close()


def eliminar_descuentos_en_cero(conn, d_lista, h_lista):
    """Elimina descuentos en cero para los rangos procesados de lista."""
    query = """
    DELETE FROM descuent
    WHERE COALESCE(lista, '') BETWEEN %s AND %s
      AND desdeart = '000.000'
      AND COALESCE(descuento, 0) = 0
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (d_lista, h_lista))
        eliminados = cursor.rowcount
        conn.commit()
        print(
            f"[OK] Descuentos en 0 eliminados (listas {d_lista}-{h_lista}): {eliminados}"
        )
        return eliminados
    finally:
        cursor.close()


def eliminar_descuento_cliente(conn, cliente, lista):
    """Elimina registro/s de descuento base de cliente-lista (desdeart=000.000)."""
    query = """
    DELETE FROM descuent
    WHERE cliente = %s
      AND lista = %s
      AND desdeart = '000.000'
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, (cliente, lista))
        eliminados = cursor.rowcount
        conn.commit()
        return eliminados
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()


def upsert_descuento_cliente(conn, cliente, lista, boni_calculada):
    actual = fetch_descuento_actual(conn, cliente, lista)
    if boni_calculada <= Decimal("0"):
        eliminados = eliminar_descuento_cliente(conn, cliente, lista)
        return "delete" if eliminados > 0 else "sin_cambios"

    cursor = conn.cursor()
    try:
        if actual is None:
            insert_query = """
            INSERT INTO descuent
                (cliente, desdeart, hastaart, descuento, detalle, lista, transferido)
            VALUES
                (%s, '000.000', '999.999', %s, '', %s, b'0')
            """
            cursor.execute(insert_query, (cliente, float(boni_calculada), lista))
            accion = "insert"
        else:
            update_query = """
            UPDATE descuent
            SET descuento = %s
            WHERE iddescuent = %s
            """
            cursor.execute(update_query, (float(boni_calculada), actual["iddescuent"]))
            accion = "update"

        conn.commit()
        return accion
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()


def build_datos(facturas_rows, remitos_rows):
    datos = {}

    for row in facturas_rows:
        cliente = str(row["cliente"])
        lista = str(row["lista"])
        key = (cliente, lista)

        if key not in datos:
            datos[key] = {
                "cliente": cliente,
                "nombre": row.get("nombre") or "",
                "lista": lista,
                "monto": Decimal("0"),
            }

        datos[key]["monto"] += decimal_or_zero(row.get("total"))

    for row in remitos_rows:
        cliente = str(row["cliente"])
        lista = str(row["lista"])
        key = (cliente, lista)

        if key not in datos:
            datos[key] = {
                "cliente": cliente,
                "nombre": row.get("nombre") or "",
                "lista": lista,
                "monto": Decimal("0"),
            }

        datos[key]["monto"] += decimal_or_zero(row.get("neto"))

    return list(datos.values())


def json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def exportar_resultado_json(resultados, lista_input):
    output_file = f"bonificacion_clientes_{lista_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = os.path.join("output", output_file)
    os.makedirs("output", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=json_default)

    print(f"[OK] Resultado exportado en: {output_path}")


def procesar_bonificaciones(fecha_desde, fecha_hasta, lista_input, actualizar):
    d_lista, h_lista = parse_lista_range(lista_input)
    meses = int((fecha_hasta - fecha_desde).days / 30)
    if meses == 0:
        meses = 1

    conn = connect_db()
    try:
        ensure_descuent_table_exists(conn)

        # Limpieza preventiva: evita acumulacion de duplicados historicos.
        eliminar_descuentos_duplicados(conn, d_lista, h_lista)
        eliminar_descuentos_en_cero(conn, d_lista, h_lista)

        if actualizar:
            resetear_descuentos(conn, d_lista, h_lista)

        f_desde = fecha_desde.strftime("%Y%m%d")
        f_hasta = fecha_hasta.strftime("%Y%m%d")

        facturas_rows = fetch_facturas(conn, f_desde, f_hasta, d_lista, h_lista)
        remitos_rows = fetch_remitos(conn, f_desde, f_hasta, d_lista, h_lista)

        datos = build_datos(facturas_rows, remitos_rows)
        total = len(datos)
        print(f"[INFO] Clientes/listas a procesar: {total}")

        resultados = []
        inserts = 0
        updates = 0
        deletes = 0

        for idx, row in enumerate(datos, start=1):
            if idx == 1 or idx % 100 == 0 or idx == total:
                print(f"[PROGRESO] {idx}/{total}")

            cliente = row["cliente"]
            lista = row["lista"]
            monto = row["monto"]
            monto_promedio_mensual = monto / Decimal(meses)

            boni_calculada = normalize_bonificacion(
                fetch_bonificacion_calculada(conn, lista, monto_promedio_mensual)
            )
            actual = fetch_descuento_actual(conn, cliente, lista)
            boni_actual = decimal_or_zero(actual.get("descuento")) if actual else Decimal("0")

            accion = "sin_cambios"
            if actualizar:
                accion = upsert_descuento_cliente(conn, cliente, lista, boni_calculada)
                if accion == "insert":
                    inserts += 1
                elif accion == "update":
                    updates += 1
                elif accion == "delete":
                    deletes += 1

            resultados.append(
                {
                    "cliente": cliente,
                    "nombre": row["nombre"],
                    "lista": lista,
                    "monto": monto,
                    "meses": meses,
                    "monto_promedio_mensual": monto_promedio_mensual,
                    "boniact": boni_actual,
                    "bonicalc": boni_calculada,
                    "accion": accion,
                }
            )

        exportar_resultado_json(resultados, lista_input)

        print("\n[RESUMEN]")
        print(f"- Total procesados: {total}")
        print(f"- Modo actualizacion: {'SI' if actualizar else 'NO'}")
        if actualizar:
            print(f"- Inserts: {inserts}")
            print(f"- Updates: {updates}")
            print(f"- Deletes (descuento=0): {deletes}")
            eliminar_descuentos_duplicados(conn, d_lista, h_lista)
            eliminar_descuentos_en_cero(conn, d_lista, h_lista)

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calcula bonificaciones por cliente y opcionalmente actualiza tabla descuent."
    )
    parser.add_argument(
        "--desde",
        required=True,
        help="Fecha desde en formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--hasta",
        required=True,
        help="Fecha hasta en formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--lista",
        default="T",
        help="Lista a procesar: 1,2,3,4 o T (todas). Por defecto T.",
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Si se indica, resetea descuento y actualiza/inserta en descuent.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        fecha_desde = datetime.strptime(args.desde, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(args.hasta, "%Y-%m-%d").date()
    except ValueError as e:
        raise SystemExit(f"Error de formato de fecha: {e}")

    if fecha_hasta < fecha_desde:
        raise SystemExit("La fecha --hasta no puede ser menor a --desde")

    print("[INICIO] Proceso de bonificacion de clientes")
    print(f"[INFO] Rango de fechas: {fecha_desde} a {fecha_hasta}")
    print(f"[INFO] Lista: {args.lista}")
    print(f"[INFO] Actualizar tabla descuent: {'SI' if args.actualizar else 'NO'}")

    procesar_bonificaciones(fecha_desde, fecha_hasta, args.lista, args.actualizar)

    print("[FIN] Proceso finalizado")


if __name__ == "__main__":
    main()