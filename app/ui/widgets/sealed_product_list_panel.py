"""Sealed tab: the list of every owned sealed product.

Mirrors ``card_list_panel.py``, minus everything sealed products don't have
(card number, condition, extras, and -- unlike cards -- a collection: sealed
products aren't kept in physical folders/binders, so there's nothing to
scope them by). The "+ Sealed-Produkt hinzufügen" action itself lives in the
toolbar (see ``main_window.py``'s ``_sealed_add_button``), not embedded here
-- it occupies the same toolbar slot the Karten-only search/manual-entry
controls do, swapped in when this tab is active (user request).

Like the Karten tab, the table allows selecting multiple rows
(Shift/Ctrl-click) -- ``delete_requested`` always carries a list of product
ids (one or more). "Bearbeiten"/"Preis aktualisieren" only make sense for a
single product, so they're left out of the context menu whenever more than
one row is selected.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.models.sealed_product import SealedProduct, SealedProductDetailsValues
from app.services.statistics_service import is_price_stale
from app.ui.dialogs.manual_price_dialog import ManualPriceDialog
from app.ui.dialogs.sealed_product_details_dialog import SealedProductDetailsDialog
from app.ui.language_icon_provider import get_language_icon
from app.ui.theme import PALETTE, apply_elevation
from app.ui.widgets.centered_icon_delegate import CenteredIconDelegate
from app.utils.formatting import format_price


def _columns() -> list[str]:
    return [
        tr("Name"),
        tr("Kategorie"),
        tr("Sprache"),
        tr("Menge"),
        tr("Einzelpreis"),
        tr("Gesamtpreis"),
    ]


_ID_ROLE = Qt.ItemDataRole.UserRole
_LANGUAGE_COLUMN = 2
_QUANTITY_COLUMN = 3
_PRICE_COLUMN = 4
#: Not stored on the model -- computed here as current_price * quantity, so
#: owning more than one copy of a product (common for sealed booster boxes
#: etc.) is directly visible in the table, not just derivable by hand.
_TOTAL_PRICE_COLUMN = 5
_TRANSPARENT = QColor(0, 0, 0, 0)


class _NumericItem(QTableWidgetItem):
    """Sorts by a separately-stored number, not its displayed text (e.g.

    "1550.00 EUR" or "—" for no price) -- ``setSortingEnabled``'s default
    comparison is text-based, which would rank these alphabetically."""

    def __init__(self, text: str, sort_value: float) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, _NumericItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


def _price_text(product: SealedProduct) -> str:
    if product.current_price is None:
        return "—"
    price = format_price(product.current_price, product.price_currency)
    return f"{price}  ⚠️" if is_price_stale(product) else price


def _price_sort_value(product: SealedProduct) -> float:
    # Unpriced products sort as the cheapest, not wherever "—" would fall
    # alphabetically -- an arbitrary but consistent choice.
    return product.current_price if product.current_price is not None else -1.0


def _total_price_text(product: SealedProduct) -> str:
    if product.total_value is None:
        return "—"
    total = format_price(product.total_value, product.price_currency)
    return f"{total}  ⚠️" if is_price_stale(product) else total


def _total_price_sort_value(product: SealedProduct) -> float:
    # Mirrors _price_sort_value: unpriced products sort as the cheapest.
    return product.total_value if product.total_value is not None else -1.0


class SealedProductListPanel(QWidget):
    """Tabular list of the sealed products in the current collection."""

    #: Emitted whenever the selected product changes; -1 means "none".
    selection_changed = Signal(int)
    #: Emitted with a list of product ids (one or more) once the user
    #: confirms deletion -- the table allows selecting multiple rows via
    #: Shift/Ctrl-click, like the Karten tab.
    delete_requested = Signal(list)
    #: Emitted with (product_id, SealedProductDetailsValues) on confirmed edits.
    edit_requested = Signal(int, object)
    #: Emitted with product_id when "Preis aktualisieren" is chosen.
    price_lookup_requested = Signal(int)
    #: Emitted with (product_id, new price) once the user confirms a manual
    #: override -- mirrors CardListPanel's own price_edit_requested.
    price_edit_requested = Signal(int, float)
    #: Emitted with a product id when "Open Cardmarket link" is chosen from
    #: the context menu -- mirrors CardListPanel's own
    #: open_cardmarket_link_requested: only offered for a single selected
    #: row, distinct from "Preis aktualisieren" (which reads and closes the
    #: tab automatically), this leaves the tab open for the user to browse.
    open_cardmarket_link_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        apply_elevation(self)
        self._products_by_id: dict[int, SealedProduct] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(tr("Sealed-Produkte"))
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        columns = _columns()
        self._table = QTableWidget(0, len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setSortingEnabled(True)
        self._table.setShowGrid(False)

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(columns)):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self._table.currentCellChanged.connect(self._on_current_cell_changed)
        self._table.itemDoubleClicked.connect(lambda item: self._prompt_edit(item.row()))
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        # Flag icon with no visible text -- center it (default delegate
        # hugs a lone icon to the cell's left edge).
        self._table.setItemDelegateForColumn(_LANGUAGE_COLUMN, CenteredIconDelegate(self._table))

        layout.addWidget(self._table, stretch=1)

    # -- Public API (called by the controller) ----------------------------- #

    def set_products(self, products: list[SealedProduct]) -> None:
        """Replace the displayed list, preserving the selection if possible."""
        previous_id = self.selected_product_id()
        self._products_by_id = {p.id: p for p in products if p.id is not None}

        self._table.setSortingEnabled(False)
        self._table.blockSignals(True)
        self._table.setRowCount(len(products))
        for row, product in enumerate(products):
            values = [
                product.name,
                product.category,
                product.language.code,
                str(product.quantity),
                _price_text(product),
                _total_price_text(product),
            ]
            for col, value in enumerate(values):
                if col == _QUANTITY_COLUMN:
                    item = _NumericItem(value, sort_value=product.quantity)
                elif col == _PRICE_COLUMN:
                    item = _NumericItem(value, sort_value=_price_sort_value(product))
                elif col == _TOTAL_PRICE_COLUMN:
                    item = _NumericItem(value, sort_value=_total_price_sort_value(product))
                else:
                    item = QTableWidgetItem(value)
                if col >= 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(_ID_ROLE, product.id)
                if col == _LANGUAGE_COLUMN:
                    item.setIcon(get_language_icon(product.language))
                    item.setForeground(_TRANSPARENT)
                if (
                    col in (_PRICE_COLUMN, _TOTAL_PRICE_COLUMN)
                    and product.current_price is not None
                    and is_price_stale(product)
                ):
                    item.setForeground(QColor(PALETTE.negative))
                self._table.setItem(row, col, item)
        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)
        self._table.resizeRowsToContents()

        self._restore_selection(previous_id)

    def selected_product_id(self) -> int | None:
        """The currently selected product's id, or ``None``."""
        item = self._table.item(self._table.currentRow(), 0)
        return item.data(_ID_ROLE) if item is not None else None

    def selected_product_ids(self) -> list[int]:
        """Every product id currently selected (possibly more than one)."""
        ids = []
        for index in sorted(self._table.selectionModel().selectedRows(), key=lambda i: i.row()):
            item = self._table.item(index.row(), 0)
            if item is not None:
                ids.append(item.data(_ID_ROLE))
        return ids

    def select_product(self, product_id: int | None) -> None:
        """Programmatically select a product by id (no-op if not found)."""
        self._restore_selection(product_id)

    def show_error(self, message: str) -> None:
        """Display a friendly error message to the user."""
        QMessageBox.warning(self, tr("Sealed-Produkte"), message)

    # -- Internals ---------------------------------------------------------- #

    def _restore_selection(self, product_id: int | None) -> None:
        if product_id is None:
            return
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(_ID_ROLE) == product_id:
                self._table.setCurrentCell(row, 0)
                return

    def _on_current_cell_changed(self, row: int, *_args) -> None:
        item = self._table.item(row, 0)
        product_id = item.data(_ID_ROLE) if item is not None else None
        self.selection_changed.emit(product_id if product_id is not None else -1)

    def _prompt_edit(self, row: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        product_id = item.data(_ID_ROLE)
        product = self._products_by_id.get(product_id)
        if product is None:
            return
        dialog = SealedProductDetailsDialog(
            title=tr("Sealed-Produkt bearbeiten"),
            accept_label=tr("Speichern"),
            display_name=product.name,
            display_category=product.category,
            initial=SealedProductDetailsValues(
                language=product.language,
                quantity=product.quantity,
                notes=product.notes,
                cardmarket_url=product.cardmarket_url,
            ),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.edit_requested.emit(product_id, dialog.get_values())

    def _prompt_edit_price(self, row: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        product_id = item.data(_ID_ROLE)
        product = self._products_by_id.get(product_id)
        if product is None:
            return
        dialog = ManualPriceDialog(current_price=product.current_price, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.price_edit_requested.emit(product_id, dialog.get_price())

    def _prompt_delete_selected(self) -> None:
        ids = self.selected_product_ids()
        if not ids:
            return
        if len(ids) == 1:
            product = self._products_by_id.get(ids[0])
            name = product.name if product is not None else ""
            message = tr("Soll das Sealed-Produkt „{name}“ wirklich gelöscht werden?").format(
                name=name
            )
        else:
            message = tr(
                "Sollen die {count} ausgewählten Sealed-Produkte wirklich gelöscht werden?"
            ).format(count=len(ids))
        answer = QMessageBox.question(
            self,
            tr("Sealed-Produkt löschen"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(ids)

    def _show_context_menu(self, position) -> None:
        row = self._table.rowAt(position.y())
        if row < 0:
            return
        item = self._table.item(row, 0)
        # Right-clicking a row outside the current multi-selection starts a
        # fresh single-row selection instead of acting on a stale selection
        # elsewhere -- mirrors standard file-manager behaviour.
        if item is not None and not item.isSelected():
            self._table.selectRow(row)
        ids = self.selected_product_ids()
        if not ids:
            return
        menu = QMenu(self)
        edit_action = menu.addAction(tr("Bearbeiten")) if len(ids) == 1 else None
        price_action = menu.addAction(tr("Preis aktualisieren")) if len(ids) == 1 else None
        price_edit_action = (
            menu.addAction(tr("Preis manuell bearbeiten")) if len(ids) == 1 else None
        )
        open_link_action = (
            menu.addAction(tr("Cardmarket-Link öffnen")) if len(ids) == 1 else None
        )
        delete_action = menu.addAction(tr("Löschen"))
        chosen = menu.exec(self._table.viewport().mapToGlobal(position))
        if edit_action is not None and chosen is edit_action:
            self._prompt_edit(row)
        elif price_action is not None and chosen is price_action:
            self.price_lookup_requested.emit(ids[0])
        elif price_edit_action is not None and chosen is price_edit_action:
            self._prompt_edit_price(row)
        elif open_link_action is not None and chosen is open_link_action:
            self.open_cardmarket_link_requested.emit(ids[0])
        elif chosen is delete_action:
            self._prompt_delete_selected()
