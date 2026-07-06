"""JSON export.

Unlike the tabular formats (CSV/Excel/PDF), keeps ``price``/``quantity`` as
real numbers (not formatted strings) since JSON is meant to be machine-
readable/re-importable, not just human-viewable.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.export.models import ExportRow, SealedExportRow


def write(rows: list[ExportRow], path: Path) -> None:
    """Write ``rows`` to ``path`` as a JSON array of objects."""
    payload = [
        {
            "collection": row.collection_name,
            "name": row.name,
            "set": row.set_name,
            "number": row.card_number,
            "language": row.language,
            "condition": row.condition,
            "extras": row.extras,
            "quantity": row.quantity,
            "price": row.price,
            "currency": row.currency,
            "price_quality": row.price_quality,
            "price_updated_at": row.price_updated_at or None,
            "notes": row.notes,
            "cardmarket_url": row.cardmarket_url or None,
        }
        for row in rows
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_sealed(rows: list[SealedExportRow], path: Path) -> None:
    """Write sealed-product ``rows`` to ``path`` as a JSON array of objects."""
    payload = [
        {
            "name": row.name,
            "category": row.category,
            "language": row.language,
            "quantity": row.quantity,
            "price": row.price,
            "currency": row.currency,
            "price_quality": row.price_quality,
            "price_updated_at": row.price_updated_at or None,
            "notes": row.notes,
            "cardmarket_url": row.cardmarket_url or None,
        }
        for row in rows
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
