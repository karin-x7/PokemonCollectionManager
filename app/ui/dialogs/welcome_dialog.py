"""First-run welcome dialog, shown on every startup unless dismissed.

Shown by default on every launch (not just the very first one) -- some users
like the reminder of where to find Help, most will check "Don't show this
again" once they know their way around. See ``app.config.WELCOME_DISMISSED_FLAG``
for the persistence mechanism: a plain marker file, consistent with this
app's existing "self-contained, plain files on disk" approach (no registry,
no QSettings).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QVBoxLayout

from app import config
from app.ui.dialogs.dimmed_dialog import DimmedDialog

#: Live-requested to be noticeably bigger than the app's own default widget
#: font -- same reasoning/value as ``SettingsDialog``'s own Help/FAQ font.
_BODY_FONT_POINT_SIZE = 15

_WELCOME_HTML = """
<p>Track your Pokémon card collection and its market value, all in one place.</p>

<p>Add cards by searching the catalog or pasting a Cardmarket link, and the
app keeps their current Cardmarket price up to date for you — matched to the
exact language and condition you own. Sealed products and a wantlist with
price alerts work the same way.</p>

<p>Not sure where to start? Check <b>Help</b> (top right) any time for a full
walkthrough — searching, pricing, sealed products, and more.</p>
"""


class WelcomeDialog(DimmedDialog):
    """Greets the user on startup with a short overview and a Help pointer."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to {config.APP_NAME}")
        self.resize(640, 520)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel(f"Welcome to {config.APP_NAME}")
        title.setObjectName("PanelHeader")
        layout.addWidget(title)

        body_font = QFont(self.font())
        body_font.setPointSize(_BODY_FONT_POINT_SIZE)
        # setFont() alone is silently overridden by theme.py's app-wide
        # "QMainWindow, QWidget { font-size: 10pt; }" QSS rule -- a
        # stylesheet's font-size always wins over a plain setFont() call
        # once any stylesheet is set anywhere up the ancestor chain (here,
        # on the QApplication itself). A widget's *own* stylesheet outranks
        # an ancestor's for its own properties, so that's applied too.
        body_style = f"font-size: {_BODY_FONT_POINT_SIZE}pt;"

        body = QLabel(_WELCOME_HTML)
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setFont(body_font)
        body.setStyleSheet(body_style)
        layout.addWidget(body)
        layout.addStretch(1)

        self._dont_show_again_check = QCheckBox("Don't show this again")
        self._dont_show_again_check.setFont(body_font)
        self._dont_show_again_check.setStyleSheet(body_style)
        layout.addWidget(self._dont_show_again_check)

        get_started_button = QPushButton("Get started")
        get_started_button.setFont(body_font)
        get_started_button.setStyleSheet(body_style)
        get_started_button.setDefault(True)
        get_started_button.clicked.connect(self.accept)
        layout.addWidget(get_started_button)

    def accept(self) -> None:
        if self._dont_show_again_check.isChecked():
            config.WELCOME_DISMISSED_FLAG.parent.mkdir(parents=True, exist_ok=True)
            config.WELCOME_DISMISSED_FLAG.touch()
        super().accept()


def maybe_show_welcome_dialog(parent=None) -> None:
    """Show :class:`WelcomeDialog` unless a prior run's checkbox suppressed it."""
    if config.WELCOME_DISMISSED_FLAG.exists():
        return
    WelcomeDialog(parent).exec()
