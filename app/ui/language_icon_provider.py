"""In-memory ``QIcon`` cache for simplified national-flag language icons.

pokemontcg.io provides no flag imagery, and there's no Cardmarket asset to
reuse -- these are drawn directly with QPainter (same approach as the app
icon/checkbox tick, see PROJECT_PROGRESS.md), not downloaded or read from a
file. Deliberately simplified (plain stripes/circles, no coats of arms or
trigrams): recognisable at the small size these appear at (a card list's
Sprache column), not a faithful vexillological reproduction.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from app.models.enums import Language

_WIDTH = 20
_HEIGHT = 14

_icons: dict[Language, QIcon] = {}


def get_language_icon(language: Language) -> QIcon:
    """Return the cached flag icon for ``language`` (drawn on first use)."""
    if language not in _icons:
        _icons[language] = QIcon(_draw_flag(language))
    return _icons[language]


def _draw_flag(language: Language) -> QPixmap:
    pixmap = QPixmap(_WIDTH, _HEIGHT)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(0, 0, _WIDTH, _HEIGHT)
    _DRAW_FUNCTIONS.get(language, _draw_german)(painter, rect)
    painter.setPen(QPen(QColor(0, 0, 0, 90), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(rect.adjusted(0, 0, -1, -1))
    painter.end()
    return pixmap


def _draw_union_jack(painter: QPainter, rect: QRectF) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#00247D"))
    painter.drawRect(rect)
    painter.setPen(QPen(QColor("#ffffff"), rect.height() * 0.22))
    painter.drawLine(rect.topLeft(), rect.bottomRight())
    painter.drawLine(rect.topRight(), rect.bottomLeft())
    painter.setPen(QPen(QColor("#CF142B"), rect.height() * 0.10))
    painter.drawLine(rect.topLeft(), rect.bottomRight())
    painter.drawLine(rect.topRight(), rect.bottomLeft())
    painter.setPen(QPen(QColor("#ffffff"), rect.height() * 0.34))
    painter.drawLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
    painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    painter.setPen(QPen(QColor("#CF142B"), rect.height() * 0.16))
    painter.drawLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
    painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())


def _draw_german(painter: QPainter, rect: QRectF) -> None:
    _horizontal_stripes(painter, rect, ("#000000", "#dd0000", "#ffce00"))


def _draw_french(painter: QPainter, rect: QRectF) -> None:
    _vertical_stripes(painter, rect, ("#002395", "#ffffff", "#ed2939"))


def _draw_italian(painter: QPainter, rect: QRectF) -> None:
    _vertical_stripes(painter, rect, ("#008C45", "#ffffff", "#CD212A"))


def _horizontal_stripes(painter: QPainter, rect: QRectF, colors: tuple[str, str, str]) -> None:
    band = rect.height() / 3
    painter.setPen(Qt.PenStyle.NoPen)
    for index, color in enumerate(colors):
        painter.setBrush(QColor(color))
        painter.drawRect(QRectF(rect.left(), rect.top() + index * band, rect.width(), band))


def _vertical_stripes(painter: QPainter, rect: QRectF, colors: tuple[str, str, str]) -> None:
    band = rect.width() / 3
    painter.setPen(Qt.PenStyle.NoPen)
    for index, color in enumerate(colors):
        painter.setBrush(QColor(color))
        painter.drawRect(QRectF(rect.left() + index * band, rect.top(), band, rect.height()))


def _draw_spanish(painter: QPainter, rect: QRectF) -> None:
    band = rect.height() / 4
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#AA151B"))
    painter.drawRect(QRectF(rect.left(), rect.top(), rect.width(), band))
    painter.setBrush(QColor("#F1BF00"))
    painter.drawRect(QRectF(rect.left(), rect.top() + band, rect.width(), band * 2))
    painter.setBrush(QColor("#AA151B"))
    painter.drawRect(QRectF(rect.left(), rect.top() + band * 3, rect.width(), band))


def _draw_portuguese(painter: QPainter, rect: QRectF) -> None:
    split = rect.width() * 0.4
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#046A38"))
    painter.drawRect(QRectF(rect.left(), rect.top(), split, rect.height()))
    painter.setBrush(QColor("#DA291C"))
    painter.drawRect(QRectF(rect.left() + split, rect.top(), rect.width() - split, rect.height()))


def _draw_japanese(painter: QPainter, rect: QRectF) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#ffffff"))
    painter.drawRect(rect)
    painter.setBrush(QColor("#BC002D"))
    radius = rect.height() * 0.32
    painter.drawEllipse(rect.center(), radius, radius)


def _draw_korean(painter: QPainter, rect: QRectF) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#ffffff"))
    painter.drawRect(rect)
    radius = rect.height() * 0.32
    center = rect.center()
    circle = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
    painter.setBrush(QColor("#C60C30"))
    painter.drawChord(circle, 90 * 16, 180 * 16)
    painter.setBrush(QColor("#003478"))
    painter.drawChord(circle, 270 * 16, 180 * 16)


def _draw_chinese(painter: QPainter, rect: QRectF) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#DE2910"))
    painter.drawRect(rect)
    painter.setBrush(QColor("#FFDE00"))
    radius = rect.height() * 0.22
    star_x = rect.left() + rect.width() * 0.22
    star_y = rect.top() + rect.height() * 0.32
    painter.drawEllipse(QRectF(star_x - radius, star_y - radius, radius * 2, radius * 2))


_DRAW_FUNCTIONS: dict[Language, Callable[[QPainter, QRectF], None]] = {
    Language.ENGLISH: _draw_union_jack,
    Language.GERMAN: _draw_german,
    Language.FRENCH: _draw_french,
    Language.ITALIAN: _draw_italian,
    Language.SPANISH: _draw_spanish,
    Language.PORTUGUESE: _draw_portuguese,
    Language.JAPANESE: _draw_japanese,
    Language.KOREAN: _draw_korean,
    Language.CHINESE: _draw_chinese,
}
