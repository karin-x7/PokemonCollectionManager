"""Downloads and locally caches card artwork from pokemontcg.io.

Read-only, best-effort: a missing/failed image must never block adding a
card, so every failure mode here returns ``None`` instead of raising.
"""

from __future__ import annotations

from pathlib import Path

import requests

from app import config
from app.catalog.models import CatalogCard
from app.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 10.0


def _safe_filename(external_id: str, url: str) -> str:
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in external_id) or "card"
    suffix = Path(url).suffix or ".png"
    return f"{safe_id}{suffix}"


def ensure_card_image(
    catalog_card: CatalogCard,
    photos_dir: Path | None = None,
    session: requests.Session | None = None,
) -> str | None:
    """Return a local file path to ``catalog_card``'s artwork, downloading it
    once and reusing the cached copy on subsequent calls for the same card.

    Returns ``None`` (logging a warning) if there is no image URL, or the
    download fails — never raises.
    """
    url = catalog_card.image_large_url or catalog_card.image_small_url
    if not url:
        return None

    directory = photos_dir if photos_dir is not None else config.PHOTOS_DIR
    dest = directory / _safe_filename(catalog_card.external_id, url)
    if dest.exists():
        return str(dest)

    try:
        response = (session or requests.Session()).get(url, timeout=_DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Card image download failed (%s): %s", url, exc)
        return None

    directory.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(response.content)
    return str(dest)
