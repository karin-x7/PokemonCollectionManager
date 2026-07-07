"""Wantlist tab: the list of every card the user wants to buy.

Mirrors ``sealed_product_list_panel.py``'s flat-table shape (no detail panel/
price-history dock -- kept simple, unlike the Karten/Sealed tabs' fuller
layout): a wantlist entry is just tracked against a target price, there's no
"owned copy" detail to show. "+ Add to wantlist" and "Check all prices" live
in this panel's own header (not the toolbar) -- the toolbar's per-tab
contextual layout is already fragile/tightly tuned (see main_window.py's own
comments), so a wantlist-specific header row avoids touching that.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.wantlist import WantlistItem, WantlistItemDetailsValues
from app.ui.dialogs.wantlist_item_details_dialog import WantlistItemDetailsDialog
from app.ui.language_icon_provider import get_language_icon
from app.ui.theme import PALETTE
from app.ui.widgets.centered_icon_delegate import CenteredIconDelegate

_COLUMNS = ["Name", "Set", "Lang.", "Target", "Current", "Status"]
_ID_ROLE = Qt.ItemDataRole.UserRole
_LANGUAGE_COLUMN = 2
_TARGET_COLUMN = 3
_CURRENT_COLUMN = 4
_STATUS_COLUMN = 5
_TRANSPARENT = QColor(0, 0, 0, 0)


class _NumericItem(QTableWidgetItem):
    """Sorts by a separately-stored number, not its displayed text (mirrors
    the identically-named class in sealed_product_list_panel.py)."""

    def __init__(self, text: str, sort_value: float) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, _NumericItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


def _current_price_text(item: WantlistItem) -> str:
    if item.current_price is None:
        return "—"
    return f"{item.current_price:.2f} {item.price_currency}"


def _current_price_sort_value(item: WantlistItem) -> float:
    return item.current_price if item.current_price is not None else -1.0


def _status_text(item: WantlistItem) -> str:
    if item.current_price is None:
        return "not checked yet"
    return "Below target!" if item.is_below_target else "above target"


class WantlistPanel(QWidget):
    """Tabular list of the user's wantlist, with a target-price alert column."""

    #: Emitted whenever the selected item changes; -1 means "none".
    selection_changed = Signal(int)
    #: Emitted with a list of item ids (one or more) once the user confirms
    #: deletion -- mirrors SealedProductListPanel's own multi-select delete.
    delete_requested = Signal(list)
    #: Emitted with (item_id, WantlistItemDetailsValues) on confirmed edits.
    edit_requested = Signal(int, object)
    #: Emitted with item_id when "Check price" is chosen for a single row.
    price_lookup_requested = Signal(int)
    #: Emitted with item_id when "Add to collection" is chosen -- the actual
    #: conversion (create the owned card, drop the wantlist entry) lives in
    #: WantlistController.
    convert_to_owned_requested = Signal(int)
    #: Emitted with every item id currently listed when "Check all prices"
    #: is clicked.
    bulk_price_lookup_requested = Signal(list)
    #: Emitted when "+ Add to wantlist" is clicked -- the actual add flow
    #: (link lookup, dialog) lives in WantlistEntryController.
    add_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._items_by_id: dict[int, WantlistItem] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header = QLabel("Wantlist")
        header.setObjectName("PanelHeader")
        header_row.addWidget(header)
        header_row.addStretch(1)
        self._add_button = QPushButton("+ Add to wantlist")
        self._add_button.setObjectName("ToolbarPrimaryAction")
        self._add_button.clicked.connect(self.add_requested)
        header_row.addWidget(self._add_button)
        self._check_all_button = QPushButton("Check all prices")
        self._check_all_button.setObjectName("Secondary")
        self._check_all_button.clicked.connect(self._on_check_all_clicked)
        header_row.addWidget(self._check_all_button)
        layout.addLayout(header_row)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setSortingEnabled(True)

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(2, len(_COLUMNS)):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self._table.currentCellChanged.connect(self._on_current_cell_changed)
        self._table.itemDoubleClicked.connect(lambda item: self._prompt_edit(item.row()))
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.setItemDelegateForColumn(_LANGUAGE_COLUMN, CenteredIconDelegate(self._table))

        layout.addWidget(self._table, stretch=1)

    # -- Public API (called by the controller) ----------------------------- #

    def set_items(self, items: list[WantlistItem]) -> None:
        """Replace the displayed list, preserving the selection if possible."""
        previous_id = self.selected_item_id()
        self._items_by_id = {i.id: i for i in items if i.id is not None}

        self._table.setSortingEnabled(False)
        self._table.blockSignals(True)
        self._table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item.name,
                item.set_name or "—",
                item.language.code,
                f"{item.target_price:.2f} {item.price_currency}",
                _current_price_text(item),
                _status_text(item),
            ]
            for col, value in enumerate(values):
                if col == _TARGET_COLUMN:
                    cell = _NumericItem(value, sort_value=item.target_price)
                elif col == _CURRENT_COLUMN:
                    cell = _NumericItem(value, sort_value=_current_price_sort_value(item))
                else:
                    cell = QTableWidgetItem(value)
                if col >= 2:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    cell.setData(_ID_ROLE, item.id)
                if col == _LANGUAGE_COLUMN:
                    cell.setIcon(get_language_icon(item.language))
                    cell.setForeground(_TRANSPARENT)
                if col == _STATUS_COLUMN and item.is_below_target:
                    cell.setForeground(QColor(PALETTE.positive))
                self._table.setItem(row, col, cell)
        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)
        self._table.resizeRowsToContents()

        self._restore_selection(previous_id)

    def selected_item_id(self) -> int | None:
        """The currently selected item's id, or ``None``."""
        item = self._table.item(self._table.currentRow(), 0)
        return item.data(_ID_ROLE) if item is not None else None

    def selected_item_ids(self) -> list[int]:
        """Every item id currently selected (possibly more than one)."""
        ids = []
        for index in sorted(self._table.selectionModel().selectedRows(), key=lambda i: i.row()):
            cell = self._table.item(index.row(), 0)
            if cell is not None:
                ids.append(cell.data(_ID_ROLE))
        return ids

    def select_item(self, item_id: int | None) -> None:
        """Programmatically select an item by id (no-op if not found)."""
        self._restore_selection(item_id)

    def show_error(self, message: str) -> None:
        """Display a friendly error message to the user."""
        QMessageBox.warning(self, "Wantlist", message)

    def set_bulk_check_running(self, running: bool) -> None:
        """Disables "Check all prices" while a batch check is in progress."""
        self._check_all_button.setEnabled(not running and bool(self._items_by_id))

    # -- Internals ---------------------------------------------------------- #

    def _restore_selection(self, item_id: int | None) -> None:
        if item_id is None:
            return
        for row in range(self._table.rowCount()):
            cell = self._table.item(row, 0)
            if cell is not None and cell.data(_ID_ROLE) == item_id:
                self._table.setCurrentCell(row, 0)
                return

    def _on_current_cell_changed(self, row: int, *_args) -> None:
        cell = self._table.item(row, 0)
        item_id = cell.data(_ID_ROLE) if cell is not None else None
        self.selection_changed.emit(item_id if item_id is not None else -1)

    def _prompt_edit(self, row: int) -> None:
        cell = self._table.item(row, 0)
        if cell is None:
            return
        item_id = cell.data(_ID_ROLE)
        item = self._items_by_id.get(item_id)
        if item is None:
            return
        dialog = WantlistItemDetailsDialog(
            title="Edit wantlist item",
            accept_label="Save",
            display_name=item.name,
            display_set=item.set_name,
            initial=WantlistItemDetailsValues(
                language=item.language,
                condition=item.condition,
                target_price=item.target_price,
                notes=item.notes,
                cardmarket_url=item.cardmarket_url,
            ),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.edit_requested.emit(item_id, dialog.get_values())

    def _prompt_delete_selected(self) -> None:
        ids = self.selected_item_ids()
        if not ids:
            return
        if len(ids) == 1:
            item = self._items_by_id.get(ids[0])
            name = item.name if item is not None else ""
            message = f'Should "{name}" really be removed from the wantlist?'
        else:
            message = f"Should the {len(ids)} selected wantlist items really be removed?"
        answer = QMessageBox.question(
            self,
            "Remove from wantlist",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(ids)

    def _on_check_all_clicked(self) -> None:
        ids = list(self._items_by_id.keys())
        if ids:
            self.bulk_price_lookup_requested.emit(ids)

    def _show_context_menu(self, position) -> None:
        row = self._table.rowAt(position.y())
        if row < 0:
            return
        cell = self._table.item(row, 0)
        if cell is not None and not cell.isSelected():
            self._table.selectRow(row)
        ids = self.selected_item_ids()
        if not ids:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Edit") if len(ids) == 1 else None
        price_action = menu.addAction("Check price") if len(ids) == 1 else None
        convert_action = menu.addAction("Add to collection") if len(ids) == 1 else None
        delete_action = menu.addAction("Remove")
        chosen = menu.exec(self._table.viewport().mapToGlobal(position))
        if edit_action is not None and chosen is edit_action:
            self._prompt_edit(row)
        elif price_action is not None and chosen is price_action:
            self.price_lookup_requested.emit(ids[0])
        elif convert_action is not None and chosen is convert_action:
            self.convert_to_owned_requested.emit(ids[0])
        elif chosen is delete_action:
            self._prompt_delete_selected()
