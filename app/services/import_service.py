"""Imports owned cards or sealed products from CSV/Excel/JSON files.

The counterpart to ``export_service.py``: reads already-parsed rows (see
``app.imports``) and adds each one via the exact same "manual entry" path a
user would use themselves (:meth:`CardService.add_card_manual`/
:meth:`SealedProductService.add_product_manual`) -- no price is set on
import, mirroring how a manually-added card starts out. A malformed
individual row is recorded as an :class:`~app.imports.models.ImportRowError`
and skipped rather than aborting the whole import: a real spreadsheet is
never perfectly clean, and losing 199 good rows over 1 bad one would be
far worse than just reporting it.
"""

from __future__ import annotations

from pathlib import Path

from app.imports import csv_import, excel_import, json_import
from app.imports.models import ImportedCardRow, ImportedSealedRow, ImportResult, ImportRowError
from app.models.card import CardDetailsValues
from app.models.collection import Collection
from app.models.enums import Condition, ExportFormat, Language
from app.models.sealed_product import SealedProductDetailsValues
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.exceptions import ServiceError
from app.services.sealed_product_service import SealedProductService

_DEFAULT_LANGUAGE = Language.ENGLISH
_DEFAULT_CONDITION = Condition.NEAR_MINT
_DEFAULT_QUANTITY = 1

#: Maps each importable format to its reader *module* (not a bound function
#: reference) -- mirrors ``export_service.py``'s own ``_MODULES``, so tests
#: can monkeypatch e.g. ``csv_import.read`` and have it take effect. PDF has
#: no entry: it's a rendered, one-way document, not a reasonable import
#: source.
_MODULES = {
    ExportFormat.CSV: csv_import,
    ExportFormat.EXCEL: excel_import,
    ExportFormat.JSON: json_import,
}

#: Extras text is free-form ("Reverse Holo, Signiert, Altered" is exactly
#: what the exporter itself writes) -- matched as a case-insensitive
#: substring rather than an exact token so a hand-edited file (extra
#: spacing, different separators, English "Signed" instead of the
#: exporter's own German "Signiert") still parses correctly.
_EXTRA_MARKERS = {
    "is_reverse_holo": ("reverse holo",),
    "is_signed": ("signiert", "signed"),
    "is_first_edition": ("1st edition", "first edition"),
    "is_altered": ("altered",),
}


def _resolve_language(text: str) -> Language | None:
    """``_DEFAULT_LANGUAGE`` for blank text, the matching member for a known

    code/label, or ``None`` if ``text`` doesn't match anything -- distinct
    from "blank", which is a normal default, not an error."""
    if not text:
        return _DEFAULT_LANGUAGE
    for member in Language:
        if text.casefold() in (member.code.casefold(), member.label.casefold()):
            return member
    return None


def _resolve_condition(text: str) -> Condition | None:
    """Mirrors ``_resolve_language`` for ``Condition``."""
    if not text:
        return _DEFAULT_CONDITION
    for member in Condition:
        if text.casefold() in (member.code.casefold(), member.label.casefold()):
            return member
    return None


def _parse_quantity(text: str) -> int | None:
    """``_DEFAULT_QUANTITY`` for blank text, the parsed int for a valid one,

    or ``None`` if it isn't a positive integer at all."""
    if not text:
        return _DEFAULT_QUANTITY
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value >= 1 else None


def _parse_extras(text: str) -> dict[str, bool]:
    lowered = text.casefold()
    return {
        field: any(marker in lowered for marker in markers)
        for field, markers in _EXTRA_MARKERS.items()
    }


class ImportService:
    """Adds owned cards/sealed products read from a CSV/Excel/JSON file."""

    def __init__(
        self,
        card_service: CardService,
        collection_service: CollectionService,
        sealed_product_service: SealedProductService,
    ) -> None:
        self._cards = card_service
        self._collections = collection_service
        self._sealed_products = sealed_product_service

    def import_cards(self, path: Path, import_format: ExportFormat) -> ImportResult:
        """Add every valid row in ``path`` as a new owned card.

        Each row's ``Sammlung`` (collection) is matched case-insensitively
        against existing collections, creating a new one if none matches --
        lets a full "export, edit, re-import" round trip work without first
        manually recreating every collection.
        """
        rows: list[ImportedCardRow] = _MODULES[import_format].read(path)
        collections_by_name = {c.name.casefold(): c for c in self._collections.list_collections()}

        imported = 0
        errors: list[ImportRowError] = []
        for row_number, row in enumerate(rows, start=2):  # row 1 is the header
            error = self._add_card_row(row, row_number, collections_by_name)
            if error is not None:
                errors.append(error)
            else:
                imported += 1
        return ImportResult(imported_count=imported, errors=errors)

    def _add_card_row(
        self, row: ImportedCardRow, row_number: int, collections_by_name: dict[str, Collection]
    ) -> ImportRowError | None:
        if not row.name:
            return ImportRowError(row_number, "Name is missing.")
        if not row.collection_name:
            return ImportRowError(row_number, "Collection (Sammlung) is missing.")

        language = _resolve_language(row.language)
        if language is None:
            return ImportRowError(row_number, f"Unrecognised language: '{row.language}'.")
        condition = _resolve_condition(row.condition)
        if condition is None:
            return ImportRowError(row_number, f"Unrecognised condition: '{row.condition}'.")
        quantity = _parse_quantity(row.quantity)
        if quantity is None:
            return ImportRowError(row_number, f"Invalid quantity: '{row.quantity}'.")

        collection = collections_by_name.get(row.collection_name.casefold())
        if collection is None:
            try:
                collection = self._collections.create_collection(row.collection_name)
            except ServiceError as exc:
                return ImportRowError(row_number, str(exc))
            collections_by_name[collection.name.casefold()] = collection

        extras = _parse_extras(row.extras)
        values = CardDetailsValues(
            language=language,
            condition=condition,
            quantity=quantity,
            notes=row.notes,
            manual_cardmarket_url=row.cardmarket_url or None,
            **extras,
        )
        try:
            self._cards.add_card_manual(collection.id, row.name, row.set_name, row.card_number, values)
        except ServiceError as exc:
            return ImportRowError(row_number, str(exc))
        return None

    def import_sealed(self, path: Path, import_format: ExportFormat) -> ImportResult:
        """Add every valid row in ``path`` as a new owned sealed product."""
        rows: list[ImportedSealedRow] = _MODULES[import_format].read_sealed(path)

        imported = 0
        errors: list[ImportRowError] = []
        for row_number, row in enumerate(rows, start=2):  # row 1 is the header
            error = self._add_sealed_row(row, row_number)
            if error is not None:
                errors.append(error)
            else:
                imported += 1
        return ImportResult(imported_count=imported, errors=errors)

    def _add_sealed_row(self, row: ImportedSealedRow, row_number: int) -> ImportRowError | None:
        if not row.name:
            return ImportRowError(row_number, "Name is missing.")

        language = _resolve_language(row.language)
        if language is None:
            return ImportRowError(row_number, f"Unrecognised language: '{row.language}'.")
        quantity = _parse_quantity(row.quantity)
        if quantity is None:
            return ImportRowError(row_number, f"Invalid quantity: '{row.quantity}'.")

        values = SealedProductDetailsValues(
            language=language,
            quantity=quantity,
            notes=row.notes,
            cardmarket_url=row.cardmarket_url or None,
        )
        try:
            self._sealed_products.add_product_manual(row.name, row.category, values)
        except ServiceError as exc:
            return ImportRowError(row_number, str(exc))
        return None
