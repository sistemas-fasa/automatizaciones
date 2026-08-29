# Rediseño industrial premium

## Objetivo

Transformar el reporte HTML de proyeccion de compras en un dashboard industrial premium, con estructura oscura, acento azul electrico y tabla clara de alta legibilidad, sin modificar calculos ni comportamiento funcional.

## Direccion visual

- Fondo grafito construido con gradientes CSS sutiles, sin imagenes externas.
- Superficies oscuras en cabecera, indicadores, graficos y controles.
- Azul electrico como acento principal para estados, bordes, cifras y jerarquia.
- Tabla hibrida: encabezado oscuro y cuerpo claro para facilitar la lectura intensiva.
- Bordes finos, sombras controladas y radios moderados; evitar una estetica generica de tarjetas flotantes.
- Tipografia del sistema para mantener portabilidad y carga inmediata.

## Componentes

### Cabecera

La cabecera tendra una composicion industrial compacta, marca visual lateral azul, titulo destacado, descripcion operativa y metadatos en bloques legibles. Mantendra la fecha, los meses proyectados y la empresa.

### Indicadores

Los siete KPI conservaran sus valores y orden. Usaran paneles grafito, etiqueta compacta, cifra protagonista, borde superior o lateral azul y variaciones semanticas discretas para proyeccion, stock y pedido.

### Graficos

Los cinco graficos conservaran datos, Top y barra `Resto`. Sus contenedores seran oscuros y Chart.js adoptara texto claro, grillas de bajo contraste, tooltips opacos y las familias cromaticas actuales ajustadas al fondo.

### Controles

Proveedor, busqueda, checkbox y contador formaran una barra operativa oscura. Inputs y select conservaran fondo claro para accesibilidad, con foco azul claramente visible.

### Tabla

- Encabezado grafito con acento azul y texto blanco.
- Filas blancas y gris muy claro alternadas.
- Hover azul palido limitado al cuerpo.
- Grupos de proveedor y subtotales con jerarquia clara.
- Numeros tabulares y alineacion actual preservados.
- Tooltip de `Dias Cob.` y filtros sin cambios funcionales.

## Responsive

En pantallas estrechas los KPI y graficos pasaran a menos columnas, los controles envolveran sus elementos y la tabla mantendra desplazamiento horizontal. No se ocultaran columnas ni datos.

## Restricciones

- No modificar formulas, datos, filtros, ordenamientos ni cantidades de los rankings.
- No agregar dependencias visuales ni fuentes remotas nuevas.
- No eliminar la dependencia existente de Chart.js.
- Mantener sincronizados `generate_html.py` y `outputs/proyeccion.html`.

## Verificacion

- Prueba de regresion para comprobar las clases y variables principales del tema.
- Pruebas funcionales existentes sin errores JavaScript.
- Capturas en escritorio y viewport estrecho.
- Inspeccion visual de contraste, legibilidad, desbordes, tooltips y tabla.
