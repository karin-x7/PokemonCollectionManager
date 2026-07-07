"""Tests for the Excel import reader: round-trips what excel_export.py writes."""

from __future__ import annotations

from app.export import excel_export
from app.export.models import ExportRow, SealedExportRow
from app.imports import excel_import
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
    path = tmp_path / "export.xlsx"
    excel_export.write([_ROW], path)

    rows = excel_import.read(path)

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
    path = tmp_path / "export.xlsx"
    excel_export.write_sealed([_SEALED_ROW], path)

    rows = excel_import.read_sealed(path)

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


def test_workbook_with_only_a_header_returns_no_rows(tmp_path) -> None:
    path = tmp_path / "empty.xlsx"
    excel_export.write([], path)

    assert excel_import.read(path) == []
