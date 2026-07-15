"""Statistics tab: value overview across cards and sealed products.

Presentation-only, like every other panel in ``app/ui/widgets`` — takes a
:class:`~app.services.statistics_service.StatisticsOverview` and renders it
via :meth:`show_overview`. Laid out as: a combined portfolio overview at the
top (two small summary tiles, "Karten" and "Sealed-Produkte"), then a
"Karten" section and a "Sealed-Produkte" section, each with their own
breakdown tables — kept visually separate (see ``SuperSectionHeader`` in
``app/ui/theme.py``) since they're two different kinds of owned item with
almost no overlap in what's meaningful to show for each (e.g. cards have a
"Zustand" breakdown, sealed products don't; sealed products have a
"Kategorie" breakdown, cards don't).
"""

from __future__ import annotations

from functools import partial

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.services.statistics_service import (
    STALE_PRICE_THRESHOLD_DAYS,
    StaleSealedPriceEntry,
    StalePriceEntry,
    StatisticsOverview,
    ValueBreakdownEntry,
    ValueOverTimePoint,
)
from app.ui.set_icon_provider import get_set_icon
from app.ui.theme import PALETTE, apply_elevation
from app.utils.formatting import format_decimal
from app.utils.time import format_display_datetime

#: Wide enough for the "Preis aktualisieren" button's bold, padded label to
#: never clip -- the label text is always the same, so a fixed width (not a
#: sizeHint-derived one, measured before the button is actually styled) is
#: simplest and reliably correct.
_UPDATE_BUTTON_WIDTH = 160


class _CaseInsensitiveItem(QTableWidgetItem):
    """Sorts alphabetically by its own text, ignoring case -- the default

    QTableWidgetItem comparison is case-sensitive (mirrors card_list_panel.py's
    identically-named class)."""

    def __lt__(self, other: object) -> bool:
        if isinstance(other, QTableWidgetItem):
            return self.text().casefold() < other.text().casefold()
        return super().__lt__(other)


class _NumericItem(QTableWidgetItem):
    """Sorts by a separately-stored number, not its displayed text (e.g.

    "1550.00 EUR") -- text-based sorting would rank these alphabetically
    (mirrors card_list_panel.py's identically-named class)."""

    def __init__(self, text: str, sort_value: float) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, _NumericItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


def _value_text(value: float) -> str:
    return f"{format_decimal(value)} EUR"


def _formatted_as_of(as_of: str | None) -> str:
    if as_of is None:
        return tr("noch nie aktualisiert")
    return format_display_datetime(as_of)


def _days_text(days_since_update: int | None) -> str:
    if days_since_update is None:
        return tr("noch nie aktualisiert")
    return tr("vor {days} Tagen").format(days=days_since_update)


class StatisticsPanel(QWidget):
    """Shows the aggregated value overview computed by StatisticsService."""

    #: Emitted with a card id when "Preis aktualisieren" is clicked on one
    #: of the stale-price rows -- the same lookup the big button in the card
    #: details panel triggers, just reachable directly from this list too.
    price_lookup_requested = Signal(int)
    #: Mirrors ``price_lookup_requested``, for a sealed product's own
    #: stale-price row instead of a card's.
    sealed_price_lookup_requested = Signal(int)
    #: Emitted with every card id currently listed under "Karten mit
    #: veraltetem Preis" when "Alle aktualisieren" is clicked.
    bulk_price_lookup_requested = Signal(list)
    #: Mirrors ``bulk_price_lookup_requested``, for the sealed-product list.
    sealed_bulk_price_lookup_requested = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The stale-price tables embed a per-row "Preis aktualisieren" button
        # as a cell widget; Qt's built-in setSortingEnabled reorders items
        # but leaves cell widgets in place, desyncing the button from its
        # row's data. So these two sort manually: clicking a header re-sorts
        # the stored entries and fully re-renders (rebuilding buttons fresh)
        # instead of letting Qt reorder rows under existing widgets.
        self._stale_entries: list[StalePriceEntry] = []
        self._stale_sort_column: int | None = None
        self._stale_sort_order = Qt.SortOrder.AscendingOrder
        self._sealed_stale_entries: list[StaleSealedPriceEntry] = []
        self._sealed_stale_sort_column: int | None = None
        self._sealed_stale_sort_order = Qt.SortOrder.AscendingOrder
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

        header = QLabel(tr("Statistiken"))
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._build_portfolio_overview(layout)
        self._build_value_over_time_section(layout)
        self._build_cards_section(layout)
        self._build_sealed_section(layout)

        layout.addStretch(1)

    # -- Construction -------------------------------------------------------- #

    def _build_portfolio_overview(self, layout: QVBoxLayout) -> None:
        self._combined_total_label = QLabel("—")
        self._combined_total_label.setObjectName("PercentPositive")
        layout.addWidget(self._combined_total_label)

        cards_tile, self._cards_tile_value, self._cards_tile_subtext = self._make_stat_card(
            tr("Karten")
        )
        sealed_tile, self._sealed_tile_value, self._sealed_tile_subtext = self._make_stat_card(
            tr("Sealed-Produkte")
        )
        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(12)
        tiles_row.addWidget(cards_tile)
        tiles_row.addWidget(sealed_tile)
        layout.addLayout(tiles_row)

    @staticmethod
    def _make_stat_card(title: str) -> tuple[QWidget, QLabel, QLabel]:
        card = QWidget()
        card.setObjectName("StatCard")
        apply_elevation(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("StatCardTitle")
        card_layout.addWidget(title_label)

        value_label = QLabel("—")
        value_label.setObjectName("StatCardValue")
        card_layout.addWidget(value_label)

        subtext_label = QLabel("—")
        subtext_label.setObjectName("StatCardSubtext")
        card_layout.addWidget(subtext_label)

        return card, value_label, subtext_label

    def _build_value_over_time_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._section_label("Combined value over time"))

        self._value_chart_placeholder = QLabel(
            "Not enough price history yet -- update a few prices over time to see a trend here."
        )
        self._value_chart_placeholder.setObjectName("EmptyState")
        self._value_chart_placeholder.setWordWrap(True)
        layout.addWidget(self._value_chart_placeholder)

        self._value_chart = QChart()
        self._value_chart.legend().hide()
        self._value_chart.setBackgroundVisible(False)
        self._value_chart_view = QChartView(self._value_chart)
        self._value_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._value_chart_view.setMinimumHeight(280)
        self._value_chart_view.hide()
        layout.addWidget(self._value_chart_view)

    def _build_cards_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._super_section_label(tr("Karten")))

        layout.addWidget(self._section_label(tr("Sammlungen")))
        self._per_collection_table = self._make_table(
            [tr("Sammlung"), tr("Karten"), tr("Wert")]
        )
        layout.addWidget(self._per_collection_table)
        self._grand_total_label = QLabel("—")
        self._grand_total_label.setObjectName("FieldValue")
        layout.addWidget(self._grand_total_label)
        self._as_of_label = QLabel("—")
        self._as_of_label.setObjectName("FieldLabel")
        self._as_of_label.setWordWrap(True)
        layout.addWidget(self._as_of_label)

        stale_header, self._bulk_update_button = self._section_label_with_action(
            tr("Karten mit veraltetem Preis"), tr("Alle aktualisieren")
        )
        self._bulk_update_button.clicked.connect(self._on_bulk_update_clicked)
        layout.addWidget(stale_header)
        self._stale_table = self._make_table(
            ["Name", "Set", tr("Zuletzt aktualisiert"), tr("Aktion")],
            stretch_columns=(0, 1),
            sortable=False,
        )
        self._stale_table.horizontalHeader().sectionClicked.connect(
            self._on_stale_header_clicked
        )
        layout.addWidget(self._stale_table)
        stale_footnote = QLabel(
            tr(
                "Karten, deren Preis seit mehr als {days} Tagen nicht "
                "aktualisiert wurde oder noch nie ermittelt wurde."
            ).format(days=STALE_PRICE_THRESHOLD_DAYS)
        )
        stale_footnote.setObjectName("FieldLabel")
        stale_footnote.setWordWrap(True)
        layout.addWidget(stale_footnote)

        layout.addWidget(self._section_label(tr("Wert nach Set")))
        self._set_table = self._make_table(["Set", tr("Wert")])
        layout.addWidget(self._set_table)

        layout.addWidget(self._section_label(tr("Wert nach Sprache")))
        self._language_table = self._make_table([tr("Sprache"), tr("Wert")])
        layout.addWidget(self._language_table)

        layout.addWidget(self._section_label(tr("Wert nach Zustand")))
        self._condition_table = self._make_table([tr("Zustand"), tr("Wert")])
        layout.addWidget(self._condition_table)

        layout.addWidget(self._section_label(tr("Teuerste Karten")))
        self._expensive_table = self._make_table(
            ["Name", "Set", tr("Wert")], stretch_columns=(0, 1)
        )
        layout.addWidget(self._expensive_table)

        layout.addWidget(self._section_label(tr("Größte Preissteigerung")))
        self._price_increase_label = QLabel("—")
        self._price_increase_label.setObjectName("FieldValue")
        self._price_increase_label.setWordWrap(True)
        layout.addWidget(self._price_increase_label)

    def _build_sealed_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self._super_section_label(tr("Sealed-Produkte")))

        layout.addWidget(self._section_label(tr("Wert nach Kategorie")))
        self._sealed_category_table = self._make_table([tr("Kategorie"), tr("Wert")])
        layout.addWidget(self._sealed_category_table)

        layout.addWidget(self._section_label(tr("Teuerste Sealed-Produkte")))
        self._sealed_expensive_table = self._make_table(
            ["Name", tr("Kategorie"), tr("Wert")], stretch_columns=(0, 1)
        )
        layout.addWidget(self._sealed_expensive_table)

        sealed_stale_header, self._sealed_bulk_update_button = self._section_label_with_action(
            tr("Sealed-Produkte mit veraltetem Preis"), tr("Alle aktualisieren")
        )
        self._sealed_bulk_update_button.clicked.connect(self._on_sealed_bulk_update_clicked)
        layout.addWidget(sealed_stale_header)
        self._sealed_stale_table = self._make_table(
            ["Name", tr("Kategorie"), tr("Zuletzt aktualisiert"), tr("Aktion")],
            stretch_columns=(0, 1),
            sortable=False,
        )
        self._sealed_stale_table.horizontalHeader().sectionClicked.connect(
            self._on_sealed_stale_header_clicked
        )
        layout.addWidget(self._sealed_stale_table)
        sealed_stale_footnote = QLabel(
            tr(
                "Sealed-Produkte, deren Preis seit mehr als {days} Tagen nicht "
                "aktualisiert wurde oder noch nie ermittelt wurde."
            ).format(days=STALE_PRICE_THRESHOLD_DAYS)
        )
        sealed_stale_footnote.setObjectName("FieldLabel")
        sealed_stale_footnote.setWordWrap(True)
        layout.addWidget(sealed_stale_footnote)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    @staticmethod
    def _super_section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SuperSectionHeader")
        return label

    @staticmethod
    def _section_label_with_action(text: str, button_text: str) -> tuple[QWidget, QPushButton]:
        """A section header with a small action button aligned to its right --

        used by the two stale-price sections for their "Alle aktualisieren"
        bulk button, keeping it visually attached to the section it acts on.
        """
        row = QWidget()
        row.setObjectName("TransparentGroup")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(StatisticsPanel._section_label(text))
        row_layout.addStretch(1)
        button = QPushButton(button_text)
        button.setObjectName("Secondary")
        row_layout.addWidget(button)
        return row, button

    @staticmethod
    def _make_table(
        columns: list[str],
        stretch_columns: tuple[int, ...] = (0,),
        sortable: bool = True,
    ) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().hide()
        # ``sortable=False`` is used for tables with a cell-widget "Aktion"
        # column (see the manual-sort comment in __init__) -- those wire up
        # their own header-click handling instead.
        table.setSortingEnabled(sortable)
        table.setShowGrid(False)
        header_view = table.horizontalHeader()
        for col in range(len(columns)):
            mode = (
                QHeaderView.ResizeMode.Stretch
                if col in stretch_columns
                else QHeaderView.ResizeMode.ResizeToContents
            )
            header_view.setSectionResizeMode(col, mode)
        return table

    # -- Rendering ------------------------------------------------------------ #

    def show_overview(self, overview: StatisticsOverview) -> None:
        """Populate every section from a freshly computed overview."""
        self._fill_portfolio_overview(overview)
        self._fill_value_over_time(overview.value_over_time)

        self._fill_collection_table(overview)
        self._grand_total_label.setText(
            tr("Gesamtwert Karten (alle Sammlungen): {value}").format(
                value=_value_text(overview.grand_total)
            )
        )
        self._as_of_label.setText(
            tr(
                "Stand: {as_of} — basiert auf dem zuletzt bekannten Preis je Karte "
                "und kann veraltet sein."
            ).format(as_of=_formatted_as_of(overview.as_of))
        )
        self._fill_stale_table(overview.stale_price_cards)
        self._fill_breakdown_table(self._set_table, overview.value_by_set)
        self._fill_breakdown_table(self._language_table, overview.value_by_language)
        self._fill_breakdown_table(self._condition_table, overview.value_by_condition)
        self._fill_expensive_table(overview)
        self._fill_price_increase(overview)

        self._fill_breakdown_table(self._sealed_category_table, overview.value_by_sealed_category)
        self._fill_sealed_expensive_table(overview)
        self._fill_sealed_stale_table(overview.sealed_stale_price_products)

    def _fill_portfolio_overview(self, overview: StatisticsOverview) -> None:
        self._combined_total_label.setText(
            tr("Gesamtwert (Karten + Sealed-Produkte): {value}").format(
                value=_value_text(overview.combined_total)
            )
        )
        total_cards = sum(summary.card_count for summary in overview.per_collection)
        self._cards_tile_value.setText(_value_text(overview.grand_total))
        self._cards_tile_subtext.setText(
            tr("{count} Karte(n) · Stand: {as_of}").format(
                count=total_cards, as_of=_formatted_as_of(overview.as_of)
            )
        )
        self._sealed_tile_value.setText(_value_text(overview.sealed_total_value))
        self._sealed_tile_subtext.setText(
            tr("{count} Stück · Stand: {as_of}").format(
                count=overview.sealed_item_count, as_of=_formatted_as_of(overview.sealed_as_of)
            )
        )

    def _fill_value_over_time(self, points: list[ValueOverTimePoint]) -> None:
        self._value_chart.removeAllSeries()
        for axis in list(self._value_chart.axes()):
            self._value_chart.removeAxis(axis)

        if len(points) < 2:
            self._value_chart_view.hide()
            self._value_chart_placeholder.show()
            return
        self._value_chart_placeholder.hide()

        accent = QColor(PALETTE.accent)
        label_font = QFont()
        label_font.setPointSize(9)

        series = QLineSeries()
        series.setPen(QPen(accent, 3))
        series.setPointsVisible(True)
        for point in points:
            timestamp = QDateTime.fromString(point.recorded_at, Qt.DateFormat.ISODate)
            series.append(timestamp.toMSecsSinceEpoch(), point.total_value)
        series.hovered.connect(self._on_value_point_hovered)
        self._value_chart.addSeries(series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd.MM.")
        axis_x.setTitleText(tr("Datum"))
        axis_x.setLabelsFont(label_font)
        axis_x.setLabelsAngle(-45)
        axis_x.setLabelsColor(QColor(PALETTE.muted))
        axis_x.setGridLineColor(QColor(PALETTE.border))
        axis_x.setTickCount(min(len(points), 6))
        self._value_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.2f")
        axis_y.setTitleText(tr("Preis (€)"))
        axis_y.setLabelsFont(label_font)
        axis_y.setLabelsColor(QColor(PALETTE.muted))
        axis_y.setGridLineColor(QColor(PALETTE.border))
        self._value_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        self._value_chart_view.show()

    @staticmethod
    def _on_value_point_hovered(point: QPointF, state: bool) -> None:
        """Mirrors ``PriceHistoryDock``'s own hover tooltip, for the combined
        value-over-time chart."""
        if not state:
            QToolTip.hideText()
            return
        when = QDateTime.fromMSecsSinceEpoch(int(point.x())).toString("dd.MM.yyyy")
        QToolTip.showText(QCursor.pos(), f"{when}\n{format_decimal(point.y())} EUR")

    def _on_stale_header_clicked(self, column: int) -> None:
        if column == 3:  # Aktion -- a button, nothing to sort by
            return
        if self._stale_sort_column == column:
            self._stale_sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._stale_sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._stale_sort_column = column
            self._stale_sort_order = Qt.SortOrder.AscendingOrder
        self._render_stale_table()
        self._stale_table.horizontalHeader().setSortIndicator(
            self._stale_sort_column, self._stale_sort_order
        )

    def _on_sealed_stale_header_clicked(self, column: int) -> None:
        if column == 3:  # Aktion -- a button, nothing to sort by
            return
        if self._sealed_stale_sort_column == column:
            self._sealed_stale_sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sealed_stale_sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sealed_stale_sort_column = column
            self._sealed_stale_sort_order = Qt.SortOrder.AscendingOrder
        self._render_sealed_stale_table()
        self._sealed_stale_table.horizontalHeader().setSortIndicator(
            self._sealed_stale_sort_column, self._sealed_stale_sort_order
        )

    @staticmethod
    def _stale_sort_key(entry: StalePriceEntry, column: int):
        if column == 0:
            return entry.card.name.casefold()
        if column == 1:
            return (entry.card.set_name or "").casefold()
        # column == 2 (Zuletzt aktualisiert): never-priced sorts as the most
        # stale, not wherever "never" would fall alphabetically -- mirrors
        # the price-sentinel convention used elsewhere in this app.
        return entry.days_since_update if entry.days_since_update is not None else float("inf")

    @staticmethod
    def _sealed_stale_sort_key(entry: StaleSealedPriceEntry, column: int):
        if column == 0:
            return entry.product.name.casefold()
        if column == 1:
            return (entry.product.category or "").casefold()
        return entry.days_since_update if entry.days_since_update is not None else float("inf")

    def _on_bulk_update_clicked(self) -> None:
        card_ids = [entry.card.id for entry in self._stale_entries if entry.card.id is not None]
        if card_ids:
            self.bulk_price_lookup_requested.emit(card_ids)

    def _on_sealed_bulk_update_clicked(self) -> None:
        product_ids = [
            entry.product.id for entry in self._sealed_stale_entries if entry.product.id is not None
        ]
        if product_ids:
            self.sealed_bulk_price_lookup_requested.emit(product_ids)

    def set_bulk_update_running(self, running: bool) -> None:
        """Disables the "Alle aktualisieren" button for cards while a batch

        is in progress -- mirrors the per-row buttons' own disabled-while-
        running convention, just for the whole section at once.
        """
        self._bulk_update_button.setEnabled(not running and bool(self._stale_entries))

    def set_sealed_bulk_update_running(self, running: bool) -> None:
        """Mirrors ``set_bulk_update_running`` for the sealed-product section."""
        self._sealed_bulk_update_button.setEnabled(
            not running and bool(self._sealed_stale_entries)
        )

    def _fill_stale_table(self, entries: list[StalePriceEntry]) -> None:
        self._stale_entries = list(entries)
        self._render_stale_table()
        self._bulk_update_button.setEnabled(bool(self._stale_entries))

    def _render_stale_table(self) -> None:
        entries = self._stale_entries
        if self._stale_sort_column is not None:
            entries = sorted(
                entries,
                key=lambda entry: self._stale_sort_key(entry, self._stale_sort_column),
                reverse=self._stale_sort_order == Qt.SortOrder.DescendingOrder,
            )
        table = self._stale_table
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(entry.card.name))
            set_item = QTableWidgetItem(entry.card.set_name or "—")
            set_icon = get_set_icon(entry.card.set_code, entry.card.set_name)
            if set_icon is not None:
                set_item.setIcon(set_icon)
            table.setItem(row, 1, set_item)
            table.setItem(row, 2, QTableWidgetItem(_days_text(entry.days_since_update)))
            button = QPushButton(tr("Preis aktualisieren"))
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

    def _fill_sealed_stale_table(self, entries: list[StaleSealedPriceEntry]) -> None:
        self._sealed_stale_entries = list(entries)
        self._render_sealed_stale_table()
        self._sealed_bulk_update_button.setEnabled(bool(self._sealed_stale_entries))

    def _render_sealed_stale_table(self) -> None:
        entries = self._sealed_stale_entries
        if self._sealed_stale_sort_column is not None:
            entries = sorted(
                entries,
                key=lambda entry: self._sealed_stale_sort_key(
                    entry, self._sealed_stale_sort_column
                ),
                reverse=self._sealed_stale_sort_order == Qt.SortOrder.DescendingOrder,
            )
        table = self._sealed_stale_table
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            table.setItem(row, 0, QTableWidgetItem(entry.product.name))
            table.setItem(row, 1, QTableWidgetItem(entry.product.category or "—"))
            table.setItem(row, 2, QTableWidgetItem(_days_text(entry.days_since_update)))
            button = QPushButton(tr("Preis aktualisieren"))
            button.setObjectName("Secondary")
            button.setMinimumWidth(_UPDATE_BUTTON_WIDTH)
            product_id = entry.product.id
            if product_id is not None:
                button.clicked.connect(
                    partial(self.sealed_price_lookup_requested.emit, product_id)
                )
            table.setCellWidget(row, 3, button)
            table.setRowHeight(row, max(table.rowHeight(row), button.sizeHint().height() + 24))
        table.resizeColumnToContents(2)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(3, _UPDATE_BUTTON_WIDTH + 30)

    def _fill_collection_table(self, overview: StatisticsOverview) -> None:
        table = self._per_collection_table
        table.setSortingEnabled(False)
        table.setRowCount(len(overview.per_collection))
        for row, summary in enumerate(overview.per_collection):
            table.setItem(row, 0, _CaseInsensitiveItem(summary.name))
            table.setItem(
                row, 1, _NumericItem(str(summary.card_count), sort_value=summary.card_count)
            )
            table.setItem(
                row,
                2,
                _NumericItem(_value_text(summary.total_value), sort_value=summary.total_value),
            )
        table.setSortingEnabled(True)
        table.resizeRowsToContents()

    def _fill_breakdown_table(
        self, table: QTableWidget, entries: list[ValueBreakdownEntry]
    ) -> None:
        table.setSortingEnabled(False)
        table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            label_item = _CaseInsensitiveItem(entry.label)
            if entry.set_code:
                set_icon = get_set_icon(entry.set_code, entry.label)
                if set_icon is not None:
                    label_item.setIcon(set_icon)
            table.setItem(row, 0, label_item)
            table.setItem(
                row, 1, _NumericItem(_value_text(entry.total_value), sort_value=entry.total_value)
            )
        table.setSortingEnabled(True)
        table.resizeRowsToContents()

    def _fill_expensive_table(self, overview: StatisticsOverview) -> None:
        table = self._expensive_table
        table.setSortingEnabled(False)
        table.setRowCount(len(overview.most_expensive_cards))
        for row, card in enumerate(overview.most_expensive_cards):
            table.setItem(row, 0, _CaseInsensitiveItem(card.name))
            set_item = _CaseInsensitiveItem(card.set_name or "—")
            set_icon = get_set_icon(card.set_code, card.set_name)
            if set_icon is not None:
                set_item.setIcon(set_icon)
            table.setItem(row, 1, set_item)
            value = card.total_value or 0.0
            table.setItem(row, 2, _NumericItem(_value_text(value), sort_value=value))
        table.setSortingEnabled(True)
        table.resizeRowsToContents()

    def _fill_sealed_expensive_table(self, overview: StatisticsOverview) -> None:
        table = self._sealed_expensive_table
        table.setSortingEnabled(False)
        table.setRowCount(len(overview.most_expensive_sealed_products))
        for row, product in enumerate(overview.most_expensive_sealed_products):
            table.setItem(row, 0, _CaseInsensitiveItem(product.name))
            table.setItem(row, 1, _CaseInsensitiveItem(product.category or "—"))
            value = product.total_value or 0.0
            table.setItem(row, 2, _NumericItem(_value_text(value), sort_value=value))
        table.setSortingEnabled(True)
        table.resizeRowsToContents()

    def _fill_price_increase(self, overview: StatisticsOverview) -> None:
        highlight = overview.biggest_price_increase
        if highlight is None:
            self._price_increase_label.setText(
                tr("Keine Karte mit einer Preissteigerung in der Historie gefunden.")
            )
            return
        self._price_increase_label.setText(
            f"{highlight.card.name}: {format_decimal(highlight.previous_price)} EUR → "
            f"{format_decimal(highlight.latest_price)} EUR "
            f"(+{format_decimal(highlight.percent_change, 1)} %)"
        )
