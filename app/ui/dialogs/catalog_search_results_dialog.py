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
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.catalog.models import CatalogCard
from app.i18n import tr
from app.ui.dialogs.dimmed_dialog import DimmedDialog
from app.ui.set_icon_provider import get_set_icon


def _columns() -> list[str]:
    # A function, not a module-level constant: tr() must run when the dialog
    # is actually built (after MainWindow has loaded the persisted UI
    # language), not once at import time, which would always bake in
    # whatever language was still the default at that point.
    return ["Name", "Set", "Nr.", tr("Rarität")]


_SET_COLUMN = 1


class CatalogSearchResultsDialog(DimmedDialog):
    """Read-only list of catalogue search matches, selectable to add."""

    #: Emitted with the selected CatalogCard when "Hinzufügen" is clicked.
    add_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Suchergebnisse"))
        self.resize(560, 400)
        self._matches: list[CatalogCard] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        columns = _columns()

        # Shown from the moment the dialog opens until set_results() is
        # called -- the search itself is a blocking network call and popping
        # the dialog up empty in the meantime made the whole app look frozen
        # (live-reported point of confusion).
        self._loading_label = QLabel(tr("Suche läuft…"))
        self._loading_label.setObjectName("SearchLoadingLabel")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._loading_label)
        self._loading_bar = QProgressBar()
        self._loading_bar.setObjectName("SearchLoadingBar")
        self._loading_bar.setRange(0, 0)  # indeterminate
        self._loading_bar.setTextVisible(False)
        layout.addWidget(self._loading_bar)

        self._empty_label = QLabel(tr("Keine Treffer."))
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self._table = QTableWidget(0, len(columns))
        self._table.hide()
        self._table.setHorizontalHeaderLabels(columns)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._update_add_button_enabled)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(columns)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        self._add_button = buttons.addButton(
            tr("Hinzufügen"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self._add_button.clicked.connect(self._on_add_clicked)
        self._update_add_button_enabled()
        layout.addWidget(buttons)

    def set_results(self, matches: list[CatalogCard]) -> None:
        """Populate the table with search matches (or show the empty state)."""
        self._loading_label.hide()
        self._loading_bar.hide()
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
                if col == _SET_COLUMN:
                    set_icon = get_set_icon(card.set_code, card.set_name)
                    if set_icon is not None:
                        item.setIcon(set_icon)
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
