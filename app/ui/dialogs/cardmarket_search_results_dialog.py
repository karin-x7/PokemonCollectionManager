"""Modal dialog showing Cardmarket's own site-search results.

Presentation-only, mirrors
:class:`~app.ui.dialogs.catalog_search_results_dialog.CatalogSearchResultsDialog`:
displays whatever :class:`~app.pricing.models.CardmarketSearchResult` list
it is given. Selecting a row and clicking "Übernehmen" emits
``result_confirmed`` with the chosen match -- resolving it to a real URL and
persisting it is handled by
:class:`~app.ui.controllers.cardmarket_search_controller.CardmarketSearchController`,
not here.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.i18n import tr
from app.pricing.models import CardmarketSearchResult
from app.ui.dialogs.dimmed_dialog import DimmedDialog


def _columns() -> list[str]:
    # A function, not a module-level constant: tr() must run when the dialog
    # is actually built (after MainWindow has loaded the persisted UI
    # language), not once at import time.
    return ["Name", "Set", "Nr.", tr("Preis")]


class CardmarketSearchResultsDialog(DimmedDialog):
    """Read-only list of Cardmarket search matches, selectable to confirm."""

    #: Emitted with the selected CardmarketSearchResult when "Übernehmen" is
    #: clicked.
    result_confirmed = Signal(object)
    #: Emitted when the empty-state "Search in browser" button is clicked --
    #: the automated search found no candidates at all, so this is an inline
    #: fallback to let the user search Cardmarket themselves in a real,
    #: normal browser window instead of being left at a dead end. The dialog
    #: itself stays open (the user can note the right product's URL, then
    #: paste it via "Bearbeiten" once they close this).
    manual_search_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Cardmarket-Suchergebnisse"))
        self.resize(560, 400)
        self._matches: list[CardmarketSearchResult] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        columns = _columns()

        # Shown from the moment the dialog opens until set_results() is
        # called -- the search itself runs in the background and can take a
        # few seconds (a real Chrome tab), so popping the dialog up empty
        # made the whole app look frozen (live-reported point of confusion).
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

        # Only shown alongside the empty state above -- a dead end otherwise
        # (live-reported: no way forward besides cancelling and giving up).
        self._manual_search_button = QPushButton(tr("In Cardmarket-Suche im Browser öffnen"))
        self._manual_search_button.clicked.connect(self.manual_search_requested)
        self._manual_search_button.hide()
        layout.addWidget(self._manual_search_button)

        self._table = QTableWidget(0, len(columns))
        self._table.hide()
        self._table.setHorizontalHeaderLabels(columns)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._update_confirm_button_enabled)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(columns)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        self._confirm_button = buttons.addButton(
            tr("Übernehmen"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self._confirm_button.clicked.connect(self._on_confirm_clicked)
        self._update_confirm_button_enabled()
        layout.addWidget(buttons)

    def set_results(self, matches: list[CardmarketSearchResult]) -> None:
        """Populate the table with search matches (or show the empty state)."""
        self._loading_label.hide()
        self._loading_bar.hide()
        self._matches = matches
        self._empty_label.setVisible(not matches)
        self._manual_search_button.setVisible(not matches)
        self._table.setVisible(bool(matches))
        self._table.setRowCount(len(matches))
        for row, result in enumerate(matches):
            values = [result.name, result.set_name, result.card_number, result.price_hint]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)
        self._update_confirm_button_enabled()

    def _update_confirm_button_enabled(self) -> None:
        self._confirm_button.setEnabled(self._table.currentRow() >= 0)

    def _on_confirm_clicked(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._matches):
            return
        self.result_confirmed.emit(self._matches[row])
        self.accept()
