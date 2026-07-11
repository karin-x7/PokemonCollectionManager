"""Displays a sealed product's photo.

Mirrors ``card_artwork_view.py``, minus the Reverse Holo overlay (a concept
that doesn't exist for sealed products) and using a square (1:1) aspect
ratio instead of a real trading card's 2.5:3.5 -- matching the roughly
square screenshot crop ``app.pricing.sealed_image_capture`` produces from a
Cardmarket product page.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from app.i18n import tr
from app.ui.theme import PALETTE

_PRODUCT_ASPECT = 1.0
_STAGE_PADDING = 14
_CORNER_RADIUS = 12


class SealedArtworkView(QWidget):
    """Shows the currently selected sealed product's photo, or a placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        # A *fixed* height, not just a min/max range -- mirrors the identical
        # fix in card_artwork_view.py: this widget sits in
        # SealedProductDetailPanel's QVBoxLayout as its only ``stretch=1``
        # element, so a min/max range let it silently grow or shrink based on
        # how much vertical space its siblings needed (e.g. a longer "Price
        # quality" rationale wrapping to two lines instead of one). 360px
        # (live-reported) overlapped the form fields below it -- 260px
        # matches this widget's old min-height floor, known to fit.
        self.setFixedHeight(260)
        self._pixmap: QPixmap | None = None

    def show_empty(self) -> None:
        """Reset to the "no photo" placeholder state."""
        self._pixmap = None
        self.update()

    def show_photo(self, photo_path: str | None) -> None:
        """Show the photo at ``photo_path`` (or the placeholder if ``None``

        / the file can't be loaded as an image)."""
        pixmap = QPixmap(photo_path) if photo_path else None
        self._pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        self.update()

    def _stage_rect(self) -> QRectF:
        """The largest square that fits inside this widget, centred."""
        available = QRectF(self.rect()).adjusted(
            _STAGE_PADDING, _STAGE_PADDING, -_STAGE_PADDING, -_STAGE_PADDING
        )
        if available.width() <= 0 or available.height() <= 0:
            return available
        if available.width() / available.height() > _PRODUCT_ASPECT:
            height = available.height()
            width = height * _PRODUCT_ASPECT
        else:
            width = available.width()
            height = width / _PRODUCT_ASPECT
        x = available.left() + (available.width() - width) / 2
        y = available.top() + (available.height() - height) / 2
        return QRectF(x, y, width, height)

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        stage_rect = self._stage_rect()
        path = QPainterPath()
        path.addRoundedRect(stage_rect, _CORNER_RADIUS, _CORNER_RADIUS)
        painter.setPen(QPen(QColor(PALETTE.accent), 2))
        painter.setBrush(QColor(PALETTE.panel_raised))
        painter.drawPath(path)

        if self._pixmap is None:
            painter.setPen(QColor(PALETTE.muted))
            painter.drawText(stage_rect, Qt.AlignmentFlag.AlignCenter, tr("Kein Foto"))
            painter.end()
            return

        painter.save()
        painter.setClipPath(path)
        scaled = self._pixmap.scaled(
            stage_rect.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = stage_rect.left() + (stage_rect.width() - scaled.width()) / 2
        y = stage_rect.top() + (stage_rect.height() - scaled.height()) / 2
        painter.drawPixmap(QPointF(x, y), scaled)
        painter.restore()

        painter.end()
