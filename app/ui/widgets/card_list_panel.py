"""Middle panel: the list of cards in the selected collection.

Bound to real ``Card`` data via :meth:`set_cards`. Emits ``selection_changed``
(card id, ``-1`` for none), and only emits ``delete_requested``/
``edit_requested``/``add_confirmed`` once the user has confirmed the
corresponding dialog — dialogs are interaction, not business logic; real
validation/persistence runs exclusively via
:class:`~app.services.card_service.CardService` through
:class:`~app.ui.controllers.card_controller.CardController`.
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

from app.catalog.models import CatalogCard
from app.models.card import Card, CardDetailsValues
from app.services.statistics_service import is_price_stale
from app.ui.dialogs.card_details_dialog import CardDetailsDialog
from app.ui.theme import PALETTE
from app.ui.widgets.card_filter_bar import CardFilterBar

_COLUMNS = ["Name", "Set", "Nr.", "Extra", "Sprache", "Zustand", "Menge", "Preis"]
_ID_ROLE = Qt.ItemDataRole.UserRole
_PRICE_COLUMN = len(_COLUMNS) - 1


def _price_text(card: Card) -> str:
    if card.current_price is None:
        return "—"
    price = f"{card.current_price:.2f} {card.price_currency}"
    # A warning emoji, not just "!" -- reuses the exact same threshold as
    # the Statistiken tab's "Karten mit veraltetem Preis" list, one
    # definition of "stale", not two.
    return f"{price}  ⚠️" if is_price_stale(card) else price


def _extras_text(card: Card) -> str:
    labels = []
    if card.is_reverse_holo:
        labels.append("Rev. Holo")
    if card.is_signed:
        labels.append("Sign.")
    if card.is_first_edition:
        labels.append("1st Ed.")
    if card.is_altered:
        labels.append("Alt.")
    return ", ".join(labels) if labels else "—"


class CardListPanel(QWidget):
    """Tabular list of the cards in the current collection."""

    #: Emitted whenever the selected card changes; -1 means "none".
    selection_changed = Signal(int)
    #: Emitted with card_id once the user confirms deletion.
    delete_requested = Signal(int)
    #: Emitted with (card_id, CardDetailsValues) once the user confirms edits.
    edit_requested = Signal(int, object)
    #: Emitted with (CatalogCard, CardDetailsValues) once the user confirms
    #: adding a catalogue match.
    add_confirmed = Signal(object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._cards_by_id: dict[int, Card] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Karten")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self.filter_bar = CardFilterBar()
        layout.addWidget(self.filter_bar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(_COLUMNS)):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self._table.currentCellChanged.connect(self._on_current_cell_changed)
        self._table.itemDoubleClicked.connect(lambda item: self._prompt_edit(item.row()))
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._table, stretch=1)

    # -- Public API (called by the controller) ----------------------------- #

    def set_cards(self, cards: list[Card]) -> None:
        """Replace the displayed list, preserving the selection if possible."""
        previous_id = self.selected_card_id()
        self._cards_by_id = {card.id: card for card in cards if card.id is not None}

        self._table.blockSignals(True)
        self._table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            values = [
                card.name,
                card.set_name,
                card.card_number,
                _extras_text(card),
                card.language.code,
                card.condition.code,
                str(card.quantity),
                _price_text(card),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(_ID_ROLE, card.id)
                if col == _PRICE_COLUMN and card.current_price is not None and is_price_stale(card):
                    item.setForeground(QColor(PALETTE.negative))
                self._table.setItem(row, col, item)
        self._table.blockSignals(False)
        self._table.resizeRowsToContents()

        self._restore_selection(previous_id)

    def selected_card_id(self) -> int | None:
        """The currently selected card's id, or ``None``."""
        item = self._table.item(self._table.currentRow(), 0)
        return item.data(_ID_ROLE) if item is not None else None

    def select_card(self, card_id: int | None) -> None:
        """Programmatically select a card by id (no-op if not found)."""
        self._restore_selection(card_id)

    def show_error(self, message: str) -> None:
        """Display a friendly error message to the user."""
        QMessageBox.warning(self, "Karten", message)

    def prompt_add_from_catalog(self, catalog_card: CatalogCard) -> None:
        """Open the add-card dialog prefilled from a catalogue match."""
        dialog = CardDetailsDialog(
            title="Karte hinzufügen",
            accept_label="Hinzufügen",
            display_name=catalog_card.name,
            display_set=catalog_card.set_name,
            display_number=catalog_card.card_number,
            display_rarity=catalog_card.rarity,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.add_confirmed.emit(catalog_card, dialog.get_values())

    # -- Internals ---------------------------------------------------------- #

    def _restore_selection(self, card_id: int | None) -> None:
        if card_id is None:
            return
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(_ID_ROLE) == card_id:
                self._table.setCurrentCell(row, 0)
                return

    def _on_current_cell_changed(self, row: int, *_args) -> None:
        item = self._table.item(row, 0)
        card_id = item.data(_ID_ROLE) if item is not None else None
        self.selection_changed.emit(card_id if card_id is not None else -1)

    def _prompt_edit(self, row: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        card_id = item.data(_ID_ROLE)
        card = self._cards_by_id.get(card_id)
        if card is None:
            return
        dialog = CardDetailsDialog(
            title="Karte bearbeiten",
            accept_label="Speichern",
            display_name=card.name,
            display_set=card.set_name,
            display_number=card.card_number,
            initial=CardDetailsValues(
                language=card.language,
                condition=card.condition,
                is_reverse_holo=card.is_reverse_holo,
                is_signed=card.is_signed,
                is_first_edition=card.is_first_edition,
                is_altered=card.is_altered,
                quantity=card.quantity,
                notes=card.notes,
            ),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.edit_requested.emit(card_id, dialog.get_values())

    def _prompt_delete(self, row: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        card_id = item.data(_ID_ROLE)
        card = self._cards_by_id.get(card_id)
        name = card.name if card is not None else ""
        answer = QMessageBox.question(
            self,
            "Karte löschen",
            f"Soll die Karte „{name}“ wirklich aus der Sammlung gelöscht werden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(card_id)

    def _show_context_menu(self, position) -> None:
        row = self._table.rowAt(position.y())
        if row < 0:
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Bearbeiten")
        delete_action = menu.addAction("Löschen")
        chosen = menu.exec(self._table.viewport().mapToGlobal(position))
        if chosen is edit_action:
            self._prompt_edit(row)
        elif chosen is delete_action:
            self._prompt_delete(row)
