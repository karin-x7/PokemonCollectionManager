"""Tests for the CSV export writer."""

from __future__ import annotations

import csv

from app.export import csv_export
from app.export.models import COLUMNS, SEALED_COLUMNS, ExportRow, SealedExportRow

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


def test_writes_header_and_row(tmp_path) -> None:
    path = tmp_path / "export.csv"

    csv_export.write([_ROW], path)

    with path.open(encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0] == list(COLUMNS)
    assert rows[1] == [
        "Binder", "Xatu", "Skyridge", "H32", "German", "Near Mint", "Reverse Holo",
        "2", "13,90", "EUR", "Exakter Treffer", "2026-07-04T12:00:00Z", "PSA 9",
        "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu",
    ]


def test_no_price_becomes_empty_string(tmp_path) -> None:
    path = tmp_path / "export.csv"
    row = ExportRow(
        collection_name="Binder", name="Xatu", set_name="Skyridge", card_number="H32",
        language="German", condition="Near Mint", extras="", quantity=1, price=None,
        currency="EUR", price_quality="Kein Preis gefunden", price_updated_at="",
        notes="", cardmarket_url="",
    )

    csv_export.write([row], path)

    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows[1][8] == ""  # price column


def test_empty_rows_still_writes_header(tmp_path) -> None:
    path = tmp_path / "export.csv"

    csv_export.write([], path)

    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows == [list(COLUMNS)]


def test_write_sealed_writes_header_and_row(tmp_path) -> None:
    path = tmp_path / "export.csv"
    row = SealedExportRow(
        name="Base Set Booster Box",
        category="Booster Box",
        language="German",
        quantity=1,
        price=5000.0,
        currency="EUR",
        price_quality="Exakter Treffer",
        price_updated_at="2026-07-05T00:00:00Z",
        notes="",
        cardmarket_url="https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
    )

    csv_export.write_sealed([row], path)

    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    assert rows[0] == list(SEALED_COLUMNS)
    assert rows[1] == [
        "Base Set Booster Box", "Booster Box", "German", "1",
        "5.000,00", "EUR", "Exakter Treffer", "2026-07-05T00:00:00Z", "",
        "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
    ]
