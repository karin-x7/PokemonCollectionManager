"""The :class:`WantlistItem` domain object.

Represents a card the user does *not* yet own but wants to buy once its
Cardmarket price drops to (or below) a target -- deliberately separate from
:class:`~app.models.card.Card`: a wantlist entry has a ``target_price`` and
no ``quantity``/``photo_path``/collection membership, and is always
identified by a directly pasted Cardmarket link (mirrors
:class:`~app.models.sealed_product.SealedProduct` in that respect -- there's
no catalogue-search integration for wantlist entries in this first version).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import Condition, Language, PriceQuality


@dataclass(slots=True)
class WantlistItem:
    """A single card the user wants to buy once its price drops far enough."""

    id: int | None
    name: str

    set_name: str = ""
    card_number: str = ""
    language: Language = Language.ENGLISH
    condition: Condition = Condition.NEAR_MINT

    #: Buy once the current price is at or below this.
    target_price: float = 0.0
    notes: str = ""

    #: Always the user-pasted Cardmarket link -- there is no pokemontcg.io-
    #: style catalogue integration for wantlist entries (mirrors
    #: SealedProduct.cardmarket_url).
    cardmarket_url: str | None = None

    current_price: float | None = None
    price_currency: str = "EUR"
    price_quality: PriceQuality = field(default=PriceQuality.NO_PRICE)
    price_rationale: str | None = None
    price_updated_at: str | None = None

    created_at: str | None = None
    updated_at: str | None = None

    @property
    def is_below_target(self) -> bool:
        """Whether the last known price has reached the target -- the "alert"."""
        return self.current_price is not None and self.current_price <= self.target_price


@dataclass(frozen=True, slots=True)
class WantlistItemDetailsValues:
    """The user-editable subset of a wantlist entry's attributes.

    Shared between the entry dialog (collects them) and
    :class:`~app.services.wantlist_service.WantlistService` (persists them),
    for both adding and editing -- mirrors ``SealedProductDetailsValues``.
    """

    language: Language
    condition: Condition
    target_price: float
    notes: str = ""
    cardmarket_url: str | None = None
