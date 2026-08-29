import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("facturas_no_procesadas.py")


def load_module():
    if not MODULE_PATH.exists():
        raise AssertionError(f"Falta el módulo operativo: {MODULE_PATH}")
    spec = importlib.util.spec_from_file_location(
        "facturas_no_procesadas_under_test",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EmailConfigFromEnvironmentTest(TestCase):
    def test_reads_all_email_settings_from_environment(self):
        env = {
            "SMTP_SERVER": "smtp.example.test",
            "SMTP_PORT": "2465",
            "SMTP_USER": "sender@example.test",
            "SMTP_PASSWORD": "secret-from-env",
            "FROM_EMAIL": "reports@example.test",
            "TO_EMAILS": "systems@example.test, purchases@example.test",
            "SMTP_USE_SSL": "true",
            "SMTP_USE_STARTTLS": "false",
        }

        with patch.dict(os.environ, env, clear=False):
            module = load_module()

        self.assertEqual(module.SMTP_SERVER, "smtp.example.test")
        self.assertEqual(module.SMTP_PORT, 2465)
        self.assertEqual(module.SMTP_USER, "sender@example.test")
        self.assertEqual(module.SMTP_PASSWORD, "secret-from-env")
        self.assertEqual(module.FROM_EMAIL, "reports@example.test")
        self.assertEqual(
            module.TO_EMAILS,
            ["systems@example.test", "purchases@example.test"],
        )
        self.assertTrue(module.SMTP_USE_SSL)
        self.assertFalse(module.SMTP_USE_STARTTLS)

    def test_reads_email_settings_from_explicit_env_file(self):
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / "mail.env"
            env_path.write_text(
                "\n".join(
                    [
                        "SMTP_SERVER=smtp.private.test",
                        "SMTP_PORT=465",
                        "SMTP_USER=private@example.test",
                        "SMTP_PASSWORD=private-secret",
                        "FROM_EMAIL=private@example.test",
                        "TO_EMAILS=systems@example.test,purchases@example.test",
                        "SMTP_USE_SSL=true",
                        "SMTP_USE_STARTTLS=false",
                    ]
                ),
                encoding="utf-8",
            )
            env = {
                "FACTURAS_ENV_FILE": str(env_path),
            }
            with patch.dict(os.environ, env, clear=True):
                module = load_module()

        self.assertEqual(module.SMTP_SERVER, "smtp.private.test")
        self.assertEqual(module.SMTP_PORT, 465)
        self.assertEqual(module.SMTP_USER, "private@example.test")
        self.assertTrue(module.SMTP_USE_SSL)
        self.assertFalse(module.SMTP_USE_STARTTLS)
