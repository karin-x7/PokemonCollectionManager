"""Connects the toolbar search field to :class:`CatalogSearchService`.

The toolbar's search field is the only input; results are shown in a modal
dialog, which opens immediately in a "Suche läuft…" loading state rather
than only after the (network-bound, sometimes multi-second) search
completes -- searching used to run synchronously with just a wait cursor,
which for however long pokemontcg.io took made the whole app look frozen/
crashed instead of "still working on it" (live-reported point of
confusion). The search itself now runs on a background
:class:`~app.ui.workers.catalog_search_worker.CatalogSearchWorker`, mirroring
the Cardmarket-search flow's own dialog-opens-immediately pattern. When the
user picks a match there and confirms "Hinzufügen", this controller
re-emits it as ``card_add_requested`` — it does not persist anything
itself, that's :class:`~app.ui.controllers.card_controller.CardController`'s
job (wired together in :class:`~app.ui.main_window.MainWindow`).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMainWindow, QMessageBox

from app.catalog.models import CatalogCard
from app.i18n import tr
from app.logging_config import get_logger
from app.services.catalog_search_service import CatalogSearchService
from app.ui.dialogs.catalog_search_results_dialog import CatalogSearchResultsDialog
from app.ui.workers.catalog_search_worker import CatalogSearchWorker

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
        self._worker: CatalogSearchWorker | None = None
        self._results_dialog: CatalogSearchResultsDialog | None = None
        self._query: str = ""
        #: Workers cancelled via :meth:`_on_dialog_finished` before they were
        #: actually done -- kept alive here (not just dropped) so Qt doesn't
        #: tear down a still-running ``QThread`` out from under itself. Each
        #: one removes itself once its own ``finished`` fires for real.
        self._cancelled_workers: list[CatalogSearchWorker] = []

    def handle_search(self, query: str) -> None:
        """Run a catalogue search for ``query`` and show the results."""
        cleaned = (query or "").strip()
        if not cleaned:
            self._main_window.statusBar().showMessage(tr("Bitte Suchbegriff eingeben."), 5000)
            return
        if self._worker is not None:
            logger.info("Catalogue search already running -- ignoring request.")
            return

        self._query = cleaned
        self._main_window.statusBar().showMessage(
            tr("Suche läuft für „{query}“ …").format(query=cleaned)
        )
        self._results_dialog = CatalogSearchResultsDialog(self._main_window)
        self._results_dialog.add_requested.connect(self.card_add_requested)
        self._results_dialog.finished.connect(self._on_dialog_finished)
        self._worker = CatalogSearchWorker(self._service, cleaned, parent=self)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()
        # ``_results_dialog`` must stay alive until this call returns -- a
        # test's synchronous worker stand-in can run the whole succeeded/
        # failed/finished chain before this line is even reached, so it must
        # not be cleared by _cleanup_worker() (tied to the worker finishing,
        # which can happen well before the dialog itself closes).
        self._results_dialog.exec()
        self._results_dialog = None

    def _on_dialog_finished(self, _result: int) -> None:
        """The results dialog closed (Close button, Esc, or window X).

        If the search behind it is still running at that point, cancel it
        and free up the busy-guard for a new search right away, instead of
        silently blocking every next search attempt until the now-abandoned
        request eventually finishes on its own -- live-reported as
        "Catalogue search already running -- ignoring request" firing
        repeatedly just from closing the dialog and searching again.
        """
        if self._worker is None:
            return
        worker = self._worker
        worker.requestInterruption()
        # Detach so a late result/error from the now-abandoned search never
        # touches a dialog that no longer exists.
        worker.succeeded.disconnect(self._on_succeeded)
        worker.failed.disconnect(self._on_failed)
        worker.finished.disconnect(self._cleanup_worker)
        self._cancelled_workers.append(worker)
        worker.finished.connect(lambda: self._cancelled_workers.remove(worker))
        self._worker = None

    def _on_succeeded(self, matches: list[CatalogCard]) -> None:
        message = (
            tr("{count} Treffer für „{query}“.").format(count=len(matches), query=self._query)
            if matches
            else tr("Keine Treffer für „{query}“.").format(query=self._query)
        )
        self._main_window.statusBar().showMessage(message, 5000)
        if self._results_dialog is not None:
            self._results_dialog.set_results(matches)

    def _on_failed(self, message: str) -> None:
        logger.error("Catalogue search failed for %r: %s", self._query, message)
        if self._results_dialog is not None:
            self._results_dialog.reject()
        self._show_error(message)

    def _cleanup_worker(self) -> None:
        self._worker = None

    # -- Overridable for headless testing (mirrors CollectionPanel.show_error) #

    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self._main_window, tr("Kartensuche"), message)
