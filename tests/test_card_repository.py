"""Tests for the SQL-level card repository."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.models.card import Card, CardFilter
from app.models.enums import Condition, Language, PriceQuality, Variant


@pytest.fixture
def repo(temp_db: Database) -> CardRepository:
    return CardRepository(temp_db)


@pytest.fixture
def collection_id(temp_db: Database) -> int:
    return CollectionRepository(temp_db).create("Binder").id


def _new_card(collection_id: int, **overrides) -> Card:
    base = dict(
        id=None,
        collection_id=collection_id,
        name="Xatu",
        set_name="Skyridge",
        set_code="skg",
        card_number="H32",
        variant=Variant.HOLO,
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
        external_card_id="skg-h32",
    )
    base.update(overrides)
    return Card(**base)


def test_create_assigns_id_and_timestamps(repo: CardRepository, collection_id: int) -> None:
    created = repo.create(_new_card(collection_id))
    assert created.id is not None
    assert created.created_at is not None
    assert created.updated_at is not None
    assert created.name == "Xatu"


def test_get_returns_none_for_missing_id(repo: CardRepository) -> None:
    assert repo.get(999) is None


def test_get_round_trips_all_fields(repo: CardRepository, collection_id: int) -> None:
    created = repo.create(_new_card(collection_id))
    fetched = repo.get(created.id)
    assert fetched == created


def test_list_by_collection_returns_only_its_own_cards(
    repo: CardRepository, temp_db: Database
) -> None:
    other_collection_id = CollectionRepository(temp_db).create("Vintage").id
    binder_id = CollectionRepository(temp_db).create("Binder 2").id
    repo.create(_new_card(binder_id, name="Xatu"))
    repo.create(_new_card(other_collection_id, name="Charizard"))

    names = [c.name for c in repo.list_by_collection(binder_id)]

    assert names == ["Xatu"]


def test_update_details_persists_new_values(repo: CardRepository, collection_id: int) -> None:
    created = repo.create(_new_card(collection_id, quantity=1, notes="alt"))

    repo.update_details(
        created.id,
        variant=Variant.REVERSE_HOLO,
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        quantity=3,
        notes="neu",
    )

    updated = repo.get(created.id)
    assert updated.variant is Variant.REVERSE_HOLO
    assert updated.language is Language.GERMAN
    assert updated.condition is Condition.EXCELLENT
    assert updated.quantity == 3
    assert updated.notes == "neu"


def test_delete_removes_card(repo: CardRepository, collection_id: int) -> None:
    created = repo.create(_new_card(collection_id))
    repo.delete(created.id)
    assert repo.get(created.id) is None


def test_update_price_persists_new_values(repo: CardRepository, collection_id: int) -> None:
    created = repo.create(_new_card(collection_id))

    repo.update_price(
        created.id,
        price=13.90,
        currency="EUR",
        quality=PriceQuality.EXACT,
        rationale="Exakter Treffer: DE, NM",
        updated_at="2026-07-03T12:00:00Z",
    )

    updated = repo.get(created.id)
    assert updated.current_price == 13.90
    assert updated.price_currency == "EUR"
    assert updated.price_quality is PriceQuality.EXACT
    assert updated.price_rationale == "Exakter Treffer: DE, NM"
    assert updated.price_updated_at == "2026-07-03T12:00:00Z"


def test_update_price_accepts_none_for_no_price_found(
    repo: CardRepository, collection_id: int
) -> None:
    created = repo.create(_new_card(collection_id))

    repo.update_price(
        created.id,
        price=None,
        currency="EUR",
        quality=PriceQuality.NO_PRICE,
        rationale="Keine Angebote gefunden.",
        updated_at="2026-07-03T12:00:00Z",
    )

    updated = repo.get(created.id)
    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE


def test_update_cardmarket_url_persists(repo: CardRepository, collection_id: int) -> None:
    created = repo.create(_new_card(collection_id))

    repo.update_cardmarket_url(created.id, "https://prices.pokemontcg.io/cardmarket/skg-h32")

    updated = repo.get(created.id)
    assert updated.cardmarket_url == "https://prices.pokemontcg.io/cardmarket/skg-h32"


# -- search() ---------------------------------------------------------------- #


def test_search_with_empty_filter_returns_everything_in_scope(
    repo: CardRepository, collection_id: int
) -> None:
    repo.create(_new_card(collection_id, name="Xatu"))
    repo.create(_new_card(collection_id, name="Charizard"))

    names = {c.name for c in repo.search(CardFilter(collection_id=collection_id))}

    assert names == {"Xatu", "Charizard"}


def test_search_collection_id_none_spans_every_collection(
    repo: CardRepository, temp_db: Database
) -> None:
    binder_id = CollectionRepository(temp_db).create("Binder 3").id
    vintage_id = CollectionRepository(temp_db).create("Vintage 2").id
    repo.create(_new_card(binder_id, name="Xatu"))
    repo.create(_new_card(vintage_id, name="Charizard"))

    names = {c.name for c in repo.search(CardFilter(collection_id=None))}

    assert names == {"Xatu", "Charizard"}


def test_search_text_matches_name_set_number_or_notes(
    repo: CardRepository, collection_id: int
) -> None:
    repo.create(_new_card(collection_id, name="Xatu", notes="PSA 9"))
    repo.create(_new_card(collection_id, name="Charizard", notes=""))

    by_name = repo.search(CardFilter(collection_id=collection_id, search_text="xatu"))
    by_notes = repo.search(CardFilter(collection_id=collection_id, search_text="psa"))

    assert [c.name for c in by_name] == ["Xatu"]
    assert [c.name for c in by_notes] == ["Xatu"]


def test_search_filters_by_set_language_variant_condition(
    repo: CardRepository, collection_id: int
) -> None:
    repo.create(
        _new_card(
            collection_id,
            name="Xatu",
            set_name="Skyridge",
            language=Language.GERMAN,
            variant=Variant.REVERSE_HOLO,
            condition=Condition.EXCELLENT,
        )
    )
    repo.create(
        _new_card(
            collection_id,
            name="Charizard",
            set_name="Base",
            language=Language.ENGLISH,
            variant=Variant.HOLO,
            condition=Condition.NEAR_MINT,
        )
    )

    assert [c.name for c in repo.search(CardFilter(collection_id=collection_id, set_name="Base"))] == [
        "Charizard"
    ]
    assert [
        c.name for c in repo.search(CardFilter(collection_id=collection_id, language=Language.GERMAN))
    ] == ["Xatu"]
    assert [
        c.name
        for c in repo.search(CardFilter(collection_id=collection_id, variant=Variant.HOLO))
    ] == ["Charizard"]
    assert [
        c.name
        for c in repo.search(
            CardFilter(collection_id=collection_id, condition=Condition.EXCELLENT)
        )
    ] == ["Xatu"]


def test_search_filters_by_price_range(repo: CardRepository, collection_id: int) -> None:
    cheap = repo.create(_new_card(collection_id, name="Cheap"))
    pricey = repo.create(_new_card(collection_id, name="Pricey"))
    repo.update_price(cheap.id, 5.0, "EUR", PriceQuality.EXACT, "", "2026-07-03T00:00:00Z")
    repo.update_price(pricey.id, 500.0, "EUR", PriceQuality.EXACT, "", "2026-07-03T00:00:00Z")

    assert [c.name for c in repo.search(CardFilter(collection_id=collection_id, min_price=100))] == [
        "Pricey"
    ]
    assert [c.name for c in repo.search(CardFilter(collection_id=collection_id, max_price=10))] == [
        "Cheap"
    ]


def test_search_combines_multiple_criteria_with_and(
    repo: CardRepository, collection_id: int
) -> None:
    repo.create(_new_card(collection_id, name="Xatu", language=Language.GERMAN))
    repo.create(_new_card(collection_id, name="Xatu", language=Language.ENGLISH))

    results = repo.search(
        CardFilter(collection_id=collection_id, search_text="xatu", language=Language.GERMAN)
    )

    assert len(results) == 1
    assert results[0].language is Language.GERMAN


# -- distinct_set_names() ----------------------------------------------------- #


def test_distinct_set_names_scoped_to_one_collection(
    repo: CardRepository, temp_db: Database
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage 3").id
    repo.create(_new_card(other_id, name="Charizard", set_name="Base"))
    repo.create(_new_card(other_id, name="Xatu", set_name="Skyridge"))

    assert repo.distinct_set_names(other_id) == ["Base", "Skyridge"]


def test_distinct_set_names_with_none_spans_every_collection(
    repo: CardRepository, temp_db: Database
) -> None:
    a = CollectionRepository(temp_db).create("Binder 4").id
    b = CollectionRepository(temp_db).create("Binder 5").id
    repo.create(_new_card(a, name="Xatu", set_name="Skyridge"))
    repo.create(_new_card(b, name="Charizard", set_name="Base"))

    assert repo.distinct_set_names(None) == ["Base", "Skyridge"]


def test_distinct_set_names_excludes_blank_set_name(
    repo: CardRepository, collection_id: int
) -> None:
    repo.create(_new_card(collection_id, name="No Set", set_name=""))

    assert repo.distinct_set_names(collection_id) == []
