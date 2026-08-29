from pathlib import Path
from unittest.mock import patch

import generate_html
import pytest


def test_generate_report_writes_requested_path(tmp_path: Path):
    destination = tmp_path / "report.html"
    with (
        patch.object(generate_html, "calcular_proyecciones", return_value=[object()]),
        patch.object(generate_html, "serialize_data", return_value=[]),
        patch.object(generate_html, "obtener_tipo_cambio", return_value=1.0),
    ):
        result = generate_html.generate_report(destination)

    assert result == destination
    assert destination.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_send_report_email_uses_only_explicit_recipients(tmp_path: Path):
    from mailer import send_report_email

    report = tmp_path / "index.html"
    report.write_text("<!DOCTYPE html><html></html>", encoding="utf-8")

    with patch("mailer.smtplib.SMTP") as smtp_class:
        smtp = smtp_class.return_value.__enter__.return_value
        send_report_email(
            report_path=report,
            public_url="https://informes.ferreteriaavenida.com.ar/proyeccion-compras/",
            recipients=["oscarvogel@gmail.com"],
        )

    message = smtp.send_message.call_args.args[0]
    serialized = message.as_string()
    assert message["To"] == "oscarvogel@gmail.com"
    assert "luis@ferreteriaavenida.com.ar" not in serialized
    assert "compras@ferreteriaavenida.com.ar" not in serialized
    assert 'filename="proyeccion-compras.html"' in serialized


def test_publish_report_creates_index_and_history(tmp_path: Path):
    import weekly_job

    generated = tmp_path / "generated.html"
    generated.write_text(
        "<!DOCTYPE html><html><script>const DATA = [];"
        + ("x" * 10_000)
        + "</script></html>",
        encoding="utf-8",
    )
    public_dir = tmp_path / "public"

    index_path, history_path = weekly_job.publish_report(generated, public_dir)

    assert index_path.read_bytes() == generated.read_bytes()
    assert history_path.read_bytes() == generated.read_bytes()
    assert history_path.name.startswith("proyeccion-compras-")


def test_invalid_generation_does_not_replace_current_report(tmp_path: Path):
    import weekly_job

    public_dir = tmp_path / "public"
    public_dir.mkdir()
    current = public_dir / "index.html"
    current.write_text("informe anterior", encoding="utf-8")
    invalid = tmp_path / "invalid.html"
    invalid.write_text("archivo incompleto", encoding="utf-8")

    with pytest.raises(ValueError):
        weekly_job.publish_report(invalid, public_dir)

    assert current.read_text(encoding="utf-8") == "informe anterior"


def test_test_recipient_replaces_every_production_recipient():
    import weekly_job

    recipients = weekly_job.select_recipients(
        "oscarvogel@gmail.com",
        ["luis@ferreteriaavenida.com.ar", "compras@ferreteriaavenida.com.ar"],
    )

    assert recipients == ["oscarvogel@gmail.com"]


def test_generation_failure_does_not_publish_or_send(tmp_path: Path):
    import weekly_job

    with (
        patch.object(weekly_job, "generate_report", side_effect=RuntimeError("DB caída")),
        patch.object(weekly_job, "publish_report") as publish,
        patch.object(weekly_job, "send_report_email") as send,
        pytest.raises(RuntimeError, match="DB caída"),
    ):
        weekly_job.run(tmp_path / "public", ["oscarvogel@gmail.com"])

    publish.assert_not_called()
    send.assert_not_called()


def test_runtime_wrapper_uses_absolute_paths_and_private_env():
    wrapper = Path("deploy/run_weekly_projection.sh").read_text(encoding="utf-8")

    assert 'source "$ENV_FILE"' in wrapper
    assert 'weekly_job.py" --public-dir "$PUBLIC_DIR" "$@"' in wrapper
    assert "/var/www/html/informes/proyeccion-compras" in wrapper


def test_cron_installer_sets_one_monday_0530_job():
    installer = Path("deploy/install_weekly_projection.sh").read_text(
        encoding="utf-8"
    )

    assert "30 5 * * 1" in installer
    assert "grep -vF \"run_job.sh proyeccion_compras_weekly\"" in installer
    assert 'crontab "$CURRENT"' in installer


@pytest.mark.parametrize(
    "script_path",
    [
        Path("deploy/run_weekly_projection.sh"),
        Path("deploy/install_weekly_projection.sh"),
    ],
)
def test_shell_scripts_use_linux_line_endings(script_path: Path):
    assert b"\r\n" not in script_path.read_bytes()


def test_git_exports_shell_scripts_with_linux_line_endings():
    attributes = Path(".gitattributes").read_text(encoding="utf-8")
    assert "*.sh text eol=lf" in attributes.splitlines()
