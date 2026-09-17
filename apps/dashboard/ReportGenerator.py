from datetime import datetime
import json
from decimal import Decimal


class ReportGenerator:
    def format_currency(self, amount):
        try:
            return f"${amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return f"${amount:.2f}"

    def generate_tailwind_table(self, title, data_dict, total_dia, use_total_mes=False):
        rows = ""
        # Calcular el total correcto según el modo
        if use_total_mes:
            total_reference = sum(monto.get('total_mes', 0) if isinstance(monto, dict) else monto for monto in data_dict.values())
        else:
            total_reference = total_dia
            
        for detalle, monto in data_dict.items():
            if isinstance(monto, (dict,)):
                value_to_display = monto.get('total_mes' if use_total_mes else 'total_dia', 0)
                porcentaje = (value_to_display / total_reference * 100) if total_reference > 0 else 0
            else:
                value_to_display = monto
                porcentaje = (monto / total_reference * 100) if total_reference > 0 else 0
            bar_width = min(100, max(0, porcentaje))
            # use empresa color variable (CSS) for a soft gradient towards white
            gradient_style = "background: linear-gradient(to right, var(--empresa-color), rgba(255,255,255,0.85));"

            rows += f"""
                <tr class="border-b border-gray-200 hover:bg-gray-50 group">
                    <td class="px-4 py-3">{detalle}</td>
                    <td class="px-4 py-3 font-medium">{self.format_currency(value_to_display)}</td>
                    <td class="px-4 py-3 text-right">{porcentaje:.1f}%</td>
                    <td class="px-4 py-3 relative">
                        <div class="relative w-full bg-gray-200 rounded-full h-2 overflow-hidden cursor-help" title="{porcentaje:.1f}%">
                            <div class="absolute inset-0 rounded-full transition-all duration-700 ease-out" style="{gradient_style} width: {bar_width:.1f}%"></div>
                            <span class="absolute inset-0 flex items-center justify-center text-xs text-white font-bold pointer-events-none">{porcentaje:.1f}%</span>
                        </div>
                    </td>
                </tr>
            """

        return f"""
        <div class="bg-white rounded-xl shadow-md overflow-hidden mb-8">
            <div class="text-white px-6 py-4 empresa-bg">
                <h3 class="text-lg font-semibold">{title}</h3>
            </div>
            <table class="w-full text-left">
                <thead class="bg-gray-100 text-sm uppercase tracking-wider">
                    <tr><th>Detalle</th><th>Monto</th><th>%Dia</th><th>Visual</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """

    def generate_html_report(self, stats, monthly_total, fecha, aging_details=None, prev_month_total=None):
        """Generar reporte HTML"""
        fecha_formateada = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
        now = datetime.now().strftime('%d/%m/%Y a las %H:%M')
        year = datetime.now().year

        # Company display settings (injected by SalesDashboard)
        empresa_title = stats.get('empresa_title', '')
        empresa_color = stats.get('empresa_color', '#1F2937')

        # Build a soft palette based on the empresa_color (tints towards white)
        def _hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def _rgb_to_hex(rgb):
            return '#%02x%02x%02x' % (max(0, min(255, int(rgb[0]))), max(0, min(255, int(rgb[1]))), max(0, min(255, int(rgb[2]))))

        def _tint_color(hexcolor, factor):
            # factor 0 -> original, 1 -> white
            r, g, b = _hex_to_rgb(hexcolor)
            nr = round(r + (255 - r) * factor)
            ng = round(g + (255 - g) * factor)
            nb = round(b + (255 - b) * factor)
            return _rgb_to_hex((nr, ng, nb))

        # soft tints: primary, + several tints (lighter)
        try:
            empresa_palette = [empresa_color]
            for f in (0.18, 0.36, 0.54, 0.72):
                empresa_palette.append(_tint_color(empresa_color, f))
        except Exception:
            empresa_palette = [empresa_color]
        empresa_palette_json = json.dumps(empresa_palette)

        # Datos para gráficos - normalizar entradas que pueden ser ints o dicts con 'total_dia'/'total_mes'
        def _normalize_series(mapping, prefer_key='total_dia'):
            out = []
            for k, v in (mapping or {}).items():
                if isinstance(v, dict):
                    val = v.get(prefer_key)
                    if val is None:
                        # fallback to other possible key
                        val = v.get('total_mes') if 'total_mes' in v else v.get('total') if 'total' in v else 0
                else:
                    val = v
                try:
                    out.append({"name": k, "value": float(val or 0)})
                except Exception:
                    out.append({"name": k, "value": 0.0})
            return out

        # Preferir 'total_mes' si estamos en acumulado mensual
        prefer_key = 'total_mes' if stats.get('acumulado_mes') else 'total_dia'
        pago_data = _normalize_series(stats.get('por_pago', {}), prefer_key=prefer_key)
        contado_data = _normalize_series(stats.get('por_contado', {}), prefer_key=prefer_key)
        lista_data = _normalize_series(stats.get('por_lista', {}), prefer_key=prefer_key)
        reparto_data = _normalize_series(stats.get('por_reparto', {}), prefer_key=prefer_key)
        aging_data = stats.get('aging', []) or []
        # Datos para cajas (espera mapping nombre -> {total_dia, total_mes})
        caja_source = stats.get('por_caja', {}) or {}
        caja_dia_data = []
        caja_mes_data = []
        try:
            for k, v in caja_source.items():
                if isinstance(v, dict):
                    dia_val = v.get('total_dia', 0) or 0
                    mes_val = v.get('total_mes', 0) or 0
                else:
                    dia_val = v or 0
                    mes_val = v or 0
                caja_dia_data.append({'name': k, 'value': float(dia_val)})
                caja_mes_data.append({'name': k, 'value': float(mes_val)})
        except Exception:
            caja_dia_data = []
            caja_mes_data = []
        
        # Procesar detalles de aging si están disponibles
        # Convertir Decimal a float para serialización JSON
        if aging_details:
            aging_details_clean = []
            for row in aging_details:
                clean_row = {}
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        clean_row[key] = float(value)
                    else:
                        clean_row[key] = value
                aging_details_clean.append(clean_row)
            aging_details_json = json.dumps(aging_details_clean)
        else:
            aging_details_json = "[]"
        
        # Generar tablas dinámicas
        # Calcular total pendiente para la categoría Pago_52 usando stats['aging'] (proviene de get_aging_summary)
        pago_52_total = 0.0
        try:
            aging_list = stats.get('aging', []) or []
            for item in aging_list:
                # item puede ser {'name': ..., 'value': ...}
                name = item.get('name') if isinstance(item, dict) else None
                if name == 'Pago_52' or name == 'Pago 52':
                    pago_52_total = float(item.get('value', 0) or 0)
                    break
        except Exception:
            pago_52_total = 0.0

        # En modo acumulado del mes no imprimimos las tablas diarias
        if stats.get('acumulado_mes'):
            tabla_pago = ''
            tabla_contado = ''
            tabla_reparto = ''
        else:
            tabla_pago = self.generate_tailwind_table("Condición de Pago", stats['por_pago'], stats['total_dia'])
            tabla_contado = self.generate_tailwind_table("Tipo de Pago", stats['por_contado'], stats['total_dia'])
            tabla_reparto = self.generate_tailwind_table("Tipo de Venta", stats['por_reparto'], stats['total_dia'])

            

        # Preparar sección de detalle de aging: no mostrar en acumulado mensual
        if stats.get('acumulado_mes'):
            tabla_aging_section = ''
        else:
            tabla_aging_section = '''
            <!-- Tabla de Detalle de Vencimientos -->
            <div class="bg-white rounded-xl shadow-md overflow-hidden mb-8" id="agingSection">
                <div class="bg-gradient-to-r from-orange-500 to-red-600 text-white px-6 py-4 flex justify-between items-center">
                    <h3 class="text-lg font-semibold">📋 Detalle de Facturas por Vencimiento</h3>
                    <button onclick="imprimirTablaAging()" class="bg-white text-orange-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-100 transition-colors flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                        </svg>
                        Imprimir
                    </button>
                </div>
                <div class="p-4">
                    <div class="mb-4 flex justify-between items-center">
                        <div class="flex-1">
                            <label for="categoriaFilter" class="block text-sm font-medium text-gray-700 mb-2">
                                Filtrar por categoría:
                            </label>
                            <select id="categoriaFilter" class="block w-full md:w-1/3 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                <option value="all">Todas las categorías</option>
                                <option value="A_Vencer">A Vencer</option>
                                <option value="Vencida_0_30d">Vencidas 0-30 días</option>
                                <option value="Vencida_mas_30d">Vencidas más de 30 días</option>
                                <option value="Sin_fecha">Sin fecha</option>
                                <option value="Pago_52">Pago 52</option>
                            </select>
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-sm">
                            <thead class="bg-gray-100 text-xs uppercase tracking-wider">
                                <tr>
                                    <th class="px-4 py-3">Categoría</th>
                                    <th class="px-4 py-3">Cliente</th>
                                    <th class="px-4 py-3">Nombre</th>
                                    <th class="px-4 py-3">Comprobante</th>
                                    <th class="px-4 py-3">Emision</th>
                                    <th class="px-4 py-3">Vencimiento</th>
                                    <th class="px-4 py-3">Cond Pago</th>
                                    <th class="px-4 py-3 text-right">Saldo</th>
                                </tr>
                            </thead>
                            <tbody id="agingTableBody">
                                <!-- Se llenará dinámicamente con JavaScript -->
                            </tbody>
                        </table>
                    </div>
                    <div id="agingTableSummary" class="mt-4 p-4 bg-blue-50 rounded-lg">
                        <div class="flex justify-between items-center">
                            <span class="font-semibold">Total filtrado:</span>
                            <span id="totalFiltered" class="text-xl font-bold empresa-accent">$0.00</span>
                        </div>
                        <div class="flex justify-between items-center mt-2">
                            <span class="font-semibold">Cantidad de facturas:</span>
                            <span id="countFiltered" class="text-lg font-bold text-gray-700">0</span>
                        </div>
                    </div>
                </div>
            </div>
            '''

        # Bloque de gráficos por proveedor (solo en acumulado mensual)
        proveedor_block = ''
        if stats.get('acumulado_mes'):
            proveedor_block = '''
            <!-- Gráficos por Proveedor (solo acumulado mensual) -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">💸 Pagos a Proveedores</h3>
                    <canvas id="pagosProveedorChart" class="w-full h-72"></canvas>
                </div>
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">📑 Comprobantes por Proveedor (Deudas)</h3>
                    <canvas id="comprobantesProveedorChart" class="w-full h-72"></canvas>
                </div>
            </div>
            '''

        # Bloque de gráfico de presupuestos por rango (solo en acumulado mensual)
        presupuestos_rango_block = ''
        presupuestos_rango_data_const = ''
        presupuestos_rango_chart_script = ''
        if stats.get('acumulado_mes') and stats.get('presupuestos_rango'):
            # Construir el bloque HTML con el canvas
            presupuestos_rango_block = '''
            <!-- Gráfico de Rango de Presupuestos -->
            <div class="bg-white p-4 rounded-xl shadow-md mb-8">
                <h3 class="text-lg font-semibold text-center mb-4">📊 Rango de Presupuestos (Tipo Z)</h3>
                <p id="presupuestosRangoEmpty" class="text-sm text-gray-500 text-center mb-3 hidden">Sin datos de presupuestos para el rango seleccionado.</p>
                <div class="flex-1 min-h-[320px]">
                    <canvas id="presupuestosRangoChart" style="width: 100%; height: 100%;"></canvas>
                </div>
            </div>
            '''

        # Bloque de gráfico por vendedor (ventas + NC, solo acumulado mensual)
        vendedor_nc_card = '''
                <div class="bg-white p-4 rounded-xl shadow-md flex flex-col">
                    <h3 class="text-lg font-semibold text-center mb-2">👨‍💼 Total de Ventas por Vendedor</h3>
                    <p class="text-sm text-gray-500 text-center mb-3">Eje X: vendedores | Eje Y: monto total vendido</p>
                    <p id="ventasNcVendedorEmpty" class="text-sm text-gray-500 text-center mb-3 hidden">Sin datos de ventas por vendedor para el rango seleccionado.</p>
                    <div class="flex-1 min-h-[560px]">
                        <canvas id="ventasNcVendedorChart" style="width: 100%; height: 100%;"></canvas>
                    </div>
                    <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                        <button onclick="abrirHistoricoVendedores()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm">
                            📈 Histórico Vendedores
                            <span class="text-xs opacity-75 font-normal">Comparativa mensual</span>
                        </button>
                        <button onclick="abrirTotalVendedores12Meses()" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm">
                            📊 Total 12 Meses
                            <span class="text-xs opacity-75 font-normal">Ventas por vendedor</span>
                        </button>
                    </div>
                </div>
            '''
        vendedor_nc_block = ''
        vendedor_nc_data_const = ''
        vendedor_history_const = ''
        vendedor_nc_chart_script = ''
        if stats.get('acumulado_mes'):
            vendedor_nc_data_const = f"const ventasNcVendedorData = {json.dumps(stats.get('ventas_nc_vendedor', []))};"

            # Transform vendedor_monthly_history for JS line chart
            _vendedor_history = stats.get('vendedor_monthly_history', [])
            _by_seller = {}
            _all_periodos = set()
            for _row in _vendedor_history:
                _vid = _row['vendedor']
                if _vid not in _by_seller:
                    _by_seller[_vid] = {'nombre': _row['nombre_vendedor'], 'data': {}}
                _by_seller[_vid]['data'][_row['periodo']] = _row['total_neto']
                _all_periodos.add(_row['periodo'])
            _sorted_periodos = sorted(_all_periodos)
            # Only show sellers present in the bar chart
            _vendedor_ids_in_bar = sorted(set(
                str(r.get('vendedor', '')) for r in stats.get('ventas_nc_vendedor', [])
                if str(r.get('vendedor', '')) in _by_seller
            ))
            vendedor_history_const = (
                f"const vendedorHistoryData = {json.dumps(_by_seller)};\n"
                f"const vendedorHistoryPeriodos = {json.dumps(_sorted_periodos)};\n"
                f"const vendedorIdsInBarchart = {json.dumps(_vendedor_ids_in_bar)};"
            )
            vendedor_nc_chart_script = '''
            // Gráfico: Total de ventas por vendedor (barras verticales)
            if (ventasNcVendedorData && ventasNcVendedorData.length) {
                const allVendedorRows = [...ventasNcVendedorData].sort((a, b) => (Number(b.ventas) || 0) - (Number(a.ventas) || 0));
                const maxVendedorBars = 20;
                const sortedRows = allVendedorRows.slice(0, maxVendedorBars);
                const remainingRows = allVendedorRows.slice(maxVendedorBars);
                if (remainingRows.length) {
                    sortedRows.push({
                        vendedor: 'otros',
                        nombre_vendedor: 'Otros vendedores',
                        ventas: remainingRows.reduce((sum, row) => sum + (Number(row.ventas) || 0), 0),
                        nc: remainingRows.reduce((sum, row) => sum + (Number(row.nc) || 0), 0)
                    });
                }
                const fullLabels = sortedRows.map(i => i.nombre_vendedor || i.vendedor || 'Sin vendedor');
                const labels = fullLabels.map(label => {
                    const text = String(label || '');
                    return text.length > 14 ? text.slice(0, 12) + '…' : text;
                });
                const ventas = sortedRows.map(i => Number(i.ventas) || 0);

                new Chart(document.getElementById('ventasNcVendedorChart'), {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Ventas ($)',
                            data: ventas,
                            backgroundColor: getPalette(labels.length),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        resizeDelay: 200,
                        plugins: {
                            legend: { position: 'bottom' },
                            tooltip: {
                                callbacks: {
                                    title: function(context) {
                                        const idx = context[0] ? context[0].dataIndex : 0;
                                        return fullLabels[idx] || '';
                                    },
                                    label: function(context) {
                                        const value = context.raw || 0;
                                        return 'Ventas: $' + Number(value).toLocaleString('es-AR', {minimumFractionDigits: 2});
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                ticks: {
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45
                                },
                                grid: { display: false }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: value => '$' + Number(value).toLocaleString('es-AR')
                                }
                            }
                        }
                    }
                });
            } else {
                const emptyEl = document.getElementById('ventasNcVendedorEmpty');
                const canvasEl = document.getElementById('ventasNcVendedorChart');
                if (emptyEl) emptyEl.classList.remove('hidden');
                if (canvasEl) canvasEl.style.display = 'none';
            }
            '''

        bonificaciones_block = ''

        bonificaciones_chart_script = ''
        if stats.get('acumulado_mes'):
            bonificaciones_chart_script = '''
            // Gráficos: Bonificaciones por lista (donut con porcentajes)
            function renderBonificacionesDonut(lista, canvasId, emptyId) {
                const source = (bonificacionesData || []).filter((row) => String(row.lista || '').trim() === lista);
                const canvasEl = document.getElementById(canvasId);
                const emptyEl = document.getElementById(emptyId);
                if (!canvasEl) return;
                if (!source.length) {
                    if (emptyEl) emptyEl.classList.remove('hidden');
                    canvasEl.style.display = 'none';
                    return;
                }

                const grouped = {};
                source.forEach((row) => {
                    const boniRaw = Number(row.boni) || 0;
                    const label = boniRaw.toFixed(2) + '%';
                    if (!grouped[label]) grouped[label] = 0;
                    grouped[label] += Number(row.facturas_unicas) || 0;
                });

                const labels = Object.keys(grouped);
                const values = labels.map(label => grouped[label]);

                new Chart(canvasEl, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Facturas unicas',
                            data: values,
                            backgroundColor: getPalette(labels.length),
                            borderColor: '#fff',
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { position: 'bottom' },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = Number(context.raw) || 0;
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                        return label + ': ' + value.toLocaleString('es-AR') + ' facturas (' + percentage + '%)';
                                    }
                                }
                            }
                        }
                    }
                });
            }

            renderBonificacionesDonut('1', 'bonificacionesLista1Chart', 'bonificacionesLista1Empty');
            renderBonificacionesDonut('4', 'bonificacionesLista4Chart', 'bonificacionesLista4Empty');
            '''

        # Bloque de gráficos de caja (día y mes según corresponda)
        caja_block = ''
        if stats.get('acumulado_mes'):
            # En acumulado mensual, mostrar cobranzas con vendedor arriba y bonificaciones abajo.
            caja_block = '''
            <!-- Cobranzas, Vendedor y Bonificaciones (solo Mes) -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">🏦 Cobranzas por tipo - Mes</h3>
                    <canvas id="cajaMesChart" class="w-full h-72"></canvas>
                </div>
''' + vendedor_nc_card + '''
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-2">🎯 Bonificaciones Lista 1 - Mes</h3>
                    <p id="bonificacionesLista1Empty" class="text-sm text-gray-500 text-center mb-3 hidden">Sin datos de Lista 1 para el rango seleccionado.</p>
                    <canvas id="bonificacionesLista1Chart" class="w-full h-72"></canvas>
                </div>
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-2">🎯 Bonificaciones Lista 4 - Mes</h3>
                    <p id="bonificacionesLista4Empty" class="text-sm text-gray-500 text-center mb-3 hidden">Sin datos de Lista 4 para el rango seleccionado.</p>
                    <canvas id="bonificacionesLista4Chart" class="w-full h-72"></canvas>
                </div>
            </div>
            '''
            vendedor_nc_block = ''
        else:
            # Mostrar ambos gráficos (día y mes)
            caja_block = '''
            <!-- Cobranzas por tipo (Día y Mes) -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">🏦 Cobranzas por tipo - Día</h3>
                    <canvas id="cajaDiaChart" class="w-full h-72"></canvas>
                </div>
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">🏦 Cobranzas por tipo - Mes</h3>
                    <canvas id="cajaMesChart" class="w-full h-72"></canvas>
                </div>
            </div>
            '''

        # Calcular comparación con mes anterior
        try:
            prev_total = float(prev_month_total or 0)
        except Exception:
            prev_total = 0.0
        try:
            current_total = float(monthly_total or 0)
        except Exception:
            current_total = 0.0
        delta = current_total - prev_total
        if prev_total and prev_total != 0:
            pct_change = (delta / prev_total) * 100
        else:
            pct_change = None

        # Icono según variación
        if pct_change is None:
            change_icon = ''
            change_color = 'text-gray-500'
            pct_display = 'N/A'
        else:
            if pct_change > 0:
                # flecha arriba verde
                change_icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12l5-5 5 5M10 19V6" /></svg>'
                change_color = 'text-green-500'
            elif pct_change < 0:
                # flecha abajo roja
                change_icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 12l-5 5-5-5M14 5v14" /></svg>'
                change_color = 'text-red-500'
            else:
                change_icon = ''
                change_color = 'text-gray-500'
            pct_display = f"{pct_change:+.1f}%"

        # Construir el card de inflación interanual (solo para informes mensuales)
        inflacion_card = ''
        # Card para la TNA (extraída desde BNA) - aparece solo en acumulado mensual si está en stats['tna']
        tna_card = ''
        if stats.get('acumulado_mes') and stats.get('inflacion_interanual'):
            inflacion_data = stats['inflacion_interanual']
            variacion = inflacion_data.get('variacion_porcentual', 0)
            
            # Determinar color e icono según la variación
            if variacion > 0:
                inflacion_icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>'
                inflacion_color = 'text-red-500'
            elif variacion < 0:
                inflacion_icon = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>'
                inflacion_color = 'text-green-500'
            else:
                inflacion_icon = ''
                inflacion_color = 'text-gray-500'
            
            inflacion_display = f"{variacion:+.2f}%"
            periodo_actual = inflacion_data.get('periodo_actual', '')
            periodo_anterior = inflacion_data.get('periodo_anterior', '')
            
            # Formatear periodos para mostrar (YYYYMM -> MM/YYYY)
            try:
                periodo_actual_fmt = f"{periodo_actual[4:6]}/{periodo_actual[0:4]}" if len(periodo_actual) == 6 else periodo_actual
                periodo_anterior_fmt = f"{periodo_anterior[4:6]}/{periodo_anterior[0:4]}" if len(periodo_anterior) == 6 else periodo_anterior
            except:
                periodo_actual_fmt = periodo_actual
                periodo_anterior_fmt = periodo_anterior
            
            inflacion_card_content = f"""
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1 cursor-pointer">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2 flex items-center justify-center gap-1">
                        📈 Inflación Interanual (Stock)
                        <span class="cursor-help relative group">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400 hover:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-80 bg-gray-800 text-white text-xs rounded-lg p-3 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-xl">
                                <div class="font-bold mb-2 text-center">¿Cómo se calcula?</div>
                                <div class="text-left space-y-1">
                                    <div>• <strong>Valor Actual:</strong> Suma de preciopro de productos visibles en tabla stock (inventario actual)</div>
                                    <div>• <strong>Valor Anterior:</strong> Suma de importes del mismo mes del año anterior en tabla valstock</div>
                                    <div>• <strong>Fórmula:</strong> ((Actual - Anterior) / Anterior) × 100</div>
                                </div>
                                <div class="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full w-0 h-0 border-8 border-transparent border-t-gray-800"></div>
                            </div>
                        </span>
                    </h3>
                    <div class="text-3xl font-bold {inflacion_color}">{inflacion_icon}{inflacion_display}</div>
                    <div class="text-xs mt-3 text-gray-600">
                        <div class="mb-1">Valor actual ({periodo_actual_fmt}): <strong>{self.format_currency(inflacion_data.get('importe_actual', 0))}</strong></div>
                        <div>Año anterior ({periodo_anterior_fmt}): <strong>{self.format_currency(inflacion_data.get('importe_anterior', 0))}</strong></div>
                    </div>
                </div>
            """
            
            # Si existe link al detalle, envolver en etiqueta <a>
            if stats.get('inflacion_link'):
                inflacion_card = f'<a href="{stats["inflacion_link"]}" target="_blank" class="block" style="text-decoration: none; color: inherit;">{inflacion_card_content}</a>'
            else:
                inflacion_card = inflacion_card_content

        # Construir card TNA si está disponible en stats (por ejemplo: stats['tna'] = {'tna':88.37, 'date':'01/22/2026'})
        try:
            tna_info = stats.get('tna') if isinstance(stats.get('tna'), dict) else None
            if stats.get('acumulado_mes') and tna_info and tna_info.get('tna'):
                tna_val = tna_info.get('tna')
                tna_date = tna_info.get('date') or ''
                tna_display = f"{tna_val:.2f}%"
                tna_card = f"""
                    <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1 cursor-pointer">
                        <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">TNA (BNA)</h3>
                        <div class="text-3xl font-bold text-black">{tna_display}</div>
                        <div class="text-xs mt-2 text-gray-600">Fecha: {tna_date}</div>
                    </div>
                """
        except Exception:
            tna_card = ''


        # Construir la tarjeta de Acumulado del Mes ahora que tenemos los íconos y el pct_display
        if stats.get('acumulado_mes'):
            acumulado_card = f"""
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">📈 Acumulado del Mes</h3>
                    <div class="text-2xl font-bold empresa-accent">{self.format_currency(monthly_total)}</div>
                    <div class="text-sm mt-2 text-gray-600">
                        <span class="mr-3">Mes anterior: <strong>{self.format_currency(prev_month_total or 0)}</strong></span>
                        <span class="font-semibold {change_color}">{change_icon}{pct_display}</span>
                    </div>
                </div>
            """
        else:
            acumulado_card = ''

        # Ajustar número de columnas para la sección de cards según cards adicionales
        try:
            extra = 0
            if inflacion_card:
                extra += 1
            if tna_card:
                extra += 1
            grid_cols = 2 + extra
            grid_cols_placeholder = f'<div class="mb-6 grid grid-cols-1 md:grid-cols-{grid_cols} gap-4">'
        except Exception:
            grid_cols_placeholder = '<div class="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">'

        # Generar el HTML final
        html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>{('Dashboard Ventas Mensuales') if stats.get('acumulado_mes') else ('Dashboard Ventas Diarias')} - {empresa_title} - {fecha_formateada}</title>

        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>    

        <!-- Chart.js -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
        <!-- Treemap plugin for Chart.js -->
        <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-treemap@1.0.0/dist/chartjs-chart-treemap.min.js"></script>
        <style>
            :root {{ --empresa-color: {empresa_color}; }}
            .empresa-accent {{ color: var(--empresa-color) !important; }}
            .empresa-bg {{ background-color: var(--empresa-color) !important; }}
            .empresa-border {{ border-color: var(--empresa-color) !important; }}
        </style>
    </head>
    <body class="bg-gray-100 text-gray-800 font-sans">

        <div class="container mx-auto px-4 py-6">

            <!-- Header -->
            <header class="text-center mb-8 text-white p-6 rounded-xl shadow-lg" style="background-color: {empresa_color};">
                <h1 class="text-3xl md:text-4xl font-bold">{('📊 Dashboard Ventas Mensuales') if stats.get('acumulado_mes') else ('📊 Dashboard Ventas Diarias')}</h1>
                <p class="opacity-95 mt-2 font-extrabold text-xl md:text-2xl inline-block px-3 py-1 rounded shadow-lg bg-white/20">{empresa_title}</p>
                {('<p class="opacity-90 mt-2 font-semibold">Acumulado del Mes hasta ' + fecha_formateada + '</p>' ) if stats.get('acumulado_mes') else ('<p class="opacity-90 mt-2">Reporte del día ' + fecha_formateada + '</p>')}
                <p class="opacity-90 mt-2">Todos los importes son con IVA incluido - Incluye N</p>
            </header>

            <!-- Stats Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                        <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">{('📈 Acumulado del Mes') if stats.get('acumulado_mes') else ('💰 Ventas del Día')}</h3>
                        <div class="text-2xl font-bold empresa-accent">{self.format_currency(monthly_total if stats.get('acumulado_mes') else stats['total_dia'])}</div>
                        {('<div class="text-sm mt-2 text-gray-600"><span class="mr-3">Mes anterior: <strong>' + self.format_currency(prev_month_total or 0) + '</strong></span><span class="font-semibold ' + change_color + '">' + change_icon + pct_display + '</span></div>') if stats.get('acumulado_mes') else ''}
                </div>
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">{('🧾 Comprobantes del Mes') if stats.get('acumulado_mes') else ('🧾 Comprobantes')}</h3>
                    <div class="text-2xl font-bold empresa-accent">{stats['facturas_count']}</div>
                </div>
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">{('📊 Ticket Promedio del Mes') if stats.get('acumulado_mes') else ('📊 Promedio por Factura')}</h3>
                    <div class="text-2xl font-bold empresa-accent">{self.format_currency(stats['promedio_factura'])}</div>
                </div>
            </div>

            <!-- Remitos sin Facturar, Total Pago 52 e Inflación Interanual -->
            {grid_cols_placeholder}
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">📦 Remitos sin Facturar</h3>
                    <div class="text-2xl font-bold empresa-accent">{self.format_currency(stats.get('remitos_sin_facturar', 0))}</div>
                </div>
                <div class="bg-white p-5 rounded-xl shadow-md text-center hover:shadow-lg transition-transform transform hover:-translate-y-1">
                    <h3 class="text-sm uppercase text-gray-500 font-semibold mb-2">💳 Total Condición Pago 52</h3>
                    <div class="text-2xl font-bold empresa-accent">{self.format_currency(pago_52_total)}</div>
                </div>
                {inflacion_card}
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
            
            <!-- Aging Chart + Special Articles (side by side) -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">📅 Vencimientos de Factura</h3>
                    <canvas id="agingChart" class="w-full h-72"></canvas>
                </div>
                <div class="bg-white p-4 rounded-xl shadow-md">
                    <h3 class="text-lg font-semibold text-center mb-4">📊 Créditos y Débitos Especiales</h3>
                    <canvas id="specialArticlesChart" class="w-full h-72"></canvas>
                </div>
            </div>

            {caja_block}

            {bonificaciones_block}

            {vendedor_nc_block}

            {proveedor_block}
            
            {presupuestos_rango_block}

            <!-- Tabla de Condición de Pago -->
            {tabla_pago}

            <!-- Tabla de Tipo de Pago -->
            {tabla_contado}
            
            <!-- Tabla de Tipo de Venta -->
            {tabla_reparto}

            {tabla_aging_section}

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
            const agingData = {json.dumps(aging_data)};
            const agingDetails = {aging_details_json};
            // Artículos especiales inyectados desde backend
            const specialArticlesRaw = {json.dumps(stats.get('articulos_especiales', {}))};
            // Datos por proveedor (solo en acumulado mensual)
            const pagosProveedor = {json.dumps(stats.get('pagos_proveedor', []))};
            const comprobantesProveedor = {json.dumps(stats.get('comprobantes_proveedor', []))};
            {vendedor_nc_data_const}
            {vendedor_history_const}
const bonificacionesData = {json.dumps(stats.get('bonificaciones', []))};
            const acumuladoMesFlag = {json.dumps(bool(stats.get('acumulado_mes')))};
            const presupuestosRangoData = {json.dumps(stats.get('presupuestos_rango', []))};
                 const cajaDiaData = {json.dumps(caja_dia_data)};
                 const cajaMesData = {json.dumps(caja_mes_data)};
            
            // Colores para gráficos de histórico (definido temprano para disponibilidad)
            const HISTORICO_COLORS = ['#2563EB','#DC2626','#16A34A','#D97706','#7C3AED','#EC4899','#0891B2','#CA8A04','#6B7280','#BE123C'];
            
            const letters = '0123456789ABCDEF';
            // Función para generar un color aleatorio en formato hex
            function getRandomColor() {{
                let color = '#';
                for (let i = 0; i < 6; i++) {{
                    color += letters[Math.floor(Math.random() * 16)];
                }}
                return color;
            }}

            // Empresa palette injected from Python (soft tints)
            const empresaPalette = {empresa_palette_json};
            function getPalette(n) {{
                const p = empresaPalette.slice(0);
                while (p.length < n) p.push(getRandomColor());
                return p.slice(0, n);
            }}
            
            // Gráfico: Condición de Pago (Doughnut)
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
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.label || '';
                                    let value = context.raw || 0;
                                    let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                    return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Gráfico: Contado vs CC (Barra)
            new Chart(document.getElementById('contadoChart'), {{
                type: 'doughnut',
                data: {{
                    labels: contadoData.map(item => item.name),
                    datasets: [{{
                        label: 'Monto',
                        data: contadoData.map(item => item.value),
                        backgroundColor: contadoData.map(() => getRandomColor()),
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
                                label: function(context) {{
                                    let label = context.label || '';
                                    let value = context.raw || 0;
                                    let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                    return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // Gráfico: Venta por Lista (Barra)
            new Chart(document.getElementById('listaChart'), {{
                type: 'doughnut',
                data: {{
                    labels: listaData.map(item => item.name),
                    datasets: [{{
                        label: 'Venta',
                        data: listaData.map(item => item.value),
                        backgroundColor: listaData.map(() => getRandomColor()),
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
                                label: function(context) {{
                                    let label = context.label || '';
                                    let value = context.raw || 0;
                                    let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                    return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }},
                }}
            }});
            
            // Gráfico: Venta por Reparto (Barra)
            new Chart(document.getElementById('repartoChart'), {{
                type: 'doughnut',
                data: {{
                    labels: repartoData.map(item => item.name),
                    datasets: [{{
                        label: 'Tipo',
                        data: repartoData.map(item => item.value),
                        backgroundColor: repartoData.map(() => getRandomColor()),
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
                                label: function(context) {{
                                    let label = context.label || '';
                                    let value = context.raw || 0;
                                    let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                    return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }},
                }}
            }});
            
            // Gráfico: Vencimientos de Factura (Doughnut)
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
                        }}
                    }}
                }}
            }});

            // Gráfico: Créditos/Débitos Especiales (Pie)
            (function(){{
                const items = stats_articulos_especiales();
                const labels = items.map(i => i.label);
                const values = items.map(i => i.value);
                new Chart(document.getElementById('specialArticlesChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            data: values,
                            backgroundColor: labels.map(() => getRandomColor()),
                            borderColor: '#fff',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        let label = context.label || '';
                                        let value = context.raw || 0;
                                        let total = context.dataset.data.reduce((a,b) => a + b, 0);
                                        let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                        return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }})();

            {vendedor_nc_chart_script}

            {bonificaciones_chart_script}

            {presupuestos_rango_chart_script}

            // Gráfico: Ventas por Caja - Día (Pie) - Solo en reporte diario
            if (!acumuladoMesFlag) {{
                (function(){{
                    const labels = cajaDiaData.map(i => i.name || 'Sin Nombre');
                    const values = cajaDiaData.map(i => Number(i.value) || 0);
                    new Chart(document.getElementById('cajaDiaChart'), {{
                        type: 'doughnut',
                        data: {{
                            labels: labels,
                            datasets: [{{
                                data: values,
                                backgroundColor: labels.map(() => getRandomColor()),
                                borderColor: '#fff',
                                borderWidth: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{
                                legend: {{ position: 'bottom' }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            let label = context.label || '';
                                            let value = context.raw || 0;
                                            let total = context.dataset.data.reduce((a,b) => a + b, 0);
                                            let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                            return label + ': $' + Number(value).toLocaleString() + ' (' + percentage + '%)';
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }})();
            }}

            // Gráfico: Ventas por Caja - Mes (Pie)
            (function(){{
                const labels = cajaMesData.map(i => i.name || 'Sin Nombre');
                const values = cajaMesData.map(i => Number(i.value) || 0);
                new Chart(document.getElementById('cajaMesChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            data: values,
                            backgroundColor: labels.map(() => getRandomColor()),
                            borderColor: '#fff',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        let label = context.label || '';
                                        let value = context.raw || 0;
                                        let total = context.dataset.data.reduce((a,b) => a + b, 0);
                                        let percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                                        return label + ': $' + Number(value).toLocaleString() + ' (' + percentage + '%)';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }})();

                // Gráfico: Pagos a Proveedores (Pareto) - solo en acumulado mensual
                if (pagosProveedor && pagosProveedor.length) {{
                    const provLabels = pagosProveedor.map(p => p.name);
                    const provValues = pagosProveedor.map(p => Number(p.value) || 0);
                    // calcular porcentaje acumulado
                    const totalPagos = provValues.reduce((a,b) => a + b, 0);
                    let cumulative = 0;
                    const cumulativePerc = provValues.map(v => {{ cumulative += v; return totalPagos ? +(cumulative / totalPagos * 100).toFixed(2) : 0; }});

                    new Chart(document.getElementById('pagosProveedorChart'), {{
                        type: 'bar',
                        data: {{
                            labels: provLabels,
                            datasets: [
                                {{
                                    type: 'bar',
                                    label: 'Pagos',
                                    data: provValues,
                                    backgroundColor: provLabels.map(() => getRandomColor()),
                                }},
                                {{
                                    type: 'line',
                                    label: 'Acumulado %',
                                    data: cumulativePerc,
                                    yAxisID: 'y2',
                                    borderColor: '#111827',
                                    backgroundColor: '#111827',
                                    fill: false,
                                    tension: 0.2,
                                    pointRadius: 3
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            interaction: {{ mode: 'index', intersect: false }},
                            scales: {{
                                x: {{ stacked: false }},
                                y: {{
                                    beginAtZero: true,
                                    ticks: {{ callback: value => '$' + Number(value).toLocaleString() }}
                                }},
                                y2: {{
                                    type: 'linear',
                                    position: 'right',
                                    beginAtZero: true,
                                    ticks: {{ callback: v => v + '%' }}
                                }}
                            }},
                            plugins: {{ legend: {{ position: 'bottom' }} }}
                        }}
                    }});
                }}

                // Gráfico: Comprobantes por Proveedor (Treemap) - solo en acumulado mensual
                if (comprobantesProveedor && comprobantesProveedor.length) {{
                    const treeData = comprobantesProveedor.filter(p => Number(p.value) > 0).map(p => ({{
                        value: Number(p.value) || 0,
                        label: p.name
                    }}));
                    
                    new Chart(document.getElementById('comprobantesProveedorChart'), {{
                        type: 'treemap',
                        data: {{
                            datasets: [{{
                                tree: treeData,
                                key: 'value',
                                backgroundColor: function(ctx) {{
                                    return getRandomColor();
                                }},
                                borderColor: 'white',
                                borderWidth: 2,
                                spacing: 1,
                                labels: {{
                                    display: true,
                                    align: 'center',
                                    position: 'top',
                                    color: 'white',
                                    font: {{
                                        size: 14,
                                        weight: 'bold'
                                    }},
                                    formatter: function(ctx) {{
                                        if (!ctx.raw || !ctx.raw._data) return '';
                                        const label = ctx.raw._data.label || '';
                                        const val = ctx.raw._data.value || 0;
                                        return label + '\\n$' + Number(val).toLocaleString('es-AR', {{maximumFractionDigits: 0}});
                                    }}
                                }}
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {{
                                legend: {{ display: false }},
                                tooltip: {{
                                    callbacks: {{
                                        title: function(context) {{
                                            if (!context[0].raw || !context[0].raw._data) return '';
                                            return context[0].raw._data.label || '';
                                        }},
                                        label: function(context) {{
                                            if (!context.raw || !context.raw._data) return '';
                                            const val = context.raw._data.value || 0;
                                            return '$' + Number(val).toLocaleString('es-AR', {{minimumFractionDigits: 2}});
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}

            // Preparar datos de artículos especiales desde backend-injected constants
            function stats_articulos_especiales() {{
                const source = specialArticlesRaw || {{}};
                const mapping = {{
                    'C01.001': 'Créditos por Descuento (C01.001)',
                    'D01.001': 'Débitos por Pago Fuera de Término (D01.001)',
                    'D01.002': 'Intereses por Financiación (D01.002)'
                }};
                const items = [];
                ['C01.001','D01.001','D01.002'].forEach(function(k) {{
                    const entry = source[k] || {{'total_dia':0,'total_mes':0}};
                    const value = acumuladoMesFlag ? (entry.total_mes || 0) : (entry.total_dia || 0);
                    items.push({{ label: mapping[k], value: Math.abs(Number(value)) }});
                }});
                return items;
            }}
            
            // Función para formatear moneda
            function formatCurrency(amount) {{
                return '$' + parseFloat(amount).toLocaleString('es-AR', {{
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                }});
            }}
            
            // Función para formatear fecha
            function formatDate(dateStr) {{
                if (!dateStr) return '-';
                const date = new Date(dateStr);
                const day = String(date.getDate()).padStart(2, '0');
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const year = date.getFullYear();
                return `${{day}}/${{month}}/${{year}}`;
            }}
            
            // Función para obtener color de categoría
            function getCategoryColor(categoria) {{
                const colors = {{
                    'A_Vencer': 'bg-green-100 text-green-800',
                    'Vencida_0_30d': 'bg-yellow-100 text-yellow-800',
                    'Vencida_mas_30d': 'bg-red-100 text-red-800',
                    'Sin_fecha': 'bg-gray-100 text-gray-800',
                    'Pago_52': 'bg-blue-100 text-blue-800'
                }};
                return colors[categoria] || 'bg-gray-100 text-gray-800';
            }}
            
            // Función para obtener nombre legible de categoría
            function getCategoryName(categoria) {{
                const names = {{
                    'A_Vencer': 'A Vencer',
                    'Vencida_0_30d': 'Vencida 0-30d',
                    'Vencida_mas_30d': 'Vencida +30d',
                    'Sin_fecha': 'Sin Fecha',
                    'Pago_52': 'Pago 52'
                }};
                return names[categoria] || categoria;
            }}
            
            // Función para renderizar la tabla de aging
            function renderAgingTable(filter = 'all') {{
                const tbody = document.getElementById('agingTableBody');
                const filteredData = filter === 'all' 
                    ? agingDetails 
                    : agingDetails.filter(row => row.CategoriaVencimiento === filter);
                
                // Calcular totales
                const total = filteredData.reduce((sum, row) => sum + parseFloat(row.saldo || 0), 0);
                const count = filteredData.length;
                
                // Actualizar resumen
                document.getElementById('totalFiltered').textContent = formatCurrency(total);
                document.getElementById('countFiltered').textContent = count;
                
                // Generar filas
                tbody.innerHTML = filteredData.map(row => `
                    <tr class="border-b border-gray-200 hover:bg-gray-50">
                        <td class="px-4 py-3">
                            <span class="px-2 py-1 rounded-full text-xs font-semibold ${{getCategoryColor(row.CategoriaVencimiento)}}">
                                ${{getCategoryName(row.CategoriaVencimiento)}}
                            </span>
                        </td>
                        <td class="px-4 py-3 font-mono text-xs">${{row.cliente || '-'}}</td>
                        <td class="px-4 py-3">${{row.nombre || '-'}}</td>
                        <td class="px-4 py-3 font-mono">${{row.comprobante || '-'}}</td>
                        <td class="px-4 py-3">${{formatDate(row.fecha)}}</td>
                        <td class="px-4 py-3">${{formatDate(row.FECHAVEN)}}</td>
                        <td class="px-4 py-3">${{row.condicion_pago || '-'}}</td>
                        <td class="px-4 py-3 text-right font-semibold">${{formatCurrency(row.saldo)}}</td>
                    </tr>
                `).join('');
            }}
            
            // Event listener para el filtro (solo si la sección de aging existe)
            const categoriaFilterEl = document.getElementById('categoriaFilter');
            if (categoriaFilterEl) {{
                categoriaFilterEl.addEventListener('change', function(e) {{
                    renderAgingTable(e.target.value);
                }});
                // Renderizar tabla inicial
                renderAgingTable();
            }}
            
            
            // --- Histórico de Vendedores (Modal + Líneas) ---
            let historicoChartInstance = null;
            let totalVendedores12MesesChartInstance = null;
            var _historicoModalOpenTime = 0;
            var _totalVendedores12MesesModalOpenTime = 0;

            function abrirHistoricoVendedores() {{
                const modal = document.getElementById('historicoVendedoresModal');
                const container = document.getElementById('vendedorCheckboxes');
                const emptyMsg = document.getElementById('historicoVendedoresEmpty');
                const canvas = document.getElementById('historicoVendedoresChart');

                if (!vendedorHistoryPeriodos || !vendedorHistoryPeriodos.length) {{
                    if (emptyMsg) emptyMsg.classList.remove('hidden');
                    if (canvas) canvas.style.display = 'none';
                    modal.style.display = 'flex';
                    return;
                }}

                if (emptyMsg) emptyMsg.classList.add('hidden');
                if (canvas) canvas.style.display = 'block';

                const sellers = Object.keys(vendedorHistoryData).filter(function(vid) {{
                    return vendedorIdsInBarchart && vendedorIdsInBarchart.indexOf(vid) !== -1;
                }});
                if (!container.querySelector('input')) {{
                    sellers.forEach(function(vid, idx) {{
                        const label = document.createElement('label');
                        label.className = 'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-300 cursor-pointer hover:bg-gray-50 transition-colors text-sm';
                        label.innerHTML = '<input type="checkbox" value="' + vid + '" class="vendedor-hist-checkbox rounded border-gray-300 text-blue-600 focus:ring-blue-500" ' + (idx < 3 ? 'checked' : '') + '> ' + (vendedorHistoryData[vid].nombre || vid);
                        container.appendChild(label);
                    }});
                    container.addEventListener('change', renderHistoricoVendedores);
                }} else {{
                    container.querySelectorAll('input').forEach(function(cb, idx) {{
                        cb.checked = idx < 3;
                    }});
                }}

                _historicoModalOpenTime = Date.now();
                modal.style.display = 'flex';
                renderHistoricoVendedores();
            }}

            function cerrarHistoricoVendedores() {{
                document.getElementById('historicoVendedoresModal').style.display = 'none';
            }}

            function getUltimos12PeriodosVendedor() {{
                const periodos = vendedorHistoryPeriodos || [];
                return periodos.slice(Math.max(periodos.length - 12, 0));
            }}

            function getTotalVendedores12MesesRows() {{
                const periodos = getUltimos12PeriodosVendedor();
                if (!periodos.length || !vendedorHistoryData) return [];

                const rows = Object.keys(vendedorHistoryData).map(function(vid) {{
                    const seller = vendedorHistoryData[vid] || {{}};
                    const total = periodos.reduce(function(sum, periodo) {{
                        return sum + Number((seller.data && seller.data[periodo]) || 0);
                    }}, 0);
                    return {{
                        vendedor: vid,
                        nombre: seller.nombre || vid,
                        total: total
                    }};
                }}).filter(function(row) {{
                    return row.total > 0;
                }});

                rows.sort(function(a, b) {{ return b.total - a.total; }});

                const maxRows = 10;
                if (rows.length <= maxRows) return rows;

                const visibleRows = rows.slice(0, maxRows);
                const otrosTotal = rows.slice(maxRows).reduce(function(sum, row) {{
                    return sum + row.total;
                }}, 0);
                if (otrosTotal > 0) {{
                    visibleRows.push({{
                        vendedor: 'otros',
                        nombre: 'Otros',
                        total: otrosTotal
                    }});
                }}
                return visibleRows;
            }}

            function abrirTotalVendedores12Meses() {{
                const modal = document.getElementById('totalVendedores12MesesModal');
                const emptyMsg = document.getElementById('totalVendedores12MesesEmpty');
                const canvas = document.getElementById('totalVendedores12MesesChart');
                const rows = getTotalVendedores12MesesRows();

                if (!rows.length) {{
                    if (emptyMsg) emptyMsg.classList.remove('hidden');
                    if (canvas) canvas.style.display = 'none';
                    _totalVendedores12MesesModalOpenTime = Date.now();
                    modal.style.display = 'flex';
                    return;
                }}

                if (emptyMsg) emptyMsg.classList.add('hidden');
                if (canvas) canvas.style.display = 'block';
                _totalVendedores12MesesModalOpenTime = Date.now();
                modal.style.display = 'flex';
                renderTotalVendedores12Meses(rows);
            }}

            function cerrarTotalVendedores12Meses() {{
                document.getElementById('totalVendedores12MesesModal').style.display = 'none';
            }}

            function renderTotalVendedores12Meses(rows) {{
                const canvas = document.getElementById('totalVendedores12MesesChart');
                if (!canvas) return;

                if (totalVendedores12MesesChartInstance) {{
                    totalVendedores12MesesChartInstance.destroy();
                }}

                const labels = rows.map(function(row) {{
                    return row.nombre || row.vendedor || 'Sin vendedor';
                }});
                const values = rows.map(function(row) {{
                    return Number(row.total) || 0;
                }});
                const periodos = getUltimos12PeriodosVendedor();
                const formatPeriodo = function(p) {{
                    if (!p) return '';
                    const parts = p.split('-');
                    return parts.length === 2 ? parts[1] + '/' + parts[0] : p;
                }};
                const periodoLabel = periodos.length
                    ? formatPeriodo(periodos[0]) + ' a ' + formatPeriodo(periodos[periodos.length - 1])
                    : 'Últimos 12 meses';

                totalVendedores12MesesChartInstance = new Chart(canvas.getContext('2d'), {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Total vendido (' + periodoLabel + ')',
                            data: values,
                            backgroundColor: labels.map(function(_, idx) {{
                                return HISTORICO_COLORS[idx % HISTORICO_COLORS.length];
                            }}),
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return 'Total: $' + Number(context.raw || 0).toLocaleString('es-AR', {{minimumFractionDigits: 2}});
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{
                                beginAtZero: true,
                                ticks: {{
                                    callback: value => '$' + Number(value).toLocaleString('es-AR')
                                }}
                            }},
                            y: {{
                                ticks: {{
                                    autoSkip: false
                                }},
                                grid: {{ display: false }}
                            }}
                        }}
                    }}
                }});
            }}

            function renderHistoricoVendedores() {{
                const periodos = vendedorHistoryPeriodos;
                if (!periodos || !periodos.length) return;

                const checks = document.querySelectorAll('.vendedor-hist-checkbox:checked');
                const sellers = Array.from(checks).map(function(cb) {{ return cb.value; }});

                if (!sellers.length) {{
                    if (historicoChartInstance) {{
                        historicoChartInstance.destroy();
                        historicoChartInstance = null;
                    }}
                    return;
                }}

                const datasets = [];
                sellers.forEach(function(vid, idx) {{
                    const seller = vendedorHistoryData[vid];
                    if (!seller) return;
                    const color = HISTORICO_COLORS[idx % HISTORICO_COLORS.length];
                    const values = periodos.map(function(p) {{
                        return seller.data && seller.data[p] ? seller.data[p] : 0;
                    }});
                    datasets.push({{
                        label: seller.nombre || vid,
                        data: values,
                        borderColor: color,
                        backgroundColor: color + '20',
                        fill: false,
                        tension: 0.2,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        borderWidth: 2
                    }});
                }});

                if (historicoChartInstance) {{
                    historicoChartInstance.destroy();
                }}

                const formatPeriodo = function(p) {{
                    if (!p) return '';
                    const parts = p.split('-');
                    return parts.length === 2 ? parts[1] + '/' + parts[0] : p;
                }};

                const ctx = document.getElementById('historicoVendedoresChart').getContext('2d');
                historicoChartInstance = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: periodos.map(formatPeriodo),
                        datasets: datasets
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {{
                            mode: 'index',
                            intersect: false
                        }},
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{
                                    usePointStyle: true,
                                    padding: 16
                                }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return context.dataset.label + ': $' + Number(context.raw || 0).toLocaleString('es-AR', {{minimumFractionDigits: 2}});
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{
                                grid: {{ display: false }},
                                ticks: {{
                                    maxRotation: 45,
                                    minRotation: 0
                                }}
                            }},
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    callback: function(value) {{
                                        return '$' + Number(value).toLocaleString('es-AR', {{minimumFractionDigits: 0}});
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }}

            // Cerrar modal al hacer click fuera del contenido
            document.addEventListener('click', function(e) {{
                const modal = document.getElementById('historicoVendedoresModal');
                if (modal && modal.style.display === 'flex') {{
                    // Ignore the same click event that opened the modal
                    if (Date.now() - _historicoModalOpenTime < 200) return;
                    const content = modal.querySelector('div.rounded-xl');
                    if (content && !content.contains(e.target)) {{
                        cerrarHistoricoVendedores();
                    }}
                }}

                const totalModal = document.getElementById('totalVendedores12MesesModal');
                if (totalModal && totalModal.style.display === 'flex') {{
                    if (Date.now() - _totalVendedores12MesesModalOpenTime < 200) return;
                    const content = totalModal.querySelector('div.rounded-xl');
                    if (content && !content.contains(e.target)) {{
                        cerrarTotalVendedores12Meses();
                    }}
                }}
            }});

            // Función para imprimir la tabla de aging
            function imprimirTablaAging() {{
                const categoriaFilter = document.getElementById('categoriaFilter');
                if (!categoriaFilter) {{
                    alert('No hay datos de vencimientos disponibles');
                    return;
                }}
                const selectedCategory = categoriaFilter.options[categoriaFilter.selectedIndex].text;
                const totalFilteredEl = document.getElementById('totalFiltered');
                const countFilteredEl = document.getElementById('countFiltered');
                const totalFiltered = totalFilteredEl ? totalFilteredEl.textContent : '';
                const countFiltered = countFilteredEl ? countFilteredEl.textContent : '';
                
                // Obtener los datos filtrados actuales
                const filter = categoriaFilter.value;
                const filteredData = filter === 'all' 
                    ? agingDetails 
                    : agingDetails.filter(row => row.CategoriaVencimiento === filter);
                
                // Crear ventana de impresión
                const printWindow = window.open('', '', 'height=800,width=1000');
                
                // Generar HTML para impresión
                let printHtml = `
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Detalle de Facturas por Vencimiento - ${{selectedCategory}}</title>
                        <style>
                            @media print {{
                                @page {{
                                    size: landscape;
                                    margin: 0.5cm;
                                }}
                            }}
                            body {{
                                font-family: Arial, sans-serif;
                                margin: 10px;
                                font-size: 9px;
                            }}
                            h1 {{
                                color: #ea580c;
                                border-bottom: 2px solid #ea580c;
                                padding-bottom: 5px;
                                font-size: 16px;
                                margin: 5px 0 10px 0;
                            }}
                            .info {{
                                margin: 8px 0;
                                font-size: 9px;
                            }}
                            table {{
                                width: 100%;
                                border-collapse: collapse;
                                margin-top: 10px;
                                font-size: 8px;
                            }}
                            th {{
                                background-color: #f3f4f6;
                                border: 1px solid #d1d5db;
                                padding: 4px 6px;
                                text-align: left;
                                font-weight: bold;
                                font-size: 8px;
                            }}
                            td {{
                                border: 1px solid #e5e7eb;
                                padding: 3px 5px;
                                line-height: 1.2;
                            }}
                            tr:nth-child(even) {{
                                background-color: #f9fafb;
                            }}
                            .text-right {{
                                text-align: right;
                            }}
                            .text-center {{
                                text-align: center;
                            }}
                            .badge {{
                                padding: 2px 6px;
                                border-radius: 8px;
                                font-size: 7px;
                                font-weight: bold;
                                display: inline-block;
                            }}
                            .badge-green {{
                                background-color: #dcfce7;
                                color: #166534;
                            }}
                            .badge-yellow {{
                                background-color: #fef3c7;
                                color: #854d0e;
                            }}
                            .badge-red {{
                                background-color: #fee2e2;
                                color: #991b1b;
                            }}
                            .badge-blue {{
                                background-color: #dbeafe;
                                color: #1e3a8a;
                            }}
                            .badge-gray {{
                                background-color: #f3f4f6;
                                color: #374151;
                            }}
                            .summary {{
                                margin-top: 10px;
                                padding: 8px;
                                background-color: #dbeafe;
                                border-radius: 6px;
                                font-size: 9px;
                            }}
                            .summary-item {{
                                display: flex;
                                justify-content: space-between;
                                margin: 4px 0;
                                font-weight: bold;
                            }}
                            .footer {{
                                margin-top: 15px;
                                text-align: center;
                                font-size: 8px;
                                color: #6b7280;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>📋 Detalle de Facturas por Vencimiento</h1>
                        <div class="info">
                            <strong>Filtro aplicado:</strong> ${{selectedCategory}}<br>
                            <strong>Fecha de impresión:</strong> ${{new Date().toLocaleDateString('es-AR')}} - ${{new Date().toLocaleTimeString('es-AR')}}
                        </div>
                        
                        <table>
                            <thead>
                                <tr>
                                    <th>Categoría</th>
                                    <th>Cliente</th>
                                    <th>Nombre</th>
                                    <th>Comprobante</th>
                                    <th>Emisión</th>
                                    <th>Vencimiento</th>
                                    <th>Cond. Pago</th>
                                    <th class="text-right">Saldo</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                // Agregar filas
                filteredData.forEach(row => {{
                    const categoryClass = {{
                        'A_Vencer': 'badge-green',
                        'Vencida_0_30d': 'badge-yellow',
                        'Vencida_mas_30d': 'badge-red',
                        'Sin_fecha': 'badge-gray',
                        'Pago_52': 'badge-blue'
                    }}[row.CategoriaVencimiento] || 'badge-gray';
                    
                    printHtml += `
                        <tr>
                            <td class="text-center">
                                <span class="badge ${{categoryClass}}">
                                    ${{getCategoryName(row.CategoriaVencimiento)}}
                                </span>
                            </td>
                            <td>${{row.cliente || '-'}}</td>
                            <td>${{row.nombre || '-'}}</td>
                            <td>${{row.comprobante || '-'}}</td>
                            <td>${{formatDate(row.fecha)}}</td>
                            <td>${{formatDate(row.FECHAVEN)}}</td>
                            <td class="text-center">${{row.condicion_pago || '-'}}</td>
                            <td class="text-right">${{formatCurrency(row.saldo)}}</td>
                        </tr>
                    `;
                }});
                
                printHtml += `
                            </tbody>
                        </table>
                        
                        <div class="summary">
                            <div class="summary-item">
                                <span>Total filtrado:</span>
                                <span>${{totalFiltered}}</span>
                            </div>
                            <div class="summary-item">
                                <span>Cantidad de facturas:</span>
                                <span>${{countFiltered}}</span>
                            </div>
                        </div>
                        
                        <div class="footer">
                            <p>Sistema de Gestión de Ventas &copy; {year}</p>
                        </div>
                    </body>
                    </html>
                `;
                
                // Escribir en la ventana e imprimir
                printWindow.document.write(printHtml);
                printWindow.document.close();
                printWindow.focus();
                
                // Esperar a que cargue y luego imprimir
                setTimeout(() => {{
                    printWindow.print();
                }}, 250);
            }}
            
        </script>

        <!-- Modal: Histórico de Ventas por Vendedor -->
        <div id="historicoVendedoresModal" class="fixed inset-0 z-50 hidden bg-black bg-opacity-60 flex items-center justify-center p-4" style="display:none;">
            <div class="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
                <div class="empresa-bg text-white px-6 py-4 flex justify-between items-center flex-shrink-0">
                    <h2 class="text-xl font-bold">📈 Histórico de Ventas por Vendedor</h2>
                    <button onclick="cerrarHistoricoVendedores()" class="text-white hover:text-gray-200 text-3xl leading-none font-bold">&times;</button>
                </div>
                <div class="px-6 py-4 border-b border-gray-200 flex-shrink-0">
                    <p class="text-sm text-gray-600 mb-3">Seleccioná uno o más vendedores para comparar su evolución mensual (últimos 12 meses):</p>
                    <div id="vendedorCheckboxes" class="flex flex-wrap gap-2">
                    </div>
                </div>
                <div class="flex-1 p-6 min-h-[400px] relative">
                    <p id="historicoVendedoresEmpty" class="text-center text-gray-500 mt-20 hidden">No hay datos de ventas por vendedor en los últimos 12 meses.</p>
                    <canvas id="historicoVendedoresChart" style="width:100%;height:100%;"></canvas>
                </div>
                <div class="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500 flex-shrink-0 text-right">
                    <button onclick="cerrarHistoricoVendedores()" class="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg font-medium transition-colors">Cerrar</button>
                </div>
            </div>
        </div>

        <!-- Modal: Total de Ventas por Vendedor en los últimos 12 meses -->
        <div id="totalVendedores12MesesModal" class="fixed inset-0 z-50 hidden bg-black bg-opacity-60 flex items-center justify-center p-4" style="display:none;">
            <div class="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
                <div class="empresa-bg text-white px-6 py-4 flex justify-between items-center flex-shrink-0">
                    <h2 class="text-xl font-bold">📊 Total de Ventas por Vendedor - Últimos 12 Meses</h2>
                    <button onclick="cerrarTotalVendedores12Meses()" class="text-white hover:text-gray-200 text-3xl leading-none font-bold">&times;</button>
                </div>
                <div class="px-6 py-4 border-b border-gray-200 flex-shrink-0">
                    <p class="text-sm text-gray-600">Ranking acumulado por vendedor, calculado con los últimos 12 períodos mensuales disponibles.</p>
                </div>
                <div class="flex-1 p-6 min-h-[520px] relative">
                    <p id="totalVendedores12MesesEmpty" class="text-center text-gray-500 mt-20 hidden">No hay datos de ventas por vendedor en los últimos 12 meses.</p>
                    <canvas id="totalVendedores12MesesChart" style="width:100%;height:100%;"></canvas>
                </div>
                <div class="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500 flex-shrink-0 text-right">
                    <button onclick="cerrarTotalVendedores12Meses()" class="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg font-medium transition-colors">Cerrar</button>
                </div>
            </div>
        </div>

    </body>
    </html>
        """
        return html

    def generate_inflacion_details_html(self, details_data, empresa_info, fecha):
        # Calcular periodos para el título
        try:
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            año_actual = fecha_dt.year
            mes_actual = fecha_dt.month
            año_anterior = año_actual - 1
            # Formato simple 01/2026 vs 01/2025
            titulo_periodo = f"Comparativa: {mes_actual:02d}/{año_actual} vs {mes_actual:02d}/{año_anterior}"
        except:
             titulo_periodo = fecha

        # Ordenar por Clave por defecto
        details_data.sort(key=lambda x: x.get('CLAVE', ''))

        rows = ""
        # Iconos SVG
        icon_up = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>'
        icon_down = '<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" /></svg>'

        for item in details_data:
            clave = item.get('CLAVE', '')
            detalle = item.get('DETALLE', '')
            precio_ant = float(item.get('precio_anterior', 0))
            precio_act = float(item.get('precio_actual', 0))
            variacion = float(item.get('variacion', 0))
            
            if variacion > 0:
                variacion_class = "text-red-600"
                icon = icon_up
            elif variacion < 0:
                variacion_class = "text-green-600"
                icon = icon_down
            else:
                variacion_class = "text-gray-600"
                icon = ""
            
            rows += f"""
            <tr class="hover:bg-gray-50 border-b border-gray-100 search-item group cursor-pointer" onclick="window.open('history_viewer.html?id={clave}', '_blank')" data-search="{clave.lower()} {detalle.lower()}">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 group-hover:text-blue-600 underline decoration-dotted" data-val="{clave}">{clave}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700" data-val="{detalle}">{detalle}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-600" data-val="{precio_ant}">{self.format_currency(precio_ant)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 font-medium" data-val="{precio_act}">{self.format_currency(precio_act)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-right {variacion_class} font-bold" data-val="{variacion}">{icon}{variacion:.2f}%</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Detalle Inflación Interanual - {empresa_info.get('title', 'Empresa')}</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Inter', sans-serif; background-color: #f3f4f6; }}
                .empresa-bg {{ background-color: {empresa_info.get('color', '#1F2937')}; }}
                th.cursor-pointer:hover {{ background-color: #f9fafb; }}
            </style>
        </head>
        <body class="min-h-screen p-6">
            <div class="max-w-7xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
                <div class="px-8 py-6 empresa-bg text-white flex justify-between items-center">
                    <div>
                        <h1 class="text-2xl font-bold">Detalle Inflación Interanual</h1>
                        <p class="opacity-90 mt-1">{empresa_info.get('title', 'Empresa')} - {titulo_periodo}</p>
                    </div>
                </div>
                
                <div class="p-6 border-b border-gray-200 bg-gray-50 flex gap-4 items-center">
                    <div class="relative flex-1 max-w-md">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                            </svg>
                        </div>
                        <input type="text" id="searchInput" 
                            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            placeholder="Buscar por código o nombre...">
                    </div>
                    
                    <div class="flex items-center space-x-2 bg-gray-100 p-1 rounded-lg">
                        <button id="btnPrev" onclick="prevPage()" class="px-3 py-1 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">
                            &#8592;
                        </button>
                        <span id="pageInfo" class="text-sm text-gray-600 font-medium w-24 text-center">Página 1</span>
                        <button id="btnNext" onclick="nextPage()" class="px-3 py-1 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed">
                            &#8594;
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200" id="detailsTable">
                        <thead class="bg-gray-50Select">
                            <tr>
                                <th scope="col" onclick="sortTable(0)" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700">
                                    Código <span id="sort-icon-0" class="ml-1 inline-block">↕</span>
                                </th>
                                <th scope="col" onclick="sortTable(1)" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700">
                                    Artículo <span id="sort-icon-1" class="ml-1 inline-block">↕</span>
                                </th>
                                <th scope="col" onclick="sortTable(2)" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700">
                                    Precio Anterior <span id="sort-icon-2" class="ml-1 inline-block">↕</span>
                                </th>
                                <th scope="col" onclick="sortTable(3)" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700">
                                    Precio Actual <span id="sort-icon-3" class="ml-1 inline-block">↕</span>
                                </th>
                                <th scope="col" onclick="sortTable(4)" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700">
                                    Variación <span id="sort-icon-4" class="ml-1 inline-block">↕</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody id="tableBody" class="bg-white divide-y divide-gray-200">
                            {rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="bg-gray-50 px-6 py-4 border-t border-gray-200 text-sm text-gray-500 flex justify-between">
                     <span id="resumenCount">Cargando...</span>
                </div>
            </div>

            <script>
                // Estado de paginación
                let currentPage = 1;
                const rowsPerPage = 50;
                let currentTotalPages = 1;

                function getRows() {{
                    return Array.from(document.getElementById("tableBody").rows);
                }}

                function updateTable() {{
                    const term = document.getElementById('searchInput').value.toLowerCase();
                    const allRows = getRows();
                    
                    // 1. Identificar filas que coinciden
                    // Usamos una propiedad temporal en el elemento DOM o clases, pero el display:none es mas directo.
                    // Para paginar, necesitamos saber CUALES coinciden primero.
                    
                    const matchedRows = [];
                    allRows.forEach(row => {{
                        const searchData = row.getAttribute('data-search');
                        if (!term || searchData.includes(term)) {{
                            matchedRows.push(row);
                        }} else {{
                            row.style.display = 'none'; // Ocultar las que no coinciden
                        }}
                    }});

                    // 2. Calcular paginación
                    const totalItems = matchedRows.length;
                    currentTotalPages = Math.ceil(totalItems / rowsPerPage) || 1;
                    
                    if (currentPage > currentTotalPages) currentPage = currentTotalPages;
                    if (currentPage < 1) currentPage = 1;

                    // Indices de la pagina actual
                    const start = (currentPage - 1) * rowsPerPage;
                    const end = start + rowsPerPage;
                    
                    // 3. Aplicar visibilidad
                    matchedRows.forEach((row, index) => {{
                        if (index >= start && index < end) {{
                            row.style.display = ''; // Mostrar
                        }} else {{
                            row.style.display = 'none'; // Ocultar por paginación
                        }}
                    }});

                    // 4. Actualizar UI
                    document.getElementById('resumenCount').textContent = `Mostrando ${{Math.min(end, totalItems) - start + (totalItems>0?0:0)}} de ${{totalItems}} registros (Total: ${{allRows.length}})`;
                    document.getElementById('pageInfo').textContent = `Pág ${{currentPage}} / ${{currentTotalPages}}`;
                    
                    document.getElementById('btnPrev').disabled = currentPage === 1;
                    document.getElementById('btnNext').disabled = currentPage === currentTotalPages;
                }}

                function prevPage() {{
                    if (currentPage > 1) {{
                        currentPage--;
                        updateTable();
                    }}
                }}

                function nextPage() {{
                    if (currentPage < currentTotalPages) {{
                        currentPage++;
                        updateTable();
                    }}
                }}

                document.getElementById('searchInput').addEventListener('keyup', function(e) {{
                    currentPage = 1;
                    updateTable();
                }});

                function sortTable(n) {{
                    var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                    table = document.getElementById("detailsTable");
                    switching = true;
                    // Set the sorting direction to ascending:
                    dir = "asc";
                    
                    // Reset icons
                    for(let k=0; k<5; k++) {{
                         const icon = document.getElementById('sort-icon-'+k);
                         if(icon) icon.innerHTML = '↕';
                    }}

                    while (switching) {{
                        switching = false;
                        rows = table.rows;
                        // Loop through all table rows (except the first, which contains table headers):
                        for (i = 1; i < (rows.length - 1); i++) {{
                            shouldSwitch = false;
                            
                            x = rows[i].getElementsByTagName("TD")[n];
                            y = rows[i + 1].getElementsByTagName("TD")[n];
                            
                            let xVal = x.getAttribute('data-val');
                            let yVal = y.getAttribute('data-val');
                            
                            // Check if numeric
                            let xNum = parseFloat(xVal);
                            let yNum = parseFloat(yVal);
                            
                            if (!isNaN(xNum) && !isNaN(yNum) && n > 1) {{ // Columns 2, 3, 4 are numeric
                                if (dir == "asc") {{
                                    if (xNum > yNum) {{ shouldSwitch = true; break; }}
                                }} else if (dir == "desc") {{
                                    if (xNum < yNum) {{ shouldSwitch = true; break; }}
                                }}
                            }} else {{
                                if (dir == "asc") {{
                                    if (xVal.toLowerCase() > yVal.toLowerCase()) {{ shouldSwitch = true; break; }}
                                }} else if (dir == "desc") {{
                                    if (xVal.toLowerCase() < yVal.toLowerCase()) {{ shouldSwitch = true; break; }}
                                }}
                            }}
                        }}
                        if (shouldSwitch) {{
                            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                            switching = true;
                            switchcount ++;
                        }} else {{
                            if (switchcount == 0 && dir == "asc") {{
                                dir = "desc";
                                switching = true;
                            }}
                        }}
                    }}
                    
                    // Update icon
                    const icon = document.getElementById('sort-icon-'+n);
                    if(icon) {{
                        icon.innerHTML = dir === 'asc' ? '↑' : '↓';
                    }}
                    
                    // Re-apply pagination after sort
                    // Reset to page 1 to avoid confusion or keep page?
                    // Let's keep page 1 for simplicity as rows shifted
                    currentPage = 1;
                    updateTable();
                }}
                
                // Inicializar tabla al cargar
                window.onload = function() {{
                    updateTable();
                }};
            </script>

        </body>
        </html>"""
        return html

    def generate_history_json(self, history_data, filename='history.json'):
        """Genera el archivo JSON con el histórico de precios"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(history_data, f)
            return True
        except Exception as e:
            print(f"Error generando history.json: {e}")
            return False

    def generate_history_viewer_html(self):
        """Genera el HTML del visor de histórico con ApexCharts y variaciones"""
        html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Histórico de Precios</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
    </style>
</head>
<body class="min-h-screen p-6">
    <div class="max-w-5xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden p-6">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl font-bold text-gray-800" id="articleTitle">Cargando...</h1>
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-2">
                    <label class="text-sm font-medium text-gray-700">Desde:</label>
                    <input type="month" id="dateStart" class="p-1 border rounded text-sm">
                </div>
                <div class="flex items-center gap-2">
                    <label class="text-sm font-medium text-gray-700">Hasta:</label>
                    <input type="month" id="dateEnd" class="p-1 border rounded text-sm">
                </div>
                <button onclick="updateView()" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium">Actualizar</button>
                <button onclick="window.close()" class="ml-4 text-gray-500 hover:text-gray-700">Cerrar</button>
            </div>
        </div>
        
        <div class="relative w-full bg-white p-2 rounded border border-gray-100 mb-6">
             <div id="priceChart"></div>
        </div>
        
        <div class="mt-8">
            <h2 class="text-lg font-semibold mb-3">Datos Históricos</h2>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Periodo</th>
                            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Precio</th>
                            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Variación</th>
                        </tr>
                    </thead>
                    <tbody id="historyTableBody" class="bg-white divide-y divide-gray-200">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const articleId = urlParams.get('id');
        let chartInstance = null;
        let fullHistoryData = [];

        async function loadHistory() {
            if (!articleId) {
                document.getElementById('articleTitle').textContent = 'Error: No se especificó artículo';
                return;
            }

            try {
                const response = await fetch('history.json');
                if (!response.ok) throw new Error('No se pudo cargar history.json');
                const allHistory = await response.json();
                
                fullHistoryData = allHistory[articleId] || [];
                
                if (fullHistoryData.length === 0) {
                    document.getElementById('articleTitle').textContent = `Artículo ${articleId}: Sin datos históricos`;
                    return;
                }
                
                document.getElementById('articleTitle').textContent = `Histórico de Precios: ${articleId}`;
                
                initDateFilters();
                updateView();
                
            } catch (error) {
                console.error(error);
                document.getElementById('articleTitle').textContent = 'Error cargando datos';
            }
        }

        function initDateFilters() {
            if (fullHistoryData.length === 0) return;
            
            fullHistoryData.sort((a,b) => a.periodo.localeCompare(b.periodo));
            
            const lastEntry = fullHistoryData[fullHistoryData.length - 1];
            const lastDateStr = lastEntry.periodo; // YYYYMM
            
            const year = parseInt(lastDateStr.substring(0,4));
            const month = parseInt(lastDateStr.substring(4,6)) - 1;
            const lastDate = new Date(year, month);
            
            const startDate = new Date(lastDate);
            startDate.setMonth(startDate.getMonth() - 23);
            
            document.getElementById('dateEnd').value = dateToMonthInput(lastDate);
            document.getElementById('dateStart').value = dateToMonthInput(startDate);
        }

        function dateToMonthInput(date) {
            const y = date.getFullYear();
            const m = (date.getMonth() + 1).toString().padStart(2, '0');
            return `${y}-${m}`;
        }
        
        function updateView() {
            const startVal = document.getElementById('dateStart').value.replace('-', '');
            const endVal = document.getElementById('dateEnd').value.replace('-', '');
            
            if (!startVal || !endVal) return;

            // Filter for Chart (Keep chronological for ApexCharts)
            const filteredData = fullHistoryData.filter(d => {
                return d.periodo >= startVal && d.periodo <= endVal;
            });
            
            renderChart(filteredData);
            renderTable(filteredData);
        }

        function renderChart(data) {
            // ApexCharts logic
            const options = {
                series: [{
                    name: "Precio Promedio",
                    data: data.map(d => d.precio)
                }],
                chart: {
                    height: 350,
                    type: 'area',
                    zoom: { enabled: false },
                    toolbar: { show: false }
                },
                dataLabels: { enabled: false },
                stroke: { curve: 'smooth', width: 2 },
                xaxis: {
                    categories: data.map(d => formatPeriod(d.periodo)),
                },
                yaxis: {
                    labels: {
                        formatter: function (value) {
                            return "$" + value.toLocaleString('es-AR', {minimumFractionDigits: 0, maximumFractionDigits: 0});
                        }
                    }
                },
                tooltip: {
                    y: {
                        formatter: function (val) {
                            return "$" + val.toLocaleString('es-AR', {minimumFractionDigits: 2});
                        }
                    }
                },
                colors: ['#2563EB'],
                fill: {
                    type: 'gradient',
                    gradient: {
                        shadeIntensity: 1,
                        opacityFrom: 0.7,
                        opacityTo: 0.1,
                        stops: [0, 90, 100]
                    }
                }
            };

            if (chartInstance) {
                chartInstance.destroy();
            }
            
            const chartDiv = document.querySelector("#priceChart");
            chartDiv.innerHTML = ""; // Clear
            chartInstance = new ApexCharts(chartDiv, options);
            chartInstance.render();
        }

        function renderTable(data) {
            const tbody = document.getElementById('historyTableBody');
            tbody.innerHTML = '';
            
            // Sort desc for table
            const sorted = [...data].sort((a,b) => b.periodo.localeCompare(a.periodo));
            
            // Icon helper
            const iconUp = '<span class="text-red-500 font-bold">↑</span>';
            const iconDown = '<span class="text-green-500 font-bold">↓</span>';
            const iconEqual = '<span class="text-gray-400">=</span>';
            
            sorted.forEach((d, index) => {
                // Calculate variation vs previous month (next item in sorted array)
                let variationHtml = '-';
                if (index < sorted.length - 1) {
                    const prevPrice = sorted[index + 1].precio;
                    if (prevPrice > 0) {
                        const diff = ((d.precio - prevPrice) / prevPrice) * 100;
                        let colorClass = "text-gray-500";
                        let icon = iconEqual;
                        if (diff > 0) { colorClass = "text-red-600 font-bold"; icon = iconUp; }
                        if (diff < 0) { colorClass = "text-green-600 font-bold"; icon = iconDown; }
                        variationHtml = `<span class="${colorClass}">${icon} ${diff.toFixed(2)}%</span>`;
                    }
                }
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatPeriod(d.periodo)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 font-medium">$${d.precio.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right">${variationHtml}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function formatPeriod(p) {
            if (!p || p.length !== 6) return p;
            return `${p.substring(4,6)}/${p.substring(0,4)}`;
        }

        loadHistory();
    </script>
</body>
</html>
"""
        return html

