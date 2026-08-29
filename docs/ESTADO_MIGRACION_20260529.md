# Estado migracion automatizaciones - 2026-05-29

## Raiz operativa Linux

Se usa `/home/ferreteria/automatizaciones` como raiz ejecutable porque `/var/www/html/automatizaciones` pertenece a `administracion:administracion` y el usuario cron `ferreteria` no puede escribir logs ni locks ahi.

La carpeta web `/var/www/html/automatizaciones` queda como copia visible/documental hasta corregir permisos.

## Migrado y activo en cron Linux

Todos los comandos existentes del crontab Linux quedaron centralizados bajo:

`/home/ferreteria/automatizaciones/jobs/`

Wrapper generico:

`/home/ferreteria/automatizaciones/jobs/run_job.sh`

Este wrapper agrega:

- log por job en `/home/ferreteria/automatizaciones/logs/linux/<job_id>/`
- lock por job en `/home/ferreteria/automatizaciones/locks/<job_id>.lock`
- timestamp de inicio y fin
- codigo de salida
- retencion simple de logs por 30 dias

Jobs activos migrados:

- resguardo_alldb
- resguardo_alldbserver_2030
- resguardo_alldbserver_1230
- resguardo_alldbdattatec
- resguardo_alldbfelix
- resguardo_backupfolder
- resguardo_backupapps
- resguardo_backupdocumentos
- resguardo_alldattatec
- stock_py_0830
- stock_py_1230
- backup_db
- ventas_diarias
- sales_dashboard_weekday_monthly_emp1
- sales_dashboard_weekday_monthly_emp2
- sales_dashboard_weekday_monthly_emp3
- sales_dashboard_weekday_daily_emp1
- sales_dashboard_weekday_daily_emp2_chmod
- sales_dashboard_saturday_daily_emp1
- sales_dashboard_saturday_daily_emp2
- sales_dashboard_saturday_monthly_emp1
- sales_dashboard_saturday_monthly_emp2
- sales_dashboard_saturday_monthly_emp3
- cron_envio_compensables
- enviar_ofertas
- envio_resumen_ctacte_vencidas
- envio_resumen_ctacte_primer_vencimiento
- envio_resumen_ctacte_vencimiento_final
- viajesfg_daily_log_summary
- monitor_puerto_3050

## Preparado pero no activo en cron

### actualiza_lista_reventa

Wrapper preparado:

`/home/ferreteria/automatizaciones/jobs/actualiza_lista_reventa.sh`

Motivo de no activacion automatica:

La tarea Windows `Actualiza Lista Reventa` sigue activa cada 30 minutos. Activarla tambien en Linux puede duplicar escrituras contra la base de reventa.

Cambios realizados:

- Se subio a Linux la version corregida de `/var/www/html/utiles/ActualizaListaReventa.py`.
- Se guardo backup previo en `/home/ferreteria/automatizaciones/backups/linux/utiles/`.
- Se valido `py_compile` del script Python.
- Se valido sintaxis Bash del wrapper.

## Alertas

### Permisos de carpeta web

`/var/www/html/automatizaciones` no es writable por `ferreteria`.

Recomendado:

```bash
sudo setfacl -R -m u:ferreteria:rwx /var/www/html/automatizaciones
sudo setfacl -R -d -m u:ferreteria:rwx /var/www/html/automatizaciones
```

### SalesDashboard con sudo chmod

El job `sales_dashboard_weekday_daily_emp2_chmod` conserva el comando anterior:

`sudo chmod 777 /var/www/html/informes -R`

Como `ferreteria` no tiene sudo no-interactivo, esa parte probablemente ya fallaba en cron. Conviene resolver permisos de `/var/www/html/informes` y quitar ese sudo.

### Windows queda como backup temporal

No se desactivaron tareas Windows ni se modifico `C:\fasa`.

## Backups creados

Backups de crontab:

- `/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2031-before-monitor-puerto-3050.txt`
- `/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2044-before-stock-wrapper.txt`
- `/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2048-before-0200-wrapper.txt`
- `/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2052-before-salesdashboard-wrapper.txt`
- `/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2056-before-utiles-viajes-wrapper.txt`
- `/home/ferreteria/automatizaciones/backups/linux/crontab-20260529-2059-before-resguardos-wrapper.txt`

Backup de script:

- `/home/ferreteria/automatizaciones/backups/linux/utiles/ActualizaListaReventa.py.20260529-2036-before-migration`

## Pendiente

- Decidir si se activa `actualiza_lista_reventa` en Linux y luego se desactiva la tarea Windows.
- Portar scripts faltantes de `reportes.bat`: `reporte.py`, `facturas_no_procesadas.py`, `run_all_exports.py`.
- Resolver permisos de `/var/www/html/automatizaciones` para usar esa carpeta web como raiz ejecutable unica, si se mantiene ese objetivo.
- Resolver el `sudo chmod` de SalesDashboard.
