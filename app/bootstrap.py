"""Application bootstrap.

Centralises the start-up sequence (logging → directories → database) so that
both the future GUI entry point and the tests share exactly one initialisation
path. Any failure here is logged and re-raised as :class:`BootstrapError`.
"""

from __future__ import annotations

import logging

from app import config
from app.database.connection import Database
from app.logging_config import configure_logging
from app.pricing.sealed_image_capture import cleanup_orphaned_temp_photos


class BootstrapError(RuntimeError):
    """Raised when the application fails to initialise."""


def bootstrap(log_level: int = logging.INFO) -> Database:
    """Initialise logging, directories and the database.

    Args:
        log_level: Logging verbosity for the session.

    Returns:
        An initialised, connected :class:`Database` ready for use.

    Raises:
        BootstrapError: If initialisation fails for any reason.
    """
    logger = configure_logging(log_level)
    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)

    try:
        config.ensure_directories()
        cleanup_orphaned_temp_photos()
        database = Database()
        applied = database.initialize()
        logger.info(
            "Bootstrap complete — database at %s (%d migration(s) applied).",
            database.path,
            applied,
        )
        return database
    except Exception as exc:  # noqa: BLE001 — top-level guard, logged and re-raised
        logger.exception("Bootstrap failed: %s", exc)
        raise BootstrapError(str(exc)) from exc
