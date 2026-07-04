"""Displays a card's artwork, with a Reverse Holo overlay effect.

Presentation-only. pokemontcg.io provides exactly one image per card
regardless of the physical print variant (Normal/Holo/Reverse Holo are the
same scan) — Reverse Holo is visually distinguished the same way Cardmarket
and physical prints do it: a translucent, diagonal "oil-slick" gradient
painted over the artwork, not a separate downloaded image.

The artwork is drawn onto a card-shaped "stage" fitted to a real trading
card's aspect ratio (2.5:3.5), cropped to fill that shape (not letterboxed)
-- rather than painting a plain rectangle background across the whole,
often much taller, widget rect, which used to leave a lot of empty space
above/below a normally-proportioned card image.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from app.ui.theme import PALETTE

_REVERSE_HOLO_GRADIENT_STOPS = (
    (0.0, QColor(255, 0, 128, 55)),
    (0.33, QColor(0, 200, 255, 55)),
    (0.66, QColor(255, 230, 0, 55)),
    (1.0, QColor(0, 255, 140, 55)),
)

#: Width:height of a real trading card.
_CARD_ASPECT = 2.5 / 3.5
#: Space (px) between the widget's edge and the fitted card shape.
_STAGE_PADDING = 14
_CORNER_RADIUS = 12


class CardArtworkView(QWidget):
    """Shows the currently selected card's artwork, or a placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.setMinimumWidth(200)
        # Capped so it can't keep consuming a tall panel's every extra pixel
        # of stretch space, crowding right up against the fields below it.
        self.setMaximumHeight(420)
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

    def _card_rect(self) -> QRectF:
        """The largest card-shaped rect that fits inside this widget, centred."""
        available = QRectF(self.rect()).adjusted(
            _STAGE_PADDING, _STAGE_PADDING, -_STAGE_PADDING, -_STAGE_PADDING
        )
        if available.width() <= 0 or available.height() <= 0:
            return available
        if available.width() / available.height() > _CARD_ASPECT:
            height = available.height()
            width = height * _CARD_ASPECT
        else:
            width = available.width()
            height = width / _CARD_ASPECT
        x = available.left() + (available.width() - width) / 2
        y = available.top() + (available.height() - height) / 2
        return QRectF(x, y, width, height)

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        card_rect = self._card_rect()
        path = QPainterPath()
        path.addRoundedRect(card_rect, _CORNER_RADIUS, _CORNER_RADIUS)
        painter.setPen(QPen(QColor(PALETTE.accent), 2))
        painter.setBrush(QColor(PALETTE.panel_raised))
        painter.drawPath(path)

        if self._pixmap is None:
            painter.setPen(QColor(PALETTE.muted))
            painter.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, "Kein Foto")
            painter.end()
            return

        painter.save()
        painter.setClipPath(path)
        # KeepAspectRatioByExpanding + centred draw = crop-to-fill: the card
        # shape is always covered edge-to-edge, never letterboxed.
        scaled = self._pixmap.scaled(
            card_rect.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = card_rect.left() + (card_rect.width() - scaled.width()) / 2
        y = card_rect.top() + (card_rect.height() - scaled.height()) / 2
        painter.drawPixmap(QPointF(x, y), scaled)

        if self._reverse_holo:
            gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
            for stop, color in _REVERSE_HOLO_GRADIENT_STOPS:
                gradient.setColorAt(stop, color)
            painter.fillPath(path, gradient)
        painter.restore()

        painter.end()
