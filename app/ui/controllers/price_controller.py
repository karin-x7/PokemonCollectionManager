"""Connects price-lookup buttons to :class:`PriceService`.

The actual lookup runs in a background :class:`~app.ui.workers.
price_lookup_worker.PriceLookupWorker` so the GUI doesn't freeze while a
browser tab opens/reads/closes. After a lookup, :class:`~app.ui.controllers.
card_controller.CardController` is asked to refresh — it re-renders the card
list and resyncs the detail panel to whatever is currently selected, so this
stays correct even if the user picked a different card while the lookup for
the previous one was still running. If a :class:`~app.ui.controllers.
statistics_controller.StatisticsController` is given too, it's refreshed as
well -- a lookup triggered from the "Karten mit veraltetem Preis" list
should make that same card disappear/move without waiting for the next tab
switch.

``start_lookup`` is public (not just the card detail panel's own signal
handler) because :class:`~app.ui.widgets.statistics_panel.StatisticsPanel`'s
inline "Preis aktualisieren" buttons trigger the exact same lookup.
``start_bulk_update`` looks up a whole list of ids one at a time, reusing
the same single-worker-slot machinery, for that panel's "Alle
aktualisieren" button.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.i18n import tr
from app.logging_config import get_logger
from app.models.card import Card
from app.ui.controllers.card_controller import CardController
from app.ui.controllers.statistics_controller import StatisticsController
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel
from app.ui.workers.open_cardmarket_link_worker import OpenCardmarketLinkWorker
from app.ui.workers.price_lookup_worker import OpenPriceService, PriceLookupWorker

logger = get_logger(__name__)


class PriceController(QObject):
    """Wires price-lookup buttons to a background :class:`PriceLookupWorker`."""

    def __init__(
        self,
        main_window: QMainWindow,
        panel: CardDetailPanel,
        open_service: OpenPriceService,
        card_controller: CardController,
        statistics_controller: StatisticsController | None = None,
        list_panel: CardListPanel | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._panel = panel
        self._open_service = open_service
        self._card_controller = card_controller
        self._statistics_controller = statistics_controller
        self._worker: PriceLookupWorker | None = None
        self._bulk_queue: list[int] = []
        self._bulk_total = 0
        self._link_worker: OpenCardmarketLinkWorker | None = None

        panel.price_lookup_requested.connect(self.start_lookup)
        if list_panel is not None:
            list_panel.open_cardmarket_link_requested.connect(self.open_cardmarket_link)

    def start_lookup(self, card_id: int) -> None:
        logger.info("Price lookup requested for card id=%s", card_id)
        if self._worker is not None or self._link_worker is not None:
            logger.info("A Cardmarket browser operation is already running -- ignoring click.")
            return  # a lookup or an "open link" is already running
        self._start(card_id, tr("Preis wird von Cardmarket abgerufen…"))

    def start_bulk_update(self, card_ids: list[int]) -> None:
        """Looks up every id in ``card_ids`` one after another.

        Refuses if a lookup (single or bulk) is already running -- mirrors
        ``start_lookup``'s own single-worker-slot guard, just checked once
        up front instead of before every item.
        """
        logger.info("Bulk price update requested for %d card(s)", len(card_ids))
        if self._worker is not None or self._link_worker is not None or not card_ids:
            logger.info("A Cardmarket browser operation is already running -- ignoring bulk request.")
            return
        self._bulk_queue = list(card_ids)
        self._bulk_total = len(self._bulk_queue)
        if self._statistics_controller is not None:
            self._statistics_controller.set_bulk_card_update_running(True)
        self._run_next_in_queue()

    def _run_next_in_queue(self) -> None:
        if not self._bulk_queue:
            self._bulk_total = 0
            if self._statistics_controller is not None:
                self._statistics_controller.set_bulk_card_update_running(False)
            self._main_window.statusBar().showMessage(
                tr("Alle veralteten Preise wurden aktualisiert."), 5000
            )
            return
        card_id = self._bulk_queue.pop(0)
        position = self._bulk_total - len(self._bulk_queue)
        self._start(
            card_id,
            tr("Preis {position}/{total} wird von Cardmarket abgerufen…").format(
                position=position, total=self._bulk_total
            ),
        )

    def _start(self, card_id: int, status_message: str) -> None:
        try:
            self._panel.set_price_lookup_running(True)
            self._main_window.statusBar().showMessage(status_message)
            self._main_window.busy_overlay.show_busy(status_message)
            self._worker = PriceLookupWorker(self._open_service, card_id, parent=self)
            self._worker.succeeded.connect(self._on_succeeded)
            self._worker.failed.connect(self._on_failed)
            self._worker.finished.connect(self._cleanup)
            self._worker.start()
        except Exception:  # noqa: BLE001 — surface it in the log; pythonw has no console
            logger.exception("Failed to start price lookup for card id=%s", card_id)
            self._panel.set_price_lookup_running(False)
            self._main_window.busy_overlay.hide_busy()
            self._worker = None
            self._bulk_queue = []
            self._bulk_total = 0
            if self._statistics_controller is not None:
                self._statistics_controller.set_bulk_card_update_running(False)
            raise

    def _on_succeeded(self, card: Card) -> None:
        message = (
            tr("Preis für „{name}“ aktualisiert: {price} {currency}").format(
                name=card.name, price=f"{card.current_price:.2f}", currency=card.price_currency
            )
            if card.current_price is not None
            else tr("Kein Preis für „{name}“ gefunden.").format(name=card.name)
        )
        if not self._bulk_total:
            self._main_window.statusBar().showMessage(message, 5000)
        self._card_controller.refresh()
        if self._statistics_controller is not None:
            self._statistics_controller.refresh()

    def _on_failed(self, message: str) -> None:
        if not self._bulk_total:
            self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        self._panel.set_price_lookup_running(False)
        self._main_window.busy_overlay.hide_busy()
        self._worker = None
        if self._bulk_total:
            self._run_next_in_queue()

    def open_cardmarket_link(self, card_id: int) -> None:
        """Open the card's Cardmarket page in Chrome, left open for the user
        to browse -- the "Cardmarket-Link öffnen" context-menu action.

        Distinct from ``start_lookup``: shares the same single-slot guard
        against a concurrent price lookup (both open a Chrome tab tied to
        this card, and the automated lookup's own window-matching could
        otherwise mistake this manually-opened tab for its own), but has no
        busy overlay of its own -- this finishes almost instantly (open and
        forget), unlike a lookup's several-second read-and-close cycle.
        """
        logger.info("Open Cardmarket link requested for card id=%s", card_id)
        if self._worker is not None or self._link_worker is not None:
            logger.info("A Cardmarket browser operation is already running -- ignoring click.")
            self._main_window.statusBar().showMessage(
                tr("Ein anderer Cardmarket-Vorgang läuft gerade -- bitte kurz warten."), 4000
            )
            return
        self._link_worker = OpenCardmarketLinkWorker(self._open_service, card_id, parent=self)
        self._link_worker.succeeded.connect(self._on_link_opened)
        self._link_worker.failed.connect(self._on_link_failed)
        self._link_worker.finished.connect(self._on_link_cleanup)
        self._link_worker.start()

    def _on_link_opened(self, url: object) -> None:
        if url is None:
            self._main_window.statusBar().showMessage(
                tr(
                    "Keine Cardmarket-Zuordnung für diese Karte bekannt -- Link kann "
                    "nicht geöffnet werden."
                ),
                5000,
            )
        else:
            self._main_window.statusBar().showMessage(tr("Cardmarket-Seite geöffnet."), 4000)

    def _on_link_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _on_link_cleanup(self) -> None:
        self._link_worker = None
