"""The application main window.

Assembles the three-column layout (collections · card list · card details),
the top toolbar (search · manual entry · export) and the dark theme. The
window itself holds no business logic: it builds the panels and hands them
to controllers (e.g. :class:`CollectionController`) that talk to the
services layer.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.catalog.pokemontcg_client import PokemonTcgClient
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.database.repositories.wantlist_repository import WantlistRepository
from app.i18n import tr
from app.logging_config import get_logger
from app.models.card import CardFilter
from app.models.sealed_product import SealedProductFilter
from app.services.card_service import CardService
from app.services.catalog_search_service import CatalogSearchService
from app.services.collection_service import CollectionService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.services.price_service import PriceService
from app.services.sealed_price_service import SealedPriceService
from app.services.sealed_product_service import SealedProductService
from app.services.statistics_service import StatisticsService
from app.services.wantlist_price_service import WantlistPriceService
from app.services.wantlist_service import WantlistService
from app.ui.controllers.backup_controller import BackupController
from app.ui.controllers.card_controller import CardController
from app.ui.controllers.cardmarket_search_controller import CardmarketSearchController
from app.ui.controllers.catalog_search_controller import CatalogSearchController
from app.ui.controllers.collection_controller import CollectionController
from app.ui.controllers.export_controller import ExportController
from app.ui.controllers.import_controller import ImportController
from app.ui.controllers.manual_entry_controller import ManualEntryController
from app.ui.controllers.price_controller import PriceController
from app.ui.controllers.sealed_entry_controller import SealedEntryController
from app.ui.controllers.sealed_price_controller import SealedPriceController
from app.ui.controllers.sealed_product_controller import SealedProductController
from app.ui.controllers.settings_controller import SettingsController
from app.ui.controllers.statistics_controller import StatisticsController
from app.ui.controllers.wantlist_controller import WantlistController
from app.ui.controllers.wantlist_entry_controller import WantlistEntryController
from app.ui.controllers.wantlist_price_controller import WantlistPriceController
from app.ui.theme import build_stylesheet
from app.ui.widgets import CardDetailPanel, CardListPanel, CollectionPanel
from app.ui.widgets.busy_overlay import BusyOverlay
from app.ui.widgets.price_history_dock import PriceHistoryDock
from app.ui.widgets.sealed_price_history_dock import SealedPriceHistoryDock
from app.ui.widgets.sealed_product_detail_panel import SealedProductDetailPanel
from app.ui.widgets.sealed_product_list_panel import SealedProductListPanel
from app.ui.widgets.statistics_panel import StatisticsPanel
from app.ui.widgets.wantlist_panel import WantlistPanel
from app.ui.workers.update_check_worker import UpdateCheckWorker

logger = get_logger(__name__)

_ICON_PATH = Path(__file__).resolve().parent.parent / "resources" / "icon.ico"

#: Panel minimum widths (px) so a normal resize can never squeeze a column's
#: text/controls out of view -- shrinking below the window's own minimum
#: size is still possible, but that's an explicit choice, not silent clipping.
_COLLECTION_PANEL_MIN_WIDTH = 160
_CARD_LIST_PANEL_MIN_WIDTH = 480
#: Narrower than the sealed-product one (below): a card's own artwork is
#: already a narrow 2.5:3.5 portrait, unlike a sealed product's wider
#: screenshot capture, so its detail panel needs less width to still show
#: everything (fields, buttons) without clipping (user request -- freed-up
#: width goes to the card list instead, see the splitter's own setSizes()).
_CARD_DETAIL_PANEL_MIN_WIDTH = 260
_SEALED_PRODUCT_LIST_PANEL_MIN_WIDTH = 480
_SEALED_PRODUCT_DETAIL_PANEL_MIN_WIDTH = 320

#: Must match PriceHistoryDock's own setMinimumWidth() -- how much wider the
#: window grows/shrinks when the history dock is toggled on/off, so it adds
#: room on the side instead of squeezing the existing three-column layout.
_HISTORY_DOCK_WIDTH = 380


class MainWindow(QMainWindow):
    """Top-level window hosting the whole interface."""

    search_submitted = Signal(str)
    manual_entry_requested = Signal()
    sealed_add_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()
    settings_requested = Signal()

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
        # Wide enough that every toolbar button (Suchen, Karte manuell
        # eintragen, Karten/Statistik, Export, Infos und Einstellungen)
        # fits without Qt's overflow "»" chevron hiding any of them --
        # the toolbar's own sizeHint() comes out to ~1550px wide.
        self.resize(1650, 900)
        self.setMinimumSize(1300, 750)

        self._build_toolbar()
        # Created before the controllers that use it (PriceController and
        # friends just store a reference to `self` and look this attribute
        # up when a lookup actually starts, but existing unambiguously this
        # early avoids any doubt about ordering).
        self.busy_overlay = BusyOverlay(self)
        self._build_central()
        self._build_statusbar()
        self._connect_signals()
        self.collection_controller.select_first_collection()
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet())
        # Frozen here, not in _build_toolbar(): sizeHint() before the
        # stylesheet above is applied still reflects unstyled (smaller)
        # fonts/padding and would freeze a width too small for the real,
        # styled search field/button/manual-entry group.
        #
        # Computed explicitly from each child's own sizeHint()/
        # maximumWidth(), not from the container's own aggregate
        # sizeHint() -- that one is unreliable here: a QLineEdit's
        # sizeHint() doesn't reflect the wider size it can actually grow
        # to (its maximumWidth), so the container ended up frozen
        # narrower than the search field wants to be, visibly squeezing
        # it (live-confirmed via screenshot).
        #
        # Taken as the *wider* of the two tab-specific combinations (never
        # their sum): Karten shows search+"Suchen"+"Karte manuell
        # eintragen" together, Sealed shows only its own add-button -- the
        # two combinations are never visible at once. Summing all four
        # widths regardless of which are actually shown together froze a
        # container far wider than any single tab's real content needs,
        # which is exactly what visibly spread the Karten-tab's search
        # field/buttons apart from each other (live-confirmed via
        # screenshot: the surplus space meant for the *other* tab's hidden
        # button leaked into gaps between the visible ones instead).
        spacing = self._cards_only_group.layout().spacing()
        cards_tab_width = (
            self._search.maximumWidth()
            + spacing + self._search_button.sizeHint().width()
            + spacing + self._manual_entry_button.sizeHint().width()
        )
        sealed_tab_width = self._sealed_add_button.sizeHint().width()
        self._cards_only_group.setFixedWidth(max(cards_tab_width, sealed_tab_width))

    # -- Construction ----------------------------------------------------- #

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Haupt-Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Karten durchsuchen  (z. B. „Light Jolteon“)"))
        self._search.setClearButtonEnabled(True)
        # A fixed width (not just a maximum): QLineEdit's default SizePolicy
        # is Expanding, which stretched it to fill whatever space a trailing
        # layout stretch (see group_layout.addStretch() below) left
        # available -- competing with that stretch for the same leftover
        # space shrank it down to a sliver instead of its intended width
        # (live-confirmed via screenshot). A fixed width sidesteps the
        # competition entirely, matching the buttons beside it. Widened from
        # 420 -- live-reported as still feeling cramped for a realistic
        # query plus the placeholder's own example text.
        self._search.setFixedWidth(520)
        self._search.returnPressed.connect(self._submit_search)

        self._search_button = QPushButton(tr("Suchen"))
        self._search_button.clicked.connect(self._submit_search)
        # QPushButton's default horizontal size policy is Minimum (i.e. it
        # WILL grow past its sizeHint into any leftover toolbar space) --
        # without pinning it to Fixed, it silently ballooned to fill the
        # entire space the hidden Sealed/Statistik-only content would
        # otherwise take, since it was the only child here able to grow.
        self._search_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        # Directly next to "Suchen" (user request) -- both are ways to add
        # a card, just via a different source (catalogue match vs. a pasted
        # Cardmarket link), so they belong together at a glance. Kept as a
        # real QAction (not just a plain QToolButton) so the rest of the app
        # can keep triggering/inspecting it the normal QAction way; the
        # QToolButton below is bound to it via setDefaultAction(), which
        # keeps the button's visible/enabled state in sync with the action.
        self._act_manual_entry = QAction(tr("Karte manuell eintragen"), self)
        self._act_manual_entry.triggered.connect(self.manual_entry_requested)
        # NOTE: QToolButton.setDefaultAction() syncs text/icon/enabled/
        # checked from the action, but NOT visibility -- hiding
        # self._act_manual_entry alone leaves this button on screen, so
        # _on_central_tab_changed toggles this widget's own visibility too.
        self._manual_entry_button = QToolButton()
        self._manual_entry_button.setDefaultAction(self._act_manual_entry)
        self._manual_entry_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Styled as a solid button (like "Suchen"), not a plain toolbar
        # action -- see QToolButton#ToolbarPrimaryAction in theme.py.
        self._manual_entry_button.setObjectName("ToolbarPrimaryAction")

        # Sealed tab's own add action -- moved here from being embedded at
        # the top of SealedProductListPanel (user request: it should sit in
        # the exact same toolbar slot the Karten-only controls occupy, not
        # leave that slot looking empty while also duplicating a button
        # inside the panel body).
        self._sealed_add_button = QPushButton(tr("+ Sealed-Produkt hinzufügen"))
        self._sealed_add_button.clicked.connect(self.sealed_add_requested)
        self._sealed_add_button.setObjectName("ToolbarPrimaryAction")
        # Same QPushButton-defaults-to-Minimum-policy issue as "Suchen"
        # above -- without pinning it to Fixed, it stretched to fill the
        # frozen container's full width instead of just fitting its text.
        self._sealed_add_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        # Karten is the initially active tab -- _on_central_tab_changed only
        # runs on a later tab *switch*, so the sealed-only button's initial
        # state has to be set explicitly here, same as the Karten-only ones
        # default to visible by simply never being hidden yet.
        self._sealed_add_button.setVisible(False)

        # Search field + button + manual entry + sealed-add live in one
        # fixed-width container instead of directly on the toolbar. Two
        # reasons: (1) a QLineEdit/QPushButton added via toolbar.addWidget()
        # sits inside an internal QWidgetAction wrapper whose own visibility
        # can silently override a plain widget.setVisible(False) after a
        # style/layout pass -- hiding them here as real container children
        # avoids that. (2) the container's width is pinned to fit its
        # widest combination of children at once, so switching tabs never
        # shifts the nav buttons/Export/Info after it (user request: their
        # positions should stay fixed regardless of the active tab).
        self._cards_only_group = QWidget()
        self._cards_only_group.setObjectName("ToolbarSearchGroup")
        # A plain QWidget's default SizePolicy (Preferred) still has Qt's
        # "grow" flag set -- since this is the only *widget* item on the
        # toolbar (every nav/export/settings item is a fixed-size QAction
        # button), the toolbar layout let it silently absorb any extra
        # width the window had beyond its minimum, pushing the separator/
        # nav cluster after it further right the wider the window was
        # (live-confirmed via screenshot: a large gap opened up here that
        # wasn't present at the app's originally-designed width). Fixed
        # stops it from ever growing past its frozen minimum.
        self._cards_only_group.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        group_layout = QHBoxLayout(self._cards_only_group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(8)
        group_layout.addWidget(self._search)
        group_layout.addWidget(self._search_button)
        group_layout.addWidget(self._manual_entry_button)
        group_layout.addWidget(self._sealed_add_button)
        # Without this, whichever slack the container's frozen width has
        # beyond its *currently visible* children (e.g. on Sealed, only
        # _sealed_add_button is shown, well short of the container's own
        # width -- frozen wide enough for Karten's three widgets instead)
        # left that visible content looking centred rather than flush
        # left (live-confirmed via screenshot). Trailing stretch pins any
        # leftover space to the right, after the visible content, instead.
        group_layout.addStretch(1)
        toolbar.addWidget(self._cards_only_group)
        # The min-width freeze itself happens in __init__, *after* the app
        # stylesheet is applied -- sizeHint() here, before that, still
        # reflects unstyled (smaller) fonts/padding and would freeze a
        # width too small for the real, styled buttons.

        # Absorbs whatever width the fixed-size group above doesn't use,
        # so the nav/export/settings cluster after it is genuinely pinned
        # to the toolbar's right edge (not just "wherever the left content
        # happens to end") regardless of window width. Same transparent
        # styling as ToolbarSearchGroup -- an unstyled QWidget here would
        # otherwise show the same dark "ghost box" bug fixed above, just
        # for this spacer instead of the search group.
        toolbar_spacer = QWidget()
        toolbar_spacer.setObjectName("ToolbarSearchGroup")
        toolbar_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        toolbar.addWidget(toolbar_spacer)

        # Everything else (navigation + export + settings) as a single
        # group after one separator -- text labels, not icons, throughout
        # this toolbar -- a standard-icon pair here wasn't obviously "Karten"
        # vs. "Statistik" at a glance, and the same plain-text style is used
        # for every other toolbar action. The active nav action is
        # highlighted via QToolButton:checked in the style sheet. The
        # QTabWidget's own tab bar is hidden (see _build_central) so these
        # two actions are the only way to switch between "Karten"/"Statistik".
        self._act_tab_cards = QAction(tr("Karten"), self)
        self._act_tab_sealed = QAction(tr("Sealed"), self)
        self._act_tab_wantlist = QAction("Wantlist", self)
        self._act_tab_stats = QAction(tr("Statistik"), self)
        self._act_tab_cards.setCheckable(True)
        self._act_tab_sealed.setCheckable(True)
        self._act_tab_wantlist.setCheckable(True)
        self._act_tab_stats.setCheckable(True)
        self._act_tab_cards.setChecked(True)
        tab_nav_group = QActionGroup(self)
        tab_nav_group.setExclusive(True)
        tab_nav_group.addAction(self._act_tab_cards)
        tab_nav_group.addAction(self._act_tab_sealed)
        tab_nav_group.addAction(self._act_tab_wantlist)
        tab_nav_group.addAction(self._act_tab_stats)
        # Tab order: Karten, Sealed, Wantlist, Statistik.
        self._act_tab_cards.triggered.connect(lambda: self._switch_central_tab(0))
        self._act_tab_sealed.triggered.connect(lambda: self._switch_central_tab(1))
        self._act_tab_wantlist.triggered.connect(lambda: self._switch_central_tab(2))
        self._act_tab_stats.triggered.connect(lambda: self._switch_central_tab(3))
        toolbar.addAction(self._act_tab_cards)
        toolbar.addAction(self._act_tab_sealed)
        toolbar.addAction(self._act_tab_wantlist)
        toolbar.addAction(self._act_tab_stats)

        self._act_export = QAction(tr("Export"), self)
        self._act_import = QAction("Import", self)
        self._act_settings = QAction(tr("Infos und Einstellungen"), self)
        self._act_export.triggered.connect(self.export_requested)
        self._act_import.triggered.connect(self.import_requested)
        self._act_settings.triggered.connect(self.settings_requested)
        toolbar.addAction(self._act_export)
        toolbar.addAction(self._act_import)
        toolbar.addAction(self._act_settings)

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

        card_service = CardService(
            CardRepository(self._database), price_repository=PriceRepository(self._database)
        )
        self.card_controller = CardController(
            self.card_list_panel,
            self.card_detail_panel,
            card_service,
            collection_service,
            PriceRepository(self._database),
            history_dock=self.price_history_dock,
            parent=self,
        )

        pokemontcg_client = PokemonTcgClient()
        catalog_search_service = CatalogSearchService(pokemontcg_client)
        self.catalog_search_controller = CatalogSearchController(
            self, catalog_search_service, parent=self
        )

        self.cardmarket_search_controller = CardmarketSearchController(
            self,
            self.card_detail_panel,
            card_service,
            self.card_controller,
            list_panel=self.card_list_panel,
            parent=self,
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

        self.sealed_product_panel = SealedProductListPanel()
        self.sealed_product_detail_panel = SealedProductDetailPanel()
        self.sealed_product_panel.setMinimumWidth(_SEALED_PRODUCT_LIST_PANEL_MIN_WIDTH)
        self.sealed_product_detail_panel.setMinimumWidth(_SEALED_PRODUCT_DETAIL_PANEL_MIN_WIDTH)
        sealed_product_service = SealedProductService(SealedProductRepository(self._database))

        self.sealed_price_history_dock = SealedPriceHistoryDock(self)
        self.sealed_price_history_dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sealed_price_history_dock)
        self.sealed_product_detail_panel.history_panel_requested.connect(
            self._toggle_sealed_history_dock
        )
        self.sealed_price_history_dock.visibilityChanged.connect(
            self.sealed_product_detail_panel.set_history_panel_visible
        )

        self.statistics_panel = StatisticsPanel()
        statistics_service = StatisticsService(
            card_service,
            collection_service,
            PriceRepository(self._database),
            sealed_product_service,
            SealedPriceRepository(self._database),
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
            list_panel=self.card_list_panel,
            parent=self,
        )
        self.statistics_panel.price_lookup_requested.connect(self.price_controller.start_lookup)
        self.statistics_panel.sealed_price_lookup_requested.connect(
            lambda product_id: self.sealed_price_controller.start_lookup(product_id)
        )
        self.statistics_panel.bulk_price_lookup_requested.connect(
            self.price_controller.start_bulk_update
        )
        self.statistics_panel.sealed_bulk_price_lookup_requested.connect(
            lambda product_ids: self.sealed_price_controller.start_bulk_update(product_ids)
        )

        export_service = ExportService(card_service, collection_service, sealed_product_service)
        self.export_controller = ExportController(
            self, export_service, collection_service, parent=self
        )

        def _refresh_after_import() -> None:
            # Referenced controllers are all constructed by the time an
            # import actually runs (a real user click, long after
            # _build_central() itself returns) -- fine even though
            # sealed_product_controller/wantlist_controller don't exist yet
            # at this exact point in _build_central().
            self.collection_controller.refresh()
            self.card_controller.refresh()
            self.sealed_product_controller.refresh()
            self.wantlist_controller.refresh()

        import_service = ImportService(card_service, collection_service, sealed_product_service)
        self.import_controller = ImportController(
            self, import_service, on_imported=_refresh_after_import, parent=self
        )

        self.manual_entry_controller = ManualEntryController(
            self, self.card_controller, pokemontcg_client, parent=self
        )

        self.backup_controller = BackupController(self, self._database, parent=self)
        self.settings_controller = SettingsController(self, self.backup_controller, parent=self)

        self.sealed_product_controller = SealedProductController(
            self.sealed_product_panel,
            sealed_product_service,
            detail_panel=self.sealed_product_detail_panel,
            price_repository=SealedPriceRepository(self._database),
            history_dock=self.sealed_price_history_dock,
            parent=self,
        )
        self.sealed_entry_controller = SealedEntryController(
            self, self.sealed_product_controller, parent=self
        )
        # Not collection-scoped (unlike cards), so there's no "collection
        # changed" trigger to react to -- load the full list once up front.
        self.sealed_product_controller.refresh()

        def open_sealed_price_service() -> tuple[SealedPriceService, Database]:
            # Mirrors open_price_service() above: a fresh connection per
            # lookup, since this runs on SealedPriceLookupWorker's own thread
            # and SQLite connections can't be shared across threads.
            thread_database = Database(self._database.path)
            thread_database.initialize()
            service = SealedPriceService(
                SealedProductRepository(thread_database), SealedPriceRepository(thread_database)
            )
            return service, thread_database

        self.sealed_price_controller = SealedPriceController(
            self,
            open_sealed_price_service,
            self.sealed_product_controller,
            detail_panel=self.sealed_product_detail_panel,
            statistics_controller=self.statistics_controller,
            parent=self,
        )
        self.sealed_add_requested.connect(self.sealed_entry_controller.start)
        self.sealed_product_panel.price_lookup_requested.connect(
            self.sealed_price_controller.start_lookup
        )

        self.wantlist_panel = WantlistPanel()
        wantlist_service = WantlistService(WantlistRepository(self._database))
        self.wantlist_controller = WantlistController(
            self.wantlist_panel,
            wantlist_service,
            card_service,
            collection_service,
            on_converted=self.card_controller.refresh,
            parent=self,
        )
        self.wantlist_entry_controller = WantlistEntryController(
            self, self.wantlist_controller, parent=self
        )
        # Not collection-scoped (like sealed products), so there's no
        # "collection changed" trigger to react to -- load the full list
        # once up front.
        self.wantlist_controller.refresh()

        def open_wantlist_price_service() -> tuple[WantlistPriceService, Database]:
            # Mirrors open_sealed_price_service() above: a fresh connection
            # per lookup, since this runs on WantlistPriceLookupWorker's own
            # thread and SQLite connections can't be shared across threads.
            thread_database = Database(self._database.path)
            thread_database.initialize()
            thread_pricing = PriceService(
                CardRepository(thread_database), PriceRepository(thread_database), pokemontcg_client
            )
            service = WantlistPriceService(WantlistRepository(thread_database), thread_pricing)
            return service, thread_database

        self.wantlist_price_controller = WantlistPriceController(
            self,
            self.wantlist_panel,
            open_wantlist_price_service,
            self.wantlist_controller,
            parent=self,
        )
        self.wantlist_panel.add_requested.connect(self.wantlist_entry_controller.start)
        self.wantlist_panel.price_lookup_requested.connect(
            self.wantlist_price_controller.start_lookup
        )
        self.wantlist_panel.bulk_price_lookup_requested.connect(
            self.wantlist_price_controller.start_bulk_update
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.collection_panel)
        splitter.addWidget(self.card_list_panel)
        splitter.addWidget(self.card_detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 6)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([170, 800, 290])
        splitter.setContentsMargins(10, 10, 10, 10)
        splitter.setHandleWidth(10)

        # No collection column here (unlike Karten): sealed products aren't
        # collection-scoped, so there's nothing for a third, left-most panel
        # to filter by.
        sealed_splitter = QSplitter(Qt.Orientation.Horizontal)
        sealed_splitter.addWidget(self.sealed_product_panel)
        sealed_splitter.addWidget(self.sealed_product_detail_panel)
        sealed_splitter.setStretchFactor(0, 5)
        sealed_splitter.setStretchFactor(1, 3)
        sealed_splitter.setSizes([730, 360])
        sealed_splitter.setContentsMargins(10, 10, 10, 10)
        sealed_splitter.setHandleWidth(10)

        # Gives the Wantlist panel the same breathing room as the Karten/
        # Sealed splitters above -- added directly (no splitter of its own,
        # since there's nothing to resize against), it would otherwise sit
        # flush against the tab's edges, clipping its rounded corners/shadow.
        wantlist_page = QWidget()
        wantlist_page_layout = QVBoxLayout(wantlist_page)
        wantlist_page_layout.setContentsMargins(10, 10, 10, 10)
        wantlist_page_layout.addWidget(self.wantlist_panel)

        tabs = QTabWidget()
        tabs.addTab(splitter, tr("Karten"))
        tabs.addTab(sealed_splitter, tr("Sealed"))
        tabs.addTab(wantlist_page, "Wantlist")
        tabs.addTab(self.statistics_panel, tr("Statistiken"))
        # Navigated exclusively via the toolbar buttons above (_act_tab_cards/
        # _act_tab_stats) -- the tab bar itself would just be a redundant
        # second way to do the same thing.
        tabs.tabBar().hide()
        tabs.currentChanged.connect(self._on_central_tab_changed)
        self.setCentralWidget(tabs)

    def _build_statusbar(self) -> None:
        status = QStatusBar()
        status.showMessage(f"{config.APP_NAME} v{config.APP_VERSION}  ·  {tr('bereit')}")
        # A permanent widget (not another showMessage() call) -- unlike the
        # message above, this must survive every later showMessage(...,
        # 5000) elsewhere (price lookups, exports, ...) auto-clearing after
        # a few seconds.
        self._update_hint_label = QLabel("")
        self._update_hint_label.setTextFormat(Qt.TextFormat.RichText)
        self._update_hint_label.setOpenExternalLinks(True)
        status.addPermanentWidget(self._update_hint_label)
        self.setStatusBar(status)

    def start_update_check(self) -> None:
        """Best-effort, non-blocking check for a newer GitHub release.

        Not called from ``__init__`` -- tests construct :class:`MainWindow`
        directly and shouldn't trigger a real network call on every
        instantiation. The real entry point (:func:`app.ui.app.run_gui`)
        calls this once after showing the window.
        """
        self._update_check_worker = UpdateCheckWorker(config.APP_VERSION, parent=self)
        self._update_check_worker.succeeded.connect(self._on_update_check_succeeded)
        self._update_check_worker.start()

    def _on_update_check_succeeded(self, info) -> None:
        if info is None:
            return
        self._update_hint_label.setText(
            f'<a href="{info.url}">Update available: v{info.version}</a>'
        )

    def _connect_signals(self) -> None:
        """Wire toolbar intents to their real handlers."""
        self.search_submitted.connect(self.catalog_search_controller.handle_search)
        self.manual_entry_requested.connect(self.manual_entry_controller.start)
        self.export_requested.connect(self.export_controller.handle_export_requested)
        self.import_requested.connect(self.import_controller.handle_import_requested)
        self.settings_requested.connect(self.settings_controller.start)
        self.collection_controller.selection_changed.connect(self.card_controller.set_collection)
        self.catalog_search_controller.card_add_requested.connect(
            self.card_controller.add_from_catalog
        )

    # -- Behaviour -------------------------------------------------------- #

    def _submit_search(self) -> None:
        self.search_submitted.emit(self._search.text().strip())

    def _switch_central_tab(self, index: int) -> None:
        self.centralWidget().setCurrentIndex(index)

    def _on_central_tab_changed(self, index: int) -> None:
        # Recomputed only when the tab actually becomes active -- statistics
        # aren't a real-time feature, so there's no need to keep them in
        # sync while the user is on the "Karten" tab. Compared by index, not
        # by tabText(): that text is translated (see app/i18n.py) and would
        # no longer match this literal once the UI language is English.
        if index == 3:
            self.statistics_controller.refresh()
        self._act_tab_cards.setChecked(index == 0)
        self._act_tab_sealed.setChecked(index == 1)
        self._act_tab_wantlist.setChecked(index == 2)
        self._act_tab_stats.setChecked(index == 3)
        # The catalogue search and manual card entry only make sense on
        # "Karten"; the sealed-add button only on "Sealed" -- each tab's
        # own controls occupy the same toolbar slot, swapped out rather
        # than left blank (user request).
        is_cards_tab = index == 0
        is_sealed_tab = index == 1
        self._search.setVisible(is_cards_tab)
        self._search_button.setVisible(is_cards_tab)
        self._act_manual_entry.setVisible(is_cards_tab)
        # setDefaultAction() does NOT sync visibility -- the actual button
        # widget needs its own setVisible() call, or it stays on screen
        # regardless of the action's own (in)visibility.
        self._manual_entry_button.setVisible(is_cards_tab)
        self._sealed_add_button.setVisible(is_sealed_tab)

        # Each tab has its own price-history dock -- only one is ever
        # relevant at a time, so leaving a tab auto-hides its own dock
        # rather than letting a stale one linger on screen for a tab that's
        # no longer active.
        if not is_cards_tab and self.price_history_dock.isVisible():
            self._toggle_history_dock(-1)
        if not is_sealed_tab and self.sealed_price_history_dock.isVisible():
            self._toggle_sealed_history_dock(-1)

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

    def _toggle_sealed_history_dock(self, product_id: int) -> None:  # noqa: ARG002 -- dock content already synced by SealedProductController
        """Mirrors :meth:`_toggle_history_dock`, for the Sealed tab's own dock."""
        if self.sealed_price_history_dock.isVisible():
            self.sealed_price_history_dock.hide()
            self.resize(self.width() - _HISTORY_DOCK_WIDTH, self.height())
        else:
            self.sealed_price_history_dock.show()
            self.sealed_price_history_dock.raise_()
            self.resize(self.width() + _HISTORY_DOCK_WIDTH, self.height())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt override
        """Close the database if this window created it itself."""
        if self._owns_database:
            self._database.close()
        super().closeEvent(event)
