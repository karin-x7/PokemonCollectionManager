"""Connects the toolbar search field to :class:`CatalogSearchService`.

The toolbar's search field is the only input; results are shown in a modal
dialog. When the user picks a match there and confirms "Hinzufügen", this
controller re-emits it as ``card_add_requested`` — it does not persist
anything itself, that's :class:`~app.ui.controllers.card_controller.
CardController`'s job (wired together in :class:`~app.ui.main_window.
MainWindow`).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMainWindow, QMessageBox

from app.catalog.models import CatalogCard
from app.logging_config import get_logger
from app.services.catalog_search_service import CatalogSearchService
from app.services.exceptions import CatalogSearchError
from app.ui.dialogs.catalog_search_results_dialog import CatalogSearchResultsDialog

logger = get_logger(__name__)


class CatalogSearchController(QObject):
    """Wires the main window's search field to :class:`CatalogSearchService`."""

    #: Re-emitted from the results dialog's "Hinzufügen" action.
    card_add_requested = Signal(object)

    def __init__(
        self,
        main_window: QMainWindow,
        service: CatalogSearchService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._service = service

    def handle_search(self, query: str) -> None:
        """Run a catalogue search for ``query`` and show the results."""
        cleaned = (query or "").strip()
        if not cleaned:
            self._main_window.statusBar().showMessage("Bitte Suchbegriff eingeben.", 5000)
            return

        try:
            matches = self._service.search(cleaned)
        except CatalogSearchError as exc:
            logger.error("Catalogue search failed for %r: %s", cleaned, exc)
            self._show_error(str(exc))
            return

        message = (
            f"{len(matches)} Treffer für „{cleaned}“."
            if matches
            else f"Keine Treffer für „{cleaned}“."
        )
        self._main_window.statusBar().showMessage(message, 5000)
        self._show_results(matches)

    # -- Overridable for headless testing (mirrors CollectionPanel.show_error) #

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self._main_window, "Kartensuche", message)

    def _show_results(self, matches: list[CatalogCard]) -> None:
        dialog = CatalogSearchResultsDialog(self._main_window)
        dialog.set_results(matches)
        dialog.add_requested.connect(self.card_add_requested)
        dialog.exec()
