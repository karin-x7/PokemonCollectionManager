"""Business logic for managing wantlist items (cards not yet owned).

Mirrors ``sealed_product_service.py``: no catalogue-based add path (a
wantlist entry is always identified by a directly pasted Cardmarket link)
and no collection scoping (a global list). Pricing is a separate concern --
see :class:`~app.services.wantlist_price_service.WantlistPriceService`,
mirroring the ``CardService``/``PriceService`` split.
"""

from __future__ import annotations

from dataclasses import replace

from app.database.repositories.wantlist_repository import WantlistRepository
from app.models.wantlist import WantlistItem, WantlistItemDetailsValues
from app.pricing.browser_price_reader import build_filtered_url, supports_language_filter
from app.services.exceptions import ValidationError, WantlistItemNotFoundError

_MIN_TARGET_PRICE = 0.01


def _validate_target_price(target_price: float) -> None:
    if target_price < _MIN_TARGET_PRICE:
        raise ValidationError(f"The target price must be at least {_MIN_TARGET_PRICE}.")


def _with_language_filter(url: str | None, values: WantlistItemDetailsValues) -> str | None:
    """Mirrors ``sealed_product_service._with_language_filter``, using the
    single-card filter (:func:`supports_language_filter`/:func:`build_filtered_url`)
    since a wantlist entry is an individual card, not a sealed product."""
    if url is None or not supports_language_filter(values.language):
        return url
    return build_filtered_url(url, language=values.language)


class WantlistService:
    """Orchestrates wantlist-item CRUD with validation and friendly errors."""

    def __init__(self, repository: WantlistRepository) -> None:
        self._repo = repository

    def list_items(self) -> list[WantlistItem]:
        """Return every wantlist item."""
        return self._repo.list_all()

    def get_item(self, item_id: int) -> WantlistItem:
        """Return a wantlist item by id.

        Raises:
            WantlistItemNotFoundError: If no such item exists.
        """
        item = self._repo.get(item_id)
        if item is None:
            raise WantlistItemNotFoundError(item_id)
        return item

    def add_item(
        self,
        name: str,
        set_name: str,
        card_number: str,
        values: WantlistItemDetailsValues,
    ) -> WantlistItem:
        """Add a new wantlist item, identified by ``values.cardmarket_url``.

        Raises:
            ValidationError: If ``values.target_price`` is not positive.
        """
        _validate_target_price(values.target_price)
        new_item = WantlistItem(
            id=None,
            name=name,
            set_name=set_name,
            card_number=card_number,
            language=values.language,
            condition=values.condition,
            target_price=values.target_price,
            notes=values.notes,
            cardmarket_url=_with_language_filter(values.cardmarket_url, values),
        )
        return self._repo.create(new_item)

    def update_item_details(self, item_id: int, values: WantlistItemDetailsValues) -> None:
        """Update an existing wantlist item's editable attributes.

        Raises:
            ValidationError: If ``values.target_price`` is not positive.
            WantlistItemNotFoundError: If the item does not exist.
        """
        self.get_item(item_id)  # raises WantlistItemNotFoundError
        _validate_target_price(values.target_price)
        values = replace(values, cardmarket_url=_with_language_filter(values.cardmarket_url, values))
        self._repo.update_details(item_id, values)

    def remove_item(self, item_id: int) -> None:
        """Delete a wantlist item.

        Raises:
            WantlistItemNotFoundError: If the item does not exist.
        """
        self.get_item(item_id)  # raises WantlistItemNotFoundError
        self._repo.delete(item_id)
