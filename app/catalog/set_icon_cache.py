"""Downloads and locally caches set symbol icons from pokemontcg.io.

Read-only, best-effort: a missing/failed icon must never break a table
render, so every failure mode here returns ``None`` instead of raising.

Unlike card artwork (:mod:`app.catalog.card_image_cache`), the icon URL needs
no API lookup at all: pokemontcg.io serves every set's symbol from a
predictable CDN path keyed by the same ``set_code`` (``set.id``) already
stored on every :class:`~app.models.card.Card` and
:class:`~app.catalog.models.CatalogCard` -- confirmed live for both a modern
(``swsh7``) and a vintage (``base1``) set code.

pokemontcg.io can lag behind for newly released sets, though -- live-confirmed
for "Perfect Order" (released 2026-03-27, user-reported): its icon URL still
404s months later. If ``set_name`` is given and the primary request fails,
this falls back to :func:`app.catalog.tcgdex_set_icon.ensure_tcgdex_set_icon`
before giving up entirely.
"""

from __future__ import annotations

from pathlib import Path

import requests

from app import config
from app.catalog.tcgdex_set_icon import ensure_tcgdex_set_icon
from app.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 10.0
_ICON_URL_TEMPLATE = "https://images.pokemontcg.io/{set_code}/symbol.png"


def ensure_set_icon(
    set_code: str,
    set_name: str = "",
    icons_dir: Path | None = None,
    session: requests.Session | None = None,
) -> str | None:
    """Return a local file path to ``set_code``'s symbol icon, downloading it
    once and reusing the cached copy on subsequent calls for the same set.

    Falls back to tcgdex.dev (see module docstring) if ``set_name`` is given
    and pokemontcg.io's own request fails. Returns ``None`` (logging a
    warning) if there is no set code, or every source fails — never raises.
    """
    if not set_code:
        return None

    directory = icons_dir if icons_dir is not None else config.SET_ICONS_DIR
    dest = directory / f"{set_code}.png"
    if dest.exists():
        return str(dest)

    url = _ICON_URL_TEMPLATE.format(set_code=set_code)
    http = session or requests.Session()
    try:
        response = http.get(url, timeout=_DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Set icon download failed (%s): %s", url, exc)
        return ensure_tcgdex_set_icon(set_name, icons_dir, http)

    directory.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return str(dest)
