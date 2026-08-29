import unittest

from calculator import (
    calcular_costo_unitario,
    calcular_valores_vfp,
    importe_vfp,
    normalizar_codigo,
    redondear_vfp,
    resolver_pedido_real,
)


class CalcularValoresVfpTest(unittest.TestCase):
    def test_normaliza_claves_char_como_vfp(self):
        self.assertEqual("200.161", normalizar_codigo("200.161 "))
        self.assertEqual("0004", normalizar_codigo("0004 "))

    def test_redondea_campos_numericos_como_vfp(self):
        self.assertEqual(1.235, redondear_vfp(1.2345, 3))
        self.assertEqual(1.2346, redondear_vfp(1.23456, 4))
        self.assertEqual("541911.377", str(importe_vfp(9.75, 55580.654)))

    def test_pedido_real_usa_proycompra_pendiente_del_mismo_periodo(self):
        self.assertEqual(20, resolver_pedido_real(15.499, 20))
        self.assertEqual(15.499, resolver_pedido_real(15.499, None))

    def test_costo_compra_usa_parcial2_y_cambio_del_proveedor(self):
        self.assertEqual(
            55580.654,
            calcular_costo_unitario(
                {"costo": 78503.748, "parcial2": 55580.654, "moneda": "P"},
                1234,
            ),
        )
        self.assertEqual(
            111161.308,
            calcular_costo_unitario(
                {"costo": 78503.748, "parcial2": 55580.654, "moneda": "D"},
                2,
            ),
        )

    def test_aplica_artpro_una_sola_vez_a_promedio_proyeccion_y_stock(self):
        valores = calcular_valores_vfp(
            suma_movimientos=120,
            meses_con_movimiento=4,
            meses_proyectados=3,
            formula="/2",
            peso=0,
            stock_central=20,
            stock_sucursal=4,
            saldo_pedidos=5,
            discontinuado=False,
        )

        self.assertEqual(15, valores["promedio_periodos"])
        self.assertEqual(5, valores["promedio_mensual"])
        self.assertEqual(15, valores["proyeccion"])
        self.assertEqual(12, valores["stock"])
        self.assertEqual(0, valores["pedido_sugerido"])

    def test_discontinuado_conserva_stock_pero_proyecta_cero(self):
        valores = calcular_valores_vfp(
            suma_movimientos=120,
            meses_con_movimiento=12,
            meses_proyectados=3,
            formula="*2",
            peso=0,
            stock_central=3,
            stock_sucursal=2,
            saldo_pedidos=0,
            discontinuado=True,
        )

        self.assertEqual(20, valores["promedio_mensual"])
        self.assertEqual(0, valores["proyeccion"])
        self.assertEqual(10, valores["stock"])
        self.assertEqual(0, valores["pedido_sugerido"])


if __name__ == "__main__":
    unittest.main()
