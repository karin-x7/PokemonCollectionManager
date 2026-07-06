"""Fallback set-symbol icon lookup via tcgdex.dev.

pokemontcg.io (:mod:`app.catalog.set_icon_cache`, the primary source) can
lag behind for newly released sets -- confirmed live for "Perfect Order"
(released 2026-03-27): its own icon URL still 404s months later, while
tcgdex.dev already has a working one for the very same set. This is
consulted only when the primary source's own icon request fails (see
``set_icon_cache.ensure_set_icon``'s own fallback wiring) -- pokemontcg.io
remains the project's primary catalogue source for everything else
(search, card images, set names).

tcgdex uses its own, unrelated set-id scheme (e.g. ``"me03"`` vs.
pokemontcg.io's ``"me3"`` for the same set), so this doesn't try to derive
one id from the other -- it resolves purely by matching pokemontcg.io's own
(already-corrected, see ``pokemontcg_client._EX_SERIES_SET_NAMES``) set
name against tcgdex's own ``/en/sets`` list, the same "match by name, not
id" approach ``pokemontcg_client.resolve_set_code`` already uses in the
opposite direction.
"""

from __future__ import annotations

from pathlib import Path

import requests

from app import config
from app.logging_config import get_logger

logger = get_logger(__name__)

_SETS_URL = "https://api.tcgdex.net/v2/en/sets"
_DEFAULT_TIMEOUT = 10.0

#: Module-level, process-lifetime cache of tcgdex's own set list -- mirrors
#: PokemonTcgClient.list_sets()'s per-instance cache, but this lookup has no
#: natural "client instance" of its own to hang the cache off, since it's
#: only ever used as a narrow, stateless fallback.
_sets_cache: list[dict] | None = None


def _list_tcgdex_sets(session: requests.Session) -> list[dict]:
    global _sets_cache
    if _sets_cache is not None:
        return _sets_cache
    response = session.get(_SETS_URL, timeout=_DEFAULT_TIMEOUT)
    response.raise_for_status()
    _sets_cache = response.json()
    return _sets_cache


def _safe_filename(set_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in set_name.casefold())
    return f"tcgdex_{safe or 'set'}.png"


def ensure_tcgdex_set_icon(
    set_name: str,
    icons_dir: Path | None = None,
    session: requests.Session | None = None,
) -> str | None:
    """Best-effort symbol icon for ``set_name``, downloaded from tcgdex.dev.

    Returns ``None`` (logging a warning) if there's no set name, no
    matching tcgdex set, or any request fails -- never raises, mirrors
    ``set_icon_cache.ensure_set_icon``'s own "never break a table render"
    contract. Cached on disk keyed by the (normalised) set name, since
    callers here only ever know pokemontcg.io's set name, not tcgdex's own
    unrelated set id.
    """
    if not set_name:
        return None

    directory = icons_dir if icons_dir is not None else config.SET_ICONS_DIR
    dest = directory / _safe_filename(set_name)
    if dest.exists():
        return str(dest)

    http = session or requests.Session()
    try:
        sets = _list_tcgdex_sets(http)
    except requests.RequestException as exc:
        logger.warning("tcgdex set list request failed: %s", exc)
        return None

    normalized = set_name.casefold().strip()
    match = next((s for s in sets if s.get("name", "").casefold() == normalized), None)
    if match is None or not match.get("symbol"):
        logger.warning("No tcgdex set icon found for %r.", set_name)
        return None

    try:
        response = http.get(f"{match['symbol']}.png", timeout=_DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("tcgdex set icon download failed (%s): %s", match["symbol"], exc)
        return None

    directory.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return str(dest)
