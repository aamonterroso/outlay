"""Structured JSON logging setup."""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from outlay_api.config import get_settings


def configure_logging() -> None:
    """Configure root logger with JSON formatter. Idempotent."""
    settings = get_settings()
    root = logging.getLogger()

    # Avoid double configuration on reload
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
