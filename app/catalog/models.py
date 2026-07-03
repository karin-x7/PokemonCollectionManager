"""Data transfer objects for external catalogue lookups.

``CatalogCard`` is a read-only snapshot of a pokemontcg.io catalogue entry —
distinct from ``app.models.card.Card``, which represents an *owned* card
persisted in the local database.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CatalogCard:
    """A single card as known by the external catalogue."""

    external_id: str
    name: str
    set_name: str
    set_code: str
    card_number: str
    rarity: str
    image_small_url: str | None
    image_large_url: str | None
    cardmarket_url: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogSet:
    """A single expansion/set as known by the external catalogue."""

    id: str
    name: str
