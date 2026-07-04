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
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.logging_config import get_logger
from app.models.card import Card
from app.ui.controllers.card_controller import CardController
from app.ui.controllers.statistics_controller import StatisticsController
from app.ui.widgets.card_detail_panel import CardDetailPanel
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
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._panel = panel
        self._open_service = open_service
        self._card_controller = card_controller
        self._statistics_controller = statistics_controller
        self._worker: PriceLookupWorker | None = None

        panel.price_lookup_requested.connect(self.start_lookup)

    def start_lookup(self, card_id: int) -> None:
        logger.info("Price lookup requested for card id=%s", card_id)
        if self._worker is not None:
            logger.info("Price lookup already running -- ignoring click.")
            return  # a lookup is already running
        try:
            self._panel.set_price_lookup_running(True)
            self._main_window.statusBar().showMessage("Preis wird von Cardmarket abgerufen…")
            self._worker = PriceLookupWorker(self._open_service, card_id, parent=self)
            self._worker.succeeded.connect(self._on_succeeded)
            self._worker.failed.connect(self._on_failed)
            self._worker.finished.connect(self._cleanup)
            self._worker.start()
        except Exception:  # noqa: BLE001 — surface it in the log; pythonw has no console
            logger.exception("Failed to start price lookup for card id=%s", card_id)
            self._panel.set_price_lookup_running(False)
            self._worker = None
            raise

    def _on_succeeded(self, card: Card) -> None:
        message = (
            f"Preis für „{card.name}“ aktualisiert: {card.current_price:.2f} {card.price_currency}"
            if card.current_price is not None
            else f"Kein Preis für „{card.name}“ gefunden."
        )
        self._main_window.statusBar().showMessage(message, 5000)
        self._card_controller.refresh()
        if self._statistics_controller is not None:
            self._statistics_controller.refresh()

    def _on_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        self._panel.set_price_lookup_running(False)
        self._worker = None
