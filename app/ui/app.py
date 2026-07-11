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
from app.ui.dialogs.welcome_dialog import maybe_show_welcome_dialog
from app.ui.main_window import MainWindow

logger = get_logger(__name__)

_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.ico"

#: Arbitrary but stable identifier so Windows treats this process as its own
#: taskbar entry, distinct from python.exe/pythonw.exe's own -- see
#: ``_set_windows_app_user_model_id``'s docstring for why this matters.
_WINDOWS_APP_USER_MODEL_ID = "Codeon.PokemonCollectionManager.Desktop.1"


def _set_windows_app_user_model_id() -> None:
    """Gives this process its own taskbar identity on Windows.

    Without this, Windows groups the taskbar icon under the *interpreter*'s
    own identity (``pythonw.exe``) and shows its icon there instead of the
    one set via ``QApplication.setWindowIcon()`` below -- a well-known quirk
    for a GUI app launched directly via the Python interpreter rather than a
    bundled, signed ``.exe`` of its own. Must run before the ``QApplication``
    is created. Best-effort: this is purely cosmetic, so a failure here must
    never block startup.
    """
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            _WINDOWS_APP_USER_MODEL_ID
        )
    except (AttributeError, OSError) as exc:
        logger.warning("Could not set the Windows taskbar app id: %s", exc)


def build_application(argv: list[str] | None = None) -> QApplication:
    """Return the singleton :class:`QApplication`, creating it if needed."""
    app = QApplication.instance()
    if app is None:
        if sys.platform == "win32":
            _set_windows_app_user_model_id()
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
    maybe_show_welcome_dialog(window)
    window.start_update_check()
    logger.info("GUI started.")
    return app.exec()
