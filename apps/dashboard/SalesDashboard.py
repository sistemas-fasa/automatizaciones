from datetime import date, datetime, timedelta
from configparser import ConfigParser
import logging
import os
import shutil
import subprocess
from dotenv import load_dotenv
import sys

from DatabaseManager import DatabaseManager
from ReportGenerator import ReportGenerator
from DataProcessor import DataProcessor
from EmailSender import EmailSender

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))

env_path = os.path.join(project_root, '.env')
if os.path.isfile(env_path):
    load_dotenv(dotenv_path=env_path, override=True)
else:
    fallback_env_path = os.path.join(script_dir, '.env')
    if os.path.isfile(fallback_env_path):
        load_dotenv(dotenv_path=fallback_env_path, override=True)


def _read_ini_db_defaults():
    ini_path = os.path.join(project_root, 'fasa.ini')
    defaults = {}
    if not os.path.isfile(ini_path):
        return defaults

    cfg = ConfigParser()
    try:
        cfg.read(ini_path, encoding='utf-8')
        if cfg.has_section('param'):
            defaults['host'] = cfg.get('param', 'ServerDB', fallback='').strip()
            defaults['database'] = cfg.get('param', 'BaseDatos', fallback='').strip()
            defaults['port'] = cfg.get('param', 'port', fallback='').strip()
    except Exception as e:
        logging.error(f"Error leyendo fasa.ini: {e}")

    return defaults


INI_DB_DEFAULTS = _read_ini_db_defaults()

logging.basicConfig(
    filename='dashboard.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.basicConfig()

class SalesDashboard:

    def __init__(self, empresa_id=None):
        db_host = os.getenv('DB_HOST') or INI_DB_DEFAULTS.get('host') or '192.168.0.150'
        db_name = os.getenv('DB_NAME') or INI_DB_DEFAULTS.get('database') or 'fasa'
        db_port_raw = os.getenv('DB_PORT') or INI_DB_DEFAULTS.get('port') or '3306'
        try:
            db_port = int(db_port_raw)
        except Exception:
            db_port = 3306

        self.db_config = {
            'host': db_host,
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'fasca'),
            'database': db_name,
            'port': db_port
        }
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('FROM_EMAIL', ''),
            # Destinatarios para informes DIARIOS
            'to_emails_daily': [e.strip() for e in os.getenv('TO_EMAILS_DAILY', os.getenv('TO_EMAILS', '')).split(',') if e.strip()] or ['default@example.com'],
            # Destinatarios para informes MENSUALES
            'to_emails_monthly': [e.strip() for e in os.getenv('TO_EMAILS_MONTHLY', os.getenv('TO_EMAILS', '')).split(',') if e.strip()] or ['default@example.com']
        }
        self.fecha_consulta = datetime.now().strftime('%Y-%m-%d')
        # Determine empresa_id: prefer explicit parameter, otherwise read from .env (default 1)
        try:
            if empresa_id is not None:
                self.empresa_id = int(empresa_id)
            else:
                self.empresa_id = int(os.getenv('EMPRESA_ID', '1'))
        except Exception:
            self.empresa_id = 1
        # Loggear empresa_id efectivo
        try:
            logging.info(f"Inicializando SalesDashboard con empresa_id={self.empresa_id}")
            print(f"[DEBUG] SalesDashboard empresa_id={self.empresa_id}")
            logging.info(
                "Configuracion DB efectiva host=%s db=%s port=%s user=%s",
                self.db_config.get('host'),
                self.db_config.get('database'),
                self.db_config.get('port'),
                self.db_config.get('user'),
            )
        except Exception:
            pass

    def _run_regenera_comision_vendedor(self, fecha_desde, fecha_hasta):
        """Regenera ventas_vendedor para el rango antes del dashboard mensual."""
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        script_path = os.path.join(project_root, 'scripts', 'regenera_comision_vendedor.py')
        if not os.path.isfile(script_path):
            logging.warning(f"No se encontro script de regeneracion: {script_path}")
            return False

        cmd = [
            sys.executable,
            script_path,
            '--desde',
            fecha_desde,
            '--hasta',
            fecha_hasta,
            '--actualiza-vendedor-reparto',
        ]

        try:
            logging.info(
                "Ejecutando regeneracion de comision vendedor: %s",
                ' '.join(cmd),
            )
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=3600,
                check=False,
            )
            if proc.returncode != 0:
                logging.error(
                    "Regeneracion comision vendedor fallo rc=%s stderr=%s",
                    proc.returncode,
                    (proc.stderr or '').strip(),
                )
                return False

            logging.info("Regeneracion comision vendedor OK")
            if proc.stdout:
                logging.info("Salida regeneracion: %s", proc.stdout.strip()[:1000])
            return True
        except Exception as e:
            logging.error(f"Error ejecutando regeneracion comision vendedor: {e}")
            return False

    def _run_carga_ventas_vendedor(self, fecha_desde, fecha_hasta):
        """Ejecuta carga_ventas_vendedor.py para repoblar estadisticas.ventas_vendedor."""
        project_root = os.path.abspath(os.path.join(script_dir, '..'))
        script_path = os.path.join(project_root, 'scripts', 'carga_ventas_vendedor.py')
        if not os.path.isfile(script_path):
            logging.warning(f"No se encontro script de carga ventas vendedor: {script_path}")
            return False

        cmd = [
            sys.executable,
            script_path,
            '--desde',
            fecha_desde,
            '--hasta',
            fecha_hasta,
        ]

        try:
            logging.info(
                "Ejecutando carga ventas vendedor: %s",
                ' '.join(cmd),
            )
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=3600,
                check=False,
            )
            if proc.returncode != 0:
                logging.error(
                    "Carga ventas vendedor fallo rc=%s stderr=%s",
                    proc.returncode,
                    (proc.stderr or '').strip(),
                )
                return False

            logging.info("Carga ventas vendedor OK")
            if proc.stdout:
                logging.info("Salida carga: %s", proc.stdout.strip()[:1000])
            return True
        except Exception as e:
            logging.error(f"Error ejecutando carga ventas vendedor: {e}")
            return False

    def _export_vendedor_detail_excel(self, db_manager, fecha_desde, fecha_hasta, suffix):
        """Genera Excel con el detalle de cada venta por vendedor."""
        try:
            import pandas as pd
        except Exception as e:
            logging.error(f"No se pudo importar pandas para exportar detalle vendedor: {e}")
            return None, 0

        rows = db_manager.get_vendedor_sales_detail(fecha_desde, fecha_hasta)
        columns = [
            'Vendedor',
            'NombreVendedor',
            'Fecha',
            'Comprobante',
            'Cliente',
            'Lista',
            'Neto',
            'PorcentajeComision',
            'ImporteComision',
            'ComprobanteRelacionado',
            'PagoAnticipado',
            'Periodo',
            'TipoComprobante',
            'ClaveArticulo',
            'Articulo',
            'Cantidad',
        ]
        df = pd.DataFrame(rows, columns=columns)

        out_dir = os.path.join(project_root, 'dashboard_output', 'informes_vendedor')
        os.makedirs(out_dir, exist_ok=True)
        filename = (
            f"detalle_ventas_vendedor_{self.empresa_id}_"
            f"{fecha_hasta.replace('-', '_')}_{suffix}.xlsx"
        )
        out_path = os.path.join(out_dir, filename)

        try:
            with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Detalle ventas')
                ws = writer.sheets['Detalle ventas']
                for idx, col_name in enumerate(columns, start=1):
                    letter = ws.cell(row=1, column=idx).column_letter
                    max_len = max([len(str(col_name))] + [len(str(v)) for v in df[col_name].head(200).fillna('')])
                    ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 45)
                ws.freeze_panes = 'A2'

            logging.info("Detalle ventas vendedor exportado: %s filas=%s", out_path, len(df))
            return out_path, len(df)
        except Exception as e:
            logging.error(f"Error exportando detalle de ventas por vendedor: {e}")
            return None, len(df)

    def _send_vendedor_detail_excel(self, db_manager, fecha_desde, fecha_hasta, suffix, company_name):
        excel_path, row_count = self._export_vendedor_detail_excel(
            db_manager=db_manager,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            suffix=suffix,
        )
        if not excel_path:
            return False

        recipients = [
            e.strip()
            for e in os.getenv('VENDEDOR_DETAIL_TO_EMAILS', 'sistemas@ferreteriaavenida.com.ar').split(',')
            if e.strip()
        ]
        sender = EmailSender(self.smtp_config)
        if not hasattr(sender, 'send_files'):
            logging.info("EmailSender sin send_files; detalle vendedor generado sin enviar: %s", excel_path)
            return True

        subject = f"Detalle de ventas por vendedor - {company_name} - {fecha_desde} a {fecha_hasta}"
        body = f"""
        <html>
            <body>
                <p>Hola,</p>
                <p>Adjunto el detalle en Excel de cada venta por vendedor correspondiente al rango <strong>{fecha_desde} a {fecha_hasta}</strong>.</p>
                <p>Registros incluidos: <strong>{row_count}</strong>.</p>
                <p><em>Sistema Automático de Reportes</em></p>
            </body>
        </html>
        """
        sent = sender.send_files(subject, body, [excel_path], to_emails=recipients)
        if sent:
            logging.info("Detalle ventas vendedor enviado a %s archivo=%s", recipients, excel_path)
        return sent

    def run(self):
        db_manager = DatabaseManager(self.db_config, empresa_id=self.empresa_id)
        # Por defecto genera el dashboard del día. Si se desea el acumulado del mes,
        # pasar la bandera `--monthly` al ejecutar el script (o usar el parámetro desde código).
        acumulado_mes = getattr(self, 'acumulado_mes', False)
        fecha_desde = self.fecha_consulta
        fecha_hasta = self.fecha_consulta

        if acumulado_mes:
            try:
                fecha_dt = datetime.strptime(self.fecha_consulta, '%Y-%m-%d')
                primer_dia = fecha_dt.replace(day=1)
            except Exception:
                primer_dia = datetime.strptime(self.fecha_consulta, '%Y-%m-%d').replace(day=1)

            fecha_desde = primer_dia.strftime('%Y-%m-%d')
            fecha_hasta = self.fecha_consulta

            # Regla de negocio: para el acumulado mensual, regenerar ventas_vendedor
            # antes de construir el dashboard para asegurar datos actualizados.
            self._run_regenera_comision_vendedor(fecha_desde, fecha_hasta)

            sales_data = []
            cur = primer_dia
            while cur <= datetime.strptime(self.fecha_consulta, '%Y-%m-%d'):
                day_str = cur.strftime('%Y-%m-%d')
                try:
                    daily = db_manager.get_sales_data(day_str) or []
                    sales_data.extend(daily)
                except Exception as e:
                    logging.error(f"Error obteniendo datos para {day_str}: {e}")
                cur = cur + timedelta(days=1)

            monthly_total = db_manager.get_monthly_total(self.fecha_consulta)
        else:
            sales_data = db_manager.get_sales_data(self.fecha_consulta)
            monthly_total = db_manager.get_monthly_total(self.fecha_consulta)
        # Calcular el periodo equivalente del mes anterior (mismo día, ajustando si el mes anterior tiene menos días)
        from datetime import datetime as _dt
        import calendar as _calendar
        try:
            fecha_dt = _dt.strptime(self.fecha_consulta, '%Y-%m-%d')
            prev_year = fecha_dt.year
            prev_month = fecha_dt.month - 1
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
            # día ajustado al máximo del mes anterior
            prev_day = min(fecha_dt.day, _calendar.monthrange(prev_year, prev_month)[1])
            prev_fecha_dt = fecha_dt.replace(year=prev_year, month=prev_month, day=prev_day)
            prev_fecha = prev_fecha_dt.strftime('%Y-%m-%d')
            prev_month_total = db_manager.get_monthly_total(prev_fecha)
        except Exception as e:
            prev_month_total = 0
        sales_data_pago = db_manager.get_sales_por_pago(self.fecha_consulta)

        # Si no hay datos diarios y NO estamos generando acumulado, abortar.
        if not sales_data and not acumulado_mes:
            print("⚠️ No hay datos para esta fecha.")
            return

        # Normalizar sales_data_pago para DataProcessor cuando sales_data está vacío
        sales_data_pago_for_processor = sales_data_pago
        if not sales_data:
            # DataProcessor espera, en el caso vacío, iterables con clave 'DESCRIPCION_PAGO' (dict)
            try:
                if sales_data_pago and not isinstance(sales_data_pago[0], dict):
                    sales_data_pago_for_processor = []
                    for row in sales_data_pago:
                        # row puede ser tupla: (descripcion_pago, reparto, total)
                        descripcion = row[0] if len(row) > 0 else ''
                        sales_data_pago_for_processor.append({'DESCRIPCION_PAGO': descripcion})
            except Exception:
                sales_data_pago_for_processor = sales_data_pago

        stats = DataProcessor().process_data(sales_data, sales_data_pago_for_processor)
        # Si estamos generando acumulado del mes, indicar en stats y limpiar valores diarios
        if acumulado_mes:
            try:
                stats['acumulado_mes'] = True
                # En el acumulado del mes, total_dia no aplica pero mantenemos facturas_count y promedio_factura
                # que ya vienen calculados con todos los datos del mes
                stats['total_dia'] = 0.0
                # facturas_count y promedio_factura ya están calculados correctamente con sales_data acumulado
                # Para tablas que usan 'total_dia' asegúrese que la estructura exista
                # (DataProcessor normalmente llena por_pago/por_reparto con 'total_dia' y 'total_mes')
            except Exception:
                pass
        # Obtener remitos no facturados y agregar al diccionario de stats
        try:
            remitos_sin_facturar = db_manager.get_remitos_sin_facturar()
            stats['remitos_sin_facturar'] = remitos_sin_facturar
        except Exception as e:
            logging.error(f"Error obteniendo remitos sin facturar: {e}")
            stats['remitos_sin_facturar'] = 0.0
        
        # Fetch aging summary from DB and attach to stats
        try:
            aging_rows = db_manager.get_aging_summary()
            mapping = {
                'A_Vencer': 'A Vencer',
                'Vencida_0_30d': 'Vencidas 0 30 Dias',
                'Vencida_mas_30d': 'Vencidas mas de 30 Dias',
                'Sin_fecha': 'Sin Fecha',
                'Remitos sin Facturar': 'Remitos sin Facturar'
            }
            aging_list = []
            for row in aging_rows:
                if isinstance(row, dict):
                    name = row.get('CategoriaVencimiento') or row.get('Categoria')
                    value = float(row.get('saldo', 0))
                else:
                    name = row[0]
                    value = float(row[2]) if len(row) > 2 and row[2] is not None else 0.0
                name = mapping.get(name, name)
                aging_list.append({"name": name, "value": value})
            # Agregar remitos sin facturar al resumen de aging para que aparezca en el gráfico
            try:
                remitos_val = float(stats.get('remitos_sin_facturar', 0) or 0)
                # Sólo agregar si hay un monto (puede agregarse aunque sea 0 si se quiere siempre mostrar)
                aging_list.append({"name": mapping.get('Remitos sin Facturar', 'Remitos sin Facturar'), "value": remitos_val})
            except Exception as e:
                logging.error(f"Error agregando remitos sin facturar al aging: {e}")
            stats['aging'] = aging_list
        except Exception as e:
            stats['aging'] = []
            logging.error(f"Error obteniendo aging: {e}")
        
        # Fetch aging details for the table
        try:
            aging_details = db_manager.get_aging_details()
        except Exception as e:
            aging_details = []
            logging.error(f"Error obteniendo detalle de aging: {e}")
        # Obtener totales de artículos especiales (C01.001, D01.001, D01.002)
        try:
            articulos_especiales = db_manager.get_special_articles_totals(self.fecha_consulta)
            stats['articulos_especiales'] = articulos_especiales
        except Exception as e:
            logging.error(f"Error obteniendo totales de artículos especiales: {e}")
            stats['articulos_especiales'] = {
                'C01.001': {'total_dia': 0.0, 'total_mes': 0.0},
                'D01.001': {'total_dia': 0.0, 'total_mes': 0.0},
                'D01.002': {'total_dia': 0.0, 'total_mes': 0.0}
            }

        # Obtener totales por tipo de caja (día y mes)
        try:
            caja_totals = db_manager.get_caja_totals(self.fecha_consulta)
            stats['por_caja'] = caja_totals
        except Exception as e:
            logging.error(f"Error obteniendo totales de caja: {e}")
            stats['por_caja'] = {}

        # Asegurar que estadisticas.ventas_vendedor esté actualizado
        if acumulado_mes:
            self._run_carga_ventas_vendedor(fecha_desde, fecha_hasta)

        # Ventas + NC por vendedor: solo en acumulado mensual.
        if acumulado_mes:
            try:
                stats['ventas_nc_vendedor'] = db_manager.get_vendedor_sales_nc(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
                logging.info(
                    "ventas_nc_vendedor filas=%s rango=%s..%s",
                    len(stats['ventas_nc_vendedor'] or []),
                    fecha_desde,
                    fecha_hasta,
                )
            except Exception as e:
                logging.error(f"Error obteniendo ventas/NC por vendedor: {e}")
                stats['ventas_nc_vendedor'] = []
        else:
            stats['ventas_nc_vendedor'] = []

        # Histórico mensual por vendedor (último año): solo en acumulado mensual.
        if acumulado_mes:
            try:
                stats['vendedor_monthly_history'] = db_manager.get_vendedor_monthly_history(
                    fecha_hasta=fecha_hasta,
                )
                logging.info(
                    "vendedor_monthly_history filas=%s",
                    len(stats['vendedor_monthly_history'] or []),
                )
            except Exception as e:
                logging.error(f"Error obteniendo histórico mensual por vendedor: {e}")
                stats['vendedor_monthly_history'] = []
        else:
            stats['vendedor_monthly_history'] = []

        # Bonificaciones por rango del dashboard: solo en acumulado mensual.
        if acumulado_mes:
            try:
                stats['bonificaciones'] = db_manager.get_bonificaciones_summary(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
                logging.info(
                    "bonificaciones filas=%s rango=%s..%s",
                    len(stats['bonificaciones'] or []),
                    fecha_desde,
                    fecha_hasta,
                )
            except Exception as e:
                logging.error(f"Error obteniendo resumen de bonificaciones: {e}")
                stats['bonificaciones'] = []
        else:
            stats['bonificaciones'] = []

        # Obtener inflación interanual (solo para informes mensuales)
        if acumulado_mes:
            try:
                inflacion = db_manager.get_inflacion_interanual(self.fecha_consulta)
                stats['inflacion_interanual'] = inflacion
            except Exception as e:
                logging.error(f"Error obteniendo inflación interanual: {e}")
                stats['inflacion_interanual'] = {
                    'variacion_porcentual': 0.0,
                    'importe_actual': 0.0,
                    'importe_anterior': 0.0
                }
        else:
            stats['inflacion_interanual'] = None

        # Si es resumen mensual, obtener pagos y comprobantes por proveedor
        if acumulado_mes:
            try:
                pagos_rows = db_manager.get_provider_payments(self.fecha_consulta) or []
                comprobantes_rows = db_manager.get_provider_comprobantes(self.fecha_consulta) or []
                
                # Top 10 proveedores + Otros
                def _top_n_providers(rows, n=10):
                    items = [{'name': r[0], 'value': float(r[1] or 0)} for r in rows]
                    # Ordenar por valor descendente
                    items.sort(key=lambda x: x['value'], reverse=True)
                    if len(items) <= n:
                        return items
                    # Tomar los primeros n y agrupar el resto
                    top_items = items[:n]
                    otros_value = sum(item['value'] for item in items[n:])
                    if otros_value > 0:
                        top_items.append({'name': 'Otros', 'value': otros_value})
                    return top_items
                
                stats['pagos_proveedor'] = _top_n_providers(pagos_rows, 10)
                stats['comprobantes_proveedor'] = _top_n_providers(comprobantes_rows, 10)
            except Exception as e:
                logging.error(f"Error obteniendo datos por proveedor: {e}")
                stats['pagos_proveedor'] = []
                stats['comprobantes_proveedor'] = []

        # Company-specific title and color based on empresa_id
        company_map = {
            1: {'title': 'Ferreteria Avenida SA', 'color': '#E60000'},
            2: {'title': 'Steffen Hnos SRL', 'color': '#006400'},
            3: {'title': 'Transporte Avenida SRL', 'color': '#FF5722'},
        }
        try:
            comp_info = company_map.get(int(self.empresa_id), {'title': 'Empresa', 'color': '#1F2937'})
        except Exception:
            comp_info = {'title': 'Empresa', 'color': '#1F2937'}
        stats['empresa_title'] = comp_info['title']
        stats['empresa_color'] = comp_info['color']

        # Generar reporte detallado de inflación si corresponde
        if getattr(self, 'acumulado_mes', False) and stats.get('inflacion_interanual'):
            try:
                inflacion_details = db_manager.get_inflacion_interanual_details(self.fecha_consulta)
                suffix_infl = 'acumulado_mes'
                inflacion_filename = f"inflacion_interanual_{self.empresa_id}_{self.fecha_consulta.replace('-', '_')}_{suffix_infl}.html"
                
                rep_gen = ReportGenerator()
                
                # Generar Archivos de Histórico (JSON + HTML Viewer)
                try:
                    logging.info("Generando datos históricos...")
                    history_data = db_manager.get_full_price_history()
                    rep_gen.generate_history_json(history_data, 'history.json')
                    with open('history_viewer.html', 'w', encoding='utf-8') as f:
                        f.write(rep_gen.generate_history_viewer_html())
                except Exception as e:
                    logging.error(f"Error generando histórico: {e}")

                inflacion_html = rep_gen.generate_inflacion_details_html(inflacion_details, comp_info, self.fecha_consulta)
                
                with open(inflacion_filename, 'w', encoding='utf-8') as f:
                    f.write(inflacion_html)
                
                # Link para el dashboard principal
                stats['inflacion_link'] = inflacion_filename

                # Copiar al servidor
                try:
                    # /var/www/html/informes es mount a /srv/fasa-data/data/informes.
                    # El servidor 195 (\\192.168.0.195) no existe mas.
                    server_path = "/var/www/html/informes"
                    if os.path.exists(server_path):
                        dest_file = os.path.join(server_path, inflacion_filename)
                        shutil.copy2(inflacion_filename, dest_file)
                        
                        # Copiar archivos de histórico
                        if os.path.exists('history.json'):
                            shutil.copy2('history.json', os.path.join(server_path, 'history.json'))
                        if os.path.exists('history_viewer.html'):
                            shutil.copy2('history_viewer.html', os.path.join(server_path, 'history_viewer.html'))
                            
                        print(f"✅ Reporte Inflación y Histórico generado y copiado: {dest_file}")
                except Exception as e:
                    logging.error(f"Error copiando reporte inflación al servidor: {e}")
            except Exception as e:
                logging.error(f"Error generando reporte detalle inflación: {e}")

        html_content = ReportGenerator().generate_html_report(stats, monthly_total, self.fecha_consulta, aging_details, prev_month_total)

        suffix = 'acumulado_mes' if getattr(self, 'acumulado_mes', False) else 'dia'
        # Incluir el id de la empresa en el nombre de archivo para evitar sobrescrituras
        filename = f"dashboard_ventas_{self.empresa_id}_{self.fecha_consulta.replace('-', '_')}_{suffix}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Dashboard generado: {filename}")
        
        # Copiar al servidor de informes
        try:
            # /var/www/html/informes es mount a /srv/fasa-data/data/informes.
            server_path = "/var/www/html/informes"
            if os.path.exists(server_path):
                dest_file = os.path.join(server_path, filename)
                shutil.copy2(filename, dest_file)
                print(f"Archivo copiado al servidor: {dest_file}")
                logging.info(f"Dashboard copiado a {dest_file}")
            else:
                print(f"No se puede acceder al servidor: {server_path}")
                logging.warning(f"No se pudo acceder a {server_path}")
        except Exception as e:
            print(f"Error al copiar al servidor: {e}")
            logging.error(f"Error copiando al servidor: {e}")

        # Determinar tipo de reporte y enviar email con destinatarios correspondientes
        report_type = 'monthly' if getattr(self, 'acumulado_mes', False) else 'daily'
        # Para incluir el nombre de la empresa en el correo usar el campo company_title definido arriba
        EmailSender(self.smtp_config).send_email(html_content, self.fecha_consulta, filename, report_type, company_name=comp_info['title'])

        try:
            skip_vendedor_detail = os.getenv('SKIP_VENDEDOR_DETAIL_EMAIL', '').lower() in ('1', 'true', 'yes', 'si')
            if not skip_vendedor_detail:
                # El informe diario tambien necesita el detalle de vendedor actualizado.
                if not acumulado_mes:
                    self._run_regenera_comision_vendedor(fecha_desde, fecha_hasta)
                self._send_vendedor_detail_excel(
                    db_manager=db_manager,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    suffix=suffix,
                    company_name=comp_info['title'],
                )
        except Exception as e:
            logging.error(f"Error generando/enviando detalle vendedor: {e}")

        # En entornos Linux, enviar logs de ejecución al terminar
        try:
            if sys.platform.startswith('linux'):
                import glob
                logs_dir = os.path.expanduser('/home/ferreteria')
                pattern = os.path.join(logs_dir, 'sales_*.log')
                log_files = sorted(glob.glob(pattern))
                if log_files:
                    subject = f"Logs Dashboard - {comp_info['title']} - {self.fecha_consulta}"
                    body = f"Adjunto los logs del dashboard para {comp_info['title']} (fecha {self.fecha_consulta})."
                    EmailSender(self.smtp_config).send_files(subject, body, log_files, to_emails=['oscar@ferreteriaavenida.com.ar'])
                else:
                    logging.info('No se encontraron logs para enviar')
        except Exception as e:
            logging.error(f"Error al intentar enviar logs: {e}")

def main():
    # parse simple CLI args and allow passing empresa-id
    empresa_id_arg = None
    # Permite usar: --monthly (o -m) para generar acumulado del mes
    # y --date=YYYY-MM-DD para forzar la fecha de consulta
    args = sys.argv[1:]
    acumulado = False
    fecha_override = None
    for a in args:
        if a in ('--monthly', '-m'):
            acumulado = True
        if a.startswith('--date='):
            try:
                fecha_override = a.split('=', 1)[1]
            except Exception:
                pass
        # Soportar --empresa-id=ID y --empresa-id ID y alias -e
        if a.startswith('--empresa-id='):
            try:
                empresa_id_arg = int(a.split('=', 1)[1])
            except Exception:
                empresa_id_arg = 1
        elif a in ('--empresa-id', '-e'):
            # tomar valor siguiente si existe
            try:
                idx = args.index(a)
                # safe check
                if idx + 1 < len(args):
                    try:
                        empresa_id_arg = int(args[idx + 1])
                    except Exception:
                        empresa_id_arg = empresa_id_arg
            except Exception:
                pass
    dashboard = SalesDashboard(empresa_id=empresa_id_arg)
    if fecha_override:
        dashboard.fecha_consulta = fecha_override
    dashboard.acumulado_mes = acumulado
    dashboard.run()

if __name__ == "__main__":
    main()        
