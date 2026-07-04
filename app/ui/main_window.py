"""The application main window.

Assembles the three-column layout (collections · card list · card details),
the top toolbar (search · scanner · price update · export) and the dark
theme. The window itself holds no business logic: it builds the panels and
hands them to controllers (e.g. :class:`CollectionController`) that talk to
the services layer. Toolbar intents without a wired controller yet still
just produce a status-bar message.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QStyle,
    QTabWidget,
    QToolBar,
    QWidget,
)

from app import config
from app.catalog.pokemontcg_client import PokemonTcgClient
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.logging_config import get_logger
from app.services.card_service import CardService
from app.services.catalog_search_service import CatalogSearchService
from app.services.collection_service import CollectionService
from app.services.price_service import PriceService
from app.services.statistics_service import StatisticsService
from app.ui.controllers.card_controller import CardController
from app.ui.controllers.catalog_search_controller import CatalogSearchController
from app.ui.controllers.collection_controller import CollectionController
from app.ui.controllers.price_controller import PriceController
from app.ui.controllers.statistics_controller import StatisticsController
from app.ui.theme import build_stylesheet
from app.ui.widgets import CardDetailPanel, CardListPanel, CollectionPanel
from app.ui.widgets.price_history_dock import PriceHistoryDock
from app.ui.widgets.statistics_panel import StatisticsPanel

logger = get_logger(__name__)

_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.ico"

#: Panel minimum widths (px) so a normal resize can never squeeze a column's
#: text/controls out of view -- shrinking below the window's own minimum
#: size is still possible, but that's an explicit choice, not silent clipping.
_COLLECTION_PANEL_MIN_WIDTH = 160
_CARD_LIST_PANEL_MIN_WIDTH = 480
_CARD_DETAIL_PANEL_MIN_WIDTH = 320

#: Must match PriceHistoryDock's own setMinimumWidth() -- how much wider the
#: window grows/shrinks when the history dock is toggled on/off, so it adds
#: room on the side instead of squeezing the existing three-column layout.
_HISTORY_DOCK_WIDTH = 380


class MainWindow(QMainWindow):
    """Top-level window hosting the whole interface."""

    search_submitted = Signal(str)
    scan_requested = Signal()
    update_prices_requested = Signal()
    export_requested = Signal()

    def __init__(self, database: Database | None = None) -> None:
        super().__init__()
        self._owns_database = database is None
        if database is None:
            # Headless/demo convenience (e.g. tests): an initialised in-memory
            # database so the window is fully functional without a caller
            # having to bootstrap one. Production always passes a real one.
            database = Database(":memory:")
            database.initialize()
        self._database = database

        self.setWindowTitle(f"{config.APP_NAME}")
        if _ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(_ICON_PATH)))
        self.resize(1360, 820)
        self.setMinimumSize(1100, 700)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._connect_placeholder_feedback()
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet())

    # -- Construction ----------------------------------------------------- #

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Haupt-Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Karten durchsuchen  (z. B. „xatu skyridge holo“)")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(420)
        self._search.returnPressed.connect(self._submit_search)
        toolbar.addWidget(self._search)

        self._search_button = QPushButton("Suchen")
        self._search_button.clicked.connect(self._submit_search)
        toolbar.addWidget(self._search_button)
        toolbar.addSeparator()

        style = self.style()

        # Navigation between the two main views. The QTabWidget's own tab
        # bar is hidden (see _build_central) so this is the only way to
        # switch -- placed here since these toolbar buttons used to do
        # nothing else useful at a glance. Text labels, not icons -- a
        # standard-icon pair here wasn't obviously "Karten" vs. "Statistik"
        # at a glance.
        self._act_tab_cards = QAction("Karten", self)
        self._act_tab_stats = QAction("Statistik", self)
        self._act_tab_cards.setCheckable(True)
        self._act_tab_stats.setCheckable(True)
        self._act_tab_cards.setChecked(True)
        tab_nav_group = QActionGroup(self)
        tab_nav_group.setExclusive(True)
        tab_nav_group.addAction(self._act_tab_cards)
        tab_nav_group.addAction(self._act_tab_stats)
        self._act_tab_cards.triggered.connect(lambda: self._switch_central_tab(0))
        self._act_tab_stats.triggered.connect(lambda: self._switch_central_tab(1))
        toolbar.addAction(self._act_tab_cards)
        toolbar.addAction(self._act_tab_stats)
        toolbar.addSeparator()

        self._act_scan = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), "Scanner", self
        )
        self._act_update = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            "Cardmarket-Preise aktualisieren",
            self,
        )
        self._act_export = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Export", self
        )
        self._act_scan.triggered.connect(self.scan_requested)
        self._act_update.triggered.connect(self.update_prices_requested)
        self._act_export.triggered.connect(self.export_requested)
        toolbar.addAction(self._act_scan)
        toolbar.addAction(self._act_update)
        toolbar.addAction(self._act_export)

    def _build_central(self) -> None:
        self.collection_panel = CollectionPanel()
        self.card_list_panel = CardListPanel()
        self.card_detail_panel = CardDetailPanel()
        self.collection_panel.setMinimumWidth(_COLLECTION_PANEL_MIN_WIDTH)
        self.card_list_panel.setMinimumWidth(_CARD_LIST_PANEL_MIN_WIDTH)
        self.card_detail_panel.setMinimumWidth(_CARD_DETAIL_PANEL_MIN_WIDTH)

        self.price_history_dock = PriceHistoryDock(self)
        self.price_history_dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.price_history_dock)
        self.card_detail_panel.history_panel_requested.connect(self._toggle_history_dock)
        self.price_history_dock.visibilityChanged.connect(
            self.card_detail_panel.set_history_panel_visible
        )

        collection_service = CollectionService(CollectionRepository(self._database))
        self.collection_controller = CollectionController(
            self.collection_panel, collection_service, parent=self
        )

        card_service = CardService(CardRepository(self._database))
        self.card_controller = CardController(
            self.card_list_panel,
            self.card_detail_panel,
            card_service,
            PriceRepository(self._database),
            history_dock=self.price_history_dock,
            parent=self,
        )

        pokemontcg_client = PokemonTcgClient()
        catalog_search_service = CatalogSearchService(pokemontcg_client)
        self.catalog_search_controller = CatalogSearchController(
            self, catalog_search_service, parent=self
        )

        def open_price_service() -> tuple[PriceService, Database]:
            # Called from PriceLookupWorker's own thread: SQLite connections
            # can't be shared across threads, so this opens a fresh one to
            # the same database file rather than reusing self._database
            # (which belongs to the GUI thread).
            thread_database = Database(self._database.path)
            thread_database.initialize()
            service = PriceService(
                CardRepository(thread_database), PriceRepository(thread_database), pokemontcg_client
            )
            return service, thread_database

        self.statistics_panel = StatisticsPanel()
        statistics_service = StatisticsService(
            card_service, collection_service, PriceRepository(self._database)
        )
        self.statistics_controller = StatisticsController(
            self.statistics_panel, statistics_service, parent=self
        )

        self.price_controller = PriceController(
            self,
            self.card_detail_panel,
            open_price_service,
            self.card_controller,
            statistics_controller=self.statistics_controller,
            parent=self,
        )
        self.statistics_panel.price_lookup_requested.connect(self.price_controller.start_lookup)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.collection_panel)
        splitter.addWidget(self.card_list_panel)
        splitter.addWidget(self.card_detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([170, 730, 360])
        splitter.setContentsMargins(10, 10, 10, 10)
        splitter.setHandleWidth(10)

        tabs = QTabWidget()
        tabs.addTab(splitter, "Karten")
        tabs.addTab(self.statistics_panel, "Statistiken")
        # Navigated exclusively via the toolbar buttons above (_act_tab_cards/
        # _act_tab_stats) -- the tab bar itself would just be a redundant
        # second way to do the same thing.
        tabs.tabBar().hide()
        tabs.currentChanged.connect(self._on_central_tab_changed)
        self.setCentralWidget(tabs)

    def _build_statusbar(self) -> None:
        status = QStatusBar()
        status.showMessage(f"{config.APP_NAME} v{config.APP_VERSION}  ·  bereit")
        self.setStatusBar(status)

    def _connect_placeholder_feedback(self) -> None:
        """Wire toolbar intents to their real handlers, or (for those not yet
        implemented) a status-bar placeholder message."""
        self.search_submitted.connect(self.catalog_search_controller.handle_search)
        self.scan_requested.connect(
            lambda: self._flash("Scanner folgt in einem späteren Schritt.")
        )
        self.update_prices_requested.connect(
            lambda: self._flash(
                "Preise werden pro Karte einzeln abgerufen (Knopf in den "
                "Kartendetails) — kein automatischer Sammel-Lauf."
            )
        )
        self.export_requested.connect(
            lambda: self._flash("Export folgt in einem späteren Schritt.")
        )
        self.collection_controller.selection_changed.connect(self.card_controller.set_collection)
        self.catalog_search_controller.card_add_requested.connect(
            self.card_controller.add_from_catalog
        )

    # -- Behaviour -------------------------------------------------------- #

    def _flash(self, message: str) -> None:
        """Show a transient status-bar message."""
        self.statusBar().showMessage(message, 5000)

    def _submit_search(self) -> None:
        self.search_submitted.emit(self._search.text().strip())

    def _switch_central_tab(self, index: int) -> None:
        self.centralWidget().setCurrentIndex(index)

    def _on_central_tab_changed(self, index: int) -> None:
        # Recomputed only when the tab actually becomes active -- statistics
        # aren't a real-time feature, so there's no need to keep them in
        # sync while the user is on the "Karten" tab.
        if self.centralWidget().tabText(index) == "Statistiken":
            self.statistics_controller.refresh()
        self._act_tab_cards.setChecked(index == 0)
        self._act_tab_stats.setChecked(index == 1)
        # The catalogue search only makes sense on "Karten" -- showing it
        # while looking at "Statistik" implied it searched something there.
        is_cards_tab = index == 0
        self._search.setVisible(is_cards_tab)
        self._search_button.setVisible(is_cards_tab)

    def _toggle_history_dock(self, card_id: int) -> None:  # noqa: ARG002 -- dock content already synced by CardController
        # A QDockWidget takes its space out of the central widget rather
        # than overlaying it -- without growing the window by the same
        # amount, showing the dock would squeeze the three-column layout
        # (and its text) instead of just adding room on the side.
        if self.price_history_dock.isVisible():
            self.price_history_dock.hide()
            self.resize(self.width() - _HISTORY_DOCK_WIDTH, self.height())
        else:
            self.price_history_dock.show()
            self.price_history_dock.raise_()
            self.resize(self.width() + _HISTORY_DOCK_WIDTH, self.height())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt override
        """Close the database if this window created it itself."""
        if self._owns_database:
            self._database.close()
        super().closeEvent(event)
