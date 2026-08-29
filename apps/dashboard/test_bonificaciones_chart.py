import unittest
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from ReportGenerator import ReportGenerator


class BonificacionesChartTest(unittest.TestCase):
    def _base_stats(self):
        return {
            "total_dia": 1000,
            "por_pago": {},
            "por_contado": {},
            "por_lista": {},
            "por_reparto": {},
            "facturas_count": 2,
            "promedio_factura": 500,
            "remitos_sin_facturar": 0,
            "aging": [],
            "articulos_especiales": {},
            "por_caja": {},
            "ventas_nc_vendedor": [
                {"vendedor": "1", "nombre_vendedor": "Vendedor Test", "ventas": 1200.0, "nc": 0}
            ],
            "bonificaciones": [
                {"lista": "1", "boni": 0.0, "facturas_unicas": 3, "suma_total": 1500.0},
                {"lista": "1", "boni": 5.0, "facturas_unicas": 1, "suma_total": 500.0},
                {"lista": "4", "boni": 1.0, "facturas_unicas": 2, "suma_total": 900.0},
            ],
            "empresa_title": "Empresa Test",
            "empresa_color": "#E60000",
        }

    def test_monthly_html_places_vendedor_next_to_cobranzas_and_bonificaciones_below(self):
        stats = self._base_stats()
        stats["acumulado_mes"] = True

        html = ReportGenerator().generate_html_report(
            stats,
            monthly_total=1000,
            fecha="2026-05-19",
            aging_details=[],
            prev_month_total=0,
        )

        self.assertIn("bonificacionesLista1Chart", html)
        self.assertIn("bonificacionesLista4Chart", html)
        self.assertIn("cajaMesChart", html)
        self.assertIn("ventasNcVendedorChart", html)
        self.assertIn("Eje X: vendedores | Eje Y: monto total vendido", html)
        self.assertIn("bonificacionesData", html)
        self.assertIn("Bonificaciones Lista 1 - Mes", html)
        self.assertIn("Bonificaciones Lista 4 - Mes", html)
        self.assertIn('"facturas_unicas": 3', html)
        self.assertIn("<!-- Cobranzas, Vendedor y Bonificaciones (solo Mes) -->", html)
        self.assertIn("lg:grid-cols-2", html)
        self.assertNotIn("<!-- Cobranzas y Bonificaciones (solo Mes) -->", html)

        cobranzas_pos = html.index("Cobranzas por tipo - Mes")
        vendedor_pos = html.index("Total de Ventas por Vendedor")
        bonif1_pos = html.index("Bonificaciones Lista 1 - Mes")
        bonif4_pos = html.index("Bonificaciones Lista 4 - Mes")

        self.assertLess(cobranzas_pos, vendedor_pos)
        self.assertLess(vendedor_pos, bonif1_pos)
        self.assertLess(bonif1_pos, bonif4_pos)

    def test_daily_html_does_not_include_bonificaciones_chart(self):
        html = ReportGenerator().generate_html_report(
            self._base_stats(),
            monthly_total=1000,
            fecha="2026-05-19",
            aging_details=[],
            prev_month_total=0,
        )

        self.assertNotIn("bonificacionesLista1Chart", html)
        self.assertNotIn("bonificacionesLista4Chart", html)
        self.assertNotIn("Bonificaciones Lista 1 - Mes", html)
        self.assertNotIn("Bonificaciones Lista 4 - Mes", html)

    def test_daily_html_does_not_include_vendedor_chart(self):
        html = ReportGenerator().generate_html_report(
            self._base_stats(),
            monthly_total=1000,
            fecha="2026-05-19",
            aging_details=[],
            prev_month_total=0,
        )

        self.assertNotIn("ventasNcVendedorChart", html)
        self.assertNotIn("Total de Ventas por Vendedor", html)
        self.assertNotIn("ventasNcVendedorData", html)

    def test_vendedor_chart_uses_vertical_bars(self):
        stats = self._base_stats()
        stats["acumulado_mes"] = True

        html = ReportGenerator().generate_html_report(
            stats,
            monthly_total=1000,
            fecha="2026-05-19",
            aging_details=[],
            prev_month_total=0,
        )

        vendedor_script_start = html.index("// Gráfico: Total de ventas por vendedor")
        vendedor_script_end = html.index("} else {", vendedor_script_start)
        vendedor_script = html[vendedor_script_start:vendedor_script_end]

        self.assertIn("type: 'bar'", vendedor_script)
        self.assertNotIn("indexAxis: 'y'", vendedor_script)
        self.assertIn("maxRotation: 45", vendedor_script)
        self.assertIn("flex-1 min-h-[560px]", html)
        self.assertNotIn("height: 384px; max-height: 384px", html)


if __name__ == "__main__":
    unittest.main()
