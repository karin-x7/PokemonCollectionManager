"""Tests for the SQL-level sealed product price history repository.

Mirrors ``test_price_repository.py``, ``card_id`` swapped for
``sealed_product_id``.
"""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.enums import PriceQuality
from app.models.sealed_price import SealedPriceRecord
from app.models.sealed_product import SealedProduct


@pytest.fixture
def repo(temp_db: Database) -> SealedPriceRepository:
    return SealedPriceRepository(temp_db)


@pytest.fixture
def product_id(temp_db: Database) -> int:
    product = SealedProductRepository(temp_db).create(
        SealedProduct(id=None, name="Base Set Booster Box", category="Booster Box")
    )
    return product.id


def test_add_record_assigns_id_and_recorded_at(
    repo: SealedPriceRepository, product_id: int
) -> None:
    record = repo.add_record(
        SealedPriceRecord(
            id=None, sealed_product_id=product_id, price=120.0, price_quality=PriceQuality.EXACT
        )
    )

    assert record.id is not None
    assert record.recorded_at is not None
    assert record.price == 120.0


def test_add_record_keeps_explicit_recorded_at(
    repo: SealedPriceRepository, product_id: int
) -> None:
    record = repo.add_record(
        SealedPriceRecord(
            id=None,
            sealed_product_id=product_id,
            price=100.0,
            recorded_at="2026-01-01T00:00:00Z",
        )
    )

    assert record.recorded_at == "2026-01-01T00:00:00Z"


def test_list_for_product_returns_oldest_first(
    repo: SealedPriceRepository, product_id: int
) -> None:
    repo.add_record(SealedPriceRecord(id=None, sealed_product_id=product_id, price=100.0))
    repo.add_record(SealedPriceRecord(id=None, sealed_product_id=product_id, price=120.0))

    prices = [r.price for r in repo.list_for_product(product_id)]

    assert prices == [100.0, 120.0]


def test_list_for_product_returns_only_its_own_records(
    repo: SealedPriceRepository, temp_db: Database, product_id: int
) -> None:
    other_product_id = SealedProductRepository(temp_db).create(
        SealedProduct(id=None, name="Evolutions ETB", category="Elite Trainer Box")
    ).id
    repo.add_record(SealedPriceRecord(id=None, sealed_product_id=product_id, price=100.0))
    repo.add_record(SealedPriceRecord(id=None, sealed_product_id=other_product_id, price=999.0))

    prices = [r.price for r in repo.list_for_product(product_id)]

    assert prices == [100.0]


def test_delete_for_product_removes_only_its_own_records(
    repo: SealedPriceRepository, temp_db: Database, product_id: int
) -> None:
    other_product_id = SealedProductRepository(temp_db).create(
        SealedProduct(id=None, name="Evolutions ETB", category="Elite Trainer Box")
    ).id
    repo.add_record(SealedPriceRecord(id=None, sealed_product_id=product_id, price=100.0))
    repo.add_record(SealedPriceRecord(id=None, sealed_product_id=other_product_id, price=999.0))

    repo.delete_for_product(product_id)

    assert repo.list_for_product(product_id) == []
    assert [r.price for r in repo.list_for_product(other_product_id)] == [999.0]


def test_delete_for_product_with_no_history_is_a_no_op(
    repo: SealedPriceRepository, product_id: int
) -> None:
    repo.delete_for_product(product_id)  # must not raise

    assert repo.list_for_product(product_id) == []
