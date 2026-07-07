"""Tests for the SQL-level wantlist repository."""

from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.wantlist_repository import WantlistRepository
from app.models.enums import Condition, Language, PriceQuality
from app.models.wantlist import WantlistItem, WantlistItemDetailsValues


def _repo(temp_db: Database) -> WantlistRepository:
    return WantlistRepository(temp_db)


def _new_item(**overrides) -> WantlistItem:
    base = dict(
        id=None,
        name="Charizard",
        set_name="Base Set",
        card_number="4",
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        target_price=500.0,
        notes="",
        cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard",
    )
    base.update(overrides)
    return WantlistItem(**base)


def test_create_assigns_id_and_timestamps(temp_db: Database) -> None:
    created = _repo(temp_db).create(_new_item())
    assert created.id is not None
    assert created.created_at is not None
    assert created.updated_at is not None
    assert created.name == "Charizard"


def test_get_returns_none_for_missing_id(temp_db: Database) -> None:
    assert _repo(temp_db).get(999) is None


def test_get_round_trips_all_fields(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_item())
    assert repo.get(created.id) == created


def test_list_all_returns_newest_first(temp_db: Database) -> None:
    repo = _repo(temp_db)
    first = repo.create(_new_item(name="Charizard"))
    second = repo.create(_new_item(name="Blastoise"))

    results = repo.list_all()

    assert [item.id for item in results] == [second.id, first.id]


def test_update_details_persists_new_values(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_item(target_price=500.0, notes="alt"))

    repo.update_details(
        created.id,
        WantlistItemDetailsValues(
            language=Language.GERMAN,
            condition=Condition.LIGHT_PLAYED,
            target_price=300.0,
            notes="neu",
            cardmarket_url="https://example.com/other-link",
        ),
    )

    updated = repo.get(created.id)
    assert updated.language is Language.GERMAN
    assert updated.condition is Condition.LIGHT_PLAYED
    assert updated.target_price == 300.0
    assert updated.notes == "neu"
    assert updated.cardmarket_url == "https://example.com/other-link"


def test_delete_removes_item(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_item())
    repo.delete(created.id)
    assert repo.get(created.id) is None


def test_update_price_persists_new_values(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_item())

    repo.update_price(
        created.id, 450.0, "EUR", PriceQuality.EXACT, "Exact match", "2026-07-05T00:00:00"
    )

    updated = repo.get(created.id)
    assert updated.current_price == 450.0
    assert updated.price_quality is PriceQuality.EXACT
    assert updated.price_rationale == "Exact match"


def test_update_price_accepts_none_for_no_price_found(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_item())

    repo.update_price(
        created.id, None, "EUR", PriceQuality.NO_PRICE, "No price found", "2026-07-05T00:00:00"
    )

    updated = repo.get(created.id)
    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
