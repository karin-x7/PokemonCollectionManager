"""Tests for the CSV import reader: round-trips what csv_export.py writes."""

from __future__ import annotations

from app.export import csv_export
from app.export.models import ExportRow, SealedExportRow
from app.imports import csv_import
from app.imports.models import ImportedCardRow, ImportedSealedRow

_ROW = ExportRow(
    collection_name="Binder",
    name="Xatu",
    set_name="Skyridge",
    card_number="H32",
    language="German",
    condition="Near Mint",
    extras="Reverse Holo",
    quantity=2,
    price=13.9,
    currency="EUR",
    price_quality="Exakter Treffer",
    price_updated_at="2026-07-04T12:00:00Z",
    notes="PSA 9",
    cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu",
)

_SEALED_ROW = SealedExportRow(
    name="Base Set Booster Box",
    category="Booster Box",
    language="English",
    quantity=1,
    price=5000.0,
    currency="EUR",
    price_quality="Exakter Treffer",
    price_updated_at="2026-07-04T12:00:00Z",
    notes="sealed",
    cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
)


def test_reads_back_a_card_row_written_by_the_exporter(tmp_path) -> None:
    path = tmp_path / "export.csv"
    csv_export.write([_ROW], path)

    rows = csv_import.read(path)

    assert rows == [
        ImportedCardRow(
            collection_name="Binder",
            name="Xatu",
            set_name="Skyridge",
            card_number="H32",
            language="German",
            condition="Near Mint",
            extras="Reverse Holo",
            quantity="2",
            notes="PSA 9",
            cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu",
        )
    ]


def test_reads_back_a_sealed_row_written_by_the_exporter(tmp_path) -> None:
    path = tmp_path / "export.csv"
    csv_export.write_sealed([_SEALED_ROW], path)

    rows = csv_import.read_sealed(path)

    assert rows == [
        ImportedSealedRow(
            name="Base Set Booster Box",
            category="Booster Box",
            language="English",
            quantity="1",
            notes="sealed",
            cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
        )
    ]


def test_missing_columns_default_to_empty_string(tmp_path) -> None:
    path = tmp_path / "minimal.csv"
    path.write_text("Name\nCharizard\n", encoding="utf-8")

    rows = csv_import.read(path)

    assert rows == [
        ImportedCardRow(
            collection_name="",
            name="Charizard",
            set_name="",
            card_number="",
            language="",
            condition="",
            extras="",
            quantity="",
            notes="",
            cardmarket_url="",
        )
    ]


def test_empty_file_returns_no_rows(tmp_path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    assert csv_import.read(path) == []
