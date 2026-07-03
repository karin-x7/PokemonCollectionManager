"""Tests for the SQL-level price history repository."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality, Variant
from app.models.price import PriceRecord


@pytest.fixture
def repo(temp_db: Database) -> PriceRepository:
    return PriceRepository(temp_db)


@pytest.fixture
def card_id(temp_db: Database) -> int:
    collection_id = CollectionRepository(temp_db).create("Binder").id
    card = CardRepository(temp_db).create(
        Card(
            id=None,
            collection_id=collection_id,
            name="Xatu",
            variant=Variant.HOLO,
            language=Language.ENGLISH,
            condition=Condition.NEAR_MINT,
        )
    )
    return card.id


def test_add_record_assigns_id_and_recorded_at(repo: PriceRepository, card_id: int) -> None:
    record = repo.add_record(
        PriceRecord(id=None, card_id=card_id, price=13.90, price_quality=PriceQuality.EXACT)
    )

    assert record.id is not None
    assert record.recorded_at is not None
    assert record.price == 13.90


def test_add_record_keeps_explicit_recorded_at(repo: PriceRepository, card_id: int) -> None:
    record = repo.add_record(
        PriceRecord(
            id=None,
            card_id=card_id,
            price=10.0,
            recorded_at="2026-01-01T00:00:00Z",
        )
    )

    assert record.recorded_at == "2026-01-01T00:00:00Z"


def test_list_for_card_returns_oldest_first(repo: PriceRepository, card_id: int) -> None:
    repo.add_record(PriceRecord(id=None, card_id=card_id, price=10.0))
    repo.add_record(PriceRecord(id=None, card_id=card_id, price=20.0))

    prices = [r.price for r in repo.list_for_card(card_id)]

    assert prices == [10.0, 20.0]


def test_list_for_card_returns_only_its_own_records(
    repo: PriceRepository, temp_db: Database, card_id: int
) -> None:
    collection_id = CollectionRepository(temp_db).create("Vintage").id
    other_card_id = CardRepository(temp_db).create(
        Card(
            id=None,
            collection_id=collection_id,
            name="Charizard",
            variant=Variant.HOLO,
            language=Language.ENGLISH,
            condition=Condition.NEAR_MINT,
        )
    ).id
    repo.add_record(PriceRecord(id=None, card_id=card_id, price=10.0))
    repo.add_record(PriceRecord(id=None, card_id=other_card_id, price=99.0))

    prices = [r.price for r in repo.list_for_card(card_id)]

    assert prices == [10.0]
