"""Tests for StatisticsService's aggregation logic (Schritt 10)."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality
from app.models.price import PriceRecord
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.statistics_service import StatisticsService


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
def service(temp_db: Database) -> StatisticsService:
    return StatisticsService(
        CardService(CardRepository(temp_db), image_downloader=lambda _card: None),
        CollectionService(CollectionRepository(temp_db)),
        PriceRepository(temp_db),
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


def test_compute_overview_with_no_cards_at_all(service: StatisticsService) -> None:
    overview = service.compute_overview()

    assert overview.per_collection == []
    assert overview.grand_total == 0.0
    assert overview.value_by_set == []
    assert overview.most_expensive_cards == []
    assert overview.biggest_price_increase is None


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
