"""The application main window.

Assembles the three-column layout (collections · card list · card details),
the top toolbar (search · scanner · price update · export) and the light/dark
theme toggle. The window itself holds no business logic: it builds the panels
and hands them to controllers (e.g. :class:`CollectionController`) that talk
to the services layer. Toolbar intents without a wired controller yet still
just produce a status-bar message.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QStyle,
    QToolBar,
    QWidget,
)

from app import config
from app.database.connection import Database
from app.database.repositories.collection_repository import CollectionRepository
from app.logging_config import get_logger
from app.services.collection_service import CollectionService
from app.ui.controllers.collection_controller import CollectionController
from app.ui.theme import Theme, build_stylesheet
from app.ui.widgets import CardDetailPanel, CardListPanel, CollectionPanel

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Top-level window hosting the whole interface."""

    search_submitted = Signal(str)
    scan_requested = Signal()
    update_prices_requested = Signal()
    export_requested = Signal()

    def __init__(self, database: Database | None = None, theme: Theme = Theme.LIGHT) -> None:
        super().__init__()
        self._owns_database = database is None
        if database is None:
            # Headless/demo convenience (e.g. tests): an initialised in-memory
            # database so the window is fully functional without a caller
            # having to bootstrap one. Production always passes a real one.
            database = Database(":memory:")
            database.initialize()
        self._database = database
        self._theme = theme

        self.setWindowTitle(f"{config.APP_NAME}")
        self.resize(1240, 780)
        self.setMinimumSize(960, 600)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._connect_placeholder_feedback()
        self.apply_theme(theme)

    # -- Construction ----------------------------------------------------- #

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Haupt-Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Karten durchsuchen  (z. B. „xatu skyridge holo“)")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(420)
        self._search.returnPressed.connect(
            lambda: self.search_submitted.emit(self._search.text().strip())
        )
        toolbar.addWidget(self._search)
        toolbar.addSeparator()

        style = self.style()
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

        # Push the theme toggle to the far right.
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,
                             spacer.sizePolicy().verticalPolicy().Preferred)
        toolbar.addWidget(spacer)

        self._act_theme = QAction("🌙  Dunkelmodus", self)
        self._act_theme.triggered.connect(self.toggle_theme)
        toolbar.addAction(self._act_theme)

    def _build_central(self) -> None:
        self.collection_panel = CollectionPanel()
        self.card_list_panel = CardListPanel()
        self.card_detail_panel = CardDetailPanel()

        collection_service = CollectionService(CollectionRepository(self._database))
        self.collection_controller = CollectionController(
            self.collection_panel, collection_service, parent=self
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.collection_panel)
        splitter.addWidget(self.card_list_panel)
        splitter.addWidget(self.card_detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([230, 620, 360])
        splitter.setContentsMargins(10, 10, 10, 10)
        splitter.setHandleWidth(10)
        self.setCentralWidget(splitter)

    def _build_statusbar(self) -> None:
        status = QStatusBar()
        status.showMessage(f"{config.APP_NAME} v{config.APP_VERSION}  ·  bereit")
        self.setStatusBar(status)

    def _connect_placeholder_feedback(self) -> None:
        """Give the toolbar intents visible (non-business-logic) feedback.

        Real handlers replace these in later steps.
        """
        self.search_submitted.connect(
            lambda text: self._flash(f"Suche: „{text}“  (Suchlogik folgt in Schritt 4)")
        )
        self.scan_requested.connect(
            lambda: self._flash("Scanner folgt in einem späteren Schritt.")
        )
        self.update_prices_requested.connect(
            lambda: self._flash("Preisaktualisierung folgt in Schritt 6.")
        )
        self.export_requested.connect(
            lambda: self._flash("Export folgt in einem späteren Schritt.")
        )
        self.collection_controller.selection_changed.connect(self._on_collection_selected)
        self.card_detail_panel.open_on_cardmarket_requested.connect(
            lambda: self._flash("Cardmarket-Link folgt in Schritt 6.")
        )

    # -- Behaviour -------------------------------------------------------- #

    def _flash(self, message: str) -> None:
        """Show a transient status-bar message."""
        self.statusBar().showMessage(message, 5000)

    def _on_collection_selected(self, collection_id: int) -> None:
        """React to a collection selection (card list wiring follows in Step 5)."""
        if collection_id == -1:
            self._flash("Keine Sammlung ausgewählt.")
            return
        self._flash(f"Sammlung gewählt (ID {collection_id}) — Kartenliste folgt in Schritt 5.")

    def toggle_theme(self) -> None:
        """Switch between light and dark mode."""
        self.apply_theme(self._theme.toggled())

    def apply_theme(self, theme: Theme) -> None:
        """Apply a theme to the whole application."""
        self._theme = theme
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(theme))
        self._act_theme.setText(
            "☀  Hellmodus" if theme is Theme.DARK else "🌙  Dunkelmodus"
        )
        logger.debug("Theme applied: %s", theme.value)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt override
        """Close the database if this window created it itself."""
        if self._owns_database:
            self._database.close()
        super().closeEvent(event)
