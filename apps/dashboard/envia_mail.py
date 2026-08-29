import os
import smtplib
import mysql.connector
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
from collections import defaultdict
import locale
from dotenv import load_dotenv
# Configuración de logging
import logging
logging.basicConfig(
    filename='dashboard.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Cargar variables de entorno
load_dotenv()

# Configurar locale para formato de moneda argentina
try:
    locale.setlocale(locale.LC_ALL, 'es_AR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'C')

class SalesDashboard:
    def __init__(self):
        # Configuración desde variables de entorno
        self.db_config = {
            'host': os.getenv('DB_HOST', '192.168.0.150'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'fasca'),
            'database': os.getenv('DB_NAME', 'fasa'),
            'port': int(os.getenv('DB_PORT', '3306'))
        }
        # Configuración SMTP
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('FROM_EMAIL', ''),
            'to_emails': os.getenv('TO_EMAILS', '').split(',')  # emails separados por coma
        }
        
        self.fecha_consulta = datetime.now().strftime('%Y-%m-%d')
    
    def connect_database(self):
        """Conectar a la base de datos MySQL"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except mysql.connector.Error as err:
            print(f"Error conectando a la base de datos: {err}")
            logging.error(f"Error conectando a la base de datos: {err}")
            return None
    
    def get_sales_data(self, fecha=None):
        """Obtener datos de ventas de la base de datos"""
        if not fecha:
            fecha = self.fecha_consulta
        connection = self.connect_database()
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
                pagos.DETALLE AS DESCRIPCION_PAGO,
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
            WHERE DATE(movi.FECHA) = %s
            ORDER BY movi.FECHA DESC;
        """
        try:
            cursor.execute(query, (fecha,))
            results = cursor.fetchall()
            cursor.close()
            connection.close()
            return results
        except mysql.connector.Error as err:
            print(f"Error ejecutando consulta: {err}")
            logging.error(f"Error ejecutando consulta: {err}")
            cursor.close()
            connection.close()
            return []
            
    def get_monthly_data(self, fecha=None):
        """Obtener datos acumulados del mes"""
        if not fecha:
            fecha = self.fecha_consulta
            
        # Primer día del mes
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        primer_dia = fecha_obj.replace(day=1).strftime('%Y-%m-%d')
        
        connection = self.connect_database()
        if not connection:
            return 0
        
        cursor = connection.cursor()
        
        query = """
        SELECT 
            SUM(
                CASE 
                    WHEN TRIM(CODIGO) = 'C' THEN -total 
                    ELSE total 
                END
            ) AS total_mes
        FROM facturas
        WHERE fecha BETWEEN %s AND %s;
        """
        
        try:
            cursor.execute(query, (primer_dia, fecha))
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            return result[0] if result[0] else 0
        except mysql.connector.Error as err:
            logging.error(f"Error obteniendo datos mensuales: {err}")
            print(f"Error obteniendo datos mensuales: {err}")
            cursor.close()
            connection.close()
            return 0
    
    def process_data(self, data):
        """Procesar los datos para generar estadísticas"""
        if not data:
            return {
                'total_dia': 0,
                'por_pago': {},
                'por_contado': {},
                'por_lista': {},
                'por_reparto': {},
                'facturas_count': 0,
                'promedio_factura': 0
            }
        
        total_dia = sum(float(row['total'] or 0) for row in data)
        def cantidad_comprobantes():
            # Set para almacenar tuplas únicas (CODIGO, CLASE, COMP)
            facturas_unicas = set()

            # Recorrer cada registro y extraer las claves relevantes
            for factura in data:
                codigo = factura.get('CODIGO')
                clase = factura.get('CLASE')
                comp = factura.get('COMP')

                # Verificar que los campos existen y no son None
                if codigo is not None and clase is not None and comp is not None:
                    clave_factura = (codigo.strip(), clase.strip(), comp.strip())  # Limpiar espacios extras
                    facturas_unicas.add(clave_factura)
            return len(facturas_unicas)
        
        facturas_count = cantidad_comprobantes()
        
        promedio_factura = total_dia / facturas_count if facturas_count > 0 else 0
        
        # Agrupar por condición de pago
        por_pago = defaultdict(float)
        for row in data:
            pago_desc = row['DESCRIPCION_PAGO'] or 'Sin definir'
            por_pago[pago_desc] += float(row['total'] or 0)
                
        # Agrupar por contado/cuenta corriente
        por_contado = defaultdict(float)
        for row in data:
            tipo = 'Contado' if row['CONTADO'] == 'S' else 'Cuenta Corriente'
            por_contado[tipo] += float(row['total'] or 0)
        
        # Agrupar por lista
        por_lista = defaultdict(float)
        for row in data:
            lista = row['LISTA'] or 'Sin asignar'
            por_lista[lista] += float(row['total'] or 0)
        
        # Agrupar por reparto
        por_reparto = defaultdict(float)
        for row in data:
            reparto = row['REPARTO'].strip() if row['REPARTO'] else ''
            if reparto == 'N':
                reparto = 'Retira'
            elif reparto == 'S':
                reparto = 'Reparto'
            else:
                reparto = reparto or 'No especificado'
            por_reparto[reparto] += float(row['total'] or 0)
        
        return {
            'total_dia': total_dia,
            'por_pago': dict(por_pago),
            'por_contado': dict(por_contado),
            'por_lista': dict(por_lista),
            'por_reparto': dict(por_reparto),
            'facturas_count': facturas_count,
            'promedio_factura': promedio_factura
        }
    
    def format_currency(self, amount):
        """Formatear cantidad como moneda argentina"""
        try:
            return f"${amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return f"${amount:.2f}"

    def generate_tailwind_table(self, title, data_dict, total_dia):
        """
        Genera una tabla HTML con TailwindCSS, mini-gráficos animados,
        colores dinámicos y etiquetas interactivas.

        :param title: Título de la tabla
        :param data_dict: Diccionario con los datos {nombre: valor}
        :param total_dia: Valor total del día para calcular porcentajes
        :return: Cadena HTML con la tabla generada
        """
        rows = ""

        for detalle, monto in data_dict.items():
            porcentaje = (monto / total_dia * 100) if total_dia > 0 else 0
            bar_width = min(100, max(0, porcentaje))  # Limitar entre 0% y 100%

            # Determinar clase de degradado basado en porcentaje
            if bar_width < 30:
                bar_gradient = "from-red-500 to-red-600"
            elif bar_width < 70:
                bar_gradient = "from-yellow-400 via-yellow-500 to-yellow-600"
            else:
                bar_gradient = "from-green-500 to-green-600"

            row = f"""
            <tr class="border-b border-gray-200 hover:bg-gray-50 group">
                <td class="px-4 py-3">{detalle}</td>
                <td class="px-4 py-3 font-medium">{self.format_currency(monto)}</td>
                <td class="px-4 py-3 text-right">{porcentaje:.1f}%</td>
                <td class="px-4 py-3 relative">
                    <div 
                        class="relative w-full bg-gray-200 rounded-full h-2 overflow-hidden cursor-help"
                        title="{porcentaje:.1f}%"
                    >
                        <div 
                            class="absolute inset-0 rounded-full transition-all duration-700 ease-out bg-gradient-to-r {bar_gradient}"
                            style="width: {bar_width:.1f}%"
                        ></div>
                        <span class="absolute inset-0 flex items-center justify-center text-xs text-white font-bold pointer-events-none">
                            {porcentaje:.1f}%
                        </span>
                    </div>
                </td>
            </tr>
            """
            rows += row

        table_html = f"""
        <div class="bg-white rounded-xl shadow-md overflow-hidden mb-8">
            <div class="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-4">
                <h3 class="text-lg font-semibold">{title}</h3>
            </div>
            <table class="w-full text-left">
                <thead class="bg-gray-100 text-sm uppercase tracking-wider">
                    <tr>
                        <th class="px-4 py-3">Detalle</th>
                        <th class="px-4 py-3">Monto</th>
                        <th class="px-4 py-3 text-right">%</th>
                        <th class="px-4 py-3">Visual</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
        return table_html
    
    
    def generate_html_report(self, stats, monthly_total, fecha):
        """Generar reporte HTML"""
        fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
        now = datetime.now().strftime('%d/%m/%Y a las %H:%M')
        year = datetime.now().year

        # Datos para gráficos
        pago_data = [{"name": k, "value": v} for k, v in stats['por_pago'].items()]
        contado_data = [{"name": k, "value": v} for k, v in stats['por_contado'].items()]
        lista_data = [{"name": k, "value": v} for k, v in stats.get('por_lista', {}).items()]
        reparto_data = [{"name": k, "value": v} for k, v in stats['por_reparto'].items()]
        
        # Generar tablas dinámicas
        tabla_pago = self.generate_tailwind_table("Condición de Pago", stats['por_pago'], stats['total_dia'])
        tabla_contado = self.generate_tailwind_table("Tipo de Pago", stats['por_contado'], stats['total_dia'])

        # Generar el HTML final
        html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Dashboard de Ventas - {fecha_formateada}</title>

        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>    

        <!-- Chart.js -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>    
    </head>
    <body class="bg-gray-100 text-gray-800 font-sans">

        <div class="container mx-auto px-4 py-6">

            <!-- Header -->
            <header class="text-center mb-8 bg-gradient-to-r from-blue-500 to-purple-600 text-white p-6 rounded-xl shadow-lg">
                <h1 class="text-3xl md:text-4xl font-bold">📊 Dashboard de Ventas</h1>
                <p class="opacity-90 mt-2">Reporte del día {fecha_formateada}</p>
            </header>

            <!-- Stats Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">💰 Ventas del Día</h3>
                    <div class="text-2xl font-bold text-green-500">{self.format_currency(stats['total_dia'])}</div>
                </div>
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">📈 Acumulado del Mes</h3>
                    <div class="text-2xl font-bold text-blue-500">{self.format_currency(monthly_total)}</div>
                </div>
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">🧾 Comprobantes del día</h3>
                    <div class="text-2xl font-bold text-indigo-500">{stats['facturas_count']}</div>
                </div>
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">📊 Promedio por Factura</h3>
                    <div class="text-2xl font-bold text-yellow-500">{self.format_currency(stats['promedio_factura'])}</div>
                </div>
            </div>

            <!-- Charts -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">💳 Ventas por Condición de Pago</h3>
                    <canvas id="pagoChart" class="w-full h-72"></canvas>
                </div>
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">💵 Contado vs Cuenta Corriente</h3>
                    <canvas id="contadoChart" class="w-full h-72"></canvas>
                </div>
            </div>

            <!-- Single Chart Row -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">💼 Venta por Lista</h3>
                    <canvas id="listaChart" class="w-full h-72"></canvas>
                </div>
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">💼 Venta por Tipo</h3>
                    <canvas id="repartoChart" class="w-full h-72"></canvas>
                </div>                
            </div>

            <!-- Tabla de Condición de Pago -->
            {tabla_pago}

            <!-- Tabla de Tipo de Pago -->
            {tabla_contado}

            <!-- Footer -->
            <footer class="text-center text-sm text-gray-500 mt-8">
                <p>📅 Reporte generado automáticamente el {now}</p>
                <p>Sistema de Gestión de Ventas &copy; {year}</p>
            </footer>

        </div>

        <!-- Scripts -->
        <script>
            // Datos desde backend
            const pagoData = {json.dumps(pago_data)};
            const contadoData = {json.dumps(contado_data)};
            const listaData = {json.dumps(lista_data)};
            const repartoData = {json.dumps(reparto_data)};

            // Gráfico: Condición de Pago (Doughnut)
            new Chart(document.getElementById('pagoChart'), {{
                type: 'doughnut',
                data: {{
                    labels: pagoData.map(item => item.name),
                    datasets: [{{
                        data: pagoData.map(item => item.value),
                        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            }});

            // Gráfico: Contado vs CC (Barra)
            new Chart(document.getElementById('contadoChart'), {{
                type: 'bar',
                data: {{
                    labels: contadoData.map(item => item.name),
                    datasets: [{{
                        label: 'Monto',
                        data: contadoData.map(item => item.value),
                        backgroundColor: ['#28a745', '#17a2b8']
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: value => '$' + value.toLocaleString()
                            }}
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: context => '$' + context.raw.toLocaleString()
                            }}
                        }}
                    }}
                }}
            }});

            // Gráfico: Venta por Lista (Barra)
            new Chart(document.getElementById('listaChart'), {{
                type: 'bar',
                data: {{
                    labels: listaData.map(item => item.name),
                    datasets: [{{
                        label: 'Venta',
                        data: listaData.map(item => item.value),
                        backgroundColor: ['#28a745', '#17a2b8']
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: value => '$' + value.toLocaleString()
                            }}
                        }}
                    }}
                }}
            }});
            
            // Gráfico: Venta por Reparto (Barra)
            new Chart(document.getElementById('repartoChart'), {{
                type: 'bar',
                data: {{
                    labels: repartoData.map(item => item.name),
                    datasets: [{{
                        label: 'Tipo',
                        data: repartoData.map(item => item.value),
                        backgroundColor: ['#28a745', '#17a2b8']
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: value => '$' + value.toLocaleString()
                            }}
                        }}
                    }}
                }}
            }});
            
        </script>
    </body>
    </html>
        """
        return html
    
    def send_email(self, html_content, fecha):
        """Enviar email con mensaje personalizado y adjuntar el archivo HTML"""
        try:
            # Crear mensaje multipart (para incluir texto/html y archivos)
            msg = MIMEMultipart()
            msg['Subject'] = f'Dashboard de Ventas - {datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")}'
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = ', '.join(self.smtp_config['to_emails'])

            # Mensaje personalizado en el cuerpo del email
            cuerpo_mensaje = f"""
            <html>
                <body>
                    <p>Hola!</p>
                    <p>Adjunto encontrarás el informe de ventas correspondiente al día <strong>{datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")}</strong>.</p>
                    <p>Este archivo contiene gráficos interactivos generados con Chart.js. Para verlos correctamente, por favor ábrelo desde tu computadora con cualquier navegador (Google Chrome, Firefox, etc.).</p>
                    <p>¡Saludos cordiales!</p>
                    <p><em>Sistema Automático de Reportes</em></p>
                </body>
            </html>
            """
            msg.attach(MIMEText(cuerpo_mensaje, 'html', 'utf-8'))

            # Guardar temporalmente el archivo HTML
            filename = f"dashboard_ventas_{fecha.replace('-', '_')}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Adjuntar el archivo HTML
            with open(filename, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={filename}",
            )
            msg.attach(part)

            # Conectar al servidor SMTP y enviar
            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            # server.starttls()
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            server.sendmail(self.smtp_config['from_email'], self.smtp_config['to_emails'], msg.as_string())
            server.quit()

            print(f"✅ Email enviado exitosamente a: {', '.join(self.smtp_config['to_emails'])}")
            logging.info(f"Email enviado exitosamente a: {', '.join(self.smtp_config['to_emails'])}")
            # os.remove(filename)  # Eliminar archivo temporal
            return True
        except Exception as e:
            logging.error(f"Error enviando email: {str(e)}")
            print(f"❌ Error enviando email: {str(e)}")
            return False
        
    def generate_and_send_report(self, fecha=None):
        """Función principal para generar y enviar el reporte"""
        if not fecha:
            fecha = self.fecha_consulta
        
        print(f"🔄 Generando reporte para el {fecha}...")
        logging.info(f"Generando reporte para el {fecha}...")
        
        # Obtener datos
        sales_data = self.get_sales_data(fecha)
        monthly_total = self.get_monthly_data(fecha)
        
        if not sales_data:
            print("⚠️  No se encontraron datos de ventas para la fecha especificada")
            return False
        
        # Procesar estadísticas
        stats = self.process_data(sales_data)
        
        print(f"📊 Datos procesados:")
        print(f"   - Total del día: {self.format_currency(stats['total_dia'])}")
        print(f"   - Facturas: {stats['facturas_count']}")
        print(f"   - Promedio por factura: {self.format_currency(stats['promedio_factura'])}")
        logging.info(f"Datos procesados para el {fecha}: Total del día: {stats['total_dia']}, Facturas: {stats['facturas_count']}, Promedio por factura: {stats['promedio_factura']}")
        
        # Generar HTML
        html_content = self.generate_html_report(stats, monthly_total, fecha)
        
        # Guardar archivo local (opcional)
        filename = f"dashboard_ventas_{fecha.replace('-', '_')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"💾 Reporte guardado como: {filename}")
        logging.info(f"Reporte guardado como: {filename}")
        
        # Enviar por email
        if self.smtp_config['from_email'] and self.smtp_config['to_emails'][0]:
            success = self.send_email(html_content, fecha)
            return success
        else:
            print("⚠️  Configuración de email incompleta. Reporte guardado localmente.")
            logging.warning("Configuración de email incompleta. Reporte guardado localmente.")
            return True

def main():
    """Función principal"""
    print("🚀 Iniciando generación de Dashboard de Ventas...")
    
    # Crear instancia del dashboard
    dashboard = SalesDashboard()
    dashboard.fecha_consulta = datetime.now().strftime('%Y-%m-%d')  # Fecha actual
    # dashboard.fecha_consulta = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')  # Fecha de ayer
    
    # Generar y enviar reporte
    success = dashboard.generate_and_send_report()
    
    if success:
        print("✅ Proceso completado exitosamente!")
    else:
        print("❌ Error en el proceso")

if __name__ == "__main__":
    main()