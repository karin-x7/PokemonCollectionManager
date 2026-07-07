"""Wires the Wantlist tab's "Check price"/"Check all prices" actions to a

background :class:`WantlistPriceLookupWorker`.

Mirrors ``sealed_price_controller.py``, minus the detail panel (wantlist has
none, see wantlist_panel.py's own docstring). "Check all prices" reuses the
same one-at-a-time bulk-queue pattern as ``PriceController.start_bulk_update``
rather than checking every item in parallel -- consistent with this
project's own "never open more than one Cardmarket tab back-to-back without
a delay" rule (account lockout risk, see price_service.py's own comments).
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.logging_config import get_logger
from app.models.wantlist import WantlistItem
from app.ui.controllers.wantlist_controller import WantlistController
from app.ui.widgets.wantlist_panel import WantlistPanel
from app.ui.workers.wantlist_price_lookup_worker import (
    OpenWantlistPriceService,
    WantlistPriceLookupWorker,
)

logger = get_logger(__name__)


class WantlistPriceController(QObject):
    """Wires the Wantlist tab's price-lookup actions to a background worker."""

    def __init__(
        self,
        main_window: QMainWindow,
        panel: WantlistPanel,
        open_service: OpenWantlistPriceService,
        wantlist_controller: WantlistController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._panel = panel
        self._open_service = open_service
        self._wantlist_controller = wantlist_controller
        self._worker: WantlistPriceLookupWorker | None = None
        self._bulk_queue: list[int] = []
        self._bulk_total = 0

    def start_lookup(self, item_id: int) -> None:
        logger.info("Wantlist price lookup requested for item id=%s", item_id)
        if self._worker is not None:
            logger.info("Wantlist price lookup already running -- ignoring click.")
            return
        self._start(item_id, "Fetching price from Cardmarket…")

    def start_bulk_update(self, item_ids: list[int]) -> None:
        """Mirrors ``PriceController.start_bulk_update`` for wantlist items."""
        logger.info("Bulk wantlist price check requested for %d item(s)", len(item_ids))
        if self._worker is not None or not item_ids:
            logger.info("A lookup is already running -- ignoring bulk request.")
            return
        self._bulk_queue = list(item_ids)
        self._bulk_total = len(self._bulk_queue)
        self._panel.set_bulk_check_running(True)
        self._run_next_in_queue()

    def _run_next_in_queue(self) -> None:
        if not self._bulk_queue:
            self._bulk_total = 0
            self._panel.set_bulk_check_running(False)
            self._main_window.statusBar().showMessage("All wantlist prices checked.", 5000)
            return
        item_id = self._bulk_queue.pop(0)
        position = self._bulk_total - len(self._bulk_queue)
        self._start(
            item_id, f"Checking price {position}/{self._bulk_total}…"
        )

    def _start(self, item_id: int, status_message: str) -> None:
        try:
            self._main_window.statusBar().showMessage(status_message)
            self._main_window.busy_overlay.show_busy(status_message)
            self._worker = WantlistPriceLookupWorker(self._open_service, item_id, parent=self)
            self._worker.succeeded.connect(self._on_succeeded)
            self._worker.failed.connect(self._on_failed)
            self._worker.finished.connect(self._cleanup)
            self._worker.start()
        except Exception:  # noqa: BLE001 — surface it in the log; pythonw has no console
            logger.exception("Failed to start wantlist price lookup for item id=%s", item_id)
            self._panel.set_bulk_check_running(False)
            self._main_window.busy_overlay.hide_busy()
            self._worker = None
            self._bulk_queue = []
            self._bulk_total = 0
            raise

    def _on_succeeded(self, item: WantlistItem) -> None:
        if item.current_price is not None:
            alert = "  Below target!" if item.is_below_target else ""
            message = f'Price for "{item.name}" checked: {item.current_price:.2f} {item.price_currency}{alert}'
        else:
            message = f'No price found for "{item.name}".'
        if not self._bulk_total:
            self._main_window.statusBar().showMessage(message, 5000)
        self._wantlist_controller.refresh()

    def _on_failed(self, message: str) -> None:
        if not self._bulk_total:
            self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        self._main_window.busy_overlay.hide_busy()
        self._worker = None
        if self._bulk_total:
            self._run_next_in_queue()
