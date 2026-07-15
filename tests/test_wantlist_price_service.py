"""Tests for wantlist price lookups: reuses PriceService's own matching ladder.

Mirrors ``test_price_service.py``'s FakeOfferReader approach, but through
``WantlistPriceService`` -- verifies the composition (ephemeral Card built
from the wantlist item's fields, fed into PriceService.determine_price)
actually produces the right price/quality, not the ladder logic itself
(already covered by test_price_service.py).
"""

from __future__ import annotations

import pytest

from app.catalog.pokemontcg_client import PokemonTcgClient
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.price_repository import PriceRepository
from app.database.repositories.wantlist_repository import WantlistRepository
from app.models.enums import Condition, Language, PriceQuality
from app.models.wantlist import WantlistItem
from app.pricing.models import CardmarketOffer
from app.services.exceptions import WantlistItemNotFoundError
from app.services.price_service import PriceService
from app.services.wantlist_price_service import WantlistPriceService

_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard"


class FakeOfferReader:
    def __init__(self, *responses: list[CardmarketOffer]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def __call__(self, url: str, match_hint: str) -> list[CardmarketOffer]:
        self.calls.append(url)
        return self._responses.pop(0) if self._responses else []


def _item(temp_db: Database, **overrides) -> WantlistItem:
    base = dict(
        id=None,
        name="Charizard",
        set_name="Base Set",
        card_number="4",
        language=Language.GERMAN,
        condition=Condition.NEAR_MINT,
        target_price=100.0,
        cardmarket_url=_URL,
    )
    base.update(overrides)
    return WantlistRepository(temp_db).create(WantlistItem(**base))


def _service(temp_db: Database, offer_reader) -> WantlistPriceService:
    pricing = PriceService(
        CardRepository(temp_db),
        PriceRepository(temp_db),
        PokemonTcgClient(),
        offer_reader=offer_reader,
        # No real delay -- these tests must run fast; the real, deliberately
        # noticeable pause is exercised/verified separately (test_price_service.py).
        request_delay=0,
    )
    return WantlistPriceService(WantlistRepository(temp_db), pricing)


def test_missing_item_raises_not_found(temp_db: Database) -> None:
    service = _service(temp_db, FakeOfferReader())
    with pytest.raises(WantlistItemNotFoundError):
        service.update_price_for_item(999)


def test_no_cardmarket_url_yields_no_price_without_reading(temp_db: Database) -> None:
    item = _item(temp_db, cardmarket_url=None)
    reader = FakeOfferReader()
    service = _service(temp_db, reader)

    updated = service.update_price_for_item(item.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
    assert reader.calls == []


def test_exact_match_picks_cheapest_offer_at_the_requested_condition(temp_db: Database) -> None:
    item = _item(temp_db, language=Language.GERMAN, condition=Condition.NEAR_MINT)
    offers = [
        CardmarketOffer(seller="a", language=Language.GERMAN, condition=Condition.NEAR_MINT, price=150.0),
        CardmarketOffer(seller="b", language=Language.GERMAN, condition=Condition.NEAR_MINT, price=120.0),
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_item(item.id)

    assert updated.current_price == 120.0
    assert updated.price_quality is PriceQuality.EXACT


def test_below_target_price_is_reflected_on_the_returned_item(temp_db: Database) -> None:
    item = _item(temp_db, target_price=130.0)
    offers = [CardmarketOffer(seller="a", language=Language.GERMAN, condition=Condition.NEAR_MINT, price=120.0)]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_item(item.id)

    assert updated.is_below_target is True


def test_above_target_price_is_not_flagged(temp_db: Database) -> None:
    item = _item(temp_db, target_price=100.0)
    offers = [CardmarketOffer(seller="a", language=Language.GERMAN, condition=Condition.NEAR_MINT, price=120.0)]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_item(item.id)

    assert updated.is_below_target is False


def test_no_offers_at_all_yields_no_price(temp_db: Database) -> None:
    item = _item(temp_db)
    service = _service(temp_db, FakeOfferReader([]))

    updated = service.update_price_for_item(item.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE


def test_reads_the_items_own_cardmarket_url(temp_db: Database) -> None:
    item = _item(temp_db, cardmarket_url=_URL, language=Language.GERMAN)
    reader = FakeOfferReader(
        [CardmarketOffer(seller="a", language=Language.GERMAN, condition=Condition.NEAR_MINT, price=100.0)]
    )
    service = _service(temp_db, reader)

    service.update_price_for_item(item.id)

    assert reader.calls[0].startswith(_URL)


def test_price_lookup_does_not_create_a_history_record(temp_db: Database) -> None:
    # Unlike cards/sealed products, wantlist items have no price_history
    # table of their own (see migration 9's own docstring) -- only the
    # latest snapshot is kept.
    item = _item(temp_db)
    offers = [CardmarketOffer(seller="a", language=Language.GERMAN, condition=Condition.NEAR_MINT, price=100.0)]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_item(item.id)

    assert updated.current_price == 100.0
    assert PriceRepository(temp_db).list_all() == []
