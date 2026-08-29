# Graficos Top + Resto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conservar el Top actual de los cinco graficos y agregar una barra `Resto` con la suma exacta de los elementos excluidos.

**Architecture:** Incorporar una funcion JavaScript pura `topNConResto` dentro del HTML autocontenido. Los cinco graficos preparan una metrica numerica uniforme, consumen esa funcion y mantienen sus formatos actuales.

**Tech Stack:** Python 3, HTML/JavaScript, Chart.js, Playwright.

---

### Task 1: Prueba de regresion

**Files:**
- Modify: `test_proyeccion.spec.js`

- [ ] **Step 1: Escribir una prueba fallida para Top + Resto**

La prueba abre `outputs/proyeccion.html`, obtiene las cinco instancias Chart.js y verifica para cada una que exista la etiqueta `Resto` y que la suma de sus barras coincida con el total calculado desde `DATA`. Tambien ejecuta `topNConResto` con una coleccion menor al limite y comprueba que no agregue `Resto`.

- [ ] **Step 2: Confirmar el fallo esperado**

Run: `npx playwright test test_proyeccion.spec.js --reporter=line`

Expected: FAIL porque `topNConResto` no existe o ninguna serie contiene `Resto`.

### Task 2: Funcion comun y adopcion en los cinco graficos

**Files:**
- Modify: `generate_html.py`
- Modify: `outputs/proyeccion.html`

- [ ] **Step 1: Implementar la funcion pura**

```javascript
function topNConResto(arr, valueFn, n) {
  const sorted = arr.map((item, index) => ({ item, index, value: Number(valueFn(item)) || 0 }))
    .sort((a, b) => b.value - a.value || a.index - b.index);
  const top = sorted.slice(0, n);
  const resto = sorted.slice(n).reduce((sum, entry) => sum + entry.value, 0);
  const result = top.reverse();
  if (sorted.length > n) result.unshift({ item: null, value: resto, label: 'Resto' });
  return result;
}
```

- [ ] **Step 2: Adaptar proveedores**

Usar `topNConResto` con limites de 15 y las metricas `total_pedido_sugerido`, `total_costo_pedido` y `total_stock`. La etiqueta sintetica es `Resto`; las demas usan `codigo`.

- [ ] **Step 3: Adaptar articulos**

Usar limite 20 para `pedido_sugerido` y para `pedido_sugerido * costo_unitario`. La etiqueta sintetica es `Resto`; las demas conservan articulo y detalle.

- [ ] **Step 4: Aplicar el mismo cambio al HTML generado actual**

Mantener `outputs/proyeccion.html` sincronizado con la plantilla para que la verificacion y el archivo entregable reflejen el cambio sin consultar la base de datos.

- [ ] **Step 5: Ejecutar la prueba completa**

Run: `npx playwright test --reporter=line`

Expected: PASS, una prueba aprobada y sin errores JavaScript.

### Task 3: Auditoria final

**Files:**
- Inspect: `generate_html.py`
- Inspect: `outputs/proyeccion.html`
- Inspect: `test_proyeccion.spec.js`

- [ ] **Step 1: Verificar invariantes numericas en navegador**

Confirmar que cada grafico contiene su Top mas `Resto`, que `Resto` aparece solo cuando hay excluidos y que la suma de barras coincide con el total original dentro de una tolerancia de redondeo de 0,01 por barra.

- [ ] **Step 2: Verificar alcance**

Confirmar que no cambiaron calculos de proyeccion, stock, pedidos, costos, cantidades del Top, colores, titulos ni filtros.

> Nota: los pasos de commit se omiten porque `D:\programacion\proyeccion_compras_auto` no es un repositorio Git.
