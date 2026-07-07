"""Tests for the JSON import reader: round-trips what json_export.py writes."""

from __future__ import annotations

from app.export import json_export
from app.export.models import ExportRow, SealedExportRow
from app.imports import json_import
from app.imports.models import ImportedCardRow, ImportedSealedRow, ImportFileError

import pytest

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
    path = tmp_path / "export.json"
    json_export.write([_ROW], path)

    rows = json_import.read(path)

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
    path = tmp_path / "export.json"
    json_export.write_sealed([_SEALED_ROW], path)

    rows = json_import.read_sealed(path)

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


def test_non_array_json_raises_import_file_error(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"not": "an array"}', encoding="utf-8")

    with pytest.raises(ImportFileError):
        json_import.read(path)


def test_malformed_json_raises_import_file_error(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ImportFileError):
        json_import.read(path)
