# Automatizaciones FASA

Snapshot local de las automatizaciones que estaban en `fasa_195`, preparado para
la migración a `fasa_189`.

## Alcance

Incluye scripts de jobs, aplicaciones Python/JavaScript y documentación operativa.
El snapshot no activa cron, timers ni workers.

## Exclusiones intencionales

- secretos y configuración local (`.env`, claves y certificados);
- `exports/`, logs, locks, `venv/` y caches;
- HTML históricos, `history.json` y capturas generadas;
- resultados de pruebas y dependencias instaladas.

Esos elementos se administran como datos/operación y se migrarán por separado,
solo después de definir retención, destino y validación.

## Próximo paso

Revisar cada job, parametrizar rutas y credenciales mediante variables de entorno,
crear Compose por grupo de servicio y probar manualmente antes de activar una
programación equivalente.
