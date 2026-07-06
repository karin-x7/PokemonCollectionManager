"""Tests for ExportService: gathering + flattening cards, format dispatch,
and collection scoping. Real repositories against a temp SQLite db --
writing is stubbed per-format so these stay fast/offline and independent
of the CSV/JSON/Excel/PDF writer tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.card import Card
from app.models.enums import Condition, ExportFormat, ExportTarget, Language, PriceQuality
from app.models.sealed_product import SealedProduct
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.export_service import ExportService
from app.services.sealed_product_service import SealedProductService


@pytest.fixture
def collections(temp_db: Database) -> CollectionRepository:
    return CollectionRepository(temp_db)


@pytest.fixture
def cards(temp_db: Database) -> CardRepository:
    return CardRepository(temp_db)


@pytest.fixture
def sealed_products(temp_db: Database) -> SealedProductRepository:
    return SealedProductRepository(temp_db)


@pytest.fixture
def service(temp_db: Database) -> ExportService:
    return ExportService(
        CardService(CardRepository(temp_db), image_downloader=lambda _card: None),
        CollectionService(CollectionRepository(temp_db)),
        SealedProductService(SealedProductRepository(temp_db)),
    )


def _card(collection_id: int, **overrides) -> Card:
    base = dict(
        id=None,
        collection_id=collection_id,
        name="Xatu",
        set_name="Skyridge",
        card_number="H32",
        language=Language.GERMAN,
        condition=Condition.NEAR_MINT,
        quantity=1,
        current_price=13.9,
        price_currency="EUR",
        price_quality=PriceQuality.EXACT,
        price_updated_at="2026-07-04T12:00:00Z",
        notes="",
        cardmarket_url="https://prices.pokemontcg.io/cardmarket/skg-h32",
    )
    base.update(overrides)
    return Card(**base)


def test_export_writes_a_row_per_card_with_the_collection_name(
    service: ExportService, cards: CardRepository, collections: CollectionRepository, monkeypatch
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id, name="Xatu"))
    cards.create(_card(binder.id, name="Charizard"))

    written = {}

    def fake_write(rows, path):
        written["rows"] = rows
        written["path"] = path

    monkeypatch.setattr("app.services.export_service.csv_export.write", fake_write)

    count = service.export(ExportFormat.CSV, "out.csv", collection_id=None)

    assert count == 2
    assert {row.name for row in written["rows"]} == {"Xatu", "Charizard"}
    assert all(row.collection_name == "Binder" for row in written["rows"])
    assert written["path"] == "out.csv"


def test_export_scoped_to_one_collection_excludes_others(
    service: ExportService, cards: CardRepository, collections: CollectionRepository, monkeypatch
) -> None:
    binder = collections.create("Binder")
    vintage = collections.create("Vintage")
    cards.create(_card(binder.id, name="Xatu"))
    cards.create(_card(vintage.id, name="Charizard"))
    written = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write",
        lambda rows, path: written.update(rows=rows),
    )

    count = service.export(ExportFormat.CSV, "out.csv", collection_id=binder.id)

    assert count == 1
    assert written["rows"][0].name == "Xatu"
    assert written["rows"][0].collection_name == "Binder"


def test_export_dispatches_to_the_matching_format_writer(
    service: ExportService, cards: CardRepository, collections: CollectionRepository, monkeypatch
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id))
    fake_writers = {
        fmt: MagicMock() for fmt in (ExportFormat.CSV, ExportFormat.EXCEL, ExportFormat.JSON, ExportFormat.PDF)
    }
    monkeypatch.setattr("app.services.export_service.csv_export.write", fake_writers[ExportFormat.CSV])
    monkeypatch.setattr("app.services.export_service.excel_export.write", fake_writers[ExportFormat.EXCEL])
    monkeypatch.setattr("app.services.export_service.json_export.write", fake_writers[ExportFormat.JSON])
    monkeypatch.setattr("app.services.export_service.pdf_export.write", fake_writers[ExportFormat.PDF])

    service.export(ExportFormat.PDF, "out.pdf", collection_id=None)

    fake_writers[ExportFormat.PDF].assert_called_once()
    for fmt, writer in fake_writers.items():
        if fmt is not ExportFormat.PDF:
            writer.assert_not_called()


def test_row_reflects_card_fields_correctly(
    service: ExportService, cards: CardRepository, collections: CollectionRepository, monkeypatch
) -> None:
    binder = collections.create("Binder")
    cards.create(
        _card(
            binder.id,
            name="Xatu",
            is_reverse_holo=True,
            is_signed=True,
            quantity=3,
            current_price=99.99,
            notes="PSA 9",
        )
    )
    written = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write",
        lambda rows, path: written.update(rows=rows),
    )

    service.export(ExportFormat.CSV, "out.csv", collection_id=None)

    row = written["rows"][0]
    assert row.quantity == 3
    assert row.price == 99.99
    assert "Reverse Holo" in row.extras
    assert "Signiert" in row.extras
    assert row.notes == "PSA 9"
    assert row.language == Language.GERMAN.label
    assert row.condition == Condition.NEAR_MINT.label


def test_manual_cardmarket_url_takes_precedence_over_automatic_one(
    service: ExportService, cards: CardRepository, collections: CollectionRepository, monkeypatch
) -> None:
    binder = collections.create("Binder")
    cards.create(
        _card(
            binder.id,
            cardmarket_url="https://prices.pokemontcg.io/cardmarket/skg-h32",
            manual_cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Singles/Awakening-Legends/Ho-Oh-AL",
        )
    )
    written = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write",
        lambda rows, path: written.update(rows=rows),
    )

    service.export(ExportFormat.CSV, "out.csv", collection_id=None)

    assert written["rows"][0].cardmarket_url == (
        "https://www.cardmarket.com/en/Pokemon/Products/Singles/Awakening-Legends/Ho-Oh-AL"
    )


def test_no_cards_exports_zero_rows(service: ExportService, tmp_path) -> None:
    count = service.export(ExportFormat.CSV, tmp_path / "out.csv", collection_id=None)

    assert count == 0


def _sealed_product(**overrides) -> SealedProduct:
    base = dict(
        id=None,
        name="Base Set Booster Box",
        category="Booster Box",
        language=Language.GERMAN,
        quantity=1,
        current_price=5000.0,
        price_currency="EUR",
        price_quality=PriceQuality.EXACT,
        price_updated_at="2026-07-05T00:00:00Z",
        notes="",
        cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
    )
    base.update(overrides)
    return SealedProduct(**base)


def test_export_sealed_writes_a_row_per_product(
    service: ExportService,
    sealed_products: SealedProductRepository,
    monkeypatch,
) -> None:
    sealed_products.create(_sealed_product(name="Base Set Booster Box"))
    sealed_products.create(_sealed_product(name="Evolutions ETB"))
    written = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write_sealed",
        lambda rows, path: written.update(rows=rows),
    )

    count = service.export(ExportFormat.CSV, "out.csv", target=ExportTarget.SEALED)

    assert count == 2
    assert {row.name for row in written["rows"]} == {"Base Set Booster Box", "Evolutions ETB"}


def test_export_sealed_ignores_collection_id(
    service: ExportService,
    sealed_products: SealedProductRepository,
    collections: CollectionRepository,
    monkeypatch,
) -> None:
    # Sealed products aren't collection-scoped -- collection_id is only
    # meaningful for target=CARDS and must be a no-op here.
    binder = collections.create("Binder")
    sealed_products.create(_sealed_product(name="Base Set Booster Box"))
    written = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write_sealed",
        lambda rows, path: written.update(rows=rows),
    )

    count = service.export(
        ExportFormat.CSV, "out.csv", target=ExportTarget.SEALED, collection_id=binder.id
    )

    assert count == 1


def test_export_sealed_row_reflects_product_fields_correctly(
    service: ExportService,
    sealed_products: SealedProductRepository,
    monkeypatch,
) -> None:
    sealed_products.create(
        _sealed_product(category="Booster Box", quantity=3, current_price=150.0, notes="OVP")
    )
    written = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write_sealed",
        lambda rows, path: written.update(rows=rows),
    )

    service.export(ExportFormat.CSV, "out.csv", target=ExportTarget.SEALED)

    row = written["rows"][0]
    assert row.category == "Booster Box"
    assert row.quantity == 3
    assert row.price == 150.0
    assert row.notes == "OVP"
    assert row.language == Language.GERMAN.label


def test_export_defaults_to_cards_target(
    service: ExportService, cards: CardRepository, collections: CollectionRepository, monkeypatch
) -> None:
    binder = collections.create("Binder")
    cards.create(_card(binder.id))
    called = {}
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write", lambda rows, path: called.update(cards=True)
    )
    monkeypatch.setattr(
        "app.services.export_service.csv_export.write_sealed",
        lambda rows, path: called.update(sealed=True),
    )

    service.export(ExportFormat.CSV, "out.csv", collection_id=None)

    assert called == {"cards": True}
