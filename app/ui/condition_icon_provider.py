"""In-memory ``QIcon`` cache for Cardmarket-style condition badges.

Drawn directly with QPainter (same approach as the app icon/checkbox tick
and the language flags, see PROJECT_PROGRESS.md): a rounded, coloured pill
with the condition's own code (e.g. "NM") on it, matching how Cardmarket's
own offer tables badge conditions -- not just a plain coloured cell
background.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap

from app.models.enums import Condition
from app.ui.condition_colors import CONDITION_COLORS

_WIDTH = 34
_HEIGHT = 18
_RADIUS = 5

_icons: dict[Condition, QIcon] = {}


def get_condition_icon(condition: Condition) -> QIcon:
    """Return the cached badge icon for ``condition`` (drawn on first use)."""
    if condition not in _icons:
        _icons[condition] = QIcon(_draw_badge(condition))
    return _icons[condition]


def _draw_badge(condition: Condition) -> QPixmap:
    background, foreground = CONDITION_COLORS[condition]
    pixmap = QPixmap(_WIDTH, _HEIGHT)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(0.5, 0.5, _WIDTH - 1, _HEIGHT - 1)
    path = QPainterPath()
    path.addRoundedRect(rect, _RADIUS, _RADIUS)
    painter.fillPath(path, QColor(background))

    font = QFont()
    font.setPointSize(8)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(foreground))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, condition.code)
    painter.end()
    return pixmap
