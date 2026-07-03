"""The :class:`PriceRecord` domain object — one point in a card's price history.

Every price update appends a record, which together form the price history
that later feeds the trend charts and "largest price increase" statistics.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import PriceQuality


@dataclass(slots=True)
class PriceRecord:
    """A single historical price observation for a card.

    Attributes:
        id: Primary key; ``None`` for an unsaved record.
        card_id: Owning card's primary key.
        price: The determined price in ``currency``.
        currency: ISO currency code (Cardmarket trades in EUR).
        price_quality: Provenance/confidence of the price.
        rationale: Human-readable explanation of why this price was used.
        source: Provider that produced the price (e.g. ``"pokemontcg.io"``).
        recorded_at: ISO-8601 UTC timestamp of the observation.
    """

    id: int | None
    card_id: int
    price: float
    currency: str = "EUR"
    price_quality: PriceQuality = PriceQuality.NO_PRICE
    rationale: str = ""
    source: str = ""
    recorded_at: str | None = None
