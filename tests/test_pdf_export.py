"""Tests for the PDF export writer.

Only a smoke test: verifying the exact rendered layout of a PDF isn't
practical (it's a binary, reportlab-generated format) -- the data mapping
itself is already covered by the CSV/JSON/Excel writer tests, since all
four share :meth:`ExportRow.as_tuple`.
"""

from __future__ import annotations

from app.export import pdf_export
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


def test_writes_a_valid_pdf_file(tmp_path) -> None:
    path = tmp_path / "export.pdf"

    pdf_export.write([_ROW], path)

    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")


def test_empty_rows_still_produces_a_valid_pdf(tmp_path) -> None:
    path = tmp_path / "export.pdf"

    pdf_export.write([], path)

    assert path.read_bytes().startswith(b"%PDF")


def test_special_characters_do_not_crash_rendering(tmp_path) -> None:
    """Real bug this guards against: reportlab's Paragraph parses its text

    as a small XML-like markup language -- a free-text note like "Zustand
    < NM" (a bare, unmatched "<") crashed the parser outright before values
    were escaped. Card data is always display text here, never markup.
    """
    path = tmp_path / "export.pdf"
    row = ExportRow(
        collection_name="Binder", name="M&M <ex>", set_name="Skyridge", card_number="H32",
        language="German", condition="Near Mint", extras="", quantity=1, price=None,
        currency="EUR", price_quality="Kein Preis gefunden", price_updated_at="",
        notes="Zustand < NM, sonst > Fehler", cardmarket_url="",
    )

    pdf_export.write([row], path)

    assert path.read_bytes().startswith(b"%PDF")


def test_write_sealed_produces_a_valid_pdf(tmp_path) -> None:
    path = tmp_path / "export.pdf"
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

    pdf_export.write_sealed([row], path)

    assert path.read_bytes().startswith(b"%PDF")
