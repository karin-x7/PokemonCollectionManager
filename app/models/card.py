"""The :class:`Card` domain object.

Represents a single owned card entry within a collection, including its
identifying attributes (name/set/number/language/condition/extras) and the
most recently determined Cardmarket-based price together with the reasoning
behind it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import Condition, Language, PriceQuality


@dataclass(slots=True)
class Card:
    """A single owned card entry.

    The identity attributes (``name``, ``set_code``, ``card_number``,
    ``language``, ``condition``, plus the "extras" below) are exactly those
    the pricing engine matches on for an "exact" Cardmarket hit.
    """

    id: int | None
    collection_id: int
    name: str

    # Identity / catalogue attributes.
    set_name: str = ""
    set_code: str = ""
    card_number: str = ""
    language: Language = Language.ENGLISH
    condition: Condition = Condition.NEAR_MINT

    # Extras. Each an independent yes/no, matching how Cardmarket itself
    # treats them (``extra[isSigned]``/``extra[isFirstEd]``/
    # ``extra[isAltered]`` filters) — a real card can be any combination,
    # e.g. signed *and* reverse holo at once. Reverse Holo has no Cardmarket
    # filter equivalent (not exposed on the product page at all); it's kept
    # here purely for the collector's own record and the artwork overlay.
    is_reverse_holo: bool = False
    is_signed: bool = False
    is_first_edition: bool = False
    is_altered: bool = False

    # Ownership attributes.
    quantity: int = 1
    notes: str = ""
    photo_path: str | None = None

    # Links to external catalogue / marketplace.
    external_card_id: str | None = None
    cardmarket_url: str | None = None

    # Latest price snapshot (full history lives in ``price_history``).
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
class CardDetailsValues:
    """The user-editable subset of a card's attributes.

    Shared between :class:`~app.ui.dialogs.card_details_dialog.
    CardDetailsDialog` (collects them) and :class:`~app.services.
    card_service.CardService` (persists them) for both adding a new card and
    editing an existing one.
    """

    language: Language
    condition: Condition
    quantity: int
    notes: str = ""
    is_reverse_holo: bool = False
    is_signed: bool = False
    is_first_edition: bool = False
    is_altered: bool = False


@dataclass(frozen=True, slots=True)
class CardFilter:
    """Criteria for :meth:`~app.services.card_service.CardService.search_cards`.

    Every field left at its default is simply not filtered on. ``collection_id
    = None`` means "search across every collection" — the UI's own per-
    collection view is just this same filter with ``collection_id`` set to
    the currently selected collection.
    """

    collection_id: int | None = None
    search_text: str = ""
    set_name: str | None = None
    language: Language | None = None
    condition: Condition | None = None
    min_price: float | None = None
    max_price: float | None = None
