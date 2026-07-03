"""Business logic for managing the cards owned within a collection.

Validates user input (quantity) and translates missing-card lookups into a
typed exception. This is the only layer the GUI is allowed to call into for
card operations.
"""

from __future__ import annotations

from collections.abc import Callable

from app.catalog.card_image_cache import ensure_card_image
from app.catalog.models import CatalogCard
from app.database.repositories.card_repository import CardRepository
from app.logging_config import get_logger
from app.models.card import Card, CardDetailsValues, CardFilter
from app.services.exceptions import CardNotFoundError, ValidationError

logger = get_logger(__name__)

_MIN_QUANTITY = 1


def _validate_quantity(quantity: int) -> None:
    if quantity < _MIN_QUANTITY:
        raise ValidationError(f"Die Menge muss mindestens {_MIN_QUANTITY} betragen.")


class CardService:
    """Orchestrates card CRUD with validation and friendly errors."""

    def __init__(
        self,
        repository: CardRepository,
        image_downloader: Callable[[CatalogCard], str | None] = ensure_card_image,
    ) -> None:
        self._repo = repository
        self._image_downloader = image_downloader

    def list_cards(self, collection_id: int) -> list[Card]:
        """Return all cards owned in a collection."""
        return self._repo.list_by_collection(collection_id)

    def search_cards(self, card_filter: CardFilter) -> list[Card]:
        """Return cards matching every set criterion in ``card_filter``."""
        return self._repo.search(card_filter)

    def list_set_names(self, collection_id: int | None) -> list[str]:
        """Return the distinct set names in scope, for populating a filter."""
        return self._repo.distinct_set_names(collection_id)

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
            variant=values.variant,
            language=values.language,
            condition=values.condition,
            quantity=values.quantity,
            notes=values.notes,
            photo_path=photo_path,
            external_card_id=catalog_card.external_id,
            cardmarket_url=catalog_card.cardmarket_url,
        )
        card = self._repo.create(new_card)
        logger.info(
            "Card added: %s (id=%s, collection_id=%s)", card.name, card.id, collection_id
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
        self._repo.update_details(
            card_id, values.variant, values.language, values.condition, values.quantity,
            values.notes,
        )
        logger.info("Card details updated: id=%s", card_id)

    def remove_card(self, card_id: int) -> None:
        """Delete a card.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        self.get_card(card_id)  # raises CardNotFoundError
        self._repo.delete(card_id)
        logger.info("Card removed: id=%s", card_id)
