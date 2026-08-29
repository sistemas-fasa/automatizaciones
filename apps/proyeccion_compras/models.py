from dataclasses import dataclass, field


@dataclass
class ProyeccionResultado:
    articulo: str
    detalle: str
    unidad: str
    proveedor: str
    nombre_proveedor: str
    stock_actual: float
    promedio_mensual: float
    proyeccion_bruta: float
    saldo_pedidos: float
    pedido_sugerido: float
    pedido_real: float
    meses_proyectados: int
    formula_conversion: str | None
    costo_unitario: float = 0.0


@dataclass
class ResumenProveedor:
    codigo: str
    nombre: str
    cantidad_articulos: int
    total_stock: float
    total_proyeccion: float
    total_pedido_sugerido: float
    total_pedido_real: float = 0.0
    total_costo_stock: float = 0.0
    total_costo_proyeccion: float = 0.0
    total_costo_pedido: float = 0.0
    total_costo_pedido_real: float = 0.0
    articulos: list[ProyeccionResultado] = field(default_factory=list)
