"""Tests for StatisticsService's aggregation logic (Schritt 10)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality
from app.models.price import PriceRecord
from app.models.sealed_price import SealedPriceRecord
from app.models.sealed_product import SealedProduct
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.sealed_product_service import SealedProductService
from app.services.statistics_service import (
    STALE_PRICE_THRESHOLD_DAYS,
    StatisticsService,
    value_over_time,
)

_FIXED_NOW = datetime(2026, 7, 4, tzinfo=timezone.utc)


@pytest.fixture
def cards(temp_db: Database) -> CardRepository:
    return CardRepository(temp_db)


@pytest.fixture
def prices(temp_db: Database) -> PriceRepository:
    return PriceRepository(temp_db)


@pytest.fixture
def collections(temp_db: Database) -> CollectionRepository:
    return CollectionRepository(temp_db)


@pytest.fixture
def sealed_products(temp_db: Database) -> SealedProductRepository:
    return SealedProductRepository(temp_db)


@pytest.fixture
def service(temp_db: Database) -> StatisticsService:
    return StatisticsService(
        CardService(CardRepository(temp_db), image_downloader=lambda _card: None),
        CollectionService(CollectionRepository(temp_db)),
        PriceRepository(temp_db),
        SealedProductService(SealedProductRepository(temp_db)),
        SealedPriceRepository(temp_db),
        now=lambda: _FIXED_NOW,
    )


def _card(collection_id: int, **overrides) -> Card:
    base = dict(
        id=None,
        collection_id=collection_id,
        name="Xatu",
        set_name="Skyridge",
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        current_price=None,
        price_quality=PriceQuality.NO_PRICE,
    )
    base.update(overrides)
    return Card(**base)


def _sealed(**overrides) -> SealedProduct:
    base = dict(
        id=None,
        name="Base Set Booster Box",
        category="Booster Box",
        language=Language.ENGLISH,
        quantity=1,
        current_price=None,
        price_quality=PriceQuality.NO_PRICE,
    )
    base.update(overrides)
    return SealedProduct(**base)


def test_compute_overview_with_no_cards_at_all(service: StatisticsService) -> None:
    overview = service.compute_overview()

    assert overview.per_collection == []
    assert overview.grand_total == 0.0
    assert overview.combined_total == 0.0
    assert overview.as_of is None
    assert overview.value_by_set == []
    assert overview.most_expensive_cards == []
    assert overview.biggest_price_increase is None
    assert overview.stale_price_cards == []
    assert overview.sealed_total_value == 0.0
    assert overview.sealed_item_count == 0
    assert overview.value_by_sealed_category == []
    assert overview.most_expensive_sealed_products == []
    assert overview.sealed_stale_price_products == []
    assert overview.value_over_time == []


def test_per_collection_totals_and_grand_total(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    vintage = collections.create("Vintage")
    cards.create(_card(binder.id, name="Xatu", current_price=10.0, quantity=2))
    cards.create(_card(binder.id, name="Charizard", current_price=5.0, quantity=1))
    cards.create(_card(vintage.id, name="Venusaur", current_price=100.0, quantity=1))

    overview = service.compute_overview()

    by_name = {summary.name: summary for summary in overview.per_collection}
    assert by_name["Binder"].card_count == 2
    assert by_name["Binder"].total_value == 25.0  # 10*2 + 5*1
    assert by_name["Vintage"].total_value == 100.0
    assert overview.grand_total == 125.0


def test_collection_with_no_cards_still_appears_with_zero_total(
    service: StatisticsService, collections: CollectionRepository
) -> None:
    collections.create("Empty Binder")

    overview = service.compute_overview()

    assert len(overview.per_collection) == 1
    assert overview.per_collection[0].card_count == 0
    assert overview.per_collection[0].total_value == 0.0


def test_cards_without_a_price_count_as_zero_value(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, current_price=None))

    overview = service.compute_overview()

    assert overview.per_collection[0].total_value == 0.0
    assert overview.grand_total == 0.0


def test_value_breakdowns_grouped_and_sorted_descending(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(
        _card(binder.id, set_name="Base", language=Language.GERMAN, current_price=5.0)
    )
    cards.create(
        _card(binder.id, set_name="Skyridge", language=Language.ENGLISH, current_price=50.0)
    )

    overview = service.compute_overview()

    assert [entry.label for entry in overview.value_by_set] == ["Skyridge", "Base"]
    assert [entry.label for entry in overview.value_by_language] == ["English", "German"]


def test_value_by_set_carries_the_set_code_for_its_icon(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(
        _card(binder.id, set_name="Skyridge", set_code="skg", current_price=50.0)
    )

    overview = service.compute_overview()

    assert overview.value_by_set[0].set_code == "skg"
    # Language/condition breakdowns group by something other than the set --
    # they don't have a matching set icon to show, so this stays unset.
    assert overview.value_by_language[0].set_code is None


def test_most_expensive_cards_sorted_descending_and_excludes_unpriced(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, name="Cheap", current_price=5.0))
    cards.create(_card(binder.id, name="Pricey", current_price=500.0))
    cards.create(_card(binder.id, name="Unpriced", current_price=None))

    overview = service.compute_overview()

    names = [card.name for card in overview.most_expensive_cards]
    assert names == ["Pricey", "Cheap"]


def test_most_expensive_cards_capped_at_ten(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    for i in range(12):
        cards.create(_card(binder.id, name=f"Card {i}", current_price=float(i)))

    overview = service.compute_overview()

    assert len(overview.most_expensive_cards) == 10
    assert overview.most_expensive_cards[0].name == "Card 11"


def test_biggest_price_increase_picks_largest_positive_change(
    service: StatisticsService,
    cards: CardRepository,
    collections: CollectionRepository,
    prices: PriceRepository,
) -> None:
    binder = collections.create("Binder")
    small_gain = cards.create(_card(binder.id, name="SmallGain", current_price=11.0))
    big_gain = cards.create(_card(binder.id, name="BigGain", current_price=20.0))
    prices.add_record(PriceRecord(id=None, card_id=small_gain.id, price=10.0))
    prices.add_record(PriceRecord(id=None, card_id=small_gain.id, price=11.0))
    prices.add_record(PriceRecord(id=None, card_id=big_gain.id, price=10.0))
    prices.add_record(PriceRecord(id=None, card_id=big_gain.id, price=20.0))

    overview = service.compute_overview()

    assert overview.biggest_price_increase is not None
    assert overview.biggest_price_increase.card.name == "BigGain"
    assert overview.biggest_price_increase.percent_change == pytest.approx(100.0)


def test_biggest_price_increase_ignores_cards_with_falling_price(
    service: StatisticsService,
    cards: CardRepository,
    collections: CollectionRepository,
    prices: PriceRepository,
) -> None:
    binder = collections.create("Binder")
    falling = cards.create(_card(binder.id, name="Falling", current_price=5.0))
    prices.add_record(PriceRecord(id=None, card_id=falling.id, price=10.0))
    prices.add_record(PriceRecord(id=None, card_id=falling.id, price=5.0))

    overview = service.compute_overview()

    assert overview.biggest_price_increase is None


def test_biggest_price_increase_ignores_cards_with_less_than_two_records(
    service: StatisticsService,
    cards: CardRepository,
    collections: CollectionRepository,
    prices: PriceRepository,
) -> None:
    binder = collections.create("Binder")
    only_one = cards.create(_card(binder.id, name="OnlyOne", current_price=10.0))
    prices.add_record(PriceRecord(id=None, card_id=only_one.id, price=10.0))

    overview = service.compute_overview()

    assert overview.biggest_price_increase is None


def test_as_of_is_the_most_recent_price_update_across_all_cards(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, name="Older", price_updated_at="2026-06-01T00:00:00+00:00"))
    cards.create(_card(binder.id, name="Newer", price_updated_at="2026-07-01T00:00:00+00:00"))

    overview = service.compute_overview()

    assert overview.as_of == "2026-07-01T00:00:00+00:00"


def test_as_of_ignores_cards_never_priced(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, price_updated_at=None))

    overview = service.compute_overview()

    assert overview.as_of is None


def test_stale_price_cards_includes_never_priced_first(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, name="NeverPriced", price_updated_at=None))
    old_timestamp = (_FIXED_NOW - timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 10)).isoformat()
    cards.create(_card(binder.id, name="VeryStale", price_updated_at=old_timestamp))

    overview = service.compute_overview()

    names = [entry.card.name for entry in overview.stale_price_cards]
    assert names == ["NeverPriced", "VeryStale"]
    assert overview.stale_price_cards[0].days_since_update is None
    assert overview.stale_price_cards[1].days_since_update == STALE_PRICE_THRESHOLD_DAYS + 10


def test_stale_price_cards_excludes_recently_updated(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    recent_timestamp = (_FIXED_NOW - timedelta(days=1)).isoformat()
    cards.create(_card(binder.id, name="Fresh", price_updated_at=recent_timestamp))

    overview = service.compute_overview()

    assert overview.stale_price_cards == []


def test_stale_price_cards_sorted_most_overdue_first(
    service: StatisticsService, cards: CardRepository, collections: CollectionRepository
) -> None:
    binder = collections.create("Binder")
    less_stale = (_FIXED_NOW - timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 5)).isoformat()
    more_stale = (_FIXED_NOW - timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 50)).isoformat()
    cards.create(_card(binder.id, name="LessStale", price_updated_at=less_stale))
    cards.create(_card(binder.id, name="MoreStale", price_updated_at=more_stale))

    overview = service.compute_overview()

    names = [entry.card.name for entry in overview.stale_price_cards]
    assert names == ["MoreStale", "LessStale"]


# --- Sealed products (not collection-scoped, see app/models/sealed_product.py) --- #


def test_sealed_total_and_combined_total(
    service: StatisticsService,
    cards: CardRepository,
    collections: CollectionRepository,
    sealed_products: SealedProductRepository,
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, name="Xatu", current_price=10.0, quantity=1))
    sealed_products.create(_sealed(name="Base Set Booster Box", current_price=5000.0, quantity=1))
    sealed_products.create(_sealed(name="Evolutions ETB", current_price=50.0, quantity=2))

    overview = service.compute_overview()

    assert overview.grand_total == 10.0
    assert overview.sealed_total_value == 5100.0  # 5000 + 50*2
    assert overview.combined_total == 5110.0
    assert overview.sealed_item_count == 3  # 1 + 2


def test_sealed_value_by_category_grouped_and_sorted_descending(
    service: StatisticsService, sealed_products: SealedProductRepository
) -> None:
    sealed_products.create(_sealed(name="Tin A", category="Tin", current_price=20.0))
    sealed_products.create(
        _sealed(name="Base Set Booster Box", category="Booster Box", current_price=5000.0)
    )

    overview = service.compute_overview()

    assert [entry.label for entry in overview.value_by_sealed_category] == [
        "Booster Box",
        "Tin",
    ]


def test_most_expensive_sealed_products_sorted_and_excludes_unpriced(
    service: StatisticsService, sealed_products: SealedProductRepository
) -> None:
    sealed_products.create(_sealed(name="Cheap", current_price=5.0))
    sealed_products.create(_sealed(name="Pricey", current_price=5000.0))
    sealed_products.create(_sealed(name="Unpriced", current_price=None))

    overview = service.compute_overview()

    names = [product.name for product in overview.most_expensive_sealed_products]
    assert names == ["Pricey", "Cheap"]


def test_sealed_stale_price_products_includes_never_priced_first(
    service: StatisticsService, sealed_products: SealedProductRepository
) -> None:
    sealed_products.create(_sealed(name="NeverPriced", price_updated_at=None))
    old_timestamp = (_FIXED_NOW - timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 10)).isoformat()
    sealed_products.create(_sealed(name="VeryStale", price_updated_at=old_timestamp))
    recent_timestamp = (_FIXED_NOW - timedelta(days=1)).isoformat()
    sealed_products.create(_sealed(name="Fresh", price_updated_at=recent_timestamp))

    overview = service.compute_overview()

    names = [entry.product.name for entry in overview.sealed_stale_price_products]
    assert names == ["NeverPriced", "VeryStale"]


def _record(card_id: int, price: float, recorded_at: str) -> PriceRecord:
    return PriceRecord(id=None, card_id=card_id, price=price, recorded_at=recorded_at)


def _sealed_record(sealed_product_id: int, price: float, recorded_at: str) -> SealedPriceRecord:
    return SealedPriceRecord(
        id=None, sealed_product_id=sealed_product_id, price=price, recorded_at=recorded_at
    )


def test_value_over_time_is_a_running_total_forward_filled_per_item() -> None:
    xatu = Card(id=1, collection_id=1, name="Xatu", quantity=2)
    charizard = Card(id=2, collection_id=1, name="Charizard", quantity=1)
    card_history = [
        _record(xatu.id, price=10.0, recorded_at="2026-01-01T00:00:00+00:00"),
        _record(charizard.id, price=5.0, recorded_at="2026-01-02T00:00:00+00:00"),
        _record(xatu.id, price=12.0, recorded_at="2026-01-03T00:00:00+00:00"),
    ]

    points = value_over_time([xatu, charizard], [], card_history, [])

    assert [(p.recorded_at, p.total_value) for p in points] == [
        ("2026-01-01T00:00:00+00:00", 20.0),  # 10 * 2 qty
        ("2026-01-02T00:00:00+00:00", 25.0),  # + 5 * 1 qty
        ("2026-01-03T00:00:00+00:00", 29.0),  # xatu 10->12: 24 + 5
    ]


def test_value_over_time_combines_cards_and_sealed_products() -> None:
    card = Card(id=1, collection_id=1, name="Xatu", quantity=1)
    product = SealedProduct(id=1, name="Booster Box", quantity=1)
    card_history = [_record(card.id, price=10.0, recorded_at="2026-01-01T00:00:00+00:00")]
    sealed_history = [_sealed_record(product.id, price=50.0, recorded_at="2026-01-02T00:00:00+00:00")]

    points = value_over_time([card], [product], card_history, sealed_history)

    assert [(p.recorded_at, p.total_value) for p in points] == [
        ("2026-01-01T00:00:00+00:00", 10.0),
        ("2026-01-02T00:00:00+00:00", 60.0),
    ]


def test_value_over_time_ignores_history_for_items_no_longer_owned() -> None:
    card_history = [_record(card_id=999, price=10.0, recorded_at="2026-01-01T00:00:00+00:00")]

    points = value_over_time([], [], card_history, [])

    assert points == []


def test_value_over_time_with_no_history_is_empty() -> None:
    card = Card(id=1, collection_id=1, name="Xatu", quantity=1)

    assert value_over_time([card], [], [], []) == []


def test_compute_overview_populates_value_over_time(
    service: StatisticsService,
    cards: CardRepository,
    collections: CollectionRepository,
    prices: PriceRepository,
) -> None:
    binder = collections.create("Binder")
    card = cards.create(_card(binder.id, name="Xatu", quantity=1))
    prices.add_record(_record(card.id, price=10.0, recorded_at="2026-01-01T00:00:00+00:00"))
    prices.add_record(_record(card.id, price=15.0, recorded_at="2026-01-02T00:00:00+00:00"))

    overview = service.compute_overview()

    assert [(p.recorded_at, p.total_value) for p in overview.value_over_time] == [
        ("2026-01-01T00:00:00+00:00", 10.0),
        ("2026-01-02T00:00:00+00:00", 15.0),
    ]
