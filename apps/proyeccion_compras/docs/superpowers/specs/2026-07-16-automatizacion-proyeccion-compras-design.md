# Automatización semanal de proyección de compras

## Objetivo

Ejecutar automáticamente la proyección de compras cada lunes antes del inicio de la jornada, publicar el resultado en `informes.ferreteriaavenida.com.ar` y enviarlo por correo electrónico a las personas responsables de compras.

## Alcance

La automatización se ejecutará en `fasa_195` todos los lunes a las 05:30, usando la zona horaria `America/Argentina/Buenos_Aires`.

Cada ejecución deberá:

1. Consultar los datos requeridos por el cálculo de proyección.
2. Generar el informe HTML completo.
3. Validar que el archivo generado sea utilizable antes de publicarlo.
4. Conservar una copia histórica fechada.
5. Actualizar de forma atómica el informe vigente.
6. Enviar un correo con el enlace público y el HTML adjunto.

No se modificará Nginx porque el dominio ya publica el contenido de `/var/www/html/informes`.

## Arquitectura

La copia operativa de la aplicación residirá en:

`/home/ferreteria/automatizaciones/apps/proyeccion_compras`

Un wrapper específico ejecutará el generador desde el entorno Python del servidor. La entrada de `cron` llamará al wrapper general existente `run_job.sh`, que aportará bloqueo contra ejecuciones simultáneas, identificación del trabajo y registro operativo uniforme.

Los artefactos públicos residirán en:

`/var/www/html/informes/proyeccion-compras`

La URL estable será:

`https://informes.ferreteriaavenida.com.ar/proyeccion-compras/`

El archivo `index.html` representará siempre el último informe publicado correctamente. Cada ejecución conservará además una copia histórica con fecha y hora en el nombre.

## Flujo de datos

1. `cron` inicia el trabajo los lunes a las 05:30.
2. `run_job.sh` adquiere el bloqueo y abre el log correspondiente.
3. El wrapper carga la configuración privada desde un archivo de entorno con permisos restringidos.
4. La aplicación calcula la proyección y escribe el HTML en un directorio temporal de la misma máquina.
5. El wrapper verifica que el archivo exista, tenga contenido, incluya la estructura HTML esperada y contenga los datos embebidos del informe.
6. El archivo validado se copia con nombre histórico.
7. La actualización de `index.html` se realiza mediante reemplazo atómico para evitar que el sitio entregue un archivo parcial.
8. Se envía un único correo a ambos destinatarios con el enlace público y el mismo HTML como adjunto.
9. El proceso registra el resultado y libera el bloqueo.

## Correo electrónico

Destinatarios obligatorios:

- `luis@ferreteriaavenida.com.ar`
- `compras@ferreteriaavenida.com.ar`

El mensaje incluirá:

- asunto que identifique la proyección semanal y la fecha de generación;
- enlace a la URL estable del informe;
- indicación de que el informe corresponde a la planificación semanal;
- archivo HTML adjunto con el mismo contenido publicado.

Las credenciales SMTP no se incorporarán al código ni al repositorio. Se cargarán desde la configuración privada del servidor, reutilizando el mecanismo operativo vigente cuando sea compatible.

Antes de habilitar los destinatarios obligatorios se realizará una ejecución de aceptación en modo prueba. Esa ejecución enviará exclusivamente a `oscarvogel@gmail.com`, aunque la configuración productiva ya exista en el servidor. El cambio a los destinatarios definitivos será explícito y posterior a la confirmación del correo de prueba.

## Manejo de errores

Una ejecución fallida no debe reemplazar el último informe válido.

Si falla la conexión de datos, el cálculo, la generación o la validación:

- el proceso terminará con código distinto de cero;
- no se publicará un archivo nuevo;
- no se enviará el correo normal;
- el informe anterior seguirá disponible;
- el detalle quedará registrado en el log del trabajo.

Si la publicación termina correctamente pero falla el correo, el informe permanecerá publicado y el proceso devolverá error para que el problema sea visible en los logs. Una repetición manual deberá evitar sobrescribir incorrectamente el histórico y podrá volver a enviar el correo de esa ejecución.

## Seguridad y operación

- Los secretos se mantendrán fuera de Git y con permisos mínimos en el servidor.
- El trabajo se ejecutará como el usuario operativo `ferreteria`.
- No se imprimirán contraseñas ni cadenas de conexión en los logs.
- La publicación se realizará únicamente dentro de `/var/www/html/informes/proyeccion-compras`.
- El wrapper usará rutas absolutas para que su comportamiento no dependa del directorio actual de `cron`.

## Verificación y aceptación

La implementación se considerará lista cuando se demuestre lo siguiente:

1. El cálculo y la generación se ejecutan correctamente en `fasa_195`.
2. Una ejecución manual controlada produce un HTML válido.
3. La URL pública responde por HTTPS con el informe generado.
4. `index.html` y el archivo histórico publicado representan el mismo contenido.
5. Los dos destinatarios reciben un correo real con el enlace y el HTML adjunto.
6. La entrada de `cron` queda instalada para los lunes a las 05:30, hora Argentina.
7. El trabajo deja logs y usa un bloqueo compatible con las automatizaciones existentes.
8. Una falla simulada no reemplaza el último informe válido ni envía el correo normal.
9. El primer envío real se limita a `oscarvogel@gmail.com` y no contacta a los destinatarios productivos hasta recibir aprobación explícita.

## Fuera de alcance

- Cambios de diseño o de lógica de cálculo del informe actual.
- Cambios en Nginx, DNS o certificados TLS.
- Desarrollo de un panel de administración para configurar el horario o los destinatarios.
- Eliminación automática de informes históricos; se evaluará por separado si el volumen futuro lo requiere.
