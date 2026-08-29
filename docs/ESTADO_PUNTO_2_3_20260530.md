# Estado puntos 2 y 3 - 2026-05-30

## Punto 2 - Actualiza Lista Reventa

Activado en Linux:

```cron
*/30 * * * * /home/ferreteria/automatizaciones/jobs/actualiza_lista_reventa.sh
```

Backup previo del crontab:

`/home/ferreteria/automatizaciones/backups/linux/crontab-20260530-before-actualiza-lista-reventa.txt`

Estado de Windows:

- Se intento desactivar la tarea `Actualiza Lista Reventa`.
- Se genero backup XML en `\\192.168.0.195\web\automatizaciones\backups\windows\scheduled-tasks`.
- `Disable-ScheduledTask` fallo con `Acceso denegado`.
- La tarea Windows sigue en estado `Ready`.

Riesgo operativo:

Hasta desactivar la tarea Windows con permisos elevados, puede haber doble ejecucion cada 30 minutos.

Comando pendiente en PowerShell elevado:

```powershell
Disable-ScheduledTask -TaskName "Actualiza Lista Reventa"
```

## Punto 3 - Scripts faltantes de reportes.bat

Portado a Linux bajo:

`/home/ferreteria/automatizaciones/apps/`

Componentes:

- `/home/ferreteria/automatizaciones/apps/reporte_remitos/reporte.py`
- `/home/ferreteria/automatizaciones/apps/informes_diarios/facturas_no_procesadas.py`
- `/home/ferreteria/automatizaciones/apps/exports/scripts/run_all_exports.py`
- todos los `export_*.py` requeridos por `run_all_exports.py`
- `.env` de la automatizacion de exports

Venv propio creado:

`/home/ferreteria/automatizaciones/venv`

Paquetes instalados:

- `mysql-connector-python`
- `pandas`
- `python-dotenv`
- `python-dateutil`

Wrappers creados:

- `/home/ferreteria/automatizaciones/jobs/run_reporte_remitos.sh`
- `/home/ferreteria/automatizaciones/jobs/run_facturas_no_procesadas.sh`
- `/home/ferreteria/automatizaciones/jobs/run_all_exports.sh`
- `/home/ferreteria/automatizaciones/jobs/run_reportes_codigo_barra.sh`

Validaciones realizadas:

- `bash -n` OK para los wrappers.
- `py_compile` OK para `reporte.py`, `facturas_no_procesadas.py`, `run_all_exports.py`.
- `py_compile` OK para todos los `export_*.py`.
- Import OK para `reporte.py` y `facturas_no_procesadas.py` sin ejecutar main ni enviar emails.
- `run_all_exports.py` probado con `DRY_RUN=1`: levanta en Linux, detecta 16 exportadores, no envia email.

Nota sobre `DRY_RUN`:

En dry-run aparecen 2 fallos simulados por el propio script:

- `export_dashboard_ejecutivo.py`
- `export_resumen_cliente_paralelo.py`

Esto no implica que hayan fallado en ejecucion real; el dry-run del script los marca como errores simulados.

Estado de activacion:

`run_reportes_codigo_barra.sh` esta preparado pero no agendado en cron todavia para no duplicar la tarea Windows `Remitos Codigo Barra`.
