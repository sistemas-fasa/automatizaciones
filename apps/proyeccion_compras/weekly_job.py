#!/usr/bin/env python3
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("weekly_job")


def validate_report(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"El informe no existe: {path}")

    text = path.read_text(encoding="utf-8")
    required = ("<!DOCTYPE html>", "const DATA", "</html>")
    missing = [marker for marker in required if marker not in text]
    if path.stat().st_size < 10_000 or missing:
        raise ValueError(f"Informe inválido; faltan marcadores: {missing}")


def publish_report(generated: Path, public_dir: Path) -> tuple[Path, Path]:
    validate_report(generated)
    public_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = generated.read_bytes()

    history_path = public_dir / f"proyeccion-compras-{stamp}.html"
    history_path.write_bytes(payload)

    index_path = public_dir / "index.html"
    temporary = public_dir / f".index-{os.getpid()}.tmp"
    try:
        temporary.write_bytes(payload)
        temporary.replace(index_path)
    finally:
        temporary.unlink(missing_ok=True)

    logger.info("Informe publicado: %s", index_path)
    logger.info("Histórico publicado: %s", history_path)
    return index_path, history_path


def run(
    public_dir: Path,
    recipients: list[str],
    *,
    send_email: bool = True,
) -> tuple[Path, Path]:
    with tempfile.TemporaryDirectory(prefix="proyeccion-compras-") as temp_dir:
        generated = generate_report(Path(temp_dir) / "proyeccion.html")
        index_path, history_path = publish_report(generated, public_dir)

    if send_email:
        send_report_email(index_path, cfg.report_public_url, recipients)
    else:
        logger.info("Email omitido por --no-email")

    return index_path, history_path


def select_recipients(
    test_recipient: str | None,
    production_recipients: list[str],
) -> list[str]:
    if test_recipient:
        return [test_recipient]
    return production_recipients


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica la proyección semanal")
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument(
        "--test-recipient",
        help="Reemplaza todos los destinatarios para una prueba controlada",
    )
    parser.add_argument("--no-email", action="store_true")
    args = parser.parse_args()

    recipients = select_recipients(
        args.test_recipient,
        cfg.report_recipient_list,
    )
    run(args.public_dir, recipients, send_email=not args.no_email)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
