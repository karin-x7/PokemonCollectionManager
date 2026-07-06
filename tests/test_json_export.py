"""Tests for the JSON export writer."""

from __future__ import annotations

import json

from app.export import json_export
from app.export.models import ExportRow, SealedExportRow

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


def test_writes_a_json_array_of_objects(tmp_path) -> None:
    path = tmp_path / "export.json"

    json_export.write([_ROW], path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == [
        {
            "collection": "Binder",
            "name": "Xatu",
            "set": "Skyridge",
            "number": "H32",
            "language": "German",
            "condition": "Near Mint",
            "extras": "Reverse Holo",
            "quantity": 2,
            "price": 13.9,
            "currency": "EUR",
            "price_quality": "Exakter Treffer",
            "price_updated_at": "2026-07-04T12:00:00Z",
            "notes": "PSA 9",
            "cardmarket_url": "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu",
        }
    ]


def test_price_stays_a_real_number_not_a_formatted_string(tmp_path) -> None:
    """Unlike the tabular formats, JSON keeps price/quantity as real numbers

    -- it's meant to be machine-readable/re-importable."""
    path = tmp_path / "export.json"

    json_export.write([_ROW], path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload[0]["price"], float)
    assert isinstance(payload[0]["quantity"], int)


def test_missing_price_and_url_become_null(tmp_path) -> None:
    path = tmp_path / "export.json"
    row = ExportRow(
        collection_name="Binder", name="Xatu", set_name="Skyridge", card_number="H32",
        language="German", condition="Near Mint", extras="", quantity=1, price=None,
        currency="EUR", price_quality="Kein Preis gefunden", price_updated_at="",
        notes="", cardmarket_url="",
    )

    json_export.write([row], path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[0]["price"] is None
    assert payload[0]["cardmarket_url"] is None
    assert payload[0]["price_updated_at"] is None


def test_empty_rows_writes_empty_array(tmp_path) -> None:
    path = tmp_path / "export.json"

    json_export.write([], path)

    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_non_ascii_characters_are_kept_readable(tmp_path) -> None:
    """``ensure_ascii=False`` -- a Japanese card name shouldn't be escaped

    into unreadable \\uXXXX sequences."""
    path = tmp_path / "export.json"
    row = ExportRow(
        collection_name="Binder", name="ポケパッド", set_name="Skyridge", card_number="H32",
        language="Japanese", condition="Near Mint", extras="", quantity=1, price=None,
        currency="EUR", price_quality="Kein Preis gefunden", price_updated_at="",
        notes="", cardmarket_url="",
    )

    json_export.write([row], path)

    raw = path.read_text(encoding="utf-8")
    assert "ポケパッド" in raw


def test_write_sealed_writes_a_json_array_of_objects(tmp_path) -> None:
    path = tmp_path / "export.json"
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

    json_export.write_sealed([row], path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == [
        {
            "name": "Base Set Booster Box",
            "category": "Booster Box",
            "language": "German",
            "quantity": 1,
            "price": 5000.0,
            "currency": "EUR",
            "price_quality": "Exakter Treffer",
            "price_updated_at": "2026-07-05T00:00:00Z",
            "notes": "",
            "cardmarket_url": "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
        }
    ]
