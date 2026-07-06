"""In-memory ``QIcon`` cache for set symbol icons.

Wraps :func:`app.catalog.set_icon_cache.ensure_set_icon`'s on-disk cache with
an in-process one, keyed the same way (``set_code``) — a table redraw (every
selection change, every search) would otherwise reconstruct the same
``QIcon`` from disk over and over for the handful of sets actually in view.
"""

from __future__ import annotations

from PySide6.QtGui import QIcon

from app.catalog.set_icon_cache import ensure_set_icon

_icons: dict[str, QIcon | None] = {}


def get_set_icon(set_code: str, set_name: str = "") -> QIcon | None:
    """Return the cached symbol icon for ``set_code``, or ``None`` if it has

    no code or the icon couldn't be downloaded. ``set_name`` (if given) lets
    ``ensure_set_icon`` fall back to tcgdex.dev when pokemontcg.io's own
    icon is missing -- see its own docs.
    """
    if set_code not in _icons:
        path = ensure_set_icon(set_code, set_name)
        _icons[set_code] = QIcon(path) if path else None
    return _icons[set_code]
