"""Connects :class:`SealedProductListPanel` to :class:`SealedProductService`.

Mirrors ``card_controller.py``, minus any notion of a collection: unlike
cards (kept in physical folders/binders), sealed products aren't organised
that way, so the panel always shows every owned sealed product -- there is
no "current collection" to react to, so ``refresh()`` always reloads the
full, unscoped list. Every panel signal is handled here, the service call is
made, the panel is refreshed from the (now authoritative) database state,
and any :class:`~app.services.exceptions.ServiceError` is surfaced as a
friendly message box instead of propagating as an exception.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.logging_config import get_logger
from app.models.sealed_product import SealedProduct, SealedProductDetailsValues, SealedProductFilter
from app.services.exceptions import ServiceError
from app.services.sealed_product_service import SealedProductService
from app.ui.widgets.sealed_price_history_dock import SealedPriceHistoryDock
from app.ui.widgets.sealed_product_detail_panel import SealedProductDetailPanel
from app.ui.widgets.sealed_product_list_panel import SealedProductListPanel

logger = get_logger(__name__)


class SealedProductController(QObject):
    """Wires a :class:`SealedProductListPanel`/:class:`SealedProductDetailPanel`

    to a :class:`SealedProductService`."""

    #: Emitted with the new product's id right after it's successfully
    #: added -- mirrors :attr:`~app.ui.controllers.card_controller.
    #: CardController.card_added`: :class:`~app.ui.main_window.MainWindow`
    #: connects this straight to :meth:`~app.ui.controllers.
    #: sealed_price_controller.SealedPriceController.start_lookup` so
    #: adding a sealed product and fetching its price happen in one step.
    product_added = Signal(int)

    def __init__(
        self,
        panel: SealedProductListPanel,
        service: SealedProductService,
        detail_panel: SealedProductDetailPanel | None = None,
        price_repository: SealedPriceRepository | None = None,
        history_dock: SealedPriceHistoryDock | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._service = service
        self._detail_panel = detail_panel
        self._prices = price_repository
        self._history_dock = history_dock

        panel.selection_changed.connect(self._on_selection_changed)
        panel.edit_requested.connect(self._on_edit)
        panel.price_edit_requested.connect(self._on_price_edit)
        panel.delete_requested.connect(self._on_delete)
        if history_dock is not None:
            history_dock.history_reset_requested.connect(self._on_history_reset)

    def refresh(self) -> None:
        """Reload every owned sealed product from the database.

        Also resyncs the detail panel to whatever ends up selected -- mirrors
        ``CardController.refresh()``'s reasoning: Qt's ``currentCellChanged``
        only fires when the *row index* changes, so an edit that leaves the
        same row selected would otherwise leave the detail panel showing
        stale (pre-edit) values.
        """
        products = self._service.search_products(SealedProductFilter())
        self._panel.set_products(products)
        self._sync_detail_panel()

    def add_product(
        self,
        name: str,
        category: str,
        values: SealedProductDetailsValues,
        photo_path: str | None,
    ) -> None:
        """Persist a new sealed product once its Cardmarket lookup has

        resolved a name/category -- called directly by
        :class:`~app.ui.controllers.sealed_entry_controller.SealedEntryController`,
        no confirmation dialog in between (user preference: name/category
        are taken as-is from the scrape, fixed up via "Bearbeiten" later if
        ever wrong, rather than reviewed before every single add)."""
        try:
            product = self._service.add_product_manual(name, category, values, photo_path)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        self.refresh()
        self._panel.select_product(product.id)
        self._sync_detail_panel()
        self.product_added.emit(product.id)

    def _on_edit(self, product_id: int, values: SealedProductDetailsValues) -> None:
        try:
            self._service.update_product_details(product_id, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_price_edit(self, product_id: int, price: float) -> None:
        try:
            self._service.set_manual_price(product_id, price)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_delete(self, product_ids: list[int]) -> None:
        errors: list[str] = []
        for product_id in product_ids:
            try:
                self._service.remove_product(product_id)
            except ServiceError as exc:
                errors.append(str(exc))
        if errors:
            self._panel.show_error("\n".join(errors))
        self.refresh()

    def _on_selection_changed(self, product_id: int) -> None:
        if product_id == -1:
            self._show_empty()
            return
        self._show_product(self._service.get_product(product_id))

    def _sync_detail_panel(self) -> None:
        selected_id = self._panel.selected_product_id()
        if selected_id is None:
            self._show_empty()
        else:
            self._show_product(self._service.get_product(selected_id))

    def _show_empty(self) -> None:
        if self._detail_panel is not None:
            self._detail_panel.show_empty()
        if self._history_dock is not None:
            self._history_dock.show_empty()

    def _show_product(self, product: SealedProduct) -> None:
        if self._detail_panel is not None:
            self._detail_panel.show_product(product)
        if self._history_dock is not None and self._prices is not None:
            self._history_dock.show_history(product, self._prices.list_for_product(product.id))

    def _on_history_reset(self, product_id: int) -> None:
        if self._prices is None:
            return
        self._prices.delete_for_product(product_id)
        logger.info("Sealed price history reset for product id=%s", product_id)
        selected_id = self._panel.selected_product_id()
        if selected_id == product_id:
            self._show_product(self._service.get_product(product_id))
