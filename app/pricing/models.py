"""Data transfer objects for scraped Cardmarket marketplace data."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import Condition, Language


@dataclass(frozen=True, slots=True)
class CardmarketOffer:
    """A single seller offer read from a Cardmarket product page.

    ``condition``/``language`` are ``None`` when the row couldn't be mapped
    to a known value (e.g. an unrecognised flag) — such offers still count
    towards the ``AVERAGE`` price-quality fallback, just not towards an
    exact or partial match.
    """

    seller: str
    condition: Condition | None
    language: Language | None
    price: float
    comment: str = ""
