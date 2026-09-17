from datetime import datetime
import logging
import mysql.connector
import os
import sys

# Prefer a log file next to this module; if that's not writable, fall back to stdout.
log_path = os.path.join(os.path.dirname(__file__), 'dashboard.log')
try:
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
except (PermissionError, OSError):
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

class DatabaseManager:
    def __init__(self, db_config, empresa_id=1):
        self.db_config = db_config
        try:
            self.empresa_id = int(empresa_id) if empresa_id is not None else 1
        except Exception:
            self.empresa_id = 1

    def connect(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as err:
            print(f"Error conectando a la base de datos: {err}")
            logging.error(f"Error conectando a la base de datos: {err}")
            return None

    def get_sales_data(self, fecha):
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor(dictionary=True)
        query = """
                SELECT 
                    CONCAT(movi.ZONA, movi.CLIENTE) AS cliente,
                    movi.NOMBRE AS nombre,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -movi.NETO ELSE movi.NETO END AS NETO,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -movi.IVA ELSE movi.IVA END AS IVA,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -movi.NETO_NETO ELSE movi.NETO_NETO END AS NETO_NETO,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.PRECIO ELSE stock_ve.PRECIO END AS PRECIO,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.UNITARIO ELSE stock_ve.UNITARIO END AS UNITARIO,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.CANTIDAD ELSE stock_ve.CANTIDAD END AS CANTIDAD,
                    movi.FECHA AS FECHA,
                    CASE 
                        WHEN TRIM(movi.CODIGO) = 'C' THEN -((stock_ve.CANTIDAD * stock_ve.UNITARIO) / ((stock_ve.IVA / 100) + 1)) 
                        ELSE ((stock_ve.CANTIDAD * stock_ve.UNITARIO) / ((stock_ve.IVA / 100) + 1)) 
                    END AS NetoRenglon,
                    CASE 
                        WHEN TRIM(movi.CODIGO) = 'C' THEN -(stock_ve.CANTIDAD * stock_ve.UNITARIO) 
                        ELSE (stock_ve.CANTIDAD * stock_ve.UNITARIO) 
                    END AS total,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -movi.PercepcionDGR ELSE movi.PercepcionDGR END AS PercepcionDGR,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.PercepcionDGR ELSE stock_ve.PercepcionDGR END AS dgrdetalle,
                    movi.LOCALIDAD AS LOCALIDAD,
                    movi.CODIGO AS CODIGO,
                    stock_ve.LISTA AS LISTA,
                    stock_ve.CLAVE AS CLAVE,
                    stock_ve.REPARTO AS REPARTO,
                    movi.COMP AS COMP,
                    movi.REGIVA AS REGIVA,
                    stock_ve.IDMOVI AS IDMOVI,
                    stock_ve.CLASE AS CLASE,
                    stock_ve.VENDEDOR AS VENDEDOR,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.FLETE ELSE stock_ve.FLETE END AS FLETE,
                    stock_ve.DESCPRET AS DESCPRET,
                    stock_ve.NOTA AS NOTA,
                    stock_ve.UNIDAD AS UNIDAD,
                    movi.PAGO AS PAGO,
                    CONCAT(pagos.pago, " - Lista ", pagos.lista, " - ", pagos.detalle) AS descripcion_pago,
                    movi.CUOTAPAGO AS CUOTAPAGO,
                    movi.FECHAVEN AS FECHAVEN,
                    movi.FECHA1VENC AS FECHA1VENC,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.FLETETRANSP ELSE stock_ve.FLETETRANSP END AS fletetransp,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.BONI ELSE stock_ve.BONI END AS boni,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.COSTO ELSE stock_ve.COSTO END AS COSTO,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.Introduccion ELSE stock_ve.Introduccion END AS Introduccion,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -movi.SALDO ELSE movi.SALDO END AS saldo,
                    movi.SUCURSAL AS SUCURSAL,
                    movi.CONTADO AS CONTADO,
                    stock_ve.IDSTOCKVE AS IDSTOCKVE,
                    stock_ve.DETEXT AS DETEXT,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.IVA ELSE stock_ve.IVA END AS aliciva,
                    stock_ve.DESCAD AS DESCAD,
                    stock_ve.Procesado AS Procesado,
                    movi.PAGOANT AS PAGOANT,
                    stock_ve.Item AS Item,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.GastoTar ELSE stock_ve.GastoTar END AS GastoTar,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.DES1 ELSE stock_ve.DES1 END AS DES1,
                    CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -stock_ve.PUNITORIO ELSE stock_ve.PUNITORIO END AS PUNITORIO
                FROM stock_ve 
                JOIN movi ON (stock_ve.IDMOVI = movi.IDMOVI)
                LEFT JOIN pagos ON movi.PAGO = pagos.PAGO
                WHERE DATE(movi.FECHA) = %s AND movi.empresa_id = %s

                UNION ALL

                SELECT 
                    CONCAT(remitos.ZONA, remitos.CLIENTE) AS cliente,
                    remitos.NOMBRE AS nombre,
                    remitos.total AS neto,
                    remitos.iva,
                    remitos.neto AS NETO_NETO,
                    detaremi.p_lista AS PRECIO,
                    detaremi.UNITARIO AS UNITARIO,
                    detaremi.CANTIDAD AS CANTIDAD,
                    remitos.FECHA AS FECHA,
                    ((detaremi.CANTIDAD * detaremi.UNITARIO) / ((detaremi.IVA / 100) + 1)) AS NetoRenglon,
                    (detaremi.CANTIDAD * detaremi.UNITARIO) AS total,
                    remitos.PercepcionDGR AS PercepcionDGR,
                    remitos.PercepcionDGR AS dgrdetalle,
                    remitos.LOCALIDAD AS LOCALIDAD,
                    'X' AS CODIGO,
                    '' AS LISTA,
                    detaremi.articulo AS CLAVE,
                    detaremi.REPARTO AS REPARTO,
                    remitos.COMP AS COMP,
                    remitos.REGIVA AS REGIVA,
                    detaremi.idremito AS IDMOVI,
                    'X' AS CLASE,
                    remitos.vendedor AS VENDEDOR,
                    detaremi.FLETE AS FLETE,
                    detaremi.DESCAD AS DESCPRET,
                    detaremi.detalle AS NOTA,
                    detaremi.UNIDAD AS UNIDAD,
                    remitos.PAGO AS PAGO,
                    CONCAT(pagos.pago, " - Lista ", pagos.lista, " - ", pagos.detalle) AS descripcion_pago,
                    remitos.CUOTAPAGO AS CUOTAPAGO,
                    remitos.fecha AS FECHAVEN,
                    remitos.fecha AS FECHA1VENC,
                    detaremi.FLETE AS fletetransp,
                    detaremi.BONI AS boni,
                    detaremi.CostoUnitario AS COSTO,
                    detaremi.introduccion AS Introduccion,
                    0 AS saldo,
                    remitos.SUCURSAL AS SUCURSAL,
                    'S' AS CONTADO,
                    detaremi.ID_DETAREMI AS IDSTOCKVE,
                    detaremi.DESCAD AS DETEXT,
                    detaremi.IVA AS aliciva,
                    detaremi.descad AS DESCAD,
                    detaremi.Procesado AS Procesado,
                    detaremi.PAGOANT AS PAGOANT,
                    detaremi.Item AS Item,
                    0 AS GastoTar,
                    detaremi.DES1 AS DES1,
                    detaremi.PUNITORIO AS PUNITORIO  -- Corregido: era "detaermi.PUNITORIO"
                FROM detaremi
                JOIN remitos ON (detaremi.tipo = remitos.tipo AND detaremi.comp = remitos.comp)
                LEFT JOIN pagos ON remitos.PAGO = pagos.PAGO
                WHERE DATE(remitos.FECHA) = %s AND remitos.empresa_id = %s AND remitos.tipo = 'N'
                ORDER BY FECHA DESC
            """

        try:
            cursor.execute(query, (fecha, self.empresa_id, fecha, self.empresa_id))
            results = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error ejecutando la consulta de ventas: {e}")
            results = []
        finally:
            cursor.close()
            connection.close()
        
        return results

    def get_provider_payments(self, fecha):
        """Pagos al proveedor (codigo='R') agregados por proveedor para el periodo del mes de 'fecha'"""
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor()
        try:
            # Debug: log which empresa_id is being used for this query
            try:
                logging.info(f"get_provider_payments called with empresa_id={self.empresa_id} fecha={fecha}")
                print(f"[DEBUG] get_provider_payments empresa_id={self.empresa_id} fecha={fecha}")
            except Exception:
                pass
            from datetime import datetime as _dt
            primer_dia = _dt.strptime(fecha, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')
            query = """
                SELECT proveedo.NOMBRE, SUM(pmovi.TOTAL) AS total
                FROM pmovi
                INNER JOIN proveedo ON pmovi.PROVEEDOR = proveedo.PROVEEDOR
                WHERE DATE(pmovi.FECHA) BETWEEN %s AND %s AND pmovi.codigo = 'R' AND pmovi.empresa_id = %s
                GROUP BY proveedo.NOMBRE
            """
            cursor.execute(query, (primer_dia, fecha, self.empresa_id))
            rows = cursor.fetchall()
            return rows
        except Exception as e:
            logging.error(f"Error obteniendo pagos a proveedores: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def get_provider_comprobantes(self, fecha):
        """Comprobantes al proveedor (codigo != 'R') agregados por proveedor para el periodo del mes del 'fecha'"""
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor()
        try:
            # Debug: log which empresa_id is being used for this query
            try:
                logging.info(f"get_provider_comprobantes called with empresa_id={self.empresa_id} fecha={fecha}")
                print(f"[DEBUG] get_provider_comprobantes empresa_id={self.empresa_id} fecha={fecha}")
            except Exception:
                pass
            from datetime import datetime as _dt
            primer_dia = _dt.strptime(fecha, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')
            query = """
                SELECT proveedo.NOMBRE,
                    SUM(CASE WHEN pmovi.codigo = 'C' THEN -pmovi.TOTAL ELSE pmovi.TOTAL END) AS total
                FROM pmovi
                INNER JOIN proveedo ON pmovi.PROVEEDOR = proveedo.PROVEEDOR
                WHERE DATE(pmovi.FECHA) BETWEEN %s AND %s AND pmovi.codigo != 'R' AND pmovi.empresa_id = %s
                GROUP BY proveedo.NOMBRE
            """
            cursor.execute(query, (primer_dia, fecha, self.empresa_id))
            rows = cursor.fetchall()
            return rows
        except Exception as e:
            logging.error(f"Error obteniendo comprobantes de proveedores: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
        return results

    def get_monthly_total(self, fecha):
        connection = self.connect()
        if not connection:
            return 0
        cursor = connection.cursor()
        query = """
            SELECT 
                COALESCE((
                    SELECT SUM(CASE WHEN TRIM(CODIGO) = 'C' THEN -total ELSE total END) 
                    FROM facturas 
                    WHERE fecha BETWEEN %s AND %s AND empresa_id = %s
                ), 0) +
                COALESCE((
                    SELECT SUM(total) 
                    FROM remitos 
                    WHERE fecha BETWEEN %s AND %s AND empresa_id = %s AND tipo = 'N'
                ), 0) AS total_mes        
        """
        try:
            # Debug: log which empresa_id is being used for this query
            try:
                logging.info(f"get_monthly_total called with empresa_id={self.empresa_id} fecha={fecha}")
                print(f"[DEBUG] get_monthly_total empresa_id={self.empresa_id} fecha={fecha}")
            except Exception:
                pass
            primer_dia = datetime.strptime(fecha, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')
            cursor.execute(query, (primer_dia, fecha, self.empresa_id, primer_dia, fecha, self.empresa_id))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logging.error(f"Error ejecutando consulta de totales de mes {e}")
        finally:
            cursor.close()
            connection.close()
            
    def get_sales_por_pago(self, fecha):
        connection = self.connect()
        if not connection:
            return 0
        cursor = connection.cursor()
        query = """
            SELECT 
                concat(pagos.pago, " - Lista ", pagos.lista, " - ", pagos.detalle) AS descripcion_pago, 
                REPARTO,
                SUM(case when TRIM(facturas.codigo) = 'C' THEN -total ELSE total END) AS total_mes,
                facturas.CONTADO
                FROM facturas
                    LEFT JOIN pagos ON facturas.pago = pagos.pago            
                WHERE DATE_FORMAT(facturas.FECHA, '%Y%m') = %s  -- formato 'YYYY-MM'
                  AND facturas.empresa_id = %s
                GROUP BY REPARTO, pagos.DETALLE, facturas.CONTADO

            UNION ALL

                SELECT 
                    'TICKET' AS descripcion_pago, 
                    'S' AS REPARTO,
                    COALESCE(SUM(remitos.total), 0) AS total_mes,
                    'S' AS CONTADO
                FROM remitos
                WHERE DATE_FORMAT(remitos.FECHA, '%Y%m') = %s
                    AND remitos.empresa_id = %s
                    AND remitos.tipo = 'N'
        """
        results = []
        try:
            # Debug: log which empresa_id is being used for this query
            try:
                logging.info(f"get_sales_por_pago called with empresa_id={self.empresa_id} fecha={fecha}")
                print(f"[DEBUG] get_sales_por_pago empresa_id={self.empresa_id} fecha={fecha}")
            except Exception:
                pass
            periodo = datetime.strptime(fecha, '%Y-%m-%d').strftime('%Y%m')
            cursor.execute(query, (periodo, self.empresa_id, periodo, self.empresa_id))
            results = cursor.fetchall()
        except Exception as e:
            logging.error(f"Errora ejecutando consulta de datos de pago {e}")
        finally:
            cursor.close()
            connection.close()
        return results

    def get_vendedor_sales_nc(self, fecha_desde, fecha_hasta):
        """Obtiene ventas y NC por vendedor para un rango de fechas.

        Retorna una lista de dicts con:
            vendedor, nombre_vendedor, ventas, nc
        Excluye vendedores con ventas <= 0.
        """
        connection = self.connect()
        if not connection:
            return []

        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT
                t.vendedor,
                COALESCE(NULLIF(TRIM(v.nom_ven), ''), CONCAT('Vendedor ', t.vendedor)) AS nombre_vendedor,
                ROUND(SUM(t.ventas), 2) AS ventas,
                SUM(t.nc) AS nc
            FROM (
                SELECT
                    vv.vendedor AS vendedor,
                    SUM(vv.neto) AS ventas,
                    0 AS nc
                FROM estadisticas.ventas_vendedor vv
                WHERE DATE(vv.fecha) BETWEEN %s AND %s
                GROUP BY vv.vendedor

                UNION ALL

                SELECT
                                        a.Vendedor AS vendedor,
                    0 AS ventas,
                    COUNT(*) AS nc
                FROM anulacomp a
                INNER JOIN movi m
                                        ON a.CompAfectado = m.comp
                                     AND a.TipoCompAf = m.clase
                                WHERE a.TipoComp = 'C'
                  AND m.pagoant = '0'
                  AND DATE(m.fecha) BETWEEN %s AND %s
                  AND m.empresa_id = %s
                                GROUP BY a.Vendedor

                UNION ALL

                SELECT
                    r.vendedor AS vendedor,
                    SUM(r.total) AS ventas,
                    0 AS nc
                FROM remitos r
                WHERE r.tipo = 'N'
                  AND r.facturado = 'S'
                  AND DATE(r.fecha) BETWEEN %s AND %s
                  AND r.empresa_id = %s
                GROUP BY r.vendedor
            ) t
            LEFT JOIN vendedor v ON v.vendedor = t.vendedor
            GROUP BY t.vendedor, nombre_vendedor
            HAVING SUM(t.ventas) > 0
            ORDER BY SUM(t.ventas) DESC;
        """

        try:
            cursor.execute(
                query,
                (
                    fecha_desde,
                    fecha_hasta,
                    fecha_desde,
                    fecha_hasta,
                    self.empresa_id,
                    fecha_desde,
                    fecha_hasta,
                    self.empresa_id,
                ),
            )
            rows = cursor.fetchall() or []
            result = []
            for row in rows:
                result.append(
                    {
                        'vendedor': row.get('vendedor') or '',
                        'nombre_vendedor': row.get('nombre_vendedor') or 'Sin vendedor',
                        'ventas': float(row.get('ventas') or 0),
                        'nc': int(row.get('nc') or 0),
                    }
                )
            if result:
                return result

            # Fallback: si estadisticas.ventas_vendedor no tiene datos en este host,
            # recalcular ventas desde tablas operativas del dashboard.
            fallback_query = """
                SELECT
                    t.vendedor,
                    COALESCE(NULLIF(TRIM(v.nom_ven), ''), CONCAT('Vendedor ', t.vendedor)) AS nombre_vendedor,
                    ROUND(SUM(t.ventas), 2) AS ventas,
                    SUM(t.nc) AS nc
                FROM (
                    SELECT
                        s.vendedor AS vendedor,
                        SUM(
                            CASE WHEN TRIM(m.codigo) = 'C'
                                THEN -(s.cantidad * s.unitario)
                                ELSE  (s.cantidad * s.unitario)
                            END
                        ) AS ventas,
                        0 AS nc
                    FROM stock_ve s
                    INNER JOIN movi m ON s.idmovi = m.idmovi
                    WHERE DATE(m.fecha) BETWEEN %s AND %s
                      AND m.empresa_id = %s
                    GROUP BY s.vendedor

                    UNION ALL

                    SELECT
                        r.vendedor AS vendedor,
                        SUM(r.total) AS ventas,
                        0 AS nc
                    FROM remitos r
                    WHERE DATE(r.fecha) BETWEEN %s AND %s
                      AND r.empresa_id = %s
                      AND r.tipo = 'N'
                      AND r.facturado = 'S'
                    GROUP BY r.vendedor

                    UNION ALL

                    SELECT
                        a.Vendedor AS vendedor,
                        0 AS ventas,
                        COUNT(*) AS nc
                    FROM anulacomp a
                    INNER JOIN movi m
                        ON a.CompAfectado = m.comp
                       AND a.TipoCompAf = m.clase
                    WHERE a.TipoComp = 'C'
                      AND m.pagoant = '0'
                      AND DATE(m.fecha) BETWEEN %s AND %s
                      AND m.empresa_id = %s
                    GROUP BY a.Vendedor
                ) t
                LEFT JOIN vendedor v ON v.vendedor = t.vendedor
                GROUP BY t.vendedor, nombre_vendedor
                HAVING SUM(t.ventas) > 0
                ORDER BY SUM(t.ventas) DESC;
            """

            cursor.execute(
                fallback_query,
                (
                    fecha_desde,
                    fecha_hasta,
                    self.empresa_id,
                    fecha_desde,
                    fecha_hasta,
                    self.empresa_id,
                    fecha_desde,
                    fecha_hasta,
                    self.empresa_id,
                ),
            )
            rows_fb = cursor.fetchall() or []
            result_fb = []
            for row in rows_fb:
                result_fb.append(
                    {
                        'vendedor': row.get('vendedor') or '',
                        'nombre_vendedor': row.get('nombre_vendedor') or 'Sin vendedor',
                        'ventas': float(row.get('ventas') or 0),
                        'nc': int(row.get('nc') or 0),
                    }
                )
            return result_fb
        except Exception as e:
            logging.error(f"Error obteniendo ventas/NC por vendedor: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def get_vendedor_sales_detail(self, fecha_desde, fecha_hasta):
        """Obtiene el detalle de ventas por vendedor para exportar a Excel."""
        connection = self.connect()
        if not connection:
            return []

        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT
                vv.vendedor AS Vendedor,
                vv.nombre_vendedor AS NombreVendedor,
                DATE_FORMAT(vv.fecha, '%Y-%m-%d') AS Fecha,
                vv.comprobante AS Comprobante,
                vv.cliente AS Cliente,
                vv.lista AS Lista,
                ROUND(COALESCE(vv.neto, 0), 2) AS Neto,
                ROUND(COALESCE(vv.comision, 0), 2) AS PorcentajeComision,
                ROUND(COALESCE(vv.neto, 0) * COALESCE(vv.comision, 0) / 100, 2) AS ImporteComision,
                vv.comp_relacionado AS ComprobanteRelacionado,
                CASE
                    WHEN vv.pago_anticipado = 1 THEN 'SI'
                    ELSE 'NO'
                END AS PagoAnticipado,
                vv.periodo AS Periodo,
                vv.tipo_comp AS TipoComprobante,
                vv.clave AS ClaveArticulo,
                vv.articulo AS Articulo,
                COALESCE(vv.cantidad, 0) AS Cantidad
            FROM estadisticas.ventas_vendedor vv
            WHERE DATE(vv.fecha) BETWEEN %s AND %s
            ORDER BY vv.nombre_vendedor, vv.fecha, vv.comprobante, vv.clave
        """

        try:
            cursor.execute(query, (fecha_desde, fecha_hasta))
            return cursor.fetchall() or []
        except Exception as e:
            logging.error(f"Error obteniendo detalle de ventas por vendedor: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def get_vendedor_monthly_history(self, fecha_hasta):
        """Obtiene ventas mensuales por vendedor para el último año.

        Retorna lista de dicts con: vendedor, nombre_vendedor, periodo, total_neto
        """
        connection = self.connect()
        if not connection:
            return []

        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT
                vv.vendedor AS vendedor,
                COALESCE(NULLIF(TRIM(vv.nombre_vendedor), ''), CONCAT('Vendedor ', vv.vendedor)) AS nombre_vendedor,
                vv.periodo AS periodo,
                ROUND(SUM(vv.neto), 2) AS total_neto
            FROM estadisticas.ventas_vendedor vv
            WHERE DATE(vv.fecha) >= DATE_SUB(%s, INTERVAL 1 YEAR)
              AND DATE(vv.fecha) <= %s
            GROUP BY vv.vendedor, vv.nombre_vendedor, vv.periodo
            ORDER BY vv.vendedor, vv.periodo
        """
        try:
            cursor.execute(query, (fecha_hasta, fecha_hasta))
            rows = cursor.fetchall() or []
            return [
                {
                    'vendedor': row.get('vendedor') or '',
                    'nombre_vendedor': row.get('nombre_vendedor') or 'Sin vendedor',
                    'periodo': row.get('periodo') or '',
                    'total_neto': float(row.get('total_neto') or 0),
                }
                for row in rows
            ]
        except Exception as e:
            logging.error(f"Error obteniendo histórico mensual por vendedor: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def get_bonificaciones_summary(self, fecha_desde, fecha_hasta):
        """Agrupa facturas por bonificacion para un rango de fechas."""
        connection = self.connect()
        if not connection:
            return []

        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT
                TRIM(COALESCE(LISTA, '')) AS lista,
                ROUND(COALESCE(boni, 0), 2) AS boni,
                COUNT(DISTINCT IDMOVI) AS facturas_unicas,
                ROUND(
                    SUM(CASE WHEN TRIM(codigo) = 'C' THEN -total ELSE total END),
                    2
                ) AS suma_total
            FROM facturas
            WHERE DATE(fecha) BETWEEN %s AND %s
              AND empresa_id = %s
              AND TRIM(COALESCE(LISTA, '')) IN ('1', '4')
            GROUP BY TRIM(COALESCE(LISTA, '')), ROUND(COALESCE(boni, 0), 2)
            ORDER BY lista, boni
        """

        try:
            cursor.execute(query, (fecha_desde, fecha_hasta, self.empresa_id))
            rows = cursor.fetchall() or []
            result = []
            for row in rows:
                result.append(
                    {
                        'lista': str(row.get('lista') or ''),
                        'boni': float(row.get('boni') or 0),
                        'facturas_unicas': int(row.get('facturas_unicas') or 0),
                        'suma_total': float(row.get('suma_total') or 0),
                    }
                )
            return result
        except Exception as e:
            logging.error(f"Error obteniendo resumen de bonificaciones: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
    
    def get_aging_summary(self):
        """Obtiene el resumen de vencimientos de facturas"""
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor()
        query = """
            SELECT 
                CASE 
                    WHEN movi.pago = 52 THEN 'Pago_52'
                    WHEN FECHAVEN > CURDATE() THEN 'A_Vencer'
                    WHEN FECHAVEN BETWEEN DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND CURDATE() THEN 'Vencida_0_30d'
                    WHEN FECHAVEN < DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 'Vencida_mas_30d'
                    ELSE 'Sin_fecha'
                END AS CategoriaVencimiento,
                COUNT(*) AS CantidadFacturas,
                ROUND(SUM(saldo), 2) AS saldo
            FROM movi
            WHERE saldo > 0 and substr(codigo,1,1) in ('F','D') AND movi.empresa_id = %s
            GROUP BY CategoriaVencimiento
            ORDER BY CategoriaVencimiento
        """
        try:
            cursor.execute(query, (self.empresa_id,))
            results = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error ejecutando consulta de aging: {e}")
            results = []
        finally:
            cursor.close()
            connection.close()
        return results
    
    def get_aging_details(self):
        """Obtiene el detalle completo de facturas con categoría de vencimiento"""
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT 
                CASE 
                    WHEN movi.pago = 52 THEN 'Pago_52'
                    WHEN FECHAVEN > CURDATE() THEN 'A_Vencer'
                    WHEN FECHAVEN BETWEEN DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND CURDATE() THEN 'Vencida_0_30d'
                    WHEN FECHAVEN < DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN 'Vencida_mas_30d'
                    ELSE 'Sin_fecha'
                END AS CategoriaVencimiento,
                CONCAT(zona, cliente) AS cliente, 
                nombre, 
                concat(SUBSTR(codigo, 1, 1), ' - ', clase, ' - ', comp) AS comprobante, 
                DATE_FORMAT(fecha, '%Y-%m-%d') AS fecha, 
                DATE_FORMAT(FECHAVEN, '%Y-%m-%d') AS FECHAVEN,
                movi.saldo,
                pagos.detalle AS condicion_pago
                        FROM movi
                            INNER JOIN pagos on movi.pago = pagos.pago
                            WHERE movi.saldo > 0 and substr(codigo,1,1) in ('F','D') AND movi.empresa_id = %s
            ORDER BY CategoriaVencimiento, FECHAVEN
        """
        try:
            cursor.execute(query, (self.empresa_id,))
            results = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error ejecutando consulta de detalle de aging: {e}")
            results = []
        finally:
            cursor.close()
            connection.close()
        return results

    def get_remitos_sin_facturar(self):
        """Obtiene la suma de TOTAL de remitos no facturados (facturado='N') y tipo='X'"""
        connection = self.connect()
        if not connection:
            return 0.0
        cursor = connection.cursor()
        query = """
            SELECT SUM(TOTAL) AS total
            FROM remitos
            WHERE facturado = 'N' AND tipo = 'X' and reparte = 'A' AND empresa_id = %s;
        """
        try:
            cursor.execute(query, (self.empresa_id,))
            result = cursor.fetchone()
            total = result[0] if result and result[0] is not None else 0.0
            try:
                return float(total)
            except Exception:
                return 0.0
        except Exception as e:
            logging.error(f"Error ejecutando consulta de remitos sin facturar: {e}")
            return 0.0
        finally:
            cursor.close()
            connection.close()

    def get_special_articles_totals(self, fecha):
        """Obtiene totales por artículo para códigos específicos (día y acumulado mes).
        Devuelve dict con claves 'C01.001','D01.001','D01.002' cada una con 'total_dia' y 'total_mes'.
        """
        defaults = {
            'C01.001': {'total_dia': 0.0, 'total_mes': 0.0},
            'D01.001': {'total_dia': 0.0, 'total_mes': 0.0},
            'D01.002': {'total_dia': 0.0, 'total_mes': 0.0}
        }
        connection = self.connect()
        if not connection:
            return defaults
        cursor = connection.cursor()
        try:
            from datetime import datetime as _dt
            primer_dia = _dt.strptime(fecha, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')

            # Totales del día por CLAVE
            query_dia = """
                SELECT stock_ve.CLAVE,
                    SUM(CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -(stock_ve.CANTIDAD * stock_ve.UNITARIO) ELSE (stock_ve.CANTIDAD * stock_ve.UNITARIO) END) AS total_dia
                FROM stock_ve
                JOIN movi ON stock_ve.IDMOVI = movi.IDMOVI
                WHERE DATE(movi.FECHA) = %s AND stock_ve.CLAVE IN (%s, %s, %s) AND movi.empresa_id = %s
                GROUP BY stock_ve.CLAVE
            """
            # Totales del mes (entre primer_dia y fecha)
            query_mes = """
                SELECT stock_ve.CLAVE,
                    SUM(CASE WHEN TRIM(movi.CODIGO) = 'C' THEN -(stock_ve.CANTIDAD * stock_ve.UNITARIO) ELSE (stock_ve.CANTIDAD * stock_ve.UNITARIO) END) AS total_mes
                FROM stock_ve
                JOIN movi ON stock_ve.IDMOVI = movi.IDMOVI
                WHERE DATE(movi.FECHA) BETWEEN %s AND %s AND stock_ve.CLAVE IN (%s, %s, %s) AND movi.empresa_id = %s
                GROUP BY stock_ve.CLAVE
            """

            codes = ('C01.001', 'D01.001', 'D01.002')
            cursor.execute(query_dia, (fecha, codes[0], codes[1], codes[2], self.empresa_id))
            rows_dia = cursor.fetchall()
            for row in rows_dia:
                clave = row[0]
                total = row[1] if row[1] is not None else 0.0
                if clave in defaults:
                    defaults[clave]['total_dia'] = float(total)

            cursor.execute(query_mes, (primer_dia, fecha, codes[0], codes[1], codes[2], self.empresa_id))
            rows_mes = cursor.fetchall()
            for row in rows_mes:
                clave = row[0]
                total = row[1] if row[1] is not None else 0.0
                if clave in defaults:
                    defaults[clave]['total_mes'] = float(total)

            return defaults
        except Exception as e:
            logging.error(f"Error obteniendo totales de artículos especiales: {e}")
            return defaults
        finally:
            cursor.close()
            connection.close()

    def get_caja_totals(self, fecha):
        """Obtiene totales por tipo de caja (cajatipo.nombre) para el día y acumulado del mes.
        Devuelve un dict { nombre: {'total_dia': x, 'total_mes': y} }
        Filtra por cajamov.empresa_id = self.empresa_id
        """
        connection = self.connect()
        if not connection:
            return {}
        cursor = connection.cursor()
        try:
            primer_dia = datetime.strptime(fecha, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')

            query_dia = """
                SELECT cajatipo.nombre, SUM(cajamov.impentra) AS importe
                FROM cajamov
                INNER JOIN cajatipo ON cajamov.TIPO = cajatipo.TIPO
                WHERE DATE(cajamov.FECHA) = %s
                  AND cajamov.caja = 'S' AND cajamov.impentra > 0
                  AND cajamov.empresa_id = %s
                GROUP BY cajatipo.nombre
            """

            query_mes = """
                SELECT cajatipo.nombre, SUM(cajamov.impentra) AS importe
                FROM cajamov
                INNER JOIN cajatipo ON cajamov.TIPO = cajatipo.TIPO
                WHERE DATE(cajamov.FECHA) BETWEEN %s AND %s
                  AND cajamov.caja = 'S' AND cajamov.impentra > 0
                  AND cajamov.empresa_id = %s
                GROUP BY cajatipo.nombre
            """

            cursor.execute(query_dia, (fecha, self.empresa_id))
            rows_dia = cursor.fetchall()

            cursor.execute(query_mes, (primer_dia, fecha, self.empresa_id))
            rows_mes = cursor.fetchall()

            result = {}
            for row in rows_dia:
                try:
                    nombre = row[0]
                    importe = float(row[1] or 0)
                except Exception:
                    nombre = row[0] if row else 'Desconocido'
                    importe = 0.0
                result[nombre] = {'total_dia': importe, 'total_mes': 0.0}

            for row in rows_mes:
                try:
                    nombre = row[0]
                    importe = float(row[1] or 0)
                except Exception:
                    nombre = row[0] if row else 'Desconocido'
                    importe = 0.0
                if nombre in result:
                    result[nombre]['total_mes'] = importe
                else:
                    result[nombre] = {'total_dia': 0.0, 'total_mes': importe}

            return result
        except Exception as e:
            logging.error(f"Error obteniendo totales de caja: {e}")
            return {}
        finally:
            cursor.close()
            connection.close()

    def _format_money(self, amount):
        """Format amount as string with thousand separator as . and decimal separator as , without currency symbol."""
        try:
            formatted = f"{amount:,.2f}"
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
            if formatted.endswith(',00'):
                formatted = formatted[:-3]
            return formatted
        except Exception:
            return str(amount)

    def get_presupuesto_rango_params(self):
        """Obtiene los parámetros de rango de presupuestos de la tabla paramsist."""
        connection = self.connect()
        if not connection:
            return {'salto': 2500000, 'max': 20000000}
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT parametro, valor FROM paramsist WHERE parametro IN (%s, %s)",
                ('RANGO_PRESUPUESTO_SALTO', 'RANGO_PRESUPUESTO_MAX')
            )
            rows = cursor.fetchall()
            params = {}
            for row in rows:
                try:
                    params[row[0]] = float(row[1]) if row[1] is not None else 0.0
                except Exception:
                    params[row[0]] = 0.0
            salto = params.get('RANGO_PRESUPUESTO_SALTO', 2500000)
            max_val = params.get('RANGO_PRESUPUESTO_MAX', 20000000)
            return {'salto': salto, 'max': max_val}
        except Exception as e:
            logging.error(f"Error obteniendo parametros de rango de presupuestos: {e}")
            return {'salto': 2500000, 'max': 20000000}
        finally:
            cursor.close()
            connection.close()

    def get_presupuestos_rango(self, fecha_desde, fecha_hasta):
        """Obtiene la distribución de presupuestos (tipo='Z') por rangos definidos en paramsist.
        Retorna una lista de dicts con keys: range, count, total.
        Rangos: 0-2.5M, 2.5M-5M, ..., 17.5M-20M, >20M
        """
        params = self.get_presupuesto_rango_params()
        salto = params['salto']
        max_val = params['max']
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor(dictionary=True)
        try:
            query = """
                SELECT r.total AS neto
                FROM remitos r
                WHERE r.tipo = 'Z'
                  AND DATE(r.FECHA) BETWEEN %s AND %s
                  AND r.empresa_id = %s
            """
            cursor.execute(query, (fecha_desde, fecha_hasta, self.empresa_id))
            rows = cursor.fetchall()
            buckets = {}
            current = 0
            while current < max_val:
                lower = current
                upper = current + salto
                label = f"{self._format_money(lower)}-{self._format_money(upper)}"
                buckets[label] = {'count': 0, 'total': 0.0}
                current = upper
            overflow_label = f"> {self._format_money(max_val)}"
            buckets[overflow_label] = {'count': 0, 'total': 0.0}
            bucket_order = list(buckets.keys())
            for row in rows:
                neto = float(row['neto']) if row['neto'] is not None else 0.0
                if neto > max_val:
                    bucket_label = overflow_label
                else:
                    index = int(neto // salto)
                    lower = index * salto
                    upper = lower + salto
                    bucket_label = f"{self._format_money(lower)}-{self._format_money(upper)}"
                if bucket_label in buckets:
                    buckets[bucket_label]['count'] += 1
                    buckets[bucket_label]['total'] += neto
                else:
                    buckets[overflow_label]['count'] += 1
                    buckets[overflow_label]['total'] += neto
            result = []
            for label in bucket_order:
                vals = buckets[label]
                if vals['count'] > 0:
                    result.append({
                        'range': label,
                        'count': vals['count'],
                        'total': vals['total']
                    })
            return result
        except Exception as e:
            logging.error(f"Error obteniendo rangos de presupuestos: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def add_presupuesto_rango_params(self):
        """Añade los parámetros de rango de presupuestos a la tabla paramsist si no existen."""
        connection = self.connect()
        if not connection:
            return False
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM paramsist WHERE parametro = 'RANGO_PRESUPUESTO_SALTO'"
            )
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute(
                    "INSERT INTO paramsist (parametro, valor) VALUES (%s, %s)",
                    ('RANGO_PRESUPUESTO_SALTO', 2500000)
                )
            cursor.execute(
                "SELECT COUNT(*) FROM paramsist WHERE parametro = 'RANGO_PRESUPUESTO_MAX'"
            )
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute(
                    "INSERT INTO paramsist (parametro, valor) VALUES (%s, %s)",
                    ('RANGO_PRESUPUESTO_MAX', 20000000)
                )
            connection.commit()
            return True
        except Exception as e:
            logging.error(f"Error añadiendo parametros de rango: {e}")
            return False
        finally:
            cursor.close()
            connection.close()

    def get_inflacion_interanual(self, fecha):
        """
        Calcula la inflación interanual comparando:
        - Periodo actual: tabla stock (productos visibles con preciopro)
        - Periodo anterior: tabla valstock (mismo mes del año anterior)
        Retorna un dict con: {'variacion_porcentual': float, 'importe_actual': float, 'importe_anterior': float}
        """
        connection = self.connect()
        if not connection:
            return {'variacion_porcentual': 0.0, 'importe_actual': 0.0, 'importe_anterior': 0.0}
        cursor = connection.cursor()
        try:
            # Obtener el periodo actual desde la fecha (YYYYMM)
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            periodo_actual = fecha_dt.strftime('%Y%m')  # Ej: 202601
            año_actual = fecha_dt.year
            mes_actual = fecha_dt.month
            
            # Calcular periodo del año anterior (mismo mes)
            año_anterior = año_actual - 1
            periodo_anterior = f"{año_anterior}{mes_actual:02d}"  # Ej: 202501
            
            # Consulta para obtener valor actual del stock visible (solo coincidente con valstock)
            query_actual = """
                SELECT SUM(sub.precio) FROM (
                    SELECT AVG(s.preciopro) as precio
                    FROM stock s
                    INNER JOIN valstock v ON s.CLAVE = v.clave
                    WHERE s.VISIBLE = 'S'
                      AND s.empresa_id = %s
                      AND v.periodo = %s 
                      AND LENGTH(TRIM(s.CLAVE)) = 7
                      AND v.empresa_id = %s
                      AND s.preciopro > 0 
                      AND v.importe > 0
                    GROUP BY s.CLAVE
                ) as sub
            """
            
            # Consulta para obtener suma de importes del periodo anterior (solo coincidente con stock)
            query_anterior = """
                SELECT SUM(sub.precio) FROM (
                    SELECT AVG(v.importe) as precio
                    FROM valstock v
                    INNER JOIN stock s ON v.clave = s.CLAVE
                    WHERE v.periodo = %s
                      AND v.empresa_id = %s
                      AND s.VISIBLE = 'S'
                      AND LENGTH(TRIM(s.CLAVE)) = 7
                      AND s.empresa_id = %s
                      AND s.preciopro > 0 
                      AND v.importe > 0
                    GROUP BY s.CLAVE
                ) as sub
            """
            
            cursor.execute(query_actual, (self.empresa_id, periodo_anterior, self.empresa_id))
            result_actual = cursor.fetchone()
            importe_actual = float(result_actual[0] or 0) if result_actual and result_actual[0] else 0.0
            
            cursor.execute(query_anterior, (periodo_anterior, self.empresa_id, self.empresa_id))
            result_anterior = cursor.fetchone()
            importe_anterior = float(result_anterior[0] or 0) if result_anterior and result_anterior[0] else 0.0
            
            # Calcular variación porcentual
            if importe_anterior > 0:
                variacion_porcentual = ((importe_actual - importe_anterior) / importe_anterior) * 100
            else:
                variacion_porcentual = 0.0
            
            logging.info(f"Inflación interanual - Periodo actual: {periodo_actual} (stock), Anterior: {periodo_anterior} (valstock), Variación: {variacion_porcentual:.2f}%")
            
            return {
                'variacion_porcentual': variacion_porcentual,
                'importe_actual': importe_actual,
                'importe_anterior': importe_anterior,
                'periodo_actual': str(periodo_actual),
                'periodo_anterior': str(periodo_anterior)
            }
        except Exception as e:
            logging.error(f"Error calculando inflación interanual: {e}")
            return {'variacion_porcentual': 0.0, 'importe_actual': 0.0, 'importe_anterior': 0.0}
        finally:
            cursor.close()
            connection.close()

    def get_inflacion_interanual_details(self, fecha):
        """
        Obtiene el detalle de productos para la inflación interanual.
        Retorna lista de dicts: {CLAVE, DETALLE, precio_anterior, precio_actual, variacion}
        """
        connection = self.connect()
        if not connection:
            return []
        cursor = connection.cursor(dictionary=True)
        try:
            # Obtener el periodo actual desde la fecha (YYYYMM)
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            año_actual = fecha_dt.year
            mes_actual = fecha_dt.month
            
            # Calcular periodo del año anterior (mismo mes)
            año_anterior = año_actual - 1
            periodo_anterior = f"{año_anterior}{mes_actual:02d}"  # Ej: 202501
            
            query = """
                SELECT 
                    s.CLAVE, 
                    s.DETALLE, 
                    AVG(v.importe) as precio_anterior, 
                    AVG(s.preciopro) as precio_actual,
                    CASE WHEN AVG(v.importe) > 0 THEN ((AVG(s.preciopro) - AVG(v.importe)) / AVG(v.importe)) * 100 ELSE 0 END as variacion
                FROM stock s
                INNER JOIN valstock v ON s.CLAVE = v.clave
                WHERE s.VISIBLE = 'S'
                  AND s.empresa_id = %s
                  AND v.periodo = %s
                  AND v.empresa_id = %s
                  AND LENGTH(TRIM(s.CLAVE)) = 7
                  AND s.preciopro > 0 
                  AND v.importe > 0
                GROUP BY s.CLAVE, s.DETALLE
                ORDER BY variacion DESC
            """
            
            cursor.execute(query, (self.empresa_id, periodo_anterior, self.empresa_id))
            results = cursor.fetchall()
            return results
        except Exception as e:
            logging.error(f"Error obteniendo detalle de inflación interanual: {e}")
            return []
        finally:
            cursor.close()
            connection.close()

    def get_full_price_history(self):
        """
        Obtiene el histórico de precios (valstock) para todos los artículos relevantes
        (visibles, length=7, precio>0).
        Retorna un diccionario: { 'CLAVE': [{'periodo': 'YYYYMM', 'precio': float}, ...] }
        """
        connection = self.connect()
        if not connection:
            return {}
        cursor = connection.cursor()
        try:
            # Seleccionar histórico de valstock para artículos activos
            # Agrupar por CLAVE y PERIODO para evitar duplicados
            query = """
                SELECT v.clave, v.periodo, AVG(v.importe) as importe
                FROM valstock v
                INNER JOIN stock s ON v.clave = s.CLAVE
                WHERE s.VISIBLE = 'S'
                  AND s.empresa_id = %s
                  AND v.empresa_id = %s
                  AND LENGTH(TRIM(s.CLAVE)) = 7
                  AND s.preciopro > 0
                  AND v.importe > 0
                GROUP BY v.clave, v.periodo
                ORDER BY v.clave, v.periodo
            """
            cursor.execute(query, (self.empresa_id, self.empresa_id))
            rows = cursor.fetchall()
            
            history = {}
            for row in rows:
                clave, periodo, importe = row
                if clave not in history:
                    history[clave] = []
                history[clave].append({
                    'periodo': periodo,
                    'precio': float(importe)
                })
                
            return history
        except Exception as e:
            logging.error(f"Error obteniendo histórico completo: {e}")
            return {}
        finally:
            cursor.close()
            connection.close()

