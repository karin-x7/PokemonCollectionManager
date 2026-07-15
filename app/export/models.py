"""Data shape shared by every export format.

A flat, already-formatted snapshot of one owned card, independent of the
``Card`` domain object — so each format writer (CSV/Excel/JSON/PDF) only
ever deals with plain strings/numbers, not enums or ``None``-handling.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.utils.formatting import format_decimal

#: Column headers, in export order — shared by every writer so the columns
#: line up the same way regardless of format.
COLUMNS = (
    "Sammlung",
    "Name",
    "Set",
    "Nr.",
    "Sprache",
    "Zustand",
    "Extra",
    "Menge",
    "Preis",
    "Währung",
    "Preisqualität",
    "Preis aktualisiert am",
    "Notizen",
    "Cardmarket-Link",
)


@dataclass(frozen=True, slots=True)
class ExportRow:
    """One owned card, flattened to plain values for export."""

    collection_name: str
    name: str
    set_name: str
    card_number: str
    language: str
    condition: str
    extras: str
    quantity: int
    price: float | None
    currency: str
    price_quality: str
    price_updated_at: str
    notes: str
    cardmarket_url: str

    def as_tuple(self) -> tuple[str, str, str, str, str, str, str, int, str, str, str, str, str, str]:
        """Values in :data:`COLUMNS` order, with ``price`` formatted and

        ``None``/empty fields normalised to ``""`` — the one shared
        representation every writer builds its own output from."""
        price_text = format_decimal(self.price) if self.price is not None else ""
        return (
            self.collection_name,
            self.name,
            self.set_name,
            self.card_number,
            self.language,
            self.condition,
            self.extras,
            self.quantity,
            price_text,
            self.currency,
            self.price_quality,
            self.price_updated_at,
            self.notes,
            self.cardmarket_url,
        )


#: Column headers for a sealed-product export -- no Set/Nr./Zustand/Extra
#: (sealed products have none of those, see app/models/sealed_product.py),
#: "Kategorie" instead (e.g. "Booster Box"). No "Sammlung" either: unlike
#: cards, sealed products don't belong to a collection.
SEALED_COLUMNS = (
    "Name",
    "Kategorie",
    "Sprache",
    "Menge",
    "Preis",
    "Währung",
    "Preisqualität",
    "Preis aktualisiert am",
    "Notizen",
    "Cardmarket-Link",
)


@dataclass(frozen=True, slots=True)
class SealedExportRow:
    """One owned sealed product, flattened to plain values for export."""

    name: str
    category: str
    language: str
    quantity: int
    price: float | None
    currency: str
    price_quality: str
    price_updated_at: str
    notes: str
    cardmarket_url: str

    def as_tuple(self) -> tuple[str, str, str, int, str, str, str, str, str, str]:
        """Values in :data:`SEALED_COLUMNS` order -- mirrors ``ExportRow.as_tuple()``."""
        price_text = format_decimal(self.price) if self.price is not None else ""
        return (
            self.name,
            self.category,
            self.language,
            self.quantity,
            price_text,
            self.currency,
            self.price_quality,
            self.price_updated_at,
            self.notes,
            self.cardmarket_url,
        )
