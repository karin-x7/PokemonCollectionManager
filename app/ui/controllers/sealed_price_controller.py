"""Wires the Sealed tab's "Preis aktualisieren" actions to a background
:class:`SealedPriceLookupWorker`.

Mirrors ``price_controller.py``. Two independent triggers feed the same
``start_lookup``: the list panel's context-menu action, and (since the
Sealed tab grew its own detail panel, mirroring Karten's) the detail panel's
"Preis von Cardmarket abrufen" button -- the latter is disabled for the
duration of the lookup via ``detail_panel.set_price_lookup_running()``, the
same as the card equivalent. If a :class:`~app.ui.controllers.
statistics_controller.StatisticsController` is given too, it's refreshed as
well -- a lookup triggered from the "Sealed-Produkte mit veraltetem Preis"
list (see ``statistics_panel.py``) should make that same product
disappear/move without waiting for the next tab switch.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.i18n import tr
from app.logging_config import get_logger
from app.models.sealed_product import SealedProduct
from app.ui.controllers.sealed_product_controller import SealedProductController
from app.ui.controllers.statistics_controller import StatisticsController
from app.ui.widgets.sealed_product_detail_panel import SealedProductDetailPanel
from app.ui.widgets.sealed_product_list_panel import SealedProductListPanel
from app.ui.workers.open_sealed_cardmarket_link_worker import OpenSealedCardmarketLinkWorker
from app.ui.workers.sealed_price_lookup_worker import OpenSealedPriceService, SealedPriceLookupWorker
from app.utils.formatting import format_decimal

logger = get_logger(__name__)


class SealedPriceController(QObject):
    """Wires the Sealed tab's price-lookup actions to a background worker."""

    def __init__(
        self,
        main_window: QMainWindow,
        open_service: OpenSealedPriceService,
        product_controller: SealedProductController,
        detail_panel: SealedProductDetailPanel | None = None,
        statistics_controller: StatisticsController | None = None,
        list_panel: SealedProductListPanel | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._open_service = open_service
        self._product_controller = product_controller
        self._detail_panel = detail_panel
        self._statistics_controller = statistics_controller
        self._worker: SealedPriceLookupWorker | None = None
        self._bulk_queue: list[int] = []
        self._bulk_total = 0
        self._link_worker: OpenSealedCardmarketLinkWorker | None = None

        if detail_panel is not None:
            detail_panel.price_lookup_requested.connect(self.start_lookup)
        if list_panel is not None:
            list_panel.open_cardmarket_link_requested.connect(self.open_cardmarket_link)

    def start_lookup(self, product_id: int) -> None:
        logger.info("Sealed price lookup requested for product id=%s", product_id)
        if self._worker is not None or self._link_worker is not None:
            logger.info("A Cardmarket browser operation is already running -- ignoring click.")
            return
        self._start(product_id, tr("Preis wird von Cardmarket abgerufen…"))

    def start_bulk_update(self, product_ids: list[int]) -> None:
        """Mirrors ``PriceController.start_bulk_update`` for sealed products."""
        logger.info("Bulk sealed price update requested for %d product(s)", len(product_ids))
        if self._worker is not None or not product_ids:
            logger.info("A lookup is already running -- ignoring bulk request.")
            return
        self._bulk_queue = list(product_ids)
        self._bulk_total = len(self._bulk_queue)
        if self._statistics_controller is not None:
            self._statistics_controller.set_bulk_sealed_update_running(True)
        self._run_next_in_queue()

    def _run_next_in_queue(self) -> None:
        if not self._bulk_queue:
            self._bulk_total = 0
            if self._statistics_controller is not None:
                self._statistics_controller.set_bulk_sealed_update_running(False)
            self._main_window.statusBar().showMessage(
                tr("Alle veralteten Preise wurden aktualisiert."), 5000
            )
            return
        product_id = self._bulk_queue.pop(0)
        position = self._bulk_total - len(self._bulk_queue)
        self._start(
            product_id,
            tr("Preis {position}/{total} wird von Cardmarket abgerufen…").format(
                position=position, total=self._bulk_total
            ),
        )

    def _start(self, product_id: int, status_message: str) -> None:
        try:
            if self._detail_panel is not None:
                self._detail_panel.set_price_lookup_running(True)
            self._main_window.statusBar().showMessage(status_message)
            self._main_window.busy_overlay.show_busy(status_message)
            self._worker = SealedPriceLookupWorker(self._open_service, product_id, parent=self)
            self._worker.succeeded.connect(self._on_succeeded)
            self._worker.failed.connect(self._on_failed)
            self._worker.finished.connect(self._cleanup)
            self._worker.start()
        except Exception:  # noqa: BLE001 — surface it in the log; pythonw has no console
            logger.exception("Failed to start sealed price lookup for product id=%s", product_id)
            if self._detail_panel is not None:
                self._detail_panel.set_price_lookup_running(False)
            self._main_window.busy_overlay.hide_busy()
            self._worker = None
            self._bulk_queue = []
            self._bulk_total = 0
            if self._statistics_controller is not None:
                self._statistics_controller.set_bulk_sealed_update_running(False)
            raise

    def _on_succeeded(self, product: SealedProduct) -> None:
        message = (
            tr("Preis für „{name}“ aktualisiert: {price} {currency}").format(
                name=product.name,
                price=format_decimal(product.current_price),
                currency=product.price_currency,
            )
            if product.current_price is not None
            else tr("Kein Preis für „{name}“ gefunden.").format(name=product.name)
        )
        if not self._bulk_total:
            self._main_window.statusBar().showMessage(message, 5000)
        self._product_controller.refresh()
        if self._statistics_controller is not None:
            self._statistics_controller.refresh()

    def _on_failed(self, message: str) -> None:
        if not self._bulk_total:
            self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        if self._detail_panel is not None:
            self._detail_panel.set_price_lookup_running(False)
        self._main_window.busy_overlay.hide_busy()
        self._worker = None
        if self._bulk_total:
            self._run_next_in_queue()

    def open_cardmarket_link(self, product_id: int) -> None:
        """Open the product's Cardmarket page in Chrome, left open for the

        user to browse -- the "Cardmarket-Link öffnen" context-menu action.
        Mirrors ``PriceController.open_cardmarket_link`` exactly.
        """
        logger.info("Open Cardmarket link requested for sealed product id=%s", product_id)
        if self._worker is not None or self._link_worker is not None:
            logger.info("A Cardmarket browser operation is already running -- ignoring click.")
            self._main_window.statusBar().showMessage(
                tr("Ein anderer Cardmarket-Vorgang läuft gerade -- bitte kurz warten."), 4000
            )
            return
        self._link_worker = OpenSealedCardmarketLinkWorker(
            self._open_service, product_id, parent=self
        )
        self._link_worker.succeeded.connect(self._on_link_opened)
        self._link_worker.failed.connect(self._on_link_failed)
        self._link_worker.finished.connect(self._on_link_cleanup)
        self._link_worker.start()

    def _on_link_opened(self, url: object) -> None:
        if url is None:
            self._main_window.statusBar().showMessage(
                tr(
                    "Keine Cardmarket-Zuordnung für dieses Produkt bekannt -- Link kann "
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
