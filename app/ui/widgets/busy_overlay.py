"""Full-window dimming overlay shown while a Cardmarket price lookup runs.

Mirrors :class:`~app.ui.dialogs.dimmed_dialog.DimmedDialog`'s own overlay
technique (a translucent widget layered on top of the host's content), but
for background ``QThread`` work rather than a modal dialog: a lookup can
take several seconds (open Chrome, load the page, read it, close the tab)
with the only feedback otherwise being a small status-bar message, easy to
miss (user request: make it obviously "busy" via dimming + a small loading
bar, not just via the status bar).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from app.ui.theme import apply_elevation


class BusyOverlay(QWidget):
    """Dims its parent and shows a small indeterminate progress bar + message.

    Created once per top-level window and reused across every lookup
    (single or bulk) rather than being built fresh each time -- there's
    only ever at most one lookup running at a time per window (each price
    controller already guards against overlapping ones).
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        # Mouse clicks fall through to whatever's underneath -- this is a
        # visual cue only, not a modal block (the lookup's own trigger
        # button is already disabled for its duration, see e.g.
        # CardDetailPanel.set_price_lookup_running).
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Required for the rgba() background below to actually paint: Qt
        # only auto-applies a stylesheet background to a *bare* QWidget
        # instance -- DimmedDialog's own overlay (mirrored here) is exactly
        # that, a plain QWidget(host), so it works without this. A
        # subclass (this class) silently renders nothing at all instead
        # unless this attribute is set explicitly -- live-confirmed via a
        # real (non-PrintWindow) screen capture during an actual lookup:
        # the label/progress bar showed up fine, the dimming never did.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Noticeably darker than DimmedDialog's own 110: that one only has
        # to add contrast behind an otherwise-bright modal dialog, whereas
        # this has no bright foreground element of its own to contrast
        # against, just a small label/bar -- 110 measured correct (pixel-
        # sampled against a real screen capture) but read as barely
        # perceptible at a glance on this already-dark theme.
        self.setStyleSheet("background-color: rgba(0, 0, 0, 170);")

        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Text + bar share one small raised card (same "Panel" look as the
        # rest of the app) instead of floating loose over the dimmed
        # background -- reads as one deliberate "busy" indicator rather
        # than two separate, disconnected widgets (user request).
        box = QWidget()
        box.setObjectName("Panel")
        apply_elevation(box)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(28, 22, 28, 22)
        box_layout.setSpacing(12)

        self._label = QLabel("")
        self._label.setObjectName("SearchLoadingLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setObjectName("SearchLoadingBar")
        self._bar.setRange(0, 0)  # indeterminate
        self._bar.setFixedWidth(260)
        self._bar.setTextVisible(False)
        box_layout.addWidget(self._bar, alignment=Qt.AlignmentFlag.AlignHCenter)

        outer_layout.addWidget(box)

        self.hide()
        parent.installEventFilter(self)

    def show_busy(self, message: str) -> None:
        """Dims the parent and shows ``message`` under the loading bar."""
        self._label.setText(message)
        self._cover_parent()
        self.show()
        self.raise_()

    def hide_busy(self) -> None:
        self.hide()

    def eventFilter(self, watched: object, event) -> bool:  # noqa: N802 — Qt override
        if watched is self.parentWidget() and event.type() == event.Type.Resize:
            self._cover_parent()
        return super().eventFilter(watched, event)

    def _cover_parent(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
