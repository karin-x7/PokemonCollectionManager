"""Exports owned cards or sealed products to CSV/Excel/JSON/PDF.

Read-only: gathers cards (optionally scoped to one collection, plus the
collection names they belong to) or every sealed product (sealed products
aren't collection-scoped), flattens them into :class:`ExportRow`/
:class:`SealedExportRow`, and delegates the actual file writing to the
matching ``app.export`` module. This is the only layer the GUI is allowed to
call into for exporting.
"""

from __future__ import annotations

from pathlib import Path

from app.export import csv_export, excel_export, json_export, pdf_export
from app.export.models import ExportRow, SealedExportRow
from app.models.card import Card, CardFilter
from app.models.enums import ExportFormat, ExportTarget
from app.models.sealed_product import SealedProduct, SealedProductFilter
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.sealed_product_service import SealedProductService

#: Maps each format to its writer *module* (not a bound ``.write``
#: reference) so ``.write``/``.write_sealed`` is looked up fresh on every
#: call -- lets tests monkeypatch e.g. ``csv_export.write`` and actually
#: have it take effect.
_MODULES = {
    ExportFormat.CSV: csv_export,
    ExportFormat.EXCEL: excel_export,
    ExportFormat.JSON: json_export,
    ExportFormat.PDF: pdf_export,
}


def _extras_text(card: Card) -> str:
    labels = []
    if card.is_reverse_holo:
        labels.append("Reverse Holo")
    if card.is_signed:
        labels.append("Signiert")
    if card.is_first_edition:
        labels.append("1st Edition")
    if card.is_altered:
        labels.append("Altered")
    return ", ".join(labels)


class ExportService:
    """Writes the owned cards or sealed products (or a single collection) to a file."""

    def __init__(
        self,
        card_service: CardService,
        collection_service: CollectionService,
        sealed_product_service: SealedProductService,
    ) -> None:
        self._cards = card_service
        self._collections = collection_service
        self._sealed_products = sealed_product_service

    def export(
        self,
        export_format: ExportFormat,
        path: Path,
        target: ExportTarget = ExportTarget.CARDS,
        collection_id: int | None = None,
    ) -> int:
        """Write every matching card or sealed product to ``path``.

        ``collection_id`` only applies to ``target=ExportTarget.CARDS``
        (``None`` exports every collection); sealed products always export
        in full, since they aren't collection-scoped. Returns the number of
        rows written.
        """
        if target is ExportTarget.SEALED:
            products = self._sealed_products.search_products(SealedProductFilter())
            rows = [self._to_sealed_row(product) for product in products]
            _MODULES[export_format].write_sealed(rows, path)
            return len(rows)

        collection_names = {c.id: c.name for c in self._collections.list_collections()}
        cards = self._cards.search_cards(CardFilter(collection_id=collection_id))
        rows = [self._to_row(card, collection_names) for card in cards]
        _MODULES[export_format].write(rows, path)
        return len(rows)

    @staticmethod
    def _to_row(card: Card, collection_names: dict[int, str]) -> ExportRow:
        return ExportRow(
            collection_name=collection_names.get(card.collection_id, ""),
            name=card.name,
            set_name=card.set_name,
            card_number=card.card_number,
            language=card.language.label,
            condition=card.condition.label,
            extras=_extras_text(card),
            quantity=card.quantity,
            price=card.current_price,
            currency=card.price_currency,
            price_quality=card.price_quality.label,
            price_updated_at=card.price_updated_at or "",
            notes=card.notes,
            cardmarket_url=card.manual_cardmarket_url or card.cardmarket_url or "",
        )

    @staticmethod
    def _to_sealed_row(product: SealedProduct) -> SealedExportRow:
        return SealedExportRow(
            name=product.name,
            category=product.category,
            language=product.language.label,
            quantity=product.quantity,
            price=product.current_price,
            currency=product.price_currency,
            price_quality=product.price_quality.label,
            price_updated_at=product.price_updated_at or "",
            notes=product.notes,
            cardmarket_url=product.cardmarket_url or "",
        )
