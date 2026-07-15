"""Wires the "Cardmarket-Link suchen" button to Cardmarket's own site search.

Two-step flow, mirroring the fact that Cardmarket's UI Automation tree never
exposes a search result's real URL (see
:mod:`app.pricing.browser_price_reader`'s own docs) -- only its visible
text:

1. :class:`~app.ui.workers.cardmarket_search_worker.CardmarketSearchWorker`
   searches Cardmarket for the card's own name, in the background.
2. The user picks a candidate from
   :class:`~app.ui.dialogs.cardmarket_search_results_dialog.CardmarketSearchResultsDialog`.
3. :class:`~app.ui.workers.cardmarket_search_resolve_worker.CardmarketSearchResolveWorker`
   clicks through to that candidate's real product page (a fresh search,
   since step 1's tab is already closed) and reads its actual URL, which is
   then persisted as the card's own Cardmarket link override -- the same
   field ("Eigener Cardmarket-Link") a user would otherwise have to fill in
   by hand.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMainWindow, QMessageBox

from app.i18n import tr
from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, open_cardmarket_search
from app.pricing.models import CardmarketSearchResult
from app.services.card_service import CardService
from app.services.exceptions import ServiceError
from app.ui.controllers.card_controller import CardController
from app.ui.dialogs.cardmarket_search_results_dialog import CardmarketSearchResultsDialog
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel
from app.ui.workers.cardmarket_search_resolve_worker import CardmarketSearchResolveWorker
from app.ui.workers.cardmarket_search_worker import CardmarketSearchWorker

logger = get_logger(__name__)


class CardmarketSearchController(QObject):
    """Starts the "Cardmarket-Link suchen" flow from the card detail panel."""

    #: Emitted with the card's id right after its Cardmarket link is
    #: successfully saved -- :class:`~app.ui.main_window.MainWindow` connects
    #: this to :meth:`~app.ui.controllers.price_controller.PriceController.
    #: start_lookup`, mirroring :attr:`~app.ui.controllers.card_controller.
    #: CardController.card_added`: fixing the link and fetching its price
    #: should be one step, not two.
    link_saved = Signal(int)

    def __init__(
        self,
        main_window: QMainWindow,
        detail_panel: CardDetailPanel,
        card_service: CardService,
        card_controller: CardController,
        list_panel: CardListPanel | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._detail_panel = detail_panel
        self._service = card_service
        self._card_controller = card_controller
        self._search_worker: CardmarketSearchWorker | None = None
        self._resolve_worker: CardmarketSearchResolveWorker | None = None
        self._card_id: int | None = None
        self._card_name: str | None = None

        detail_panel.cardmarket_search_requested.connect(self.start)
        # "Fix Cardmarket-Link" context-menu action (live-reported request:
        # this was previously only reachable via the detail panel button).
        if list_panel is not None:
            list_panel.cardmarket_search_requested.connect(self.start)

    def start(self, card_id: int) -> None:
        """Look up ``card_id``'s own name and search Cardmarket for it."""
        if self._search_worker is not None or self._resolve_worker is not None:
            logger.info("Cardmarket search already running -- ignoring click.")
            return
        try:
            card = self._service.get_card(card_id)
        except ServiceError as exc:
            self._main_window.statusBar().showMessage(str(exc), 5000)
            return

        self._card_id = card_id
        self._card_name = card.name
        self._detail_panel.set_cardmarket_search_running(True)
        self._main_window.statusBar().showMessage(tr("Cardmarket wird durchsucht…"))
        self._search_worker = CardmarketSearchWorker(card.name, parent=self)
        self._search_worker.succeeded.connect(self._on_search_succeeded)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.finished.connect(self._cleanup_search)
        self._search_worker.start()

    def _on_search_succeeded(self, results: list[CardmarketSearchResult]) -> None:
        self._main_window.statusBar().clearMessage()
        dialog = CardmarketSearchResultsDialog(parent=self._main_window)
        dialog.set_results(results)
        dialog.result_confirmed.connect(self._on_result_confirmed)
        dialog.manual_search_requested.connect(self._on_manual_search_requested)
        dialog.exec()

    def _on_manual_search_requested(self) -> None:
        """The automated search found nothing at all -- open Cardmarket's

        own search for the card's name in a normal, foreground browser
        window instead, left open for the user to search further
        themselves (mirrors "Cardmarket-Link öffnen"'s own "leave it open"
        contract). The found product's link still needs to be pasted in via
        "Bearbeiten" afterward -- this only gets the user to the right
        starting point.
        """
        if self._card_name is None:
            return
        try:
            open_cardmarket_search(self._card_name)
        except BrowserPriceReaderError as exc:
            self._main_window.statusBar().showMessage(str(exc), 5000)

    def _on_search_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup_search(self) -> None:
        self._search_worker = None
        self._detail_panel.set_cardmarket_search_running(False)

    def _on_result_confirmed(self, chosen: CardmarketSearchResult) -> None:
        if self._card_id is None or self._card_name is None:
            return
        self._detail_panel.set_cardmarket_search_running(True)
        self._main_window.statusBar().showMessage(tr("Link wird übernommen…"))
        self._resolve_worker = CardmarketSearchResolveWorker(self._card_name, chosen, parent=self)
        self._resolve_worker.succeeded.connect(self._on_resolve_succeeded)
        self._resolve_worker.failed.connect(self._on_resolve_failed)
        self._resolve_worker.finished.connect(self._cleanup_resolve)
        self._resolve_worker.start()

    def _on_resolve_succeeded(self, url: str) -> None:
        if self._card_id is None or self._card_name is None:
            return
        # Captured into locals *before* the blocking QMessageBox below --
        # live-reported bug: confirming the dialog silently did nothing.
        # Root cause: QMessageBox.question() runs its own nested Qt event
        # loop while it waits for the user, and the worker's own `finished`
        # signal (queued right behind `succeeded`, since the thread emits
        # it immediately after returning from run()) gets processed during
        # that wait -- which resets self._card_id/self._card_name to None
        # via _cleanup_resolve *before* the user ever clicks anything. By
        # the time "Yes" was clicked, self._card_id was already None, so
        # set_manual_cardmarket_url(None, url) failed with a "card not
        # found" error that only ever reached the status bar, never the
        # log -- indistinguishable from "nothing happened".
        card_id = self._card_id
        card_name = self._card_name
        # One last explicit confirmation before actually saving/overwriting
        # the card's Cardmarket link -- live-reported request: everything
        # up to here (picking a candidate) only confirms *which product* to
        # resolve, not the final URL this step just discovered.
        answer = QMessageBox.question(
            self._main_window,
            tr("Cardmarket-Link suchen"),
            tr("Diesen Link für „{name}“ speichern?\n{url}").format(
                name=card_name, url=url
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            self._main_window.statusBar().showMessage(tr("Cardmarket-Link nicht übernommen."), 5000)
            return
        try:
            self._service.set_manual_cardmarket_url(card_id, url)
        except ServiceError as exc:
            self._main_window.statusBar().showMessage(str(exc), 5000)
            return
        self._main_window.statusBar().showMessage(tr("Cardmarket-Link gespeichert."), 5000)
        self._card_controller.refresh()
        self.link_saved.emit(card_id)

    def _on_resolve_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup_resolve(self) -> None:
        self._resolve_worker = None
        self._card_id = None
        self._card_name = None
        self._detail_panel.set_cardmarket_search_running(False)
