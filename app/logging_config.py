"""Application-wide logging configuration.

Logging is intentionally centralised: every relevant event is written both
to the console and to a rotating ``logs/application.log`` file so that
failures can be diagnosed after the fact. The rotating handler prevents the
log from growing without bound.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app import config

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root logger with console and rotating-file handlers.

    Safe to call multiple times; handlers are only attached once.

    Args:
        level: Minimum log level for the handlers.

    Returns:
        The configured root logger.
    """
    global _configured

    config.ensure_directories()
    root = logging.getLogger()

    if _configured:
        return root

    root.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        filename=Path(config.LOG_FILE),
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True
    root.info("Logging configured — writing to %s", config.LOG_FILE)
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring logging on first use."""
    if not _configured:
        configure_logging()
    return logging.getLogger(name)
