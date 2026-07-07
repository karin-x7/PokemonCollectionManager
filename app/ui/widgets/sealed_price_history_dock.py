"""Right-side collapsible dock: price-history chart for a sealed product.

Mirrors ``price_history_dock.py`` almost verbatim, ``Card``/``PriceRecord``
swapped for ``SealedProduct``/``SealedPriceRecord``. A separate dock
instance from the Karten tab's (not shared) -- only one tab is ever active
at a time, and ``MainWindow`` hides whichever dock belongs to the tab being
left, mirroring how other tab-scoped UI elements already toggle visibility.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.models.sealed_price import SealedPriceRecord
from app.models.sealed_product import SealedProduct
from app.ui.theme import PALETTE

_MAX_HISTORY_ROWS = 10


class SealedPriceHistoryDock(QDockWidget):
    """Collapsible price-history panel for a sealed product: chart, % change,

    recent updates, reset."""

    #: Emitted with the product id after the user confirms the reset prompt.
    history_reset_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(tr("Preisverlauf"), parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self._current_product_id: int | None = None
        self._build()

    def _build(self) -> None:
        container = QWidget()
        container.setObjectName("Panel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._product_name_label = QLabel("—")
        self._product_name_label.setObjectName("PanelHeader")
        layout.addWidget(self._product_name_label)

        self._placeholder = QLabel(tr("Noch kein Preisverlauf vorhanden."))
        self._placeholder.setObjectName("EmptyState")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        layout.addWidget(self._placeholder)

        self._chart = QChart()
        self._chart.legend().hide()
        self._chart.setBackgroundVisible(False)
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(280)
        self._chart_view.hide()
        layout.addWidget(self._chart_view)

        self._percent_label = QLabel("")
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._percent_label.hide()
        layout.addWidget(self._percent_label)

        history_header = QLabel(tr("Letzte Aktualisierungen:"))
        history_header.setObjectName("FieldLabel")
        layout.addWidget(history_header)

        self._history_list = QListWidget()
        self._history_list.setWordWrap(True)
        self._history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._history_list.setMinimumHeight(260)
        layout.addWidget(self._history_list, stretch=1)

        self._reset_button = QPushButton(tr("Historie zurücksetzen"))
        self._reset_button.setObjectName("Danger")
        self._reset_button.setEnabled(False)
        self._reset_button.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self._reset_button)

        self.setWidget(container)
        self.setMinimumWidth(380)

    def show_history(self, product: SealedProduct, records: list[SealedPriceRecord]) -> None:
        """Populate the chart, % change and recent-updates list for ``product``."""
        self._current_product_id = product.id
        self._reset_button.setEnabled(bool(records))
        self._product_name_label.setText(product.name)

        self._clear_chart()
        if len(records) < 2:
            self._chart_view.hide()
            self._percent_label.hide()
            self._placeholder.setText(
                tr("Nur ein Preis bisher: {price} {currency}").format(
                    price=f"{records[0].price:.2f}", currency=records[0].currency
                )
                if records
                else tr("Noch kein Preisverlauf vorhanden.")
            )
            self._placeholder.show()
        else:
            self._placeholder.hide()
            self._render_chart(records)
            self._render_percent_change(records)

        self._render_history_list(records)

    def show_empty(self) -> None:
        """Reset to the no-product placeholder state."""
        self._current_product_id = None
        self._product_name_label.setText("—")
        self._reset_button.setEnabled(False)
        self._clear_chart()
        self._chart_view.hide()
        self._percent_label.hide()
        self._placeholder.setText(tr("Noch kein Preisverlauf vorhanden."))
        self._placeholder.show()
        self._history_list.clear()

    def _clear_chart(self) -> None:
        self._chart.removeAllSeries()
        for axis in list(self._chart.axes()):
            self._chart.removeAxis(axis)

    def _render_chart(self, records: list[SealedPriceRecord]) -> None:
        accent = QColor(PALETTE.accent)
        label_font = QFont()
        label_font.setPointSize(9)

        series = QLineSeries()
        series.setPen(QPen(accent, 3))
        series.setPointsVisible(True)
        for record in records:
            timestamp = QDateTime.fromString(record.recorded_at, Qt.DateFormat.ISODate)
            series.append(timestamp.toMSecsSinceEpoch(), record.price)
        series.hovered.connect(self._on_point_hovered)
        self._chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd.MM.")
        axis_x.setTitleText(tr("Datum"))
        axis_x.setLabelsFont(label_font)
        axis_x.setLabelsAngle(-45)
        axis_x.setLabelsColor(QColor(PALETTE.muted))
        axis_x.setGridLineColor(QColor(PALETTE.border))
        axis_x.setTickCount(min(len(records), 6))
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.2f")
        axis_y.setTitleText(tr("Preis (€)"))
        axis_y.setLabelsFont(label_font)
        axis_y.setLabelsColor(QColor(PALETTE.muted))
        axis_y.setGridLineColor(QColor(PALETTE.border))
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self._chart_view.show()

    @staticmethod
    def _on_point_hovered(point: QPointF, state: bool) -> None:
        """Mirrors ``price_history_dock.PriceHistoryDock``'s own hover tooltip."""
        if not state:
            QToolTip.hideText()
            return
        when = QDateTime.fromMSecsSinceEpoch(int(point.x())).toString("dd.MM.yyyy")
        QToolTip.showText(QCursor.pos(), f"{when}\n{point.y():.2f} EUR")

    def _render_percent_change(self, records: list[SealedPriceRecord]) -> None:
        previous, latest = records[-2].price, records[-1].price
        if previous == 0:
            self._percent_label.hide()
            return
        change = (latest - previous) / previous * 100
        sign = "+" if change >= 0 else "−"
        self._percent_label.setText(
            tr("{sign}{value} % ggü. letzter Aktualisierung").format(
                sign=sign, value=f"{abs(change):.1f}"
            )
        )
        self._percent_label.setObjectName("PercentPositive" if change >= 0 else "PercentNegative")
        self._percent_label.style().unpolish(self._percent_label)
        self._percent_label.style().polish(self._percent_label)
        self._percent_label.show()

    def _render_history_list(self, records: list[SealedPriceRecord]) -> None:
        self._history_list.clear()
        for record in reversed(records[-_MAX_HISTORY_ROWS:]):
            timestamp = QDateTime.fromString(record.recorded_at, Qt.DateFormat.ISODate)
            when = timestamp.toString("dd.MM.yy   HH:mm")
            price_text = f"{record.price:.2f} {record.currency}"
            # The rationale (e.g. "estimated from German, requested was
            # Japanese") is appended when it says more than the quality
            # label alone already does -- see price_history_dock.py's
            # matching change.
            quality_label = tr(record.price_quality.label)
            rationale = record.rationale or ""
            text = f"{when}  ·  {price_text}\n{quality_label}"
            if rationale and rationale != quality_label:
                text += f"\n{rationale}"
            item = QListWidgetItem(text)
            self._history_list.addItem(item)

    def _on_reset_clicked(self) -> None:
        if self._current_product_id is None:
            return
        confirmed = QMessageBox.question(
            self,
            tr("Historie zurücksetzen"),
            tr(
                "Wirklich den gesamten Preisverlauf dieses Produkts löschen? "
                "Das kann nicht rückgängig gemacht werden."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self.history_reset_requested.emit(self._current_product_id)
