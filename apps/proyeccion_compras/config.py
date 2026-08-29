import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    db_database: str = field(default_factory=lambda: os.getenv("DB_DATABASE", "fasa"))
    db_username: str = field(default_factory=lambda: os.getenv("DB_USERNAME", "root"))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))

    smtp_server: str = field(default_factory=lambda: os.getenv("SMTP_SERVER", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", ""))
    smtp_to: str = field(default_factory=lambda: os.getenv("SMTP_TO", ""))

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

    proy_meses: int = field(default_factory=lambda: int(os.getenv("PROY_MESES", "3")))
    empresa_id: int = field(default_factory=lambda: int(os.getenv("EMPRESA_ID", "1")))
    excel_output_dir: str = field(
        default_factory=lambda: os.getenv("EXCEL_OUTPUT_DIR", "outputs")
    )

    @property
    def db_conn_params(self) -> dict:
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_database,
            "user": self.db_username,
            "password": self.db_password,
        }

    @property
    def report_recipient_list(self) -> list[str]:
        return [
            value.strip()
            for value in self.report_recipients.split(",")
            if value.strip()
        ]


cfg = Config()
