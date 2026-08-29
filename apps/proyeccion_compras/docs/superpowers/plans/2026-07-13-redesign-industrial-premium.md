# Rediseño industrial premium Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar un sistema visual industrial oscuro con acento azul electrico y tabla clara al reporte HTML completo, preservando toda su funcionalidad.

**Architecture:** El reporte seguira siendo un HTML autocontenido generado por `generate_html.py`. El tema se expresara mediante variables y componentes CSS; una configuracion global de Chart.js alineara ejes, grillas y tooltips con las superficies oscuras.

**Tech Stack:** Python 3, HTML5, CSS, JavaScript, Chart.js y Playwright.

---

### Task 1: Contrato visual automatizado

**Files:**
- Modify: `test_proyeccion.spec.js`

- [ ] Agregar una prueba que compruebe `data-theme="industrial"`, variables `--surface-dark` y `--accent-electric`, fondo oscuro del documento, panel oscuro de graficos, tabla clara y configuracion opaca del tooltip Chart.js.
- [ ] Ejecutar `npx playwright test test_proyeccion.spec.js --reporter=line` y confirmar que falla porque el tema todavia no existe.

### Task 2: Estructura y sistema CSS

**Files:**
- Modify: `generate_html.py`
- Modify: `outputs/proyeccion.html`

- [ ] Agregar `data-theme="industrial"` al documento y reemplazar las variables CSS por la paleta grafito, acero y azul electrico.
- [ ] Rediseñar cabecera, KPI, paneles de graficos, barra de controles y pie manteniendo el mismo DOM funcional.
- [ ] Aplicar el modelo hibrido a la tabla: cabecera oscura, filas claras alternadas, grupos y subtotales jerarquizados y hover solo en `tbody`.
- [ ] Incorporar breakpoints para dos columnas, una columna y scroll horizontal sin ocultar datos.
- [ ] Mantener sincronizados la plantilla y el HTML generado actual.

### Task 3: Integracion visual de Chart.js

**Files:**
- Modify: `generate_html.py`
- Modify: `outputs/proyeccion.html`

- [ ] Definir defaults de Chart.js para texto claro, grillas de bajo contraste y tooltip opaco antes de construir los cinco graficos.
- [ ] Mantener datos, Top, `Resto`, colores por familia y formatos monetarios existentes.

### Task 4: Verificacion funcional y visual

**Files:**
- Test: `test_proyeccion.spec.js`
- Create: `outputs/premium-desktop.png`
- Create: `outputs/premium-mobile.png`

- [ ] Ejecutar `npx playwright test --reporter=line` y exigir cero fallos y cero errores JavaScript.
- [ ] Ejecutar `python -m py_compile generate_html.py`.
- [ ] Capturar el dashboard en 1600 px y 390 px de ancho.
- [ ] Inspeccionar contraste, desbordes, tabla, controles, tooltips y los cinco graficos.
- [ ] Confirmar mediante Playwright que filtros, cantidades Top y barra `Resto` siguen intactos.

> No se incluyen pasos de commit porque `D:\programacion\proyeccion_compras_auto` no es un repositorio Git.
