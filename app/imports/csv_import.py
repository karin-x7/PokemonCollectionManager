"""CSV import -- reads the same column layout ``app.export.csv_export`` writes."""

from __future__ import annotations

import csv
from pathlib import Path

from app.imports.models import ImportedCardRow, ImportedSealedRow, ImportFileError


def _get(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def read(path: Path) -> list[ImportedCardRow]:
    """Read owned-card rows from a CSV file.

    Only the columns actually needed are looked up by name (not position),
    so a file with extra/reordered/missing columns still works -- a missing
    column just reads as ``""`` for every row.
    """
    rows = _read_dicts(path)
    return [
        ImportedCardRow(
            collection_name=_get(row, "Sammlung"),
            name=_get(row, "Name"),
            set_name=_get(row, "Set"),
            card_number=_get(row, "Nr."),
            language=_get(row, "Sprache"),
            condition=_get(row, "Zustand"),
            extras=_get(row, "Extra"),
            quantity=_get(row, "Menge"),
            notes=_get(row, "Notizen"),
            cardmarket_url=_get(row, "Cardmarket-Link"),
        )
        for row in rows
    ]


def read_sealed(path: Path) -> list[ImportedSealedRow]:
    """Read owned-sealed-product rows from a CSV file."""
    rows = _read_dicts(path)
    return [
        ImportedSealedRow(
            name=_get(row, "Name"),
            category=_get(row, "Kategorie"),
            language=_get(row, "Sprache"),
            quantity=_get(row, "Menge"),
            notes=_get(row, "Notizen"),
            cardmarket_url=_get(row, "Cardmarket-Link"),
        )
        for row in rows
    ]


def _read_dicts(path: Path) -> list[dict[str, str]]:
    try:
        # utf-8-sig transparently strips a BOM if present (our own exporter
        # writes one) but works identically for a plain UTF-8 file that has
        # none.
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except (OSError, csv.Error) as exc:
        raise ImportFileError(f"Could not read '{path.name}': {exc}") from exc
