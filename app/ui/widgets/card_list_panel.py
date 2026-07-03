"""Middle panel: the list of cards in the selected collection.

Presentation-only shell. Displays a table with the columns the application
tracks. Emits ``card_selected`` (row index) for the detail panel to react to.
The two sample rows are placeholder content, replaced by real data in Step 5.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_COLUMNS = ["Name", "Set", "Nr.", "Variante", "Sprache", "Zustand", "Menge", "Preis"]

# Placeholder rows purely to visualise the layout (Step 5 replaces this).
_DEMO_ROWS = [
    ["Xatu", "Skyridge", "H32", "Holo", "EN", "NM", "1", "—"],
    ["Charizard", "Base Set", "4", "Holo", "DE", "EX", "1", "—"],
]


class CardListPanel(QWidget):
    """Tabular list of the cards in the current collection."""

    card_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Karten")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

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

        self._populate_placeholder()
        self._table.currentCellChanged.connect(
            lambda row, *_: self.card_selected.emit(row)
        )
        layout.addWidget(self._table, stretch=1)

    def _populate_placeholder(self) -> None:
        """Fill the table with demo rows (temporary, replaced in Step 5)."""
        self._table.setRowCount(len(_DEMO_ROWS))
        for row, values in enumerate(_DEMO_ROWS):
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:  # numeric-ish columns centred
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)
