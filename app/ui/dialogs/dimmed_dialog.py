"""Shared base for every custom dialog in this app.

Dims the host window's content behind the dialog while it's open -- a
plain ``QDialog`` (even a modal one) leaves the window behind it looking
fully normal, which reads as "the app just froze" rather than "waiting for
you" (live-reported point of confusion, especially during a slower search).
Qt has no built-in "dim the parent" effect, so this overlays a translucent
widget on top of the parent window's content for the dialog's lifetime.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget


class DimmedDialog(QDialog):
    """A QDialog that dims its parent window while open."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dim_overlay: QWidget | None = None

    def showEvent(self, event) -> None:  # noqa: N802 -- Qt's own naming
        super().showEvent(event)
        self._show_dim_overlay()

    def closeEvent(self, event) -> None:  # noqa: N802 -- Qt's own naming
        self._hide_dim_overlay()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802 -- Qt's own naming
        self._hide_dim_overlay()
        super().hideEvent(event)

    def _show_dim_overlay(self) -> None:
        if self._dim_overlay is not None:
            return
        host = self._dim_host()
        if host is None:
            return
        overlay = QWidget(host)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 110);")
        overlay.setGeometry(host.rect())
        overlay.show()
        overlay.raise_()
        self._dim_overlay = overlay

    def _hide_dim_overlay(self) -> None:
        if self._dim_overlay is None:
            return
        self._dim_overlay.deleteLater()
        self._dim_overlay = None

    def _dim_host(self) -> QWidget | None:
        """The parent's top-level window -- ``None`` if this dialog has no

        parent (e.g. constructed standalone in a test), in which case there
        is nothing sensible to dim.
        """
        parent = self.parentWidget()
        return parent.window() if parent is not None else None
