# Activacion completa Linux - 2026-05-30

## Activado en cron Linux

Se activo `reportes_codigo_barra` en Linux:

```cron
05 19 * * * /home/ferreteria/automatizaciones/jobs/run_reportes_codigo_barra.sh
```

Backup previo del crontab:

`/home/ferreteria/automatizaciones/backups/linux/crontab-20260530-before-reportes-codigo-barra.txt`

Tambien siguen activos en Linux:

```cron
0 * * * * /home/ferreteria/automatizaciones/jobs/monitor_puerto_3050.sh
*/30 * * * * /home/ferreteria/automatizaciones/jobs/actualiza_lista_reventa.sh
```

## Verificacion Linux

- No quedan lineas directas en crontab fuera de `/home/ferreteria/automatizaciones/jobs/`.
- `bash -n` OK para wrappers principales.
- `py_compile` OK para `reporte.py`, `facturas_no_procesadas.py`, `run_all_exports.py` y todos los `export_*.py`.
- Import OK para `reporte.py` y `facturas_no_procesadas.py`.
- `run_all_exports.py` ejecutado en `DRY_RUN=1`: no envio email y genero preview HTML.

Nota: el `DRY_RUN` sigue marcando 2 fallos simulados por el propio script: `export_dashboard_ejecutivo.py` y `export_resumen_cliente_paralelo.py`.

## Estado Windows

- `Actualiza Lista Reventa`: Disabled.
- `Monitor Puerto 3050 suevos`: Disabled.
- `Remitos Codigo Barra`: Ready.

Se intento desactivar `Remitos Codigo Barra` con `Disable-ScheduledTask` y con `schtasks /Change /DISABLE`, ambos fallaron con `Acceso denegado`.

Riesgo: si no se desactiva con permisos elevados antes de las 19:05, puede correr duplicado junto con Linux.

Comando pendiente en PowerShell elevado:

```powershell
Disable-ScheduledTask -TaskName "Remitos Codigo Barra"
```
