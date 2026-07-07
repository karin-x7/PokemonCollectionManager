"""Tests for ImportService: row validation, defaults, and error reporting.

Mirrors test_export_service.py's shape (real repositories against a temp
SQLite db); the actual file-reading is monkeypatched per test via the
reader modules' own read()/read_sealed(), so these stay independent of the
CSV/Excel/JSON reader tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.imports import csv_import
from app.imports.models import ImportedCardRow, ImportedSealedRow
from app.models.card import CardFilter
from app.models.enums import Condition, ExportFormat, Language
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.import_service import ImportService
from app.services.sealed_product_service import SealedProductService

_PATH = Path("dummy.csv")


def _card_row(**overrides) -> ImportedCardRow:
    base = dict(
        collection_name="Binder",
        name="Xatu",
        set_name="Skyridge",
        card_number="H32",
        language="German",
        condition="Near Mint",
        extras="",
        quantity="2",
        notes="",
        cardmarket_url="",
    )
    base.update(overrides)
    return ImportedCardRow(**base)


def _sealed_row(**overrides) -> ImportedSealedRow:
    base = dict(
        name="Base Set Booster Box",
        category="Booster Box",
        language="English",
        quantity="1",
        notes="",
        cardmarket_url="",
    )
    base.update(overrides)
    return ImportedSealedRow(**base)


@pytest.fixture
def collections(temp_db: Database) -> CollectionRepository:
    return CollectionRepository(temp_db)


@pytest.fixture
def cards(temp_db: Database) -> CardRepository:
    return CardRepository(temp_db)


@pytest.fixture
def service(temp_db: Database) -> ImportService:
    return ImportService(
        CardService(CardRepository(temp_db), image_downloader=lambda _card: None),
        CollectionService(CollectionRepository(temp_db)),
        SealedProductService(SealedProductRepository(temp_db)),
    )


def test_imports_a_valid_card_row(monkeypatch, service: ImportService, cards: CardRepository) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row()])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 1
    assert result.errors == []
    imported = cards.search(CardFilter())
    assert imported[0].name == "Xatu"
    assert imported[0].language is Language.GERMAN
    assert imported[0].condition is Condition.NEAR_MINT
    assert imported[0].quantity == 2
    assert imported[0].current_price is None  # no price set on import


def test_creates_a_missing_collection(
    monkeypatch, service: ImportService, collections: CollectionRepository
) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(collection_name="New Binder")])

    service.import_cards(_PATH, ExportFormat.CSV)

    names = [c.name for c in collections.list_all()]
    assert "New Binder" in names


def test_reuses_an_existing_collection_case_insensitively(
    monkeypatch, service: ImportService, collections: CollectionRepository
) -> None:
    existing = collections.create("binder", "")
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(collection_name="Binder")])

    service.import_cards(_PATH, ExportFormat.CSV)

    assert len(collections.list_all()) == 1
    assert collections.list_all()[0].id == existing.id


def test_two_rows_with_the_same_new_collection_name_share_one_collection(
    monkeypatch, service: ImportService, collections: CollectionRepository
) -> None:
    monkeypatch.setattr(
        csv_import,
        "read",
        lambda path: [
            _card_row(name="Xatu", collection_name="Fresh"),
            _card_row(name="Blastoise", collection_name="Fresh"),
        ],
    )

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 2
    assert len(collections.list_all()) == 1


def test_missing_name_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(name="")])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2
    assert "Name" in result.errors[0].message


def test_missing_collection_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(collection_name="")])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0
    assert "Collection" in result.errors[0].message


def test_unrecognised_language_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(language="Klingon")])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0
    assert "language" in result.errors[0].message.lower()


def test_unrecognised_condition_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(condition="Terrible")])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0
    assert "condition" in result.errors[0].message.lower()


def test_invalid_quantity_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(quantity="not a number")])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0
    assert "quantity" in result.errors[0].message.lower()


def test_zero_quantity_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read", lambda path: [_card_row(quantity="0")])

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0


def test_blank_language_condition_and_quantity_use_defaults(
    monkeypatch, service: ImportService, cards: CardRepository
) -> None:
    monkeypatch.setattr(
        csv_import, "read", lambda path: [_card_row(language="", condition="", quantity="")]
    )

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 1
    imported = cards.search(CardFilter())[0]
    assert imported.language is Language.ENGLISH
    assert imported.condition is Condition.NEAR_MINT
    assert imported.quantity == 1


def test_extras_text_is_parsed_into_flags(
    monkeypatch, service: ImportService, cards: CardRepository
) -> None:
    monkeypatch.setattr(
        csv_import, "read", lambda path: [_card_row(extras="Reverse Holo, Signiert, Altered")]
    )

    service.import_cards(_PATH, ExportFormat.CSV)

    imported = cards.search(CardFilter())[0]
    assert imported.is_reverse_holo is True
    assert imported.is_signed is True
    assert imported.is_altered is True
    assert imported.is_first_edition is False


def test_one_bad_row_does_not_prevent_other_rows_from_importing(
    monkeypatch, service: ImportService
) -> None:
    monkeypatch.setattr(
        csv_import,
        "read",
        lambda path: [_card_row(name=""), _card_row(name="Xatu"), _card_row(name="Blastoise")],
    )

    result = service.import_cards(_PATH, ExportFormat.CSV)

    assert result.imported_count == 2
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2  # first data row, right after the header


def test_imports_a_valid_sealed_row(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read_sealed", lambda path: [_sealed_row()])

    result = service.import_sealed(_PATH, ExportFormat.CSV)

    assert result.imported_count == 1
    assert result.errors == []


def test_sealed_row_has_no_collection_requirement(monkeypatch, service: ImportService) -> None:
    # Sealed products aren't collection-scoped at all -- unlike cards,
    # there's no "Sammlung" column/requirement to satisfy.
    monkeypatch.setattr(csv_import, "read_sealed", lambda path: [_sealed_row()])

    result = service.import_sealed(_PATH, ExportFormat.CSV)

    assert result.errors == []


def test_sealed_missing_name_is_a_row_error(monkeypatch, service: ImportService) -> None:
    monkeypatch.setattr(csv_import, "read_sealed", lambda path: [_sealed_row(name="")])

    result = service.import_sealed(_PATH, ExportFormat.CSV)

    assert result.imported_count == 0
    assert "Name" in result.errors[0].message
