"""Connects :class:`CardListPanel`/:class:`CardDetailPanel` to :class:`CardService`.

Every panel signal is handled here: the service call is made, the panel is
refreshed from the (now authoritative) database state, and any
:class:`~app.services.exceptions.ServiceError` is surfaced as a friendly
message box instead of propagating as an exception. Which collection is
"current" is tracked here (set by :class:`~app.ui.main_window.MainWindow`
when the collection selection changes) since neither panel knows about
collections.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QMessageBox

from app.catalog.models import CatalogCard
from app.database.repositories.price_repository import PriceRepository
from app.i18n import tr
from app.logging_config import get_logger
from app.models.card import Card, CardDetailsValues, CardFilter
from app.pricing.models import ProductInfo
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.exceptions import ServiceError
from app.ui.dialogs.move_dialog import MoveDialog
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel
from app.ui.widgets.price_history_dock import PriceHistoryDock

logger = get_logger(__name__)


class CardController(QObject):
    """Wires a :class:`CardListPanel`/:class:`CardDetailPanel` to a :class:`CardService`."""

    def __init__(
        self,
        panel: CardListPanel,
        detail_panel: CardDetailPanel,
        service: CardService,
        collection_service: CollectionService,
        price_repository: PriceRepository | None = None,
        history_dock: PriceHistoryDock | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._detail_panel = detail_panel
        self._service = service
        self._collections = collection_service
        self._prices = price_repository
        self._history_dock = history_dock
        self._collection_id: int | None = None
        self._filter_fields = CardFilter()
        self._search_all_collections = False

        panel.selection_changed.connect(self._on_selection_changed)
        panel.add_confirmed.connect(self._on_add_confirmed)
        panel.manual_add_confirmed.connect(self._on_manual_add_confirmed)
        panel.edit_requested.connect(self._on_edit)
        panel.price_edit_requested.connect(self._on_price_edit)
        panel.delete_requested.connect(self._on_delete)
        panel.move_requested.connect(self._on_move_requested)
        panel.filter_bar.filter_changed.connect(self._on_filter_changed)
        panel.filter_bar.scope_changed.connect(self._on_scope_changed)
        if history_dock is not None:
            history_dock.history_reset_requested.connect(self._on_history_reset)

    def set_collection(self, collection_id: int | None) -> None:
        """React to a new collection being selected (or none, id == -1/None)."""
        self._collection_id = collection_id if collection_id != -1 else None
        self.refresh()

    def refresh(self) -> None:
        """Reload the currently filtered/scoped set of cards from the database.

        Also resyncs the detail panel to whatever ends up selected: Qt's
        ``currentCellChanged`` only fires when the *row index* changes, so an
        edit that leaves the same row selected would otherwise leave the
        detail panel showing stale (pre-edit) values.
        """
        if not self._search_all_collections and self._collection_id is None:
            self._panel.set_cards([])
            self._detail_panel.show_empty()
            if self._history_dock is not None:
                self._history_dock.show_empty()
            return
        scope_id = None if self._search_all_collections else self._collection_id
        active_filter = replace(self._filter_fields, collection_id=scope_id)
        self._panel.set_cards(self._service.search_cards(active_filter))
        self._panel.filter_bar.set_available_sets(self._service.list_set_names(scope_id))
        self._sync_detail_panel()

    def _on_filter_changed(self, card_filter: CardFilter) -> None:
        self._filter_fields = card_filter
        self.refresh()

    def _on_scope_changed(self, search_all_collections: bool) -> None:
        self._search_all_collections = search_all_collections
        self.refresh()

    @property
    def collection_id(self) -> int | None:
        """The currently selected collection's id, or ``None`` if none is."""
        return self._collection_id

    def add_from_catalog(self, catalog_card: CatalogCard) -> None:
        """Start the add-card flow for a catalogue match the user picked."""
        if self._collection_id is None:
            self._panel.show_error(tr("Bitte zuerst eine Sammlung auswählen."))
            return
        self._panel.prompt_add_from_catalog(catalog_card)

    def _on_add_confirmed(self, catalog_card: CatalogCard, values: CardDetailsValues) -> None:
        if self._collection_id is None:
            return
        duplicates = self._service.find_duplicates(
            catalog_card.name, catalog_card.set_name, catalog_card.card_number, values
        )
        if not self._confirm_duplicate(catalog_card.name, duplicates):
            return
        try:
            card = self._service.add_card_from_catalog(self._collection_id, catalog_card, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        self.refresh()
        self._panel.select_card(card.id)
        self._sync_detail_panel()

    def prompt_add_manual(self, info: ProductInfo, url: str) -> None:
        """Start the add-card flow for a manually-entered Cardmarket link."""
        if self._collection_id is None:
            self._panel.show_error(tr("Bitte zuerst eine Sammlung auswählen."))
            return
        self._panel.prompt_add_manual(info, url)

    def _on_manual_add_confirmed(
        self,
        name: str,
        set_name: str,
        card_number: str,
        values: CardDetailsValues,
        photo_path: str | None,
        set_code: str,
    ) -> None:
        if self._collection_id is None:
            return
        duplicates = self._service.find_duplicates(name, set_name, card_number, values)
        if not self._confirm_duplicate(name, duplicates):
            return
        try:
            card = self._service.add_card_manual(
                self._collection_id, name, set_name, card_number, values, photo_path, set_code
            )
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        self.refresh()
        self._panel.select_card(card.id)
        self._sync_detail_panel()

    def _confirm_duplicate(self, name: str, duplicates: list[Card]) -> bool:
        """Ask the user to confirm adding an apparent duplicate.

        Returns ``True`` to proceed (no duplicates found, or the user
        confirmed anyway), ``False`` to abort the add.
        """
        if not duplicates:
            return True
        collection_names = {c.id: c.name for c in self._collections.list_collections()}
        where = ", ".join(
            sorted({collection_names.get(d.collection_id, "?") for d in duplicates})
        )
        total_owned = sum(d.quantity for d in duplicates)
        unit = "copy" if total_owned == 1 else "copies"
        answer = QMessageBox.question(
            self._panel,
            "Possible duplicate",
            f'You already own {total_owned} {unit} of "{name}" with the same set, '
            f"number, language, and condition (in: {where}).\n\n"
            "Add another copy anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _on_edit(self, card_id: int, values: CardDetailsValues) -> None:
        try:
            self._service.update_card_details(card_id, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_price_edit(self, card_id: int, price: float) -> None:
        try:
            self._service.set_manual_price(card_id, price)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_delete(self, card_ids: list[int]) -> None:
        errors: list[str] = []
        for card_id in card_ids:
            try:
                self._service.remove_card(card_id)
            except ServiceError as exc:
                errors.append(str(exc))
        if errors:
            self._panel.show_error("\n".join(errors))
        self.refresh()

    def _on_move_requested(self, card_ids: list[int]) -> None:
        if not card_ids:
            return
        cards = [self._service.get_card(card_id) for card_id in card_ids]
        # Excluding the selection's own collection only makes sense when
        # every selected card actually shares one -- a mixed-collection
        # selection (possible via "search all collections") has no single
        # "own" collection to exclude, so every collection stays a valid
        # target then.
        collection_ids = {card.collection_id for card in cards}
        exclude = collection_ids if len(collection_ids) == 1 else set()
        others = [c for c in self._collections.list_collections() if c.id not in exclude]
        if not others:
            self._panel.show_error(
                tr("Es gibt keine andere Sammlung, in die verschoben werden könnte.")
            )
            return
        dialog = MoveDialog(others, parent=self._panel)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        target_id = dialog.get_target_collection_id()
        errors: list[str] = []
        for card_id in card_ids:
            try:
                self._service.move_card(card_id, target_id)
            except ServiceError as exc:
                errors.append(str(exc))
        if errors:
            self._panel.show_error("\n".join(errors))
        self.refresh()

    def _on_selection_changed(self, card_id: int) -> None:
        if card_id == -1:
            self._detail_panel.show_empty()
            if self._history_dock is not None:
                self._history_dock.show_empty()
            return
        self._show_card(self._service.get_card(card_id))

    def _sync_detail_panel(self) -> None:
        selected_id = self._panel.selected_card_id()
        if selected_id is None:
            self._detail_panel.show_empty()
            if self._history_dock is not None:
                self._history_dock.show_empty()
        else:
            self._show_card(self._service.get_card(selected_id))

    def _show_card(self, card: Card) -> None:
        self._detail_panel.show_card(card)
        if self._history_dock is not None and self._prices is not None:
            self._history_dock.show_history(card, self._prices.list_for_card(card.id))

    def _on_history_reset(self, card_id: int) -> None:
        if self._prices is None:
            return
        self._prices.delete_for_card(card_id)
        logger.info("Price history reset for card id=%s", card_id)
        selected_id = self._panel.selected_card_id()
        if selected_id == card_id:
            self._show_card(self._service.get_card(card_id))
