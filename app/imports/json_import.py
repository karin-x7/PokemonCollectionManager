"""JSON import -- reads the same layout ``app.export.json_export`` writes.

Unlike the tabular formats, quantity may already be a real JSON number
(as the exporter itself writes it) rather than text -- normalised to a
string here so :class:`~app.imports.models.ImportedCardRow`/
``ImportedSealedRow`` stay format-agnostic, same as CSV/Excel.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.imports.models import ImportedCardRow, ImportedSealedRow, ImportFileError


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read(path: Path) -> list[ImportedCardRow]:
    """Read owned-card rows from a JSON array of objects."""
    entries = _load(path)
    return [
        ImportedCardRow(
            collection_name=_text(entry.get("collection")),
            name=_text(entry.get("name")),
            set_name=_text(entry.get("set")),
            card_number=_text(entry.get("number")),
            language=_text(entry.get("language")),
            condition=_text(entry.get("condition")),
            extras=_text(entry.get("extras")),
            quantity=_text(entry.get("quantity")),
            notes=_text(entry.get("notes")),
            cardmarket_url=_text(entry.get("cardmarket_url")),
        )
        for entry in entries
    ]


def read_sealed(path: Path) -> list[ImportedSealedRow]:
    """Read owned-sealed-product rows from a JSON array of objects."""
    entries = _load(path)
    return [
        ImportedSealedRow(
            name=_text(entry.get("name")),
            category=_text(entry.get("category")),
            language=_text(entry.get("language")),
            quantity=_text(entry.get("quantity")),
            notes=_text(entry.get("notes")),
            cardmarket_url=_text(entry.get("cardmarket_url")),
        )
        for entry in entries
    ]


def _load(path: Path) -> list[dict[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportFileError(f"Could not read '{path.name}': {exc}") from exc
    if not isinstance(payload, list):
        raise ImportFileError(f"'{path.name}' is not a JSON array of objects.")
    return [entry for entry in payload if isinstance(entry, dict)]
