import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelos.Vendedores import VentasVendedor
from datetime import date

rows = VentasVendedor.ventas_por_vendedor_y_periodo(date(2026, 5, 1), date(2026, 5, 31))
print(f"{'VEND':>4} {'NOMBRE':30s} {'TOTAL_NETO':>15s}")
print("=" * 52)
for r in rows:
    print(f"{r['vendedor']:>4} {r['nombre_vendedor']:30s} {r['total_neto']:>15,.2f}")
total = sum(r['total_neto'] for r in rows)
print("=" * 52)
print(f"{'':4} {'TOTAL':30s} {total:>15,.2f}")

# Also generate the Excel
VentasVendedor.exportar_a_excel(date(2026,5,1), date(2026,5,31), 'detalle_ventas_vendedor.xlsx')
print("\nExcel generado: detalle_ventas_vendedor.xlsx")
