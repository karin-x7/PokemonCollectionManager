"""Read-only access to external card catalogues (pokemontcg.io).

Provides card metadata (name, set, number, images) used to power catalogue
search (Step 4). Pricing/marketplace data lives in ``app.cardmarket``.
"""

from __future__ import annotations

from app.catalog.card_image_cache import ensure_card_image
from app.catalog.models import CatalogCard, CatalogSet
from app.catalog.pokemontcg_client import PokemonTcgClient, PokemonTcgClientError

__all__ = [
    "CatalogCard",
    "CatalogSet",
    "PokemonTcgClient",
    "PokemonTcgClientError",
    "ensure_card_image",
]
