# Graficos Top + Resto

## Objetivo

Agregar a cada grafico de ranking una barra `Resto` que represente la suma de todos los elementos excluidos del Top, sin cambiar las metricas ni el ordenamiento actuales.

## Alcance

- Los graficos por proveedor conservan el Top 15 y pueden agregar una barra adicional `Resto`.
- Los graficos por articulo conservan el Top 20 y pueden agregar una barra adicional `Resto`.
- `Resto` se muestra solamente cuando existen elementos fuera del Top.
- La barra usa la misma unidad y formato que el grafico correspondiente.

## Graficos alcanzados

1. Proveedores por pedido sugerido: suma `total_pedido_sugerido` fuera del Top 15.
2. Proveedores por costo de pedido: suma `total_costo_pedido` fuera del Top 15.
3. Proveedores por stock actual: suma `total_stock` fuera del Top 15.
4. Articulos por pedido sugerido: suma `pedido_sugerido` fuera del Top 20.
5. Articulos por costo de pedido: suma `pedido_sugerido * costo_unitario` fuera del Top 20.

## Diseno tecnico

Se incorporara una funcion pura que reciba la coleccion, la metrica y el limite. La funcion ordenara los elementos, devolvera el Top en el orden visual actual y agregara un elemento sintetico con etiqueta `Resto` y la suma de los valores excluidos. Si no hay elementos excluidos, no agregara esa barra.

Los cinco graficos consumiran el resultado de esa funcion para evitar criterios distintos o doble conteo.

## Verificacion

- Una prueba automatizada debe fallar antes de implementar la funcion.
- Para cada grafico, la suma del Top mas `Resto` debe coincidir con el total de la coleccion original.
- Debe comprobarse que no aparezca `Resto` cuando la cantidad de elementos no supera el limite.
- La prueba existente de renderizado debe continuar sin errores de JavaScript.

## Fuera de alcance

- Cambiar la cantidad del Top.
- Cambiar colores, titulos, formatos o dimensiones de los graficos.
- Modificar el calculo de proyecciones, stock, pedidos o costos.
