"""Displays a card's artwork, with a Reverse Holo overlay effect.

Presentation-only. pokemontcg.io provides exactly one image per card
regardless of the physical print variant (Normal/Holo/Reverse Holo are the
same scan) — Reverse Holo is visually distinguished the same way Cardmarket
and physical prints do it: a translucent, diagonal "oil-slick" gradient
painted over the artwork, not a separate downloaded image.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QStyle, QStyleOption, QWidget

_REVERSE_HOLO_GRADIENT_STOPS = (
    (0.0, QColor(255, 0, 128, 55)),
    (0.33, QColor(0, 200, 255, 55)),
    (0.66, QColor(255, 230, 0, 55)),
    (1.0, QColor(0, 255, 140, 55)),
)


class CardArtworkView(QWidget):
    """Shows the currently selected card's artwork, or a placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumHeight(180)
        self._pixmap: QPixmap | None = None
        self._reverse_holo = False

    def show_empty(self) -> None:
        """Reset to the "no photo" placeholder state."""
        self._pixmap = None
        self._reverse_holo = False
        self.update()

    def show_photo(self, photo_path: str | None, reverse_holo: bool) -> None:
        """Show the artwork at ``photo_path`` (or the placeholder if ``None``
        / the file can't be loaded as an image), with the Reverse Holo
        overlay applied if ``reverse_holo`` is set."""
        self._reverse_holo = reverse_holo
        pixmap = QPixmap(photo_path) if photo_path else None
        self._pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt override
        painter = QPainter(self)

        # Respect the QSS-styled #Panel background/border for this widget,
        # since a custom paintEvent otherwise bypasses the stylesheet.
        option = QStyleOption()
        option.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

        if self._pixmap is None:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Kein Foto")
            painter.end()
            return

        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        if self._reverse_holo:
            gradient = QLinearGradient(x, y, x + scaled.width(), y + scaled.height())
            for stop, color in _REVERSE_HOLO_GRADIENT_STOPS:
                gradient.setColorAt(stop, color)
            painter.fillRect(x, y, scaled.width(), scaled.height(), gradient)

        painter.end()
