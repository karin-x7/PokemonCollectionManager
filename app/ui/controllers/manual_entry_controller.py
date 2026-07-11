"""Wires the "Karte manuell eintragen" toolbar action to a background
Cardmarket product-page lookup, then the normal add-card dialog.

Lets the user paste a Cardmarket product link directly instead of picking a
catalogue match that automatic matching might get wrong (vintage
multi-version products, JP/KO/ZH prints, ...). The link is opened in exactly
one Chrome tab (background thread, same mechanism as price lookups, see
:class:`~app.ui.workers.product_info_worker.ProductInfoWorker`) to read its
own title for name/set/card-number, then the usual add-card dialog opens,
prefilled but editable, with the link stored as the card's manual Cardmarket
override.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QMainWindow, QMessageBox

from app.catalog.pokemontcg_client import PokemonTcgClient
from app.i18n import tr
from app.logging_config import get_logger
from app.pricing.models import ProductInfo
from app.ui.controllers.card_controller import CardController
from app.ui.dialogs.manual_entry_dialog import ManualEntryDialog
from app.ui.workers.product_info_worker import ProductInfoWorker

logger = get_logger(__name__)


class ManualEntryController(QObject):
    """Starts the "Karte manuell eintragen" flow."""

    def __init__(
        self,
        main_window: QMainWindow,
        card_controller: CardController,
        pokemontcg_client: PokemonTcgClient | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._card_controller = card_controller
        self._pokemontcg = pokemontcg_client
        self._worker: ProductInfoWorker | None = None
        self._url: str | None = None

    def start(self) -> None:
        """Show the link dialog and (if confirmed) look up its page."""
        if self._card_controller.collection_id is None:
            # A status-bar toast alone is too easy to miss -- a blocking
            # dialog makes the "nothing happened" confusion impossible
            # (mirrors SealedEntryController's own guard).
            QMessageBox.information(
                self._main_window,
                tr("Karten"),
                tr("Bitte zuerst eine Sammlung auswählen."),
            )
            return
        if self._worker is not None:
            logger.info("Manual entry lookup already running -- ignoring click.")
            return

        dialog = ManualEntryDialog(parent=self._main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = dialog.get_url()
        if not url:
            return

        self._url = url
        status_message = tr("Cardmarket-Seite wird gelesen…")
        self._main_window.statusBar().showMessage(status_message)
        # A status-bar message alone is easy to miss (the read itself can
        # take several seconds) -- mirrors PriceController's own busy overlay
        # for price lookups, the same underlying browser-automation wait.
        self._main_window.busy_overlay.show_busy(status_message)
        self._worker = ProductInfoWorker(url, self._pokemontcg, parent=self)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._cleanup)
        self._worker.start()

    def _on_succeeded(self, info: ProductInfo) -> None:
        self._main_window.statusBar().clearMessage()
        self._card_controller.prompt_add_manual(info, self._url)

    def _on_failed(self, message: str) -> None:
        self._main_window.statusBar().showMessage(message, 5000)

    def _cleanup(self) -> None:
        self._main_window.busy_overlay.hide_busy()
        self._worker = None
        self._url = None
