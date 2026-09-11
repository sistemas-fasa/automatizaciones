# Operativa cron 19:15 + reportes FASA (2026-09-11)

## Qué se arregló hoy
1. **19:15 sin correo (incidente 09-10/09):** los jobs del scheduler no se dispararon esa
   tarde. El cron del container está vivo ahora y hay red de seguridad con el
   resumen diario de las 07:30 (`resumen_diario_automatizaciones`, OK/FALLIDAS por mail).
2. **Script viejo eliminado:** se borró `apps/dashboard/envia_mail.py` (junio 2025, sin link,
   con `smtplib.SMTP` plano al puerto 465 que se colgaba y nunca enviaba). Queda solo
   `apps/dashboard/SalesDashboard.py` + `EmailSender.py` (con link a informes y SMTP_SSL).
3. **Servidor 195 eliminado del código:** `SalesDashboard.py` y `enviar_reporte_inflacion.py`
   publicaban en `\\192.168.0.195\web\informes` (no existe más). Ahora publican en
   `/srv/fasa-data/data/informes` (en el container vale `/var/www/html/informes` por mount).
4. **Proyección de compras:** `mailer.py` usaba STARTTLS incondicional (rompe contra 465);
   ahora usa SMTP_SSL en 465. Se creó su `.env` (git-ignored) y publica en
   `informes/proyeccion-compras`. Destinatarios: compras@, luis@, oscar@ferreteriaavenida.com.ar.
5. **Reporte de remitos:** alta nueva. Todos los días 19:15 a sistemas@ferreteriaavenida.com.ar.
   Env en volumen de datos: `/srv/fasa-data/data/automatizaciones/env/reporte-remitos.env`
   (visible en el container como `/data/env/reporte-remitos.env`; sobrevive recreates).

## Dónde corre cada cosa (única fuente: scheduler Docker `automatizaciones-scheduler`)
| Job | Cron | Comando |
|---|---|---|
| Dashboard daily emp1/emp2 + monthly emp1/2/3 | `15 19 * * 1-5` | `SalesDashboard.py --daily/--monthly --empresa-id=N` |
| Dashboard daily emp1/2 + monthly emp1/2/3 | `15 12 * * 6` | idem (sábado) |
| Reporte remitos | `15 19 * * *` | `apps/reporte_remitos/reporte.py` |
| Proyección compras | `30 5 * * 1-5` | `apps/proyeccion_compras/deploy/run_weekly_projection.sh` |
| Útiles (compensables, ofertas, ctacte x3) | `0 6 ...` | `run_utiles_job.189.sh ...` |
| Reventa, código_barra, monitor 3050, ventas_diarias, cumpleaños, facturas, resumen | varios | ver `/etc/cron.d/automatizaciones` del container |

NO duplicar estos horarios en el crontab del usuario: el 11/09 se quitaron los duplicados
(`fasa-dashboard-1915.sh`, proyección weekly) para evitar mails dobles.

## Secrets (fuera de git, solo servidor)
- Scheduler: `/srv/env/*.env` → `/run/secrets/*.env` (+ reporte-remitos en `/data/env/`).
- Copias de trabajo locales `apps/dashboard/.env` y `apps/proyeccion_compras/.env`: git-ignored.

## Si el container se recrea
Las líneas de `/etc/cron.d/automatizaciones` son edición en vivo: re-agregar la de remitos:
`15 19 * * * root JOB_NAME=reporte_remitos JOB_TIMEOUT_SECONDS=3600 JOB_COMMAND='set -a; . /data/env/reporte-remitos.env; set +a; cd /opt/automatizaciones/apps/reporte_remitos && python3 reporte.py' JOB_LOCK_FILE=/data/locks/reporte_remitos_cron.lock /usr/local/bin/automatizaciones-runner >> /data/logs/linux/reporte_remitos/cron.log 2>&1`
y `mkdir -p /data/logs/linux/reporte_remitos` (el entrypoint crea el resto desde el cron).

## Pendientes 195 (bloqueados)
- `descuentos`: app `export_actualizar_descuentos` inexistente (solo corrida manual 31/08).
- `backup_fg_db`: requiere `/srv/env/registro_produccion/mavis_ro.env` (solo root, sin validar).
- Resguardos `/media/discoh`: reemplazados por `mysql-central-backup` + `mysql-containers-backup`.
- `viajesfg` log diario: vive en otro compose.
