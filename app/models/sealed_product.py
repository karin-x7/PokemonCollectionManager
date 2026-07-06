"""The :class:`SealedProduct` domain object.

Represents a single owned sealed product (booster box, elite trainer box,
display, blister, ...) — deliberately separate from :class:`~app.models.
card.Card`: Cardmarket only ever sells these products sealed (no condition
ladder) and they have no card number, so those columns would be empty on
every row if folded into ``cards``. Unlike cards (kept in physical folders/
binders, so a ``collection`` maps naturally onto that), sealed products
aren't organised that way, so they don't belong to a collection at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import Language, PriceQuality


@dataclass(slots=True)
class SealedProduct:
    """A single owned sealed product entry."""

    id: int | None
    name: str

    #: Free text (e.g. "Booster Box", "Elite Trainer Box") -- parsed off
    #: Cardmarket's own breadcrumb where possible, not a fixed enum: there
    #: are too many product types to enumerate up front.
    category: str = ""
    language: Language = Language.ENGLISH

    quantity: int = 1
    notes: str = ""

    #: Always the user-pasted Cardmarket link -- there is no pokemontcg.io-
    #: style catalogue for sealed products, so "manuell eintragen" is the
    #: only way to add one.
    cardmarket_url: str | None = None

    #: Local file path to a product photo, best-effort screenshot-captured
    #: from Cardmarket at add time (there's no pokemontcg.io-style image API
    #: for sealed products) -- ``None`` if the capture failed or hasn't run.
    photo_path: str | None = None

    current_price: float | None = None
    price_currency: str = "EUR"
    price_quality: PriceQuality = field(default=PriceQuality.NO_PRICE)
    price_rationale: str | None = None
    price_updated_at: str | None = None

    created_at: str | None = None
    updated_at: str | None = None

    @property
    def total_value(self) -> float | None:
        """Combined value of all copies (``current_price * quantity``)."""
        if self.current_price is None:
            return None
        return round(self.current_price * self.quantity, 2)


@dataclass(frozen=True, slots=True)
class SealedProductDetailsValues:
    """The user-editable subset of a sealed product's attributes.

    Shared between the details dialog (collects them) and
    :class:`~app.services.sealed_product_service.SealedProductService`
    (persists them), for both adding and editing.
    """

    language: Language
    quantity: int
    notes: str = ""
    cardmarket_url: str | None = None


@dataclass(frozen=True, slots=True)
class SealedProductFilter:
    """Criteria for :meth:`~app.services.sealed_product_service.
    SealedProductService.search_products`.

    Every field left at its default is simply not filtered on.
    """

    search_text: str = ""
