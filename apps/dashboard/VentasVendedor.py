import sys
import os

from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# Dependencias modelos/libs residen en el dashboard web
sys.path.append('/var/www/html/dashboard')

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import json
from modelos.Stock import Stock
from modelos.Comisiones import Comision
from modelos.Remitos import Remito
from modelos.DetalleRemitos import Detaremi
from modelos.Vendedores import Vendedor, VentasVendedor
from datetime import date, timedelta

# Cargar variables de entorno
load_dotenv()

def carga_datos_remitos(controlador):
    VentasVendedor.delete().where(
        VentasVendedor.fecha.between(
            lo=controlador.desde,
            hi=controlador.hasta
        )
    ).execute()
    remitos = Remito.select(Remito, Vendedor).where(
        Remito.tipo.in_(['X', 'T', 'C']),
        Remito.facturado == 'S',
        Remito.fecha.between(
            lo=controlador.desde,
            hi=controlador.hasta
        ),
        Remito.obs != 'MERCADERIA DESCONTADA DE PENDIENTE DE ENTREGA',
    ).join(Vendedor, on=(Remito.vendedor == Vendedor.vendedor))
    
    for rem in remitos:
        if rem.tipo == 'X' and rem.reparte == 'O':
            continue
        
        detalle = Detaremi.select().where(Detaremi.idremito == rem.idremito)
        for det in detalle:
            print(f'Procesando remito {rem.tipo} {rem.numero} del cliente {rem.cliente} {rem.nombre}')
            pagoant = "SI" if det.pagoant else "NO"
            stock = Stock.get(Stock.clave == det.articulo)
            comision = Comision.ObtieneComisionVendedor(stock.incre1 if rem.lista == '1' else stock.incre4, rem.lista)
            if comision:
                comision_vendedor = comision.comvendedor
                detalle_comision = comision.detalle if comision.detalle else f'Comision {comision_vendedor}%'
            else:
                comision_vendedor = 0
                detalle_comision = ''
            item = [
                f'{rem.vendedor.vendedor}-{rem.vendedor.nom_ven}', rem.fecha, f'{rem.tipo} {rem.numero}',
                f'{rem.cliente}-{rem.nombre}', rem.lista, det.cantidad * det.unitario, comision_vendedor, f'{rem.tipocomp} {rem.clase} {rem.factura}',
                pagoant, f'{rem.fecha.year}-{str(rem.fecha.month).zfill(2)}', rem.tipo, detalle_comision,
                stock.clave, stock.detalle, det.cantidad
            ]

            VentasVendedor.create(
                vendedor=rem.vendedor.vendedor,
                nombre_vendedor=rem.vendedor.nom_ven,
                fecha=rem.fecha,
                comprobante=f'{rem.tipo} {rem.numero}',
                cliente=f'{rem.cliente}-{rem.nombre}',
                lista=rem.lista,
                neto=det.cantidad * det.unitario,
                comision=comision_vendedor,
                comp_relacionado=f'{rem.tipocomp} {rem.clase} {rem.factura}',
                pago_anticipado=det.pagoant,
                periodo=f'{rem.fecha.year}-{str(rem.fecha.month).zfill(2)}',
                tipo_comp=rem.tipo,
                clave=stock.clave,
                articulo=stock.detalle,
                cantidad=det.cantidad
            )

def generar_json_ventas(rango_fecha_inicio, rango_fecha_fin, nombre_archivo='ventas.json'):
    # fecha_inicio = datetime.strptime(rango_fecha_inicio, '%Y-%m-%d').date()
    # fecha_fin = datetime.strptime(rango_fecha_fin, '%Y-%m-%d').date()
    fecha_inicio = rango_fecha_inicio
    fecha_fin = rango_fecha_fin

    query = VentasVendedor.select().where(
        (VentasVendedor.fecha >= fecha_inicio) &
        (VentasVendedor.fecha <= fecha_fin)
    )

    datos_vendedores = {}

    for venta in query:
        vendedor = venta.nombre_vendedor or venta.vendedor
        if vendedor not in datos_vendedores:
            datos_vendedores[vendedor] = {'total_neto': 0, 'total_cantidad': 0}

        datos_vendedores[vendedor]['total_neto'] += venta.neto or 0
        datos_vendedores[vendedor]['total_cantidad'] += venta.cantidad or 0

    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        json.dump(datos_vendedores, f, indent=4, ensure_ascii=False)

    print(f"Archivo '{nombre_archivo}' generado correctamente.")
    return datos_vendedores

def generar_html(datos_vendedores, nombre_html='reporte_ventas.html'):
    datos_json = json.dumps(datos_vendedores, ensure_ascii=False)

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Ventas</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script> 
    <style>
        /* Reset y estilos generales */
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f7f9fc;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        /* Contenedor del gráfico */
        .chart-container {{
            position: relative;
            width: 100%;
            max-width: 100%;
            height: auto;
            min-height: 300px;
            margin: auto;
        }}
        .chart-container canvas {{
            width: 100% !important;
            height: auto !important;
        }}

        /* Tabla responsiva */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
            background-color: white;
            box-shadow: 0 0 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            border: 1px solid #ddd;
            text-align: center;
        }}
        th {{
            background-color: #f2f2f2;
        }}

        /* Responsive en pantallas pequeñas */
        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}
            h1 {{
                font-size: 1.2em;
            }}
            th, td {{
                font-size: 0.9em;
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <h1>Reporte de Ventas por Vendedor</h1>

    <div class="chart-container">
        <canvas id="graficoVentas"></canvas>
    </div>

    <table>
        <thead>
            <tr>
                <th>Vendedor</th>
                <th>Total Neto</th>
                <th>Total Artículos Vendidos</th>
            </tr>
        </thead>
        <tbody id="tablaDatos">
        </tbody>
    </table>

    <script>
        const data = {datos_json};

        const labels = Object.keys(data);
        const netos = labels.map(v => data[v].total_neto);

        // Gráfico de barras
        const ctx = document.getElementById('graficoVentas').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Total Neto Vendido',
                    data: netos,
                    backgroundColor: '#4CAF50'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: value => '$' + value.toLocaleString()
                        }}
                    }},
                    x: {{
                        ticks: {{
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45
                        }}
                    }}
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            label: context => `$${{context.raw.toLocaleString()}}`
                        }}
                    }}
                }}
            }}
        }});

        // Rellenar tabla
        const tbody = document.getElementById('tablaDatos');
        labels.forEach(vendedor => {{
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${{vendedor}}</td>
                <td>$${{data[vendedor].total_neto.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}</td>
                <td>${{data[vendedor].total_cantidad}}</td>
            `;
            tbody.appendChild(tr);
        }});
    </script>
</body>
</html>
"""

    with open(nombre_html, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Página '{nombre_html}' generada correctamente.")
    
def enviar_email(destinatario, archivo_adjunto):
    remitente = os.getenv('SMTP_USER')
    contraseña = os.getenv('SMTP_PASSWORD')

    # Normalizar destinatario a lista de emails (acepta string con comas o lista)
    if isinstance(destinatario, str):
        destinatario = [e.strip() for e in destinatario.split(',') if e.strip()]
    elif not isinstance(destinatario, (list, tuple)):
        destinatario = []
    if not destinatario:
        print('Error al enviar correo: no hay destinatarios configurados')
        return

    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = ', '.join(destinatario)
    mensaje['Subject'] = "Reporte de Ventas por Vendedor"

    cuerpo = "Adjunto encontrarás el reporte de ventas acumuladas."
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    # Adjuntar archivo HTML
    with open(archivo_adjunto, "rb") as adjunto:
        parte = MIMEBase('application', 'octet-stream')
        parte.set_payload(adjunto.read())
        encoders.encode_base64(parte)
        parte.add_header('Content-Disposition',
                         f'attachment; filename="{archivo_adjunto}"')
        mensaje.attach(parte)

    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '465'))
        if smtp_port == 465:
            servidor = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            servidor = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            try:
                servidor.starttls()
            except smtplib.SMTPException:
                pass
        servidor.login(remitente, contraseña)
        texto = mensaje.as_string()
        servidor.sendmail(remitente, destinatario, texto)
        servidor.quit()
        print("Correo enviado exitosamente.")
    except Exception as e:
        print(f"Error al enviar correo: {e}")

        
if __name__ == "__main__":

    class Controlador:
        pass

    today = date.today()
    desde = today.replace(day=1)
    # Para obtener el último día del mes
    if today.month == 12:
        hasta = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        hasta = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    controlador = Controlador()
    controlador.desde = desde
    controlador.hasta = hasta

    carga_datos_remitos(controlador)
    
    # Generar JSON
    datos_vendedores = generar_json_ventas(controlador.desde, controlador.hasta)

    # Generar HTML
    generar_html(datos_vendedores)

    # Enviar por email
    enviar_email(os.getenv('TO_EMAILS_MONTHLY') or os.getenv('TO_EMAILS'), "reporte_ventas.html")

    # enviar_email("destino@example.com", "reporte_ventas.html")