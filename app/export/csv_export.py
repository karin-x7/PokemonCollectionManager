"""CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

from app.export.models import COLUMNS, SEALED_COLUMNS, ExportRow, SealedExportRow


def write(rows: list[ExportRow], path: Path) -> None:
    """Write ``rows`` to ``path`` as UTF-8 CSV with a header row.

    ``utf-8-sig`` (a BOM-prefixed UTF-8) so Excel — the most common CSV
    consumer on Windows — detects the encoding and renders accented/non-Latin
    characters (e.g. "Pikachu Nº", Japanese card names) correctly instead of
    guessing the system codepage.
    """
    _write(rows, COLUMNS, path)


def write_sealed(rows: list[SealedExportRow], path: Path) -> None:
    """Write sealed-product ``rows`` to ``path`` as UTF-8 CSV with a header row."""
    _write(rows, SEALED_COLUMNS, path)


def _write(rows: list[ExportRow] | list[SealedExportRow], columns: tuple[str, ...], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row.as_tuple())
