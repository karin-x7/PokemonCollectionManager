"""GUI application factory and run loop.

Separated from :mod:`app.main` so the window can also be constructed head-
lessly in tests (with the ``offscreen`` Qt platform) without starting an event
loop.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import config
from app.database.connection import Database
from app.logging_config import get_logger
from app.ui.main_window import MainWindow

logger = get_logger(__name__)

_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.ico"


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
    if _ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))
    return app


def run_gui(database: Database | None = None) -> int:
    """Launch the GUI and block until the window is closed.

    Args:
        database: Initialised database (passed through for later steps).

    Returns:
        The Qt event-loop exit code.
    """
    app = build_application()
    window = MainWindow(database=database)
    window.show()
    logger.info("GUI started.")
    return app.exec()
