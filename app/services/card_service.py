"""Business logic for managing the cards owned within a collection.

Validates user input (quantity) and translates missing-card lookups into a
typed exception. This is the only layer the GUI is allowed to call into for
card operations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from app import config
from app.catalog.card_image_cache import ensure_card_image
from app.catalog.models import CatalogCard
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.price_repository import PriceRepository
from app.i18n import tr
from app.logging_config import get_logger
from app.models.card import Card, CardDetailsValues, CardFilter
from app.models.enums import PriceQuality
from app.models.price import PriceRecord
from app.services.exceptions import CardNotFoundError, ValidationError
from app.utils.time import utc_now_iso

logger = get_logger(__name__)

_MIN_QUANTITY = 1
_MANUAL_PRICE_CURRENCY = "EUR"
_MANUAL_PRICE_SOURCE = "manual"


def _validate_quantity(quantity: int) -> None:
    if quantity < _MIN_QUANTITY:
        raise ValidationError(
            tr("Die Menge muss mindestens {min_quantity} betragen.").format(
                min_quantity=_MIN_QUANTITY
            )
        )


def _validate_price(price: float) -> None:
    if price <= 0:
        raise ValidationError(tr("Der Preis muss größer als 0 sein."))


def _finalize_photo(card_id: int, temp_photo_path: str | None) -> str | None:
    """Move a manually-entered card's temp screenshot capture into its final,

    id-based filename -- mirrors ``sealed_product_service._finalize_photo``.
    The card's id is only known after ``repository.create()`` returns, so
    the capture (which ran before that) had to land in a temp file first.
    Returns the final path, or ``None`` if there was no temp file to begin
    with, or the move fails (never blocks adding the card over a photo
    problem)."""
    if temp_photo_path is None:
        return None
    temp_path = Path(temp_photo_path)
    if not temp_path.exists():
        return None
    dest = config.PHOTOS_DIR / f"manual_{card_id}{temp_path.suffix}"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp_path.replace(dest)
    except OSError as exc:
        logger.warning("Could not finalize manual card photo for id=%s: %s", card_id, exc)
        return None
    return str(dest)


class CardService:
    """Orchestrates card CRUD with validation and friendly errors."""

    def __init__(
        self,
        repository: CardRepository,
        image_downloader: Callable[[CatalogCard], str | None] = ensure_card_image,
        price_repository: PriceRepository | None = None,
    ) -> None:
        self._repo = repository
        self._image_downloader = image_downloader
        self._prices = price_repository

    def list_cards(self, collection_id: int) -> list[Card]:
        """Return all cards owned in a collection."""
        return self._repo.list_by_collection(collection_id)

    def search_cards(self, card_filter: CardFilter) -> list[Card]:
        """Return cards matching every set criterion in ``card_filter``."""
        return self._repo.search(card_filter)

    def list_set_names(self, collection_id: int | None) -> list[str]:
        """Return the distinct set names in scope, for populating a filter."""
        return self._repo.distinct_set_names(collection_id)

    def find_duplicates(
        self, name: str, set_name: str, card_number: str, values: CardDetailsValues
    ) -> list[Card]:
        """Already-owned cards that look like the same physical card, in any

        collection -- matched case-insensitively on name/set, exactly on
        everything else (number/language/condition/extras). Used to warn
        (never block) before adding what might be an accidental re-entry of
        a card already owned; the actual "is this a real duplicate" call is
        the user's, since owning several genuine copies is completely
        normal too (see ``quantity``).
        """
        name_key = name.strip().casefold()
        set_key = set_name.strip().casefold()
        number_key = card_number.strip()
        return [
            card
            for card in self._repo.search(CardFilter(collection_id=None))
            if card.name.strip().casefold() == name_key
            and card.set_name.strip().casefold() == set_key
            and card.card_number.strip() == number_key
            and card.language is values.language
            and card.condition is values.condition
            and card.is_reverse_holo == values.is_reverse_holo
            and card.is_signed == values.is_signed
            and card.is_first_edition == values.is_first_edition
            and card.is_altered == values.is_altered
        ]

    def get_card(self, card_id: int) -> Card:
        """Return a card by id.

        Raises:
            CardNotFoundError: If no such card exists.
        """
        card = self._repo.get(card_id)
        if card is None:
            raise CardNotFoundError(card_id)
        return card

    def add_card_from_catalog(
        self, collection_id: int, catalog_card: CatalogCard, values: CardDetailsValues
    ) -> Card:
        """Add a new owned card, identified by a catalogue search match.

        Raises:
            ValidationError: If ``values.quantity`` is less than 1.
        """
        _validate_quantity(values.quantity)
        photo_path = self._image_downloader(catalog_card)
        new_card = Card(
            id=None,
            collection_id=collection_id,
            name=catalog_card.name,
            set_name=catalog_card.set_name,
            set_code=catalog_card.set_code,
            card_number=catalog_card.card_number,
            language=values.language,
            condition=values.condition,
            is_reverse_holo=values.is_reverse_holo,
            is_signed=values.is_signed,
            is_first_edition=values.is_first_edition,
            is_altered=values.is_altered,
            quantity=values.quantity,
            notes=values.notes,
            photo_path=photo_path,
            external_card_id=catalog_card.external_id,
            cardmarket_url=catalog_card.cardmarket_url,
            manual_cardmarket_url=values.manual_cardmarket_url,
        )
        card = self._repo.create(new_card)
        logger.info(
            "Card added: %s (id=%s, collection_id=%s)", card.name, card.id, collection_id
        )
        return card

    def add_card_manual(
        self,
        collection_id: int,
        name: str,
        set_name: str,
        card_number: str,
        values: CardDetailsValues,
        temp_photo_path: str | None = None,
        set_code: str = "",
    ) -> Card:
        """Add a new owned card identified directly by a Cardmarket product link.

        Bypasses the catalogue entirely -- for vintage multi-version
        products, JP/KO/ZH prints, or any other case where automatic
        catalogue matching would pick the wrong product.
        ``values.manual_cardmarket_url`` is stored as the card's own
        override (never the plain ``cardmarket_url``, reserved for
        catalogue matches), so price lookups use exactly the product page
        the user confirmed, with no matching heuristics involved at all.

        There is no catalogue image for a manually-entered card, so
        ``temp_photo_path`` (if given, from a best-effort screenshot capture
        taken during the lookup -- see ``app.pricing.sealed_image_capture``,
        reused as-is) is moved into its final, id-based location once the
        new card's real id is known. ``set_code`` (if resolved -- see
        ``PokemonTcgClient.resolve_set_code``) lets the card show the same
        set icon a catalogue-matched card gets, even without a full
        catalogue match; blank is a normal, harmless outcome (no icon).

        Raises:
            ValidationError: If ``values.quantity`` is less than 1.
        """
        _validate_quantity(values.quantity)
        new_card = Card(
            id=None,
            collection_id=collection_id,
            name=name,
            set_name=set_name,
            set_code=set_code,
            card_number=card_number,
            language=values.language,
            condition=values.condition,
            is_reverse_holo=values.is_reverse_holo,
            is_signed=values.is_signed,
            is_first_edition=values.is_first_edition,
            is_altered=values.is_altered,
            quantity=values.quantity,
            notes=values.notes,
            manual_cardmarket_url=values.manual_cardmarket_url,
        )
        card = self._repo.create(new_card)
        photo_path = _finalize_photo(card.id, temp_photo_path)
        if photo_path is not None:
            self._repo.update_photo_path(card.id, photo_path)
            card = replace(card, photo_path=photo_path)
        logger.info(
            "Card added manually via Cardmarket link: %s (id=%s, collection_id=%s)",
            card.name, card.id, collection_id,
        )
        return card

    def update_card_details(self, card_id: int, values: CardDetailsValues) -> None:
        """Update the owned-copy attributes of an existing card.

        Raises:
            ValidationError: If ``values.quantity`` is less than 1.
            CardNotFoundError: If the card does not exist.
        """
        self.get_card(card_id)  # raises CardNotFoundError
        _validate_quantity(values.quantity)
        self._repo.update_details(card_id, values)
        logger.info("Card details updated: id=%s", card_id)

    def set_manual_cardmarket_url(self, card_id: int, manual_cardmarket_url: str) -> None:
        """Set a card's own Cardmarket link override, e.g. once the user has

        confirmed a result from the "Cardmarket-Link suchen" flow.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        self.get_card(card_id)  # raises CardNotFoundError
        self._repo.update_manual_cardmarket_url(card_id, manual_cardmarket_url)
        logger.info("Manual Cardmarket URL set via search: id=%s", card_id)

    def set_manual_price(self, card_id: int, price: float) -> Card:
        """Overrides a card's price with a user-supplied value.

        For cases where the automatic Cardmarket matching picked a
        mislabeled listing (e.g. a seller listing a PSA 1 graded card as
        "Near Mint" condition, live-reported) and the user knows the actual
        price better than another automated lookup would find. Recorded
        with :class:`~app.models.enums.PriceQuality.MANUAL` (shown in the UI
        the same as any other quality tier) and added to the price history
        like any other update, so it still shows up in the trend graph.

        Raises:
            CardNotFoundError: If the card does not exist.
            ValidationError: If ``price`` isn't a positive number.
        """
        self.get_card(card_id)  # raises CardNotFoundError
        _validate_price(price)
        now = utc_now_iso()
        self._repo.update_price(
            card_id, price, _MANUAL_PRICE_CURRENCY, PriceQuality.MANUAL, tr("Manuell eingetragen"), now
        )
        if self._prices is not None:
            self._prices.add_record(
                PriceRecord(
                    id=None,
                    card_id=card_id,
                    price=price,
                    currency=_MANUAL_PRICE_CURRENCY,
                    price_quality=PriceQuality.MANUAL,
                    rationale=tr("Manuell eingetragen"),
                    source=_MANUAL_PRICE_SOURCE,
                )
            )
        logger.info("Manual price set: card id=%s price=%s", card_id, price)
        return self.get_card(card_id)

    def remove_card(self, card_id: int) -> None:
        """Delete a card.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        self.get_card(card_id)  # raises CardNotFoundError
        self._repo.delete(card_id)
        logger.info("Card removed: id=%s", card_id)

    def move_card(self, card_id: int, target_collection_id: int) -> None:
        """Move a card to a different collection.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        self.get_card(card_id)  # raises CardNotFoundError
        self._repo.move(card_id, target_collection_id)
        logger.info("Card moved: id=%s -> collection_id=%s", card_id, target_collection_id)
