# Automatización semanal de proyección de compras Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar, publicar y enviar semanalmente la proyección de compras desde `fasa_195`, con una primera prueba aislada a `oscarvogel@gmail.com`.

**Architecture:** El generador expondrá una función reutilizable que escriba el HTML en una ruta indicada. Un orquestador semanal validará el artefacto, lo publicará de forma atómica, conservará un histórico y enviará el correo con enlace y adjunto. El servidor ejecutará el orquestador mediante el wrapper `run_job.sh` y `cron`, manteniendo secretos y selección de destinatarios fuera de Git.

**Tech Stack:** Python 3.12, mysql-connector-python, python-dotenv, smtplib, pytest/unittest.mock, Bash, cron, Nginx estático.

---

## Estructura de archivos

- Modificar `generate_html.py`: separar la construcción y escritura del HTML de la entrada CLI.
- Modificar `config.py`: incorporar URL pública y destinatarios semanales configurables.
- Modificar `mailer.py`: enviar el informe publicado como enlace y archivo HTML adjunto.
- Crear `weekly_job.py`: validar, publicar atómicamente, conservar histórico y coordinar el correo.
- Crear `test_weekly_job.py`: cubrir publicación, fallos y aislamiento de destinatarios.
- Crear `deploy/run_weekly_projection.sh`: cargar el entorno privado y ejecutar el trabajo con rutas absolutas.
- Crear `deploy/install_weekly_projection.sh`: instalar o actualizar de manera idempotente la entrada de cron.

### Task 1: Hacer reutilizable el generador HTML

**Files:**
- Modify: `generate_html.py`
- Test: `test_weekly_job.py`

- [ ] **Step 1: Escribir una prueba que exija una función de generación con ruta explícita**

```python
from pathlib import Path
from unittest.mock import patch

import generate_html


def test_generate_report_writes_requested_path(tmp_path):
    destination = tmp_path / "report.html"
    with (
        patch.object(generate_html, "calcular_proyecciones", return_value=[object()]),
        patch.object(generate_html, "serialize_data", return_value=[]),
        patch.object(generate_html, "obtener_tipo_cambio", return_value=1.0),
    ):
        result = generate_html.generate_report(destination)

    assert result == destination
    assert destination.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
```

- [ ] **Step 2: Ejecutar la prueba y comprobar que falla por la función inexistente**

Run: `python -m pytest test_weekly_job.py::test_generate_report_writes_requested_path -v`

Expected: `FAIL` o error de colección indicando que `generate_report` no existe.

- [ ] **Step 3: Extraer la función reutilizable**

Cambiar la firma de generación a:

```python
def generate_report(output_path: str | Path) -> Path:
    output_path = Path(output_path)
    resumenes = calcular_proyecciones()
    if not resumenes:
        raise RuntimeError("No se generaron proyecciones")

    data = serialize_data(resumenes)
    json_data = json.dumps(data, ensure_ascii=False)
    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    tc = obtener_tipo_cambio()
    html = build_report_document(json_data, fecha_gen, tc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main():
    output_path = Path(cfg.excel_output_dir) / "proyeccion.html"
    generated = generate_report(output_path)
    logger.info("HTML generado: %s", generated.resolve())
    print(f"\nAbre el archivo en tu navegador:\n  file:///{generated.resolve().as_posix()}\n")
```

Mover la plantilla actual sin cambios funcionales a `build_report_document(json_data: str, fecha_gen: str, tc: float) -> str`.

- [ ] **Step 4: Ejecutar la prueba y la suite existente**

Run: `python -m pytest test_weekly_job.py::test_generate_report_writes_requested_path test_calculator.py -v`

Expected: todas las pruebas seleccionadas en `PASS`.

- [ ] **Step 5: Confirmar que la generación CLI mantiene el contrato actual**

Run: `python generate_html.py`

Expected: salida `HTML generado:` y archivo `outputs/proyeccion.html` con tamaño mayor que cero.

- [ ] **Step 6: Commit**

```bash
git add generate_html.py test_weekly_job.py
git commit -m "refactor: exponer generador de proyeccion html"
```

### Task 2: Incorporar correo semanal con enlace y HTML adjunto

**Files:**
- Modify: `config.py`
- Modify: `mailer.py`
- Test: `test_weekly_job.py`

- [ ] **Step 1: Escribir pruebas para destinatarios explícitos y adjunto HTML**

```python
from unittest.mock import MagicMock, patch

from mailer import send_report_email


def test_send_report_email_uses_only_explicit_recipients(tmp_path):
    report = tmp_path / "index.html"
    report.write_text("<!DOCTYPE html><html></html>", encoding="utf-8")

    smtp = MagicMock()
    with patch("mailer.smtplib.SMTP", return_value=smtp):
        send_report_email(
            report_path=report,
            public_url="https://informes.ferreteriaavenida.com.ar/proyeccion-compras/",
            recipients=["oscarvogel@gmail.com"],
        )

    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "oscarvogel@gmail.com"
    assert "luis@ferreteriaavenida.com.ar" not in message.as_string()
    assert "compras@ferreteriaavenida.com.ar" not in message.as_string()
    assert 'filename="proyeccion-compras.html"' in message.as_string()
```

- [ ] **Step 2: Ejecutar la prueba y comprobar el fallo inicial**

Run: `python -m pytest test_weekly_job.py::test_send_report_email_uses_only_explicit_recipients -v`

Expected: `FAIL` porque `send_report_email` todavía no existe.

- [ ] **Step 3: Agregar configuración sin secretos al objeto Config**

```python
report_public_url: str = field(
    default_factory=lambda: os.getenv(
        "REPORT_PUBLIC_URL",
        "https://informes.ferreteriaavenida.com.ar/proyeccion-compras/",
    )
)
report_recipients: str = field(
    default_factory=lambda: os.getenv(
        "REPORT_RECIPIENTS",
        "luis@ferreteriaavenida.com.ar,compras@ferreteriaavenida.com.ar",
    )
)

@property
def report_recipient_list(self) -> list[str]:
    return [value.strip() for value in self.report_recipients.split(",") if value.strip()]
```

- [ ] **Step 4: Implementar el correo específico del informe**

```python
def send_report_email(
    report_path: str | Path,
    public_url: str,
    recipients: list[str],
) -> None:
    path = Path(report_path)
    if not recipients:
        raise ValueError("No hay destinatarios configurados")
    if not path.is_file():
        raise FileNotFoundError(path)

    msg = MIMEMultipart()
    msg["From"] = cfg.smtp_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"Proyección semanal de compras - {datetime.now():%d/%m/%Y}"
    body = (
        "<p>La proyección semanal de compras ya está disponible.</p>"
        f'<p><a href="{public_url}">Abrir informe publicado</a></p>'
        "<p>También se adjunta una copia HTML.</p>"
    )
    msg.attach(MIMEText(body, "html", "utf-8"))

    attachment = MIMEBase("text", "html")
    attachment.set_payload(path.read_bytes())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        'attachment; filename="proyeccion-compras.html"',
    )
    msg.attach(attachment)

    with smtplib.SMTP(cfg.smtp_server, cfg.smtp_port) as server:
        server.starttls()
        if cfg.smtp_user:
            server.login(cfg.smtp_user, cfg.smtp_password)
        server.send_message(msg)
```

Agregar `from datetime import datetime` en `mailer.py`.

- [ ] **Step 5: Ejecutar la prueba**

Run: `python -m pytest test_weekly_job.py::test_send_report_email_uses_only_explicit_recipients -v`

Expected: `PASS`.

- [ ] **Step 6: Commit**

```bash
git add config.py mailer.py test_weekly_job.py
git commit -m "feat: enviar proyeccion semanal con enlace y adjunto"
```

### Task 3: Publicar de forma atómica y preservar el informe anterior ante fallos

**Files:**
- Create: `weekly_job.py`
- Modify: `test_weekly_job.py`

- [ ] **Step 1: Escribir pruebas de publicación e invariantes de fallo**

```python
from unittest.mock import patch

import pytest
import weekly_job


def test_publish_report_creates_index_and_history(tmp_path):
    generated = tmp_path / "generated.html"
    generated.write_text("<!DOCTYPE html><html><script>const DATA = [];</script></html>", encoding="utf-8")
    public_dir = tmp_path / "public"

    index_path, history_path = weekly_job.publish_report(generated, public_dir)

    assert index_path.read_bytes() == generated.read_bytes()
    assert history_path.read_bytes() == generated.read_bytes()
    assert history_path.name.startswith("proyeccion-compras-")


def test_invalid_generation_does_not_replace_current_report(tmp_path):
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    current = public_dir / "index.html"
    current.write_text("informe anterior", encoding="utf-8")
    invalid = tmp_path / "invalid.html"
    invalid.write_text("archivo incompleto", encoding="utf-8")

    with pytest.raises(ValueError):
        weekly_job.publish_report(invalid, public_dir)

    assert current.read_text(encoding="utf-8") == "informe anterior"
```

- [ ] **Step 2: Ejecutar las pruebas y comprobar el fallo inicial**

Run: `python -m pytest test_weekly_job.py::test_publish_report_creates_index_and_history test_weekly_job.py::test_invalid_generation_does_not_replace_current_report -v`

Expected: `FAIL` porque `weekly_job.py` no existe.

- [ ] **Step 3: Implementar validación y publicación atómica**

```python
from __future__ import annotations

import argparse
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

from config import cfg
from generate_html import generate_report
from mailer import send_report_email

logger = logging.getLogger("weekly_job")


def validate_report(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required = ("<!DOCTYPE html>", "const DATA", "</html>")
    missing = [marker for marker in required if marker not in text]
    if path.stat().st_size < 10_000 or missing:
        raise ValueError(f"Informe inválido; faltan marcadores: {missing}")


def publish_report(generated: Path, public_dir: Path) -> tuple[Path, Path]:
    validate_report(generated)
    public_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    history_path = public_dir / f"proyeccion-compras-{stamp}.html"
    history_path.write_bytes(generated.read_bytes())

    index_path = public_dir / "index.html"
    temporary = public_dir / f".index-{os.getpid()}.tmp"
    temporary.write_bytes(generated.read_bytes())
    temporary.replace(index_path)
    return index_path, history_path
```

- [ ] **Step 4: Implementar el orquestador y el override seguro para pruebas**

```python
def run(public_dir: Path, recipients: list[str], send_email: bool = True) -> tuple[Path, Path]:
    with tempfile.TemporaryDirectory(prefix="proyeccion-compras-") as temp_dir:
        generated = generate_report(Path(temp_dir) / "proyeccion.html")
        index_path, history_path = publish_report(generated, public_dir)
    if send_email:
        send_report_email(index_path, cfg.report_public_url, recipients)
    return index_path, history_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--test-recipient")
    parser.add_argument("--no-email", action="store_true")
    args = parser.parse_args()

    recipients = (
        [args.test_recipient]
        if args.test_recipient
        else cfg.report_recipient_list
    )
    run(args.public_dir, recipients, send_email=not args.no_email)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Ejecutar las pruebas de publicación y toda la suite Python**

Run: `python -m pytest test_weekly_job.py test_calculator.py -v`

Expected: todas las pruebas en `PASS`.

- [ ] **Step 6: Commit**

```bash
git add weekly_job.py test_weekly_job.py
git commit -m "feat: publicar proyeccion semanal de forma atomica"
```

### Task 4: Preparar ejecución e instalación en `fasa_195`

**Files:**
- Create: `deploy/run_weekly_projection.sh`
- Create: `deploy/install_weekly_projection.sh`

- [ ] **Step 1: Crear el wrapper operativo**

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/ferreteria/automatizaciones/apps/proyeccion_compras"
ENV_FILE="$APP_DIR/.env"
PYTHON="/home/ferreteria/automatizaciones/venv/bin/python"
PUBLIC_DIR="/var/www/html/informes/proyeccion-compras"

cd "$APP_DIR"
set -a
source "$ENV_FILE"
set +a

exec "$PYTHON" "$APP_DIR/weekly_job.py" --public-dir "$PUBLIC_DIR" "$@"
```

- [ ] **Step 2: Crear el instalador idempotente de cron**

```bash
#!/usr/bin/env bash
set -euo pipefail

LINE="30 5 * * 1 /home/ferreteria/automatizaciones/jobs/run_job.sh proyeccion_compras_weekly /home/ferreteria/automatizaciones/apps/proyeccion_compras/deploy/run_weekly_projection.sh"
MARKER="# FASA_AUTOMATIZACIONES proyeccion_compras_weekly"
CURRENT="$(mktemp)"
trap 'rm -f "$CURRENT"' EXIT

crontab -l 2>/dev/null | grep -vF "$MARKER" | grep -vF "run_job.sh proyeccion_compras_weekly" > "$CURRENT" || true
printf '\n%s\n%s\n' "$MARKER" "$LINE" >> "$CURRENT"
crontab "$CURRENT"
```

- [ ] **Step 3: Validar sintaxis local**

Run: `bash -n deploy/run_weekly_projection.sh deploy/install_weekly_projection.sh`

Expected: exit code `0` sin salida.

- [ ] **Step 4: Commit**

```bash
git add deploy/run_weekly_projection.sh deploy/install_weekly_projection.sh
git commit -m "ops: agregar ejecucion semanal de proyeccion"
```

### Task 5: Desplegar y validar sin enviar correo

**Files:**
- Deploy target: `/home/ferreteria/automatizaciones/apps/proyeccion_compras`
- Public target: `/var/www/html/informes/proyeccion-compras`

- [ ] **Step 1: Crear un paquete limpio desde Git y copiarlo al servidor**

Run:

```powershell
git archive --format=tar HEAD | ssh fasa_195 "mkdir -p /home/ferreteria/automatizaciones/apps/proyeccion_compras && tar -xf - -C /home/ferreteria/automatizaciones/apps/proyeccion_compras"
```

Expected: exit code `0`; no transferir `.env`, `.git`, `outputs` ni resultados locales.

- [ ] **Step 2: Transferir la configuración privada actual sin imprimir secretos y agregar las variables nuevas**

Run desde Windows:

```powershell
scp .env fasa_195:/home/ferreteria/automatizaciones/apps/proyeccion_compras/.env.incoming
ssh fasa_195 "chmod 600 /home/ferreteria/automatizaciones/apps/proyeccion_compras/.env.incoming && mv /home/ferreteria/automatizaciones/apps/proyeccion_compras/.env.incoming /home/ferreteria/automatizaciones/apps/proyeccion_compras/.env && printf '\nREPORT_PUBLIC_URL=https://informes.ferreteriaavenida.com.ar/proyeccion-compras/\nREPORT_RECIPIENTS=luis@ferreteriaavenida.com.ar,compras@ferreteriaavenida.com.ar\n' >> /home/ferreteria/automatizaciones/apps/proyeccion_compras/.env"
```

Expected: exit code `0`; el archivo remoto queda con modo `600`. No mostrar su contenido en consola ni logs.

- [ ] **Step 3: Ejecutar generación y publicación sin correo**

Run:

```bash
/home/ferreteria/automatizaciones/jobs/run_job.sh proyeccion_compras_manual_no_email /home/ferreteria/automatizaciones/apps/proyeccion_compras/deploy/run_weekly_projection.sh --no-email
```

Expected: exit code `0`, nuevo `index.html`, archivo histórico y log con `END ... exit_code=0`.

- [ ] **Step 4: Verificar archivo y URL pública**

Run:

```bash
sha256sum /var/www/html/informes/proyeccion-compras/index.html
curl -fsS -o /dev/null -w '%{http_code} %{size_download}\n' https://informes.ferreteriaavenida.com.ar/proyeccion-compras/
```

Expected: hash SHA-256 y respuesta HTTP `200` con tamaño mayor a `10000` bytes.

### Task 6: Enviar la prueba aislada a Oscar

**Files:**
- Runtime log: `/home/ferreteria/automatizaciones/logs/linux/proyeccion_compras_test_email/`

- [ ] **Step 1: Ejecutar usando el override de destinatario**

Run:

```bash
/home/ferreteria/automatizaciones/jobs/run_job.sh proyeccion_compras_test_email /home/ferreteria/automatizaciones/apps/proyeccion_compras/deploy/run_weekly_projection.sh --test-recipient oscarvogel@gmail.com
```

Expected: exit code `0`; el log registra un envío a `oscarvogel@gmail.com` y no menciona los dos destinatarios productivos.

- [ ] **Step 2: Auditar el log sin exponer secretos**

Run:

```bash
latest="$(find /home/ferreteria/automatizaciones/logs/linux/proyeccion_compras_test_email -type f -name '*.log' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)"
grep -E 'START|HTML generado|Email enviado|END' "$latest"
```

Expected: `START`, generación correcta, envío a Oscar y `END ... exit_code=0`.

- [ ] **Step 3: Solicitar confirmación humana de recepción y apertura**

Confirmar que Oscar recibió el mensaje, pudo abrir el enlace HTTPS y descargar/abrir el HTML adjunto. No instalar todavía el cron productivo si falta esta confirmación.

### Task 7: Activar destinatarios productivos y cron después de la aceptación

**Files:**
- Remote crontab for user `ferreteria`

- [ ] **Step 1: Instalar la entrada semanal**

Run:

```bash
/home/ferreteria/automatizaciones/apps/proyeccion_compras/deploy/install_weekly_projection.sh
```

Expected: exit code `0`.

- [ ] **Step 2: Verificar exactamente una entrada y el horario**

Run:

```bash
crontab -l | grep -F "run_job.sh proyeccion_compras_weekly"
```

Expected: una única línea `30 5 * * 1 ...`.

- [ ] **Step 3: Auditar la configuración productiva sin mostrar secretos**

Run:

```bash
set -a
source /home/ferreteria/automatizaciones/apps/proyeccion_compras/.env
set +a
python3 - <<'PY'
import os
actual = {x.strip() for x in os.environ["REPORT_RECIPIENTS"].split(",") if x.strip()}
expected = {"luis@ferreteriaavenida.com.ar", "compras@ferreteriaavenida.com.ar"}
assert actual == expected, (actual, expected)
print("destinatarios_productivos_ok=2")
PY
```

Expected: `destinatarios_productivos_ok=2`.

- [ ] **Step 4: Verificación final completa**

Run:

```bash
test "$(timedatectl show -p Timezone --value)" = "America/Argentina/Buenos_Aires"
curl -fsS -o /dev/null https://informes.ferreteriaavenida.com.ar/proyeccion-compras/
test "$(crontab -l | grep -Fc 'run_job.sh proyeccion_compras_weekly')" -eq 1
```

Expected: exit code `0` en los tres controles.
