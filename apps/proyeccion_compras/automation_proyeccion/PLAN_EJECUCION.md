# PLAN DE EJECUCIÓN: Automatización Python de Proyección de Compras

## 1. Resumen del problema

El formulario VFP `proyeccion_compra` (clase en `FASA.VCX`) permite:
1. Seleccionar un proveedor y rango de artículos
2. Calcular proyección de compras basada en historial de 12 meses de movimientos (`movmer`)
3. Aplicar conversiones de unidades (compra vs venta)
4. Descontar stock actual y pedidos pendientes
5. Generar orden de compra sugerida
6. Exportar a Excel e imprimir/email

**Objetivo de la automatización:** Un script Python que corra sin intervención, tome **todos los artículos activos** (no un rango), identifique su **proveedor principal** desde `artpro` o `stock.principal`, calcule la proyección (en unidades de compra, con fórmula de conversión desde `artpro.calculo`) y envíe un email con el resultado.

---

## 2. Arquitectura propuesta

```
automation_proyeccion/
├── config.py                  # Conexión DB, SMTP, parámetros generales
├── db.py                      # Capa de acceso a SQL Server
├── models.py                  # Dataclasses / tipado
├── calculator.py              # Lógica de proyección (el core)
├── mailer.py                  # Envío de email (HTML + adjunto)
├── main.py                    # Entry point / orquestador
├── requirements.txt           # Dependencias Python
├── .env                       # Credenciales (no versionar)
├── .env.template              # Template de credenciales
└── outputs/                   # Archivos generados (Excel, PDF)
```

---

## 3. Dependencias (`requirements.txt`)

```
mysql-connector-python>=9.0.0
pandas>=2.0.0
openpyxl>=3.1.0
python-dotenv>=1.0.0
```

Opcional para futura expansión:
```
smtplib  (stdlib)
email    (stdlib)
```

---

## 4. Configuración (`config.py` + `.env`)

| Variable | Descripción |
|---|---|
| Variable | Descripción |
|---|---|
| `DB_HOST` | Host MySQL |
| `DB_PORT` | Puerto MySQL (default: 3306) |
| `DB_DATABASE` | Base de datos FASA |
| `DB_USERNAME` | Usuario BD |
| `DB_PASSWORD` | Password BD |
| `SMTP_SERVER` | Servidor SMTP |
| `SMTP_PORT` | Puerto SMTP |
| `SMTP_USER` | Usuario SMTP |
| `SMTP_PASSWORD` | Password SMTP |
| `SMTP_FROM` | Email remitente |
| `SMTP_TO` | Email(s) destinatario(s) |
| `PROY_MESES` | Meses a proyectar (default: 3) |
| `EMPRESA_ID` | ID de empresa (default: 1) |
| `EXCEL_OUTPUT_DIR` | Directorio de salida para Excel |

---

## 5. Algoritmo de proyección (core)

### 5.1. Cálculo de fechas (port desde VFP)

```python
def calcular_rango_fechas():
    hoy = date.today()
    if hoy.day < 15:
        desde = date(hoy.year - 1, hoy.month, 1)
        hasta = fin_de_mes(date(hoy.year, hoy.month - 1, 1))  # último día del mes anterior
    else:
        if hoy.month == 12:
            desde = date(hoy.year, 1, 1)
        else:
            desde = date(hoy.year - 1, hoy.month + 1, 1)
        hasta = hoy
    return desde, hasta
```

### 5.2. Obtener artículos activos

```sql
SELECT s.clave, a.disconti, s.principal, s.unidad, s.stock, s.campoa1,
       s.peso, s.espesor, s.mts2, s.admitepedido, s.visible
FROM stock s
INNER JOIN articulo a ON s.clave = a.clave
WHERE s.visible = 'S'
  AND s.admitepedido = 'S'
  AND a.disconti <> 'S'
  AND s.stock > 0
  AND s.empresa_id = 1
```

### 5.3. Obtener proveedor principal por artículo

```python
def proveedor_principal(articulo):
    # 1. Si stock.principal tiene valor -> ese es
    # 2. Sino, de artpro donde es el principal
    # 3. Sino, el primer registro de artpro
    pass
```

### 5.4. Obtener histórico de movimientos (12 meses)

```sql
SELECT articulo, 
       SUM(cantidad) as cantidad, 
       MONTH(fecha) as mes,
       YEAR(fecha) as año
FROM movmer
WHERE fecha >= ? AND fecha <= ?
  AND cliente NOT IN ('', '50000', '00002')
  AND SUBSTRING(comp, 1, 1) <> 'A'
GROUP BY articulo, YEAR(fecha), MONTH(fecha)
```

Ajustar signo: movimientos tipo 'I' con código 'C' o tipo 'I' se multiplican por -1 (son egresos/salidas que deben negarse en la lógica VFP).

### 5.5. Calcular proyección por artículo

```python
def calcular_proyeccion(articulo, movimientos_12meses, meses_proyectar):
    # promedio mensual = suma de cantidades / 12
    promedio_mensual = sum(movimientos_12meses) / 12
    
    # proyección = promedio_mensual * meses_proyectar
    proyeccion = promedio_mensual * meses_proyectar
    
    # Descontar stock actual
    proyeccion -= stock_actual
    
    # Descontar pedidos pendientes (pedpro con saldo > 0)
    proyeccion -= saldo_pedidos_pendientes
    
    return max(0, proyeccion)
```

### 5.6. Conversión de unidades (por `campoa1`)

**Modo: Unidades de compra (`chkStVta = False`)** — se aplica `artpro.calculo` como fórmula de conversión evaluable sobre el resultado.

| `campoa1` | Significado | Fórmula VFP |
|---|---|---|
| `'C'` | Piezas/KG | `stock_a = stock * peso` |
| `'M'` | Metro lineal | `stock_a = stock / peso` |
| `'S'` | Metro cuadrado | `stock_a = stock / (espesor * 8)` |
| `'A'` | Área | `stock_a = stock / mts2` |

Tanto `stock_a` como `promedio_a` se calculan con estas fórmulas. Luego la proyección final es:

```python
proyeccion = promedmens * meses_proyectar
# Si artpro.calculo tiene una fórmula (ej: "* 1.05 + 10"), se evalúa:
if artpro.calculo:
    resultado_bruto = promedmens * meses_proyectar
    proyeccion = eval(f"{resultado_bruto} {artpro.calculo}")
```

---

## 6. Agrupación por proveedor

Cada artículo tiene asignado un proveedor principal. El resultado se agrupa así:

```python
{
    "proveedor_001": {
        "nombre": "...",
        "articulos": [
            {"codigo": "...", "detalle": "...", "proyeccion": 100, "unidad": "..."},
        ],
        "total_proveedor": ...
    },
    ...
}
```

---

## 7. Generación de reporte

### 7.1. Excel (por proveedor)

Un archivo Excel con tantas hojas como proveedores, más un resumen general:

- **Hoja "Resumen"**: Tabla con proveedor, cant. artículos, total proyectado
- **Hoja por proveedor**: Código, detalle, unidad, stock, promedio mensual, proyección, pedido sugerido

### 7.2. Cuerpo del email (HTML)

Tabla resumen con:
- Proveedor
- Cantidad de artículos
- Stock actual total
- Proyección total
- Pedido sugerido total

---

## 8. Flujo del orquestador (`main.py`)

```
1. Cargar configuración
2. Conectar a SQL Server
3. Calcular rango de fechas (12 meses)
4. Obtener todos los artículos activos con stock > 0 y admitepedido = 'S'
5. Para cada artículo:
   a. Determinar proveedor principal
   b. Obtener movimientos de 12 meses
   c. Calcular promedio mensual
   d. Calcular proyección bruta
   e. Descontar stock actual
   f. Descontar pedidos pendientes
   g. Aplicar conversión de unidades si corresponde
6. Agrupar resultados por proveedor
7. Generar Excel con hojas por proveedor + resumen
8. Enviar email con resumen HTML + Excel adjunto
9. Log de resultados
```

---

## 9. Consideraciones de implementación

### 9.1. Manejo de errores
- Si un artículo no tiene proveedor principal asignado, loguear warning y saltar
- Si no hay movimientos para un artículo, proyección = 0
- Si falla la conexión a DB, abortar con error claro
- Capturar errores por artículo sin abortar todo el proceso

### 9.2. Performance
- Los artículos pueden ser miles. No hacer una consulta SQL por artículo.
- Estrategia: traer TODOS los movimientos agrupados por artículo en una sola query y procesar en memoria con pandas
- Traer stock y pedpro en bloque, mergear con pandas

### 9.3. Seguridad
- Credenciales en `.env`, nunca en código
- `.env` en `.gitignore`
- No exponer datos de producción en logs

### 9.4. Idempotencia
- Si el script se ejecuta dos veces el mismo día, debe producir el mismo resultado
- Los registros se leen, no se escriben (solo lectura de la BD)

---

## 10. Tareas de implementación (orden sugerido)

| # | Tarea | Descripción | Depende de |
|---|---|---|---|
| 1 | `config.py` + `.env.template` | Variables de entorno, carga con `python-dotenv` | - |
| 2 | `db.py` | Conexión MySQL (`mysql.connector`), funciones de query helper | 1 |
| 3 | `models.py` | Dataclasses: `Articulo`, `Movimiento`, `Proveedor`, `ProyeccionResultado` | - |
| 4 | `calculator.py` | Core: `calcular_rango_fechas()`, `calcular_proyeccion()`, agrupación | 2, 3 |
| 5 | `main.py` | Orquestador: loader + calculator + Excel output | 4 |
| 6 | `mailer.py` | Construcción HTML + envío SMTP con adjunto | 1 |
| 7 | Integración `main.py` + `mailer.py` | Pipeline completo | 5, 6 |
| 8 | Logging | stdout + archivo de log | 5 |
| 9 | Pruebas con datos reales o sanitizados | Verificar contra resultados VFP conocidos | 7 |
| 10 | Documentación y cleanup | README del módulo | 9 |

---

## 11. Tablas MySQL involucradas

| Tabla | Uso | Campos clave |
|---|---|---|
| `stock` | Stock actual, unidad, flags | `clave`, `stock`, `principal`, `unidad`, `campoa1`, `peso`, `espesor`, `mts2`, `admitepedido`, `visible`, `empresa_id` (filtro = 1) |
| `articulo` | Artículos, flag discontinuado | `clave`, `disconti` |
| `artpro` | Relación artículo-proveedor, precio, fórmula conversión | `articulo`, `proveedo`, `calculo`, `total`, `parcial2`, `moneda`, `codigo` |
| `movmer` | Historial de movimientos (12 meses) | `articulo`, `fecha`, `cantidad`, `tipo`, `codigo`, `comp`, `cliente` |
| `pedpro` | Pedidos pendientes | `articulo`, `saldo`, `periodo` |
| `proveedo` | Maestro proveedores | `proveedo`, `nombre`, `nped` |
| `ProyCompra` | Proyecciones guardadas (solo lectura, opcional) | `proveedor`, `articulo`, `pedido`, `estado` |

---

## 12. Notas importantes (lecciones del VFP)

1. **Fechas**: El VFP calcula el rango dependiendo de si hoy es antes o después del día 15. Esto afecta qué 12 meses se toman.
2. **Signo de movimientos**: Los egresos se niegan con `cantidad * -1` cuando (`tipo='I' AND codigo='C'`) o (`tipo='I'`).
3. **Clientes excluidos**: `'50000'`, `'00002'` y string vacío se excluyen de movimientos.
4. **Comprobantes tipo 'A'** (Ferretería Avenida) se excluyen de movimientos.
5. **Unidad de compra vs venta**: Si `campoa1` es 'C', 'M', 'S' o 'A', hay conversiones específicas (ver sección 5.6).
6. **Artículos discontinuados**: `disconti = 'S'` → proyección = 0.
7. **Pedidos pendientes**: Se descuentan de la proyección (campo `saldopedido`).
8. **ProyCompra**: Si ya existe una proyección guardada en estado 'P', se puede cargar como valor inicial de `pedareal`.
9. **Cálculo de costo**: Usa `artpro.total` con conversión de moneda (USD a ARS si aplica) y aplica `artpro.calculo` como fórmula evaluable.
10. **Empresa**: En la versión más nueva del class, se filtra por `empresa_id = ?goApp.Empresa`.

---

## 13. Próximos pasos

1. Confirmar acceso a la base MySQL (host, puerto, credenciales, BD)
2. Confirmar configuración SMTP
3. Definir si se incluye la lógica de costo (cotización USD) o solo proyección de cantidades
4. Definir asunto y frecuencia del email (los destinatarios van en `.env`)
