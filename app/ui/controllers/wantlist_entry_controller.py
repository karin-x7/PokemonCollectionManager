"""Wires the Wantlist tab's "+ Add to wantlist" button to a single upfront

dialog (link + language/condition/target price/notes), then a background
Cardmarket product-page lookup that fills in name/set/card_number and adds
the item directly -- no second confirmation dialog.

Mirrors ``sealed_entry_controller.py``, reusing
:class:`~app.ui.workers.product_info_worker.ProductInfoWorker` (the same
single-card lookup ``manual_entry_controller.py`` uses) rather than the
sealed-product one -- a wantlist entry is an individual card, not a sealed
product, so it needs the same name/set/card_number parsing single cards get.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QMainWindow

from app.logging_config import get_logger
from app.models.wantlist import WantlistItemDetailsValues
from app.pricing.models import ProductInfo
from app.ui.controllers.wantlist_controller import WantlistController
from app.ui.dialogs.wantlist_add_dialog import WantlistAddDialog
from app.ui.workers.product_info_worker import ProductInfoWorker

logger = get_logger(__name__)


class WantlistEntryController(QObject):
    """Starts the "+ Add to wantlist" flow."""

    def __init__(
        self,
        main_window: QMainWindow,
        wantlist_controller: WantlistController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._wantlist_controller = wantlist_controller
        self._worker: ProductInfoWorker | None = None
        self._url: str | None = None
        self._values: WantlistItemDetailsValues | None = None

    def start(self) -> None:
        """Show the add dialog and (if confirmed) look up its page."""
        if self._worker is not None:
            logger.info("Wantlist entry lookup already running -- ignoring click.")
            return

        dialog = WantlistAddDialog(parent=self._main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = dialog.get_url()
        if not url:
            return

        self._url = url
        self._values = dialog.get_values()
        self._main_window.statusBar().showMessage("Reading Cardmarket page…")
        self._worker = ProductInfoWorker(url, parent=self)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._cleanup)
        self._worker.start()

    def _on_succeeded(self, info: ProductInfo) -> None:
        self._main_window.statusBar().clearMessage()
        values = replace(self._values, cardmarket_url=self._url)
        self._wantlist_controller.add_item(info.name, info.set_name, info.card_number, values)

    def _on_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        self._worker = None
        self._url = None
        self._values = None
