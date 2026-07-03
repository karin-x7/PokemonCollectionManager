"""Modal dialog showing catalogue search results.

Presentation-only: displays whatever :class:`~app.catalog.models.CatalogCard`
list it is given. Selecting a row and clicking "Hinzufügen" emits
``add_requested`` with the chosen match — the actual owned-copy details
(variant/language/condition/quantity/notes) and persistence are handled by
:class:`~app.ui.widgets.card_list_panel.CardListPanel` /
:class:`~app.services.card_service.CardService` (Step 5), not here.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.catalog.models import CatalogCard

_COLUMNS = ["Name", "Set", "Nr.", "Rarität"]


class CatalogSearchResultsDialog(QDialog):
    """Read-only list of catalogue search matches, selectable to add."""

    #: Emitted with the selected CatalogCard when "Hinzufügen" is clicked.
    add_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Suchergebnisse")
        self.resize(560, 400)
        self._matches: list[CatalogCard] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        self._empty_label = QLabel("Keine Treffer.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._update_add_button_enabled)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        self._add_button = buttons.addButton(
            "Hinzufügen", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._add_button.clicked.connect(self._on_add_clicked)
        self._update_add_button_enabled()
        layout.addWidget(buttons)

    def set_results(self, matches: list[CatalogCard]) -> None:
        """Populate the table with search matches (or show the empty state)."""
        self._matches = matches
        self._empty_label.setVisible(not matches)
        self._table.setVisible(bool(matches))
        self._table.setRowCount(len(matches))
        for row, card in enumerate(matches):
            values = [card.name, card.set_name, card.card_number, card.rarity]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)
        self._update_add_button_enabled()

    def _update_add_button_enabled(self) -> None:
        self._add_button.setEnabled(self._table.currentRow() >= 0)

    def _on_add_clicked(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._matches):
            return
        self.add_requested.emit(self._matches[row])
        self.accept()
