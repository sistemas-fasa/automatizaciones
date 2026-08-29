from datetime import datetime
import json
import os


class ReportGenerator:
    def __init__(self):
        self.static_dir = os.path.join(os.path.dirname(__file__), 'static')
        
    def load_local_js(self, filename):
        """Load JavaScript file content from static directory"""
        try:
            filepath = os.path.join(self.static_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Escape single braces by doubling them for f-string
                # But we need to be careful - the content is already JavaScript
                return content
        except Exception as e:
            print(f"Warning: Could not load {filename}: {e}")
            return f"console.error('Error loading {filename}: {{e}}');"
    
    def format_currency(self, amount):
        try:
            return f"${float(amount):,.2f}"
        except Exception:
            return "$0.00"

    def generate_tailwind_table(self, title, data_dict, total_dia):
        rows = []
        for detalle, monto in data_dict.items():
            if isinstance(monto, dict):
                total_dia_val = monto.get("total_dia", 0)
                total_mes_val = monto.get("total_mes", 0)
            else:
                total_dia_val = monto
                total_mes_val = 0
            porcentaje = (total_dia_val / total_dia * 100) if total_dia > 0 else 0
            bar_width = min(100, max(0, porcentaje))
            if bar_width >= 70:
                gradient_class = "from-green-500 to-green-600"
            elif bar_width >= 30:
                gradient_class = "from-yellow-400 via-yellow-500 to-yellow-600"
            else:
                gradient_class = "from-red-500 to-red-600"
            row = f"""<tr class="border-b border-gray-200 hover:bg-gray-50 group"><td class="px-4 py-3">{detalle}</td><td class="px-4 py-3 font-medium">{self.format_currency(total_dia_val)}</td><td class="px-4 py-3 text-right">{porcentaje:.1f}%</td><td class="px-4 py-3 font-medium">{self.format_currency(total_mes_val)}</td><td class="px-4 py-3 relative"><div class="relative w-full bg-gray-200 rounded-full h-2 overflow-hidden cursor-help" title="{porcentaje:.1f}%"><div class="absolute inset-0 rounded-full transition-all duration-700 ease-out bg-gradient-to-r {gradient_class}" style="width: {bar_width:.1f}%"></div><span class="absolute inset-0 flex items-center justify-center text-xs text-white font-bold pointer-events-none">{porcentaje:.1f}%</span></div></td></tr>"""
            rows.append(row)
        html_table = f"""<div class="bg-white rounded-xl shadow-md overflow-hidden mb-8"><div class="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-4"><h3 class="text-lg font-semibold">{title}</h3></div><table class="w-full text-left"><thead class="bg-gray-100 text-sm uppercase tracking-wider"><tr><th>Detalle</th><th>Monto</th><th>%Dia</th><th>Total mes</th><th>Visual</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>"""
        return html_table

    def generate_html_report(self, stats, monthly_total, fecha):
        fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        year = datetime.now().year
        pago_data = [{"name": k, "value": float(v.get("total_dia", 0)) if isinstance(v, dict) else float(v)} for k, v in stats.get("por_pago", {}).items()]
        contado_data = [{"name": k, "value": float(v)} for k, v in stats.get("por_contado", {}).items()]
        lista_data = [{"name": k, "value": float(v)} for k, v in stats.get("por_lista", {}).items()]
        reparto_data = [{"name": k, "value": float(v.get("total_dia", 0)) if isinstance(v, dict) else float(v)} for k, v in stats.get("por_reparto", {}).items()]
        aging_data = stats.get("aging", []) or []
        tabla_pago = self.generate_tailwind_table("Condición de Pago", stats.get("por_pago", {}), stats.get("total_dia", 0))
        tabla_contado = self.generate_tailwind_table("Tipo de Pago", stats.get("por_contado", {}), stats.get("total_dia", 0))
        tabla_reparto = self.generate_tailwind_table("Tipo de Venta", stats.get("por_reparto", {}), stats.get("total_dia", 0))
        pago_json = json.dumps(pago_data)
        contado_json = json.dumps(contado_data)
        lista_json = json.dumps(lista_data)
        reparto_json = json.dumps(reparto_data)
        aging_json = json.dumps(aging_data)
        
        # Load JavaScript libraries
        chartjs_code = self.load_local_js('chart.min.js')
        datalabels_code = self.load_local_js('chartjs-plugin-datalabels.min.js')
        
        html_parts = []
        html_parts.append(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Dashboard de Ventas - {fecha_formateada}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: #f3f4f6;
            color: #1f2937;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            padding: 1.5rem 1rem;
        }}
        .container {{
            max-width: 1280px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            background: linear-gradient(to right, #3b82f6, #9333ea);
            color: white;
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }}
        .header h1 {{ font-size: 2rem; font-weight: bold; margin-bottom: 0.5rem; }}
        .header p {{ opacity: 0.9; margin-top: 0.5rem; font-size: 0.95rem; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: white;
            padding: 1.25rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-card h3 {{
            font-size: 0.875rem;
            text-transform: uppercase;
            color: #6b7280;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .stat-value {{
            font-size: 1.5rem;
            font-weight: bold;
        }}
        .stat-value.green {{ color: #10b981; }}
        .stat-value.blue {{ color: #3b82f6; }}
        .stat-value.indigo {{ color: #6366f1; }}
        .stat-value.yellow {{ color: #eab308; }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .chart-card {{
            background: white;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .chart-card h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 1rem;
        }}
        .chart-container {{
            position: relative;
            height: 300px;
            width: 100%;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}
        .table-header {{
            background: linear-gradient(to right, #3b82f6, #9333ea);
            color: white;
            padding: 1rem 1.5rem;
        }}
        .table-header h3 {{
            font-size: 1.125rem;
            font-weight: 600;
        }}
        thead {{
            background-color: #f3f4f6;
        }}
        th {{
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }}
        td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        tbody tr:hover {{
            background-color: #f9fafb;
        }}
        .progress-bar {{
            position: relative;
            width: 100%;
            background-color: #e5e7eb;
            border-radius: 9999px;
            height: 0.5rem;
            overflow: hidden;
        }}
        .progress-fill {{
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            transition: width 0.7s ease-out;
            border-radius: 9999px;
        }}
        .progress-fill.green {{ background: linear-gradient(to right, #10b981, #059669); }}
        .progress-fill.yellow {{ background: linear-gradient(to right, #fbbf24, #d97706); }}
        .progress-fill.red {{ background: linear-gradient(to right, #ef4444, #dc2626); }}
        .progress-text {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75rem;
            font-weight: bold;
            pointer-events: none;
        }}
        .footer {{
            text-align: center;
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 2rem;
        }}
        .footer p {{ margin-top: 0.25rem; }}
        @media (min-width: 768px) {{
            .header h1 {{ font-size: 2.5rem; }}
        }}
    </style>
</head>
<body>
    <script>
        // Chart.js library embedded
        """ + self.load_local_js('chart.min.js') + """
    </script>
    <script>
        // DataLabels plugin embedded  
        """ + self.load_local_js('chartjs-plugin-datalabels.min.js') + """
    </script>
    <div class="container">
        <div class="header">
            <h1>Dashboard de Ventas</h1>
            <p>Reporte del día {fecha_formateada}</p>
            <p>Todos los importes son con IVA incluido</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Ventas del Día</h3>
                <div class="stat-value green">{self.format_currency(stats.get("total_dia", 0))}</div>
            </div>
            <div class="stat-card">
                <h3>Acumulado del Mes</h3>
                <div class="stat-value blue">{self.format_currency(monthly_total)}</div>
            </div>
            <div class="stat-card">
                <h3>Comprobantes del día</h3>
                <div class="stat-value indigo">{stats.get("facturas_count", 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Promedio por Factura</h3>
                <div class="stat-value yellow">{self.format_currency(stats.get("promedio_factura", 0))}</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <h3>Ventas por Condición de Pago</h3>
                <div class="chart-container">
                    <canvas id="pagoChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>Contado vs Cuenta Corriente</h3>
                <div class="chart-container">
                    <canvas id="contadoChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <h3>Venta por Lista</h3>
                <div class="chart-container">
                    <canvas id="listaChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>Venta por Tipo</h3>
                <div class="chart-container">
                    <canvas id="repartoChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <h3>Vencimientos de Factura</h3>
                <div class="chart-container">
                    <canvas id="agingChart"></canvas>
                </div>
            </div>
        </div>
        
        {tabla_pago}
        {tabla_contado}
        {tabla_reparto}
        
        <footer class="text-center text-sm text-gray-500 mt-8">
            <p>Reporte generado automáticamente el {now}</p>
            <p>Sistema de Gestión de Ventas &copy; {year}</p>
        </footer>
    </div>
    <script>
const pagoData = {pago_json};
const contadoData = {contado_json};
const listaData = {lista_json};
const repartoData = {reparto_json};
const agingData = {aging_json};
const letters = '0123456789ABCDEF';

function getRandomColor() {{
    let color = '#';
    for (let i = 0; i < 6; i++) {{
        color += letters[Math.floor(Math.random() * 16)];
    }}
    return color;
}}

Chart.register(ChartDataLabels);

new Chart(document.getElementById('pagoChart'), {{
    type: 'doughnut',
    data: {{
        labels: pagoData.map(item => item.name),
        datasets: [{{
            data: pagoData.map(item => item.value),
            backgroundColor: pagoData.map(() => getRandomColor()),
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

new Chart(document.getElementById('contadoChart'), {{
    type: 'doughnut',
    data: {{
        labels: contadoData.map(item => item.name),
        datasets: [{{
            label: 'Monto',
            data: contadoData.map(item => item.value),
            backgroundColor: contadoData.map(() => getRandomColor())
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: context => '$' + context.raw.toLocaleString()
                }}
            }}
        }}
    }}
}});

new Chart(document.getElementById('listaChart'), {{
    type: 'doughnut',
    data: {{
        labels: listaData.map(item => item.name),
        datasets: [{{
            label: 'Venta',
            data: listaData.map(item => item.value),
            backgroundColor: listaData.map(() => getRandomColor())
        }}]
    }},
    options: {{
        responsive: true
    }}
}});

new Chart(document.getElementById('repartoChart'), {{
    type: 'doughnut',
    data: {{
        labels: repartoData.map(item => item.name),
        datasets: [{{
            label: 'Tipo',
            data: repartoData.map(item => item.value),
            backgroundColor: repartoData.map(() => getRandomColor())
        }}]
    }},
    options: {{
        responsive: true
    }}
}});

new Chart(document.getElementById('agingChart'), {{
    type: 'doughnut',
    data: {{
        labels: agingData.map(item => item.name),
        datasets: [{{
            data: agingData.map(item => item.value),
            backgroundColor: agingData.map(() => getRandomColor()),
            borderWidth: 2,
            borderColor: '#fff'
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{
                position: 'bottom'
            }},
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        let label = context.label || '';
                        let value = context.raw;
                        let total = context.dataset.data.reduce((a, b) => a + b, 0);
                        let percentage = ((value / total) * 100).toFixed(1);
                        return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                    }}
                }}
            }},
            datalabels: {{
                formatter: (value, ctx) => {{
                    let sum = ctx.dataset.data.reduce((a, b) => a + b, 0);
                    let percentage = (value * 100 / sum).toFixed(1) + "%";
                    return percentage;
                }},
                color: '#fff',
                font: {{
                    weight: 'bold'
                }}
            }}
        }}
    }}
}});
    </script>
</body>
</html>"""
        return html
