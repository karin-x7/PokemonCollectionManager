"""GUI application factory and run loop.

Separated from :mod:`app.main` so the window can also be constructed head-
lessly in tests (with the ``offscreen`` Qt platform) without starting an event
loop.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app import config
from app.database.connection import Database
from app.logging_config import get_logger
from app.ui.main_window import MainWindow
from app.ui.theme import Theme

logger = get_logger(__name__)


def build_application(argv: list[str] | None = None) -> QApplication:
    """Return the singleton :class:`QApplication`, creating it if needed."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationDisplayName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName("PokemonCollectionManager")
    app.setStyle("Fusion")  # consistent base look before our style sheet
    return app


def run_gui(database: Database | None = None, theme: Theme = Theme.LIGHT) -> int:
    """Launch the GUI and block until the window is closed.

    Args:
        database: Initialised database (passed through for later steps).
        theme: Initial colour theme.

    Returns:
        The Qt event-loop exit code.
    """
    app = build_application()
    window = MainWindow(database=database, theme=theme)
    window.show()
    logger.info("GUI started.")
    return app.exec()
