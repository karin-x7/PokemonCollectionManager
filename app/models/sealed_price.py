"""The :class:`SealedPriceRecord` domain object — one point in a sealed

product's price history. Mirrors :class:`~app.models.price.PriceRecord`,
``card_id`` swapped for ``sealed_product_id``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import PriceQuality


@dataclass(slots=True)
class SealedPriceRecord:
    """A single historical price observation for a sealed product.

    Attributes:
        id: Primary key; ``None`` for an unsaved record.
        sealed_product_id: Owning sealed product's primary key.
        price: The determined price in ``currency``.
        currency: ISO currency code (Cardmarket trades in EUR).
        price_quality: Provenance/confidence of the price.
        rationale: Human-readable explanation of why this price was used.
        source: Provider that produced the price (e.g. ``"cardmarket"``).
        recorded_at: ISO-8601 UTC timestamp of the observation.
    """

    id: int | None
    sealed_product_id: int
    price: float
    currency: str = "EUR"
    price_quality: PriceQuality = PriceQuality.NO_PRICE
    rationale: str = ""
    source: str = ""
    recorded_at: str | None = None
