"""Statistics tab: value overview across every collection.

Presentation-only, like every other panel in ``app/ui/widgets`` — takes a
:class:`~app.services.statistics_service.StatisticsOverview` and renders it
via :meth:`show_overview`. No signals: the only "user intent" here is the
tab switch itself, already handled by :class:`~app.ui.main_window.MainWindow`
via ``QTabWidget.currentChanged``.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.statistics_service import StatisticsOverview, ValueBreakdownEntry


def _value_text(value: float) -> str:
    return f"{value:.2f} EUR"


class StatisticsPanel(QWidget):
    """Shows the aggregated value overview computed by StatisticsService."""

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
        self._expensive_table = self._make_table(["Name", "Set", "Wert"])
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
        label.setObjectName("FieldLabel")
        return label

    @staticmethod
    def _make_table(columns: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().hide()
        header_view = table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(columns)):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def show_overview(self, overview: StatisticsOverview) -> None:
        """Populate every section from a freshly computed overview."""
        self._fill_collection_table(overview)
        self._grand_total_label.setText(
            f"Gesamtwert (alle Sammlungen): {_value_text(overview.grand_total)}"
        )
        self._fill_breakdown_table(self._set_table, overview.value_by_set)
        self._fill_breakdown_table(self._language_table, overview.value_by_language)
        self._fill_breakdown_table(self._condition_table, overview.value_by_condition)
        self._fill_expensive_table(overview)
        self._fill_price_increase(overview)

    def _fill_collection_table(self, overview: StatisticsOverview) -> None:
        table = self._per_collection_table
        table.setRowCount(len(overview.per_collection))
        for row, summary in enumerate(overview.per_collection):
            table.setItem(row, 0, QTableWidgetItem(summary.name))
            table.setItem(row, 1, QTableWidgetItem(str(summary.card_count)))
            table.setItem(row, 2, QTableWidgetItem(_value_text(summary.total_value)))

    def _fill_breakdown_table(
        self, table: QTableWidget, entries: list[ValueBreakdownEntry]
    ) -> None:
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(entry.label))
            table.setItem(row, 1, QTableWidgetItem(_value_text(entry.total_value)))

    def _fill_expensive_table(self, overview: StatisticsOverview) -> None:
        table = self._expensive_table
        table.setRowCount(len(overview.most_expensive_cards))
        for row, card in enumerate(overview.most_expensive_cards):
            table.setItem(row, 0, QTableWidgetItem(card.name))
            table.setItem(row, 1, QTableWidgetItem(card.set_name or "—"))
            table.setItem(row, 2, QTableWidgetItem(_value_text(card.total_value or 0.0)))

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
