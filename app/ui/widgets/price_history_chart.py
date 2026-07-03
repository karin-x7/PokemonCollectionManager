"""Small embedded line chart of a card's Cardmarket price history.

Presentation-only: takes whatever :class:`~app.models.price.PriceRecord`
list it's given and renders it, or a short explanatory placeholder text if
there isn't enough data yet for a meaningful line. No persistence, no
business logic — the caller (``CardController``) fetches the history.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.models.price import PriceRecord


class PriceHistoryChartView(QWidget):
    """Embedded price-over-time chart for the card details panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Noch kein Preisverlauf vorhanden.")
        self._placeholder.setObjectName("FieldValue")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        layout.addWidget(self._placeholder)

        self._chart = QChart()
        self._chart.legend().hide()
        self._chart.setMargins(self._chart.margins())
        self._chart.setBackgroundVisible(False)

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(150)
        self._chart_view.hide()
        layout.addWidget(self._chart_view)

    def show_history(self, records: list[PriceRecord]) -> None:
        """Render ``records`` (oldest first), or a placeholder if too few."""
        self._chart.removeAllSeries()
        for axis in list(self._chart.axes()):
            self._chart.removeAxis(axis)

        if len(records) < 2:
            self._chart_view.hide()
            self._placeholder.setText(
                f"Nur ein Preis bisher: {records[0].price:.2f} {records[0].currency}"
                if records
                else "Noch kein Preisverlauf vorhanden."
            )
            self._placeholder.show()
            return

        self._placeholder.hide()

        series = QLineSeries()
        for record in records:
            timestamp = QDateTime.fromString(record.recorded_at, Qt.DateFormat.ISODate)
            series.append(timestamp.toMSecsSinceEpoch(), record.price)
        self._chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd.MM.yy")
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.2f")
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self._chart_view.show()

    def show_empty(self) -> None:
        """Reset to the no-history placeholder."""
        self.show_history([])
