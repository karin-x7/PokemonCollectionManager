"""In-memory ``QIcon`` cache for set symbol icons.

Wraps :func:`app.catalog.set_icon_cache.ensure_set_icon`'s on-disk cache with
an in-process one, keyed the same way (``set_code``) — a table redraw (every
selection change, every search) would otherwise reconstruct the same
``QIcon`` from disk over and over for the handful of sets actually in view.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

from app.catalog.set_icon_cache import ensure_set_icon

_icons: dict[str, QIcon | None] = {}

#: Every other per-cell icon (language flag, condition badge) is a small,
#: precisely-sized pixmap drawn straight onto a transparent canvas (see
#: language_icon_provider.py/condition_icon_provider.py) -- set icons are
#: the one exception, downloaded straight from pokemontcg.io/tcgdex at
#: whatever native resolution the source happens to serve (live-confirmed:
#: some are literally 884x452px). Wrapped directly into a QIcon with no
#: resizing at all, Qt's default item-view icon rendering reserved a
#: decoration slot sized to that huge source image and only fit a small,
#: aspect-ratio-correct chunk of it inside -- live-reported as the icon
#: looking "surrounded by a black box" (the same class of bug the
#: QComboBox dropdown arrow had, see theme.py's own docs on that). Scaling
#: down into a small, fixed, transparent canvas here -- same recipe the
#: other icon columns already use -- keeps the reserved decoration space
#: no bigger than the icon actually needs.
_ICON_SIZE = 20


def get_set_icon(set_code: str, set_name: str = "") -> QIcon | None:
    """Return the cached symbol icon for ``set_code``, or ``None`` if it has

    no code or the icon couldn't be downloaded. ``set_name`` (if given) lets
    ``ensure_set_icon`` fall back to tcgdex.dev when pokemontcg.io's own
    icon is missing -- see its own docs.
    """
    if set_code not in _icons:
        path = ensure_set_icon(set_code, set_name)
        _icons[set_code] = _load_scaled_icon(path) if path else None
    return _icons[set_code]


def _load_scaled_icon(path: str) -> QIcon | None:
    source = QPixmap(path)
    if source.isNull():
        return None
    scaled = source.scaled(
        _ICON_SIZE,
        _ICON_SIZE,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(_ICON_SIZE, _ICON_SIZE)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap(
        int((_ICON_SIZE - scaled.width()) / 2),
        int((_ICON_SIZE - scaled.height()) / 2),
        scaled,
    )
    painter.end()
    return QIcon(canvas)
