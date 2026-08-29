#!/usr/bin/env python3

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from calculator import calcular_proyecciones, importe_vfp, obtener_tipo_cambio
from config import cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("generate_html")


def serialize_data(resumenes):
    data = []
    for prov in resumenes:
        prov_dict = {
            "codigo": prov.codigo,
            "nombre": prov.nombre,
            "cantidad_articulos": prov.cantidad_articulos,
            "total_stock": prov.total_stock,
            "total_proyeccion": prov.total_proyeccion,
            "total_pedido_sugerido": prov.total_pedido_sugerido,
            "total_pedido_real": prov.total_pedido_real,
            "total_costo_stock": prov.total_costo_stock,
            "total_costo_proyeccion": prov.total_costo_proyeccion,
            "total_costo_pedido": prov.total_costo_pedido,
            "total_costo_pedido_real": prov.total_costo_pedido_real,
            "articulos": [],
        }
        for art in prov.articulos:
            prov_dict["articulos"].append(
                {
                    "articulo": art.articulo,
                    "detalle": art.detalle,
                    "unidad": art.unidad,
                    "stock_actual": art.stock_actual,
                    "promedio_mensual": art.promedio_mensual,
                    "proyeccion_bruta": art.proyeccion_bruta,
                    "saldo_pedidos": art.saldo_pedidos,
                    "pedido_sugerido": art.pedido_sugerido,
                    "pedido_real": art.pedido_real,
                    "costo_unitario": art.costo_unitario,
                    "costo_proyectado_vfp": float(
                        importe_vfp(art.pedido_sugerido, art.costo_unitario)
                    ),
                    "costo_pedido_vfp": float(
                        importe_vfp(art.pedido_real, art.costo_unitario)
                    ),
                }
            )
        data.append(prov_dict)
    return data


def generate_report(output_path: str | Path) -> Path:
    logger.info("Calculando proyecciones...")
    resumenes = calcular_proyecciones()

    if not resumenes:
        raise RuntimeError("No se generaron proyecciones")

    logger.info("Generando HTML...")
    data = serialize_data(resumenes)
    json_data = json.dumps(data, ensure_ascii=False)

    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    tc = obtener_tipo_cambio()

    html = r"""<!DOCTYPE html>
<html lang="es" data-theme="industrial">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proyección de Compras</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {
    --primary: #1687ff;
    --primary-light: #e7f2ff;
    --accent-electric: #2f9bff;
    --accent-glow: rgba(47,155,255,.28);
    --surface-deep: #080d14;
    --surface-dark: #151d28;
    --surface-mid: #1d2836;
    --surface-raised: #243244;
    --danger: #ff5d69;
    --success: #35d39a;
    --warning: #ffbd45;
    --gray: #64748b;
    --muted-light: #93a4b8;
    --border: #d9e1ea;
    --dark-border: rgba(148,163,184,.18);
    --bg: #0c121b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh; color: #172033; padding: 24px;
    background-color: var(--bg);
    background-image: radial-gradient(circle at 12% 0%, rgba(47,155,255,.14), transparent 26%), linear-gradient(135deg, #0c121b 0%, #111a26 55%, #091019 100%);
  }
  .container { max-width: 1540px; margin: 0 auto; }
  header {
    position: relative; overflow: hidden;
    background: linear-gradient(125deg, #192433 0%, #111925 70%);
    color: #fff; padding: 28px 32px 28px 38px; border-radius: 14px;
    border: 1px solid var(--dark-border); border-left: 5px solid var(--accent-electric);
    margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 20px 50px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.04);
  }
  header::after { content: ''; position: absolute; width: 280px; height: 280px; right: -100px; top: -145px; border: 1px solid rgba(47,155,255,.18); border-radius: 50%; box-shadow: 0 0 0 42px rgba(47,155,255,.035), 0 0 0 84px rgba(47,155,255,.025); }
  header h1 { font-size: 27px; font-weight: 720; letter-spacing: -.5px; }
  header h1::before { content: '///'; color: var(--accent-electric); margin-right: 12px; letter-spacing: -3px; }
  header .meta { position: relative; z-index: 1; font-size: 12px; color: #b8c6d8; letter-spacing: .35px; }
  header > .meta { padding: 9px 13px; background: rgba(8,13,20,.5); border: 1px solid var(--dark-border); border-radius: 7px; }
  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
  .stats-grid-bottom { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }
  .stat-card {
    position: relative; background: linear-gradient(145deg, var(--surface-mid), var(--surface-dark));
    color: #f7fbff; border-radius: 10px; padding: 18px 20px 17px; border: 1px solid var(--dark-border);
    box-shadow: 0 10px 24px rgba(0,0,0,.2), inset 0 1px rgba(255,255,255,.025); overflow: hidden;
  }
  .stat-card::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 3px; background: linear-gradient(var(--accent-electric), #1769d2); box-shadow: 0 0 14px var(--accent-glow); }
  .stat-card::after { content: ''; position: absolute; width: 58px; height: 58px; right: -20px; top: -24px; border: 1px solid rgba(47,155,255,.12); transform: rotate(45deg); }
  .stat-card .label { font-size: 10px; color: var(--muted-light); text-transform: uppercase; letter-spacing: 1.15px; white-space: nowrap; }
  .stat-card .value { font-size: 24px; font-weight: 720; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .stat-card .value.sm { font-size: 17px; }
  .stat-card .value.xs { font-size: 14px; }
  .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .chart-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .chart-card {
    background: rgb(21, 29, 40); border-radius: 12px; padding: 20px 22px; border: 1px solid var(--dark-border);
    box-shadow: 0 14px 32px rgba(0,0,0,.22), inset 0 1px rgba(255,255,255,.025);
  }
  .chart-card h3 { font-size: 12px; color: #dce8f6; margin-bottom: 14px; padding-left: 11px; border-left: 3px solid var(--accent-electric); text-transform: uppercase; letter-spacing: .55px; }
  .chart-card canvas { max-height: 300px; }
  .chart-card.full { grid-column: 1 / -1; }
  .controls {
    display: flex; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; align-items: center;
    padding: 14px 16px; background: var(--surface-dark); border: 1px solid var(--dark-border); border-radius: 10px;
    box-shadow: 0 10px 24px rgba(0,0,0,.18);
  }
  .controls select, .controls input {
    padding: 9px 12px; border: 1px solid #cbd5e1; border-radius: 6px;
    font-size: 13px; background: #f8fafc; color: #152033; outline: none;
  }
  .controls select:focus, .controls input:focus { border-color: var(--accent-electric); box-shadow: 0 0 0 3px rgba(47,155,255,.2); }
  .controls input[type="checkbox"] { accent-color: var(--accent-electric); }
  .controls label { font-size: 12px; color: #c2cfde; }
  #rowCount { margin-left: auto; color: #9fb1c5 !important; font-variant-numeric: tabular-nums; }
  .table-wrap {
    background: #fff; border-radius: 11px; border: 1px solid #26374b;
    overflow: hidden; box-shadow: 0 18px 38px rgba(0,0,0,.26);
  }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  thead { background: linear-gradient(90deg, #172334, #1e3148); color: #fff; border-bottom: 3px solid var(--accent-electric); }
  th { padding: 13px 10px; text-align: left; font-size: 11px; font-weight: 650; letter-spacing: .28px; white-space: nowrap; user-select: none; text-transform: uppercase; }
  td { padding: 10px; border-bottom: 1px solid #e2e8f0; background: #fff; }
  tbody tr:not(.prov-group):not(.subtotal):nth-child(even) td { background: #f7f9fc; }
  tbody tr:hover { background: var(--primary-light); }
  tbody tr:not(.prov-group):not(.subtotal):hover td { background: #e8f3ff; }
  .col-header { background: linear-gradient(90deg, #172334, #1e3148); }
  .col-header th { padding: 10px 10px; text-align: left; font-size: 11px; font-weight: 650; letter-spacing: .28px; white-space: nowrap; user-select: none; text-transform: uppercase; color: #fff; border-bottom: 2px solid var(--accent-electric); }
  .prov-group td { background: #dce7f3; color: #17263a; font-weight: 720; border-top: 1px solid #bdccdc; border-bottom-color: #bdccdc; letter-spacing: .15px; }
  .subtotal td { background: #eaf2fb !important; color: #17263a; border-top: 2px solid var(--accent-electric) !important; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 11px; font-weight: 600;
  }
  .text-right { text-align: right; }
  .text-center { text-align: center; }
  .detalle-cell { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .money { font-variant-numeric: tabular-nums; white-space: nowrap; }
  .progress-bar {
    height: 6px; background: #e8eaed; border-radius: 3px; overflow: hidden; min-width: 80px;
  }
  .progress-bar .fill { height: 100%; border-radius: 3px; transition: width .3s; }
  footer { text-align: center; margin-top: 24px; padding: 18px; font-size: 10px; color: #75869a; text-transform: uppercase; letter-spacing: 1px; }
  @media (max-width: 768px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .stats-grid-bottom { grid-template-columns: 1fr; }
    .chart-row { grid-template-columns: 1fr; }
    .chart-row-3 { grid-template-columns: 1fr; }
    .chart-row-3 .full { grid-column: auto; }
    body { padding: 12px; }
    header { flex-direction: column; text-align: left; align-items: flex-start; gap: 12px; padding: 22px; }
    header h1 { font-size: 22px; }
    .stat-card { padding: 16px 14px; }
    .stat-card .value { font-size: 18px; }
    .stat-card .value.sm { font-size: 15px; }
    .stat-card .value.xs { font-size: 12px; }
    .controls { align-items: stretch; }
    .controls select, .controls input[type="text"] { width: 100%; }
    #rowCount { margin-left: 0; width: 100%; }
    .table-wrap { overflow-x: auto; }
  }
  @media (min-width: 769px) and (max-width: 1100px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .chart-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="container" id="app">
  <header>
    <div>
      <h1>Proyeccion de Compras</h1>
      <div class="meta">__MESES__ meses proyectados &middot; Empresa ID: __EMPRESA__</div>
    </div>
    <div class="meta">Generado: __FECHA__</div>
  </header>

  <div class="stats-grid" id="statsGridUnidades"></div>
  <div class="stats-grid-bottom" id="statsGridCostos"></div>
  <div style="font-size:10px;color:#90a3b8;margin-bottom:16px;text-align:right;letter-spacing:.6px;text-transform:uppercase">Tipo de Cambio USD: <strong style="color:#d8e6f5">$__TC__</strong></div>

  <div class="chart-row">
    <div class="chart-card">
      <h3>Top 15 Proveedores - Pedido Sugerido</h3>
      <canvas id="chartPedido"></canvas>
    </div>
    <div class="chart-card">
      <h3>Top 15 Proveedores - Costo Pedido</h3>
      <canvas id="chartCostoPedido"></canvas>
    </div>
    <div class="chart-card">
      <h3>Top 15 Proveedores - Stock Actual</h3>
      <canvas id="chartStockProv"></canvas>
    </div>
  </div>
  <div class="chart-row">
    <div class="chart-card">
      <h3>Top 20 Articulos - Pedido Sugerido</h3>
      <canvas id="chartTopArticulos"></canvas>
    </div>
    <div class="chart-card">
      <h3>Top 20 Articulos - Costo Pedido</h3>
      <canvas id="chartTopCosto"></canvas>
    </div>
  </div>

  <div class="controls">
    <label>Proveedor:</label>
    <select id="filterProv"><option value="">Todos</option></select>
    <label>Buscar:</label>
    <input id="filterSearch" placeholder="articulo, detalle..." />
    <label style="display:flex;align-items:center;gap:4px">
      <input type="checkbox" id="hideZero" checked /> Ocultar pedido $0
    </label>
    <span style="flex:1"></span>
    <span style="font-size:13px;color:var(--gray)" id="rowCount"></span>
  </div>

  <div class="table-wrap">
    <table>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
  <div style="margin-top:8px;font-size:11px;color:var(--gray);text-align:right"><strong>Dias Cob.</strong> = Stock / Prom.Mensual * 30 — dias de venta que cubre el stock actual</div>
  <footer>Generado automaticamente por el sistema de Proyeccion de Compras</footer>
</div>

<script>
const DATA = __JSON_DATA__;

function fmt(n) {
  return Number(n).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmt3(n) {
  return Number(n).toLocaleString('es-AR', { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

function importeVfp(cantidad, costo) {
  return Math.round((Number(cantidad) * Number(costo) + Number.EPSILON) * 1000) / 1000;
}

function initStats() {
  const totalArticulos = DATA.reduce((s, p) => s + p.cantidad_articulos, 0);
  const totalStock = DATA.reduce((s, p) => s + p.total_stock, 0);
  const totalProy = DATA.reduce((s, p) => s + p.total_proyeccion, 0);
  const totalPedido = DATA.reduce((s, p) => s + p.total_pedido_real, 0);
  const totalCostoPedido = DATA.reduce((s, p) => s + p.total_costo_pedido_real, 0);
  const totalCostoProy = DATA.reduce((s, p) => s + p.total_costo_proyeccion, 0);
  const totalCostoStock = DATA.reduce((s, p) => s + p.total_costo_stock, 0);

  function valClass(n) {
    const s = fmt(n);
    if (s.length > 16) return 'value xs';
    if (s.length > 12) return 'value sm';
    return 'value';
  }

  document.getElementById('statsGridUnidades').innerHTML = `
    <div class="stat-card"><div class="label">Proveedores</div><div class="value" style="color:#53adff">${DATA.length}</div></div>
    <div class="stat-card"><div class="label">Articulos</div><div class="value" style="color:#53adff">${totalArticulos}</div></div>
    <div class="stat-card"><div class="label">Stock Total (uds)</div><div class="${valClass(totalStock)}">${fmt(totalStock)}</div></div>
    <div class="stat-card"><div class="label">Proyeccion (uds)</div><div class="${valClass(totalProy)}" style="color:#ffbd45">${fmt(totalProy)}</div></div>
  `;
  document.getElementById('statsGridCostos').innerHTML = `
    <div class="stat-card"><div class="label">Costo Stock Total</div><div class="${valClass(totalCostoStock)}">$${fmt(totalCostoStock)}</div></div>
    <div class="stat-card"><div class="label">Costo Proyeccion</div><div class="${valClass(totalCostoProy)}" style="color:#ffbd45">$${fmt3(totalCostoProy)}</div></div>
    <div class="stat-card"><div class="label">Total Pedido</div><div class="${valClass(totalCostoPedido)}" style="color:#35d39a">$${fmt3(totalCostoPedido)}</div></div>
  `;
}

function topNConResto(arr, valueFn, n) {
  const sorted = arr.map((item, index) => ({ item, index, value: Number(valueFn(item)) || 0 }))
    .sort((a, b) => b.value - a.value || a.index - b.index);
  const top = sorted.slice(0, n).reverse();
  const resto = sorted.slice(n).reduce((sum, entry) => sum + entry.value, 0);
  if (sorted.length > n) top.unshift({ item: null, value: resto, label: 'Resto' });
  return top;
}

function initCharts() {
  Chart.defaults.color = '#aebdce';
  Chart.defaults.borderColor = 'rgba(148, 163, 184, .14)';
  Chart.defaults.scale.grid.color = 'rgba(148, 163, 184, .12)';
  Chart.defaults.scale.ticks.color = '#9fb0c3';
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(7, 12, 20, 0.96)';
  Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
  Chart.defaults.plugins.tooltip.bodyColor = '#dce8f6';
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(47, 155, 255, .45)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 11;
  const allArts = DATA.flatMap(p => p.articulos.map(a => ({ ...a, proveedor: p.codigo })));

  function barHoriz(id, items, labelFn, fmtVal, color) {
    new Chart(document.getElementById(id), {
      type: 'bar',
      data: {
        labels: items.map(entry => entry.label || labelFn(entry.item)),
        datasets: [{
          label: '',
          data: items.map(entry => Math.round(entry.value * 100) / 100),
          backgroundColor: color || 'rgba(26,115,232,.7)',
          borderColor: color ? color.replace('.7', '1') : 'rgba(26,115,232,1)',
          borderWidth: 1,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { callback: v => fmtVal ? fmtVal(v) : fmt(v) } } }
      }
    });
  }

  // Top 15 proveedores by pedido sugerido
  const topProvPed = topNConResto(DATA, a => a.total_pedido_real, 15);
  barHoriz('chartPedido', topProvPed, a => a.codigo, null, 'rgba(26,115,232,.7)');

  // Top 15 proveedores by costo pedido
  const topProvCosto = topNConResto(DATA, a => a.total_costo_pedido_real, 15);
  barHoriz('chartCostoPedido', topProvCosto, a => a.codigo, v => '$' + fmt(v), 'rgba(234,67,53,.7)');

  // Top 15 proveedores by stock actual
  const topProvStock = topNConResto(DATA, a => a.total_stock, 15);
  barHoriz('chartStockProv', topProvStock, a => a.codigo, null, 'rgba(52,168,83,.7)');

  // Top 20 articulos by pedido sugerido
  const topArtsLabeled = topNConResto(allArts, a => a.pedido_real, 20);
  new Chart(document.getElementById('chartTopArticulos'), {
    type: 'bar',
    data: {
      labels: topArtsLabeled.map(entry => entry.label || entry.item.articulo + ' - ' + entry.item.detalle.substring(0, 30)),
      datasets: [{
        label: '',
        data: topArtsLabeled.map(entry => Math.round(entry.value * 100) / 100),
        backgroundColor: 'rgba(26,115,232,.7)',
        borderColor: 'rgba(26,115,232,1)',
        borderWidth: 1,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { callback: v => fmt(v) } } }
    }
  });

  // Top 20 articulos by costo pedido
  const topArtsCosto = topNConResto(allArts, a => a.pedido_real * a.costo_unitario, 20);
  new Chart(document.getElementById('chartTopCosto'), {
    type: 'bar',
    data: {
      labels: topArtsCosto.map(entry => entry.label || entry.item.articulo + ' - ' + entry.item.detalle.substring(0, 30)),
      datasets: [{
        label: '',
        data: topArtsCosto.map(entry => Math.round(entry.value * 100) / 100),
        backgroundColor: 'rgba(234,67,53,.7)',
        borderColor: 'rgba(234,67,53,1)',
        borderWidth: 1,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { callback: v => '$' + fmt(v) } } }
    }
  });
}

function initFilters() {
  const sel = document.getElementById('filterProv');
  DATA.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.codigo;
    opt.textContent = p.codigo + ' - ' + p.nombre;
    sel.appendChild(opt);
  });
  sel.addEventListener('change', renderTable);
  document.getElementById('filterSearch').addEventListener('input', renderTable);
  document.getElementById('hideZero').addEventListener('change', renderTable);
}

function renderTable() {
  const filterProv = document.getElementById('filterProv').value;
  const filterSearch = document.getElementById('filterSearch').value.toLowerCase();
  const hideZero = document.getElementById('hideZero').checked;

  const totalPedidoGlobal = DATA.reduce((s, p) => s + p.total_pedido_real, 0);

  let html = '';
  let visibleCount = 0;

  DATA.forEach(prov => {
    let provVisible = 0;
    const rows = [];
    let sumStock = 0, sumProm = 0, sumProy = 0, sumSaldo = 0, sumPed = 0;
    let sumCostoStock = 0, sumCostoProyMills = 0;
    const provTotalPed = prov.total_pedido_real;
    prov.articulos.forEach(a => {
      if (filterProv && prov.codigo !== filterProv) return;
      if (hideZero && a.pedido_sugerido === 0 && a.pedido_real === 0) return;
      if (filterSearch && !a.articulo.toLowerCase().includes(filterSearch) && !a.detalle.toLowerCase().includes(filterSearch)) return;
      visibleCount++;
      provVisible++;
      sumStock += a.stock_actual;
      sumProm += a.promedio_mensual;
      sumProy += a.proyeccion_bruta;
      sumSaldo += a.saldo_pedidos;
      sumPed += a.pedido_sugerido;
      sumCostoStock += a.stock_actual * a.costo_unitario;
      sumCostoProyMills += Math.round(a.costo_proyectado_vfp * 1000);
      const pctProv = provTotalPed > 0 ? (a.pedido_real / provTotalPed * 100) : 0;
      const diasCobertura = a.promedio_mensual > 0 ? (a.stock_actual / a.promedio_mensual * 30) : 0;
      rows.push(`<tr>
        <td>${prov.codigo}</td>
        <td><strong>${a.articulo}</strong></td>
        <td class="detalle-cell" title="${a.detalle}">${a.detalle}</td>
        <td>${a.unidad}</td>
        <td class="text-right money">${fmt(a.stock_actual)}</td>
        <td class="text-right money">${fmt(a.promedio_mensual)}</td>
        <td class="text-right money">${fmt(a.proyeccion_bruta)}</td>
        <td class="text-right money">${fmt(a.saldo_pedidos)}</td>
        <td class="text-right money"><strong>${fmt(a.pedido_sugerido)}</strong></td>
        <td class="text-right money">$${fmt(a.costo_unitario)}</td>
        <td class="text-right money">$${fmt(a.stock_actual * a.costo_unitario)}</td>
        <td class="text-right money">$${fmt3(a.costo_proyectado_vfp)}</td>
        <td class="text-right money">${diasCobertura > 0 ? fmt(diasCobertura) : '—'}</td>
        <td class="text-right money">${pctProv.toFixed(1)}%</td>
      </tr>`);
    });
    if (provVisible > 0) {
      const pctGral = totalPedidoGlobal > 0 ? (provTotalPed / totalPedidoGlobal * 100) : 0;
      html += `<tr class="prov-group"><td colspan="14">${prov.codigo} - ${prov.nombre} &mdash; ${provVisible} articulos</td></tr>`;
      html += `<tr class="col-header"><th>Prov</th><th>Articulo</th><th>Detalle</th><th>Ud</th><th class="text-right">Stock</th><th class="text-right">Prom.Men</th><th class="text-right">Proyeccion</th><th class="text-right">Pedido Prov</th><th class="text-right">Pedido Sug</th><th class="text-right">Costo Unit</th><th class="text-right">Costo Stock</th><th class="text-right">Costo Proy</th><th class="text-right">Dias Cob.</th><th class="text-right">% Prov</th></tr>`;
      html += rows.join('');
      html += `<tr class="subtotal" style="background:#eef2ff;font-weight:600;border-top:2px solid #1a73e8">
        <td colspan="4" style="text-align:right;padding-right:12px">SUBTOTAL ${prov.codigo}</td>
        <td class="text-right money">${fmt(sumStock)}</td>
        <td class="text-right money">${fmt(sumProm)}</td>
        <td class="text-right money">${fmt(sumProy)}</td>
        <td class="text-right money">${fmt(sumSaldo)}</td>
        <td class="text-right money">${fmt(sumPed)}</td>
        <td></td>
        <td class="text-right money">$${fmt(sumCostoStock)}</td>
        <td class="text-right money">$${fmt3(sumCostoProyMills / 1000)}</td>
        <td></td>
        <td class="text-right money" style="color:#1a73e8">${pctGral.toFixed(1)}%</td>
      </tr>`;
    }
  });

  document.getElementById('tableBody').innerHTML = html || '<tr><td colspan="14" style="text-align:center;padding:40px;color:var(--gray)">Sin resultados</td></tr>';
  document.getElementById('rowCount').textContent = visibleCount + ' articulos';
}

initStats();
initFilters();
initCharts();
renderTable();
</script>
</body>
</html>"""

    html = html.replace("__JSON_DATA__", json_data)
    html = html.replace("__MESES__", str(cfg.proy_meses))
    html = html.replace("__EMPRESA__", str(cfg.empresa_id))
    html = html.replace("__FECHA__", fecha_gen)
    html = html.replace("__TC__", f"{tc:,.2f}")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    logger.info("HTML generado: %s", out_path.resolve())
    return out_path


def main():
    out_path = generate_report(Path(cfg.excel_output_dir) / "proyeccion.html")
    print(
        f"\nAbre el archivo en tu navegador:\n  file:///{out_path.resolve().as_posix()}\n"
    )


if __name__ == "__main__":
    main()
