"""Tests for the SQL-level sealed product repository."""

from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.enums import Language, PriceQuality
from app.models.sealed_product import SealedProduct, SealedProductDetailsValues, SealedProductFilter


def _repo(temp_db: Database) -> SealedProductRepository:
    return SealedProductRepository(temp_db)


def _new_product(**overrides) -> SealedProduct:
    base = dict(
        id=None,
        name="Base Set Booster Box",
        category="Booster Box",
        language=Language.ENGLISH,
        quantity=1,
        notes="",
        cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
    )
    base.update(overrides)
    return SealedProduct(**base)


def test_create_assigns_id_and_timestamps(temp_db: Database) -> None:
    created = _repo(temp_db).create(_new_product())
    assert created.id is not None
    assert created.created_at is not None
    assert created.updated_at is not None
    assert created.name == "Base Set Booster Box"


def test_get_returns_none_for_missing_id(temp_db: Database) -> None:
    assert _repo(temp_db).get(999) is None


def test_get_round_trips_all_fields(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_product())
    assert repo.get(created.id) == created


def test_update_details_persists_new_values(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_product(quantity=1, notes="alt"))

    repo.update_details(
        created.id,
        SealedProductDetailsValues(
            language=Language.GERMAN,
            quantity=3,
            notes="neu",
            cardmarket_url="https://example.com/other-link",
        ),
    )

    updated = repo.get(created.id)
    assert updated.language is Language.GERMAN
    assert updated.quantity == 3
    assert updated.notes == "neu"
    assert updated.cardmarket_url == "https://example.com/other-link"


def test_delete_removes_product(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_product())
    repo.delete(created.id)
    assert repo.get(created.id) is None


def test_update_price_persists_new_values(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_product())

    repo.update_price(created.id, 120.50, "EUR", PriceQuality.EXACT, "Exakter Treffer", "2026-07-05T00:00:00")

    updated = repo.get(created.id)
    assert updated.current_price == 120.50
    assert updated.price_quality is PriceQuality.EXACT
    assert updated.price_rationale == "Exakter Treffer"


def test_update_price_accepts_none_for_no_price_found(temp_db: Database) -> None:
    repo = _repo(temp_db)
    created = repo.create(_new_product())

    repo.update_price(created.id, None, "EUR", PriceQuality.NO_PRICE, "Kein Preis gefunden", "2026-07-05T00:00:00")

    updated = repo.get(created.id)
    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE


def test_search_with_empty_filter_returns_everything(temp_db: Database) -> None:
    repo = _repo(temp_db)
    repo.create(_new_product(name="Base Set Booster Box"))
    repo.create(_new_product(name="Evolutions ETB"))

    results = repo.search(SealedProductFilter())

    assert len(results) == 2


def test_search_text_matches_name_category_or_notes(temp_db: Database) -> None:
    repo = _repo(temp_db)
    repo.create(_new_product(name="Base Set Booster Box", category="Booster Box"))
    repo.create(_new_product(name="Evolutions ETB", category="Elite Trainer Box"))

    by_name = repo.search(SealedProductFilter(search_text="Base Set"))
    by_category = repo.search(SealedProductFilter(search_text="Elite Trainer"))

    assert [p.name for p in by_name] == ["Base Set Booster Box"]
    assert [p.name for p in by_category] == ["Evolutions ETB"]
