"""Wires the Sealed tab's "+ Sealed-Produkt hinzufügen" button to a single

upfront dialog (link + language/quantity/notes), then a background
Cardmarket product-page lookup that fills in name/category/photo and
creates the product directly -- no second confirmation dialog.

Originally a two-dialog flow (link first, then a details dialog prefilled
from the lookup): user feedback was that the Chrome tab flashing open
*between* two dialogs felt like unexplained, disruptive activity. Since the
details dialog already had every other field (language/quantity/notes) and
the *only* thing genuinely dependent on the lookup was name/category, the
two steps collapse into one: ask for everything upfront, run the lookup
after the dialog closes, and create the product once it resolves --
explicit user preference over reviewing the auto-detected name/category
each time (fixed up via "Bearbeiten" afterward if ever wrong).
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QMainWindow

from app.i18n import tr
from app.logging_config import get_logger
from app.models.sealed_product import SealedProductDetailsValues
from app.pricing.models import SealedProductInfo
from app.ui.controllers.sealed_product_controller import SealedProductController
from app.ui.dialogs.sealed_product_add_dialog import SealedProductAddDialog
from app.ui.workers.sealed_product_info_worker import SealedProductInfoWorker

logger = get_logger(__name__)


class SealedEntryController(QObject):
    """Starts the "Sealed-Produkt hinzufügen" flow."""

    def __init__(
        self,
        main_window: QMainWindow,
        product_controller: SealedProductController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._product_controller = product_controller
        self._worker: SealedProductInfoWorker | None = None
        self._url: str | None = None
        self._values: SealedProductDetailsValues | None = None

    def start(self) -> None:
        """Show the add dialog and (if confirmed) look up its page."""
        if self._worker is not None:
            logger.info("Sealed entry lookup already running -- ignoring click.")
            return

        dialog = SealedProductAddDialog(parent=self._main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = dialog.get_url()
        if not url:
            return

        self._url = url
        self._values = dialog.get_values()
        self._main_window.statusBar().showMessage(tr("Cardmarket-Seite wird gelesen…"))
        self._worker = SealedProductInfoWorker(url, parent=self)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._cleanup)
        self._worker.start()

    def _on_succeeded(self, info: SealedProductInfo) -> None:
        self._main_window.statusBar().clearMessage()
        values = replace(self._values, cardmarket_url=self._url)
        self._product_controller.add_product(info.name, info.category, values, info.photo_path)

    def _on_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        self._worker = None
        self._url = None
        self._values = None
