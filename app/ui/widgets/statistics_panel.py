"""Statistics tab: value overview across every collection.

Presentation-only, like every other panel in ``app/ui/widgets`` — takes a
:class:`~app.services.statistics_service.StatisticsOverview` and renders it
via :meth:`show_overview`. No signals: the only "user intent" here is the
tab switch itself, already handled by :class:`~app.ui.main_window.MainWindow`
via ``QTabWidget.currentChanged``.
"""

from __future__ import annotations

from datetime import datetime
from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.statistics_service import (
    STALE_PRICE_THRESHOLD_DAYS,
    StalePriceEntry,
    StatisticsOverview,
    ValueBreakdownEntry,
)


#: Wide enough for the "Preis aktualisieren" button's bold, padded label to
#: never clip -- the label text is always the same, so a fixed width (not a
#: sizeHint-derived one, measured before the button is actually styled) is
#: simplest and reliably correct.
_UPDATE_BUTTON_WIDTH = 160


def _value_text(value: float) -> str:
    return f"{value:.2f} EUR"


def _formatted_as_of(as_of: str | None) -> str:
    if as_of is None:
        return "noch nie aktualisiert"
    return datetime.fromisoformat(as_of).strftime("%d.%m.%Y %H:%M")


def _days_text(days_since_update: int | None) -> str:
    return "noch nie aktualisiert" if days_since_update is None else f"vor {days_since_update} Tagen"


class StatisticsPanel(QWidget):
    """Shows the aggregated value overview computed by StatisticsService."""

    #: Emitted with a card id when "Preis aktualisieren" is clicked on one
    #: of the stale-price rows -- the same lookup the big button in the card
    #: details panel triggers, just reachable directly from this list too.
    price_lookup_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("Panel")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(18)

        header = QLabel("Statistiken")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        layout.addWidget(self._section_label("Gesamtpreis-Übersicht"))
        self._per_collection_table = self._make_table(["Sammlung", "Karten", "Wert"])
        layout.addWidget(self._per_collection_table)
        self._grand_total_label = QLabel("—")
        self._grand_total_label.setObjectName("PercentPositive")
        layout.addWidget(self._grand_total_label)
        self._as_of_label = QLabel("—")
        self._as_of_label.setObjectName("FieldLabel")
        self._as_of_label.setWordWrap(True)
        layout.addWidget(self._as_of_label)

        layout.addWidget(self._section_label("Karten mit veraltetem Preis"))
        self._stale_table = self._make_table(
            ["Name", "Set", "Zuletzt aktualisiert", "Aktion"], stretch_columns=(0, 1)
        )
        layout.addWidget(self._stale_table)
        stale_footnote = QLabel(
            f"Karten, deren Preis seit mehr als {STALE_PRICE_THRESHOLD_DAYS} Tagen nicht "
            "aktualisiert wurde oder noch nie ermittelt wurde."
        )
        stale_footnote.setObjectName("FieldLabel")
        stale_footnote.setWordWrap(True)
        layout.addWidget(stale_footnote)

        layout.addWidget(self._section_label("Wert nach Set"))
        self._set_table = self._make_table(["Set", "Wert"])
        layout.addWidget(self._set_table)

        layout.addWidget(self._section_label("Wert nach Sprache"))
        self._language_table = self._make_table(["Sprache", "Wert"])
        layout.addWidget(self._language_table)

        layout.addWidget(self._section_label("Wert nach Zustand"))
        self._condition_table = self._make_table(["Zustand", "Wert"])
        layout.addWidget(self._condition_table)

        layout.addWidget(self._section_label("Teuerste Karten"))
        self._expensive_table = self._make_table(["Name", "Set", "Wert"], stretch_columns=(0, 1))
        layout.addWidget(self._expensive_table)

        layout.addWidget(self._section_label("Größte Preissteigerung"))
        self._price_increase_label = QLabel("—")
        self._price_increase_label.setObjectName("FieldValue")
        self._price_increase_label.setWordWrap(True)
        layout.addWidget(self._price_increase_label)

        layout.addStretch(1)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    @staticmethod
    def _make_table(columns: list[str], stretch_columns: tuple[int, ...] = (0,)) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().hide()
        header_view = table.horizontalHeader()
        for col in range(len(columns)):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if col in stretch_columns
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header_view.setSectionResizeMode(col, mode)
        return table

    def show_overview(self, overview: StatisticsOverview) -> None:
        """Populate every section from a freshly computed overview."""
        self._fill_collection_table(overview)
        self._grand_total_label.setText(
            f"Gesamtwert (alle Sammlungen): {_value_text(overview.grand_total)}"
        )
        self._as_of_label.setText(
            f"Stand: {_formatted_as_of(overview.as_of)} — basiert auf dem zuletzt "
            "bekannten Preis je Karte und kann veraltet sein."
        )
        self._fill_stale_table(overview.stale_price_cards)
        self._fill_breakdown_table(self._set_table, overview.value_by_set)
        self._fill_breakdown_table(self._language_table, overview.value_by_language)
        self._fill_breakdown_table(self._condition_table, overview.value_by_condition)
        self._fill_expensive_table(overview)
        self._fill_price_increase(overview)

    def _fill_stale_table(self, entries: list[StalePriceEntry]) -> None:
        table = self._stale_table
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(entry.card.name))
            table.setItem(row, 1, QTableWidgetItem(entry.card.set_name or "—"))
            table.setItem(row, 2, QTableWidgetItem(_days_text(entry.days_since_update)))
            button = QPushButton("Preis aktualisieren")
            button.setObjectName("Secondary")
            button.setMinimumWidth(_UPDATE_BUTTON_WIDTH)
            card_id = entry.card.id
            if card_id is not None:
                button.clicked.connect(partial(self.price_lookup_requested.emit, card_id))
            table.setCellWidget(row, 3, button)
            # resizeRowsToContents() (below) doesn't reliably account for a
            # cell *widget*'s real, QSS-styled height (only QTableWidgetItem
            # text) -- rows stayed too short, clipping the button's bold,
            # padded label top/bottom and making it look garbled. Setting
            # the row height explicitly from the button's own sizeHint
            # fixes that regardless of what resizeRowsToContents decides.
            table.setRowHeight(row, max(table.rowHeight(row), button.sizeHint().height() + 24))
        table.resizeColumnToContents(2)
        # Likewise, the column width heuristic doesn't reliably pick up a
        # cell widget's sizeHint either -- fixed width for this one,
        # constant button label instead.
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(3, _UPDATE_BUTTON_WIDTH + 30)

    def _fill_collection_table(self, overview: StatisticsOverview) -> None:
        table = self._per_collection_table
        table.setRowCount(len(overview.per_collection))
        for row, summary in enumerate(overview.per_collection):
            table.setItem(row, 0, QTableWidgetItem(summary.name))
            table.setItem(row, 1, QTableWidgetItem(str(summary.card_count)))
            table.setItem(row, 2, QTableWidgetItem(_value_text(summary.total_value)))
        table.resizeRowsToContents()

    def _fill_breakdown_table(
        self, table: QTableWidget, entries: list[ValueBreakdownEntry]
    ) -> None:
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(entry.label))
            table.setItem(row, 1, QTableWidgetItem(_value_text(entry.total_value)))
        table.resizeRowsToContents()

    def _fill_expensive_table(self, overview: StatisticsOverview) -> None:
        table = self._expensive_table
        table.setRowCount(len(overview.most_expensive_cards))
        for row, card in enumerate(overview.most_expensive_cards):
            table.setItem(row, 0, QTableWidgetItem(card.name))
            table.setItem(row, 1, QTableWidgetItem(card.set_name or "—"))
            table.setItem(row, 2, QTableWidgetItem(_value_text(card.total_value or 0.0)))
        table.resizeRowsToContents()

    def _fill_price_increase(self, overview: StatisticsOverview) -> None:
        highlight = overview.biggest_price_increase
        if highlight is None:
            self._price_increase_label.setText(
                "Keine Karte mit einer Preissteigerung in der Historie gefunden."
            )
            return
        self._price_increase_label.setText(
            f"{highlight.card.name}: {highlight.previous_price:.2f} EUR → "
            f"{highlight.latest_price:.2f} EUR (+{highlight.percent_change:.1f} %)"
        )
