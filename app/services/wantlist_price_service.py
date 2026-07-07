"""Cardmarket price lookup + persistence for wantlist items.

Reuses :meth:`~app.services.price_service.PriceService.determine_price` --
the same condition/language/extras matching ladder owned cards use -- via an
ephemeral :class:`~app.models.card.Card` built from the wantlist item's own
fields, rather than duplicating that logic (see ``determine_price``'s own
docstring for why). Unlike owned cards, a wantlist item's ``cardmarket_url``
is always a directly pasted link (mirrors sealed products), so none of
``update_price_for_card``'s catalogue/shortlink-resolution wrapper logic is
needed here -- this mirrors ``sealed_price_service.py``'s own shape instead.

No price-history table of its own (see the migration's own docstring): only
the latest determination is kept, since there's no "value over time" to
track for something not owned yet.
"""

from __future__ import annotations

from app.database.repositories.wantlist_repository import WantlistRepository
from app.logging_config import get_logger
from app.models.card import Card
from app.models.enums import PriceQuality
from app.models.wantlist import WantlistItem
from app.services.exceptions import WantlistItemNotFoundError
from app.services.price_service import PriceService
from app.utils.time import utc_now_iso

logger = get_logger(__name__)

_CURRENCY = "EUR"


class WantlistPriceService:
    """Determines and persists a wantlist item's current Cardmarket price."""

    def __init__(self, repository: WantlistRepository, price_service: PriceService) -> None:
        self._repo = repository
        self._pricing = price_service

    def update_price_for_item(self, item_id: int) -> WantlistItem:
        """Look up and persist the current Cardmarket price for a wantlist item.

        Raises:
            WantlistItemNotFoundError: If the item does not exist.
        """
        item = self._repo.get(item_id)
        if item is None:
            raise WantlistItemNotFoundError(item_id)

        if item.cardmarket_url is None:
            return self._record(
                item, None, PriceQuality.NO_PRICE, "No Cardmarket link set for this wantlist item."
            )

        ephemeral_card = Card(
            id=None,
            collection_id=0,
            name=item.name,
            set_name=item.set_name,
            card_number=item.card_number,
            language=item.language,
            condition=item.condition,
        )
        price, quality, rationale = self._pricing.determine_price(
            ephemeral_card, item.cardmarket_url
        )
        return self._record(item, price, quality, rationale)

    def _record(
        self, item: WantlistItem, price: float | None, quality: PriceQuality, rationale: str
    ) -> WantlistItem:
        updated_at = utc_now_iso()
        self._repo.update_price(item.id, price, _CURRENCY, quality, rationale, updated_at)
        logger.info(
            "Wantlist item price updated: id=%s quality=%s price=%s", item.id, quality.value, price
        )
        return self._repo.get(item.id)
