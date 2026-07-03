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

from PySide6.QtCore import QObject

from app.catalog.models import CatalogCard
from app.logging_config import get_logger
from app.models.card import CardDetailsValues
from app.services.card_service import CardService
from app.services.exceptions import ServiceError
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel

logger = get_logger(__name__)


class CardController(QObject):
    """Wires a :class:`CardListPanel`/:class:`CardDetailPanel` to a :class:`CardService`."""

    def __init__(
        self,
        panel: CardListPanel,
        detail_panel: CardDetailPanel,
        service: CardService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._detail_panel = detail_panel
        self._service = service
        self._collection_id: int | None = None

        panel.selection_changed.connect(self._on_selection_changed)
        panel.add_confirmed.connect(self._on_add_confirmed)
        panel.edit_requested.connect(self._on_edit)
        panel.delete_requested.connect(self._on_delete)

    def set_collection(self, collection_id: int | None) -> None:
        """React to a new collection being selected (or none, id == -1/None)."""
        self._collection_id = collection_id if collection_id != -1 else None
        self.refresh()

    def refresh(self) -> None:
        """Reload the current collection's cards from the database.

        Also resyncs the detail panel to whatever ends up selected: Qt's
        ``currentCellChanged`` only fires when the *row index* changes, so an
        edit that leaves the same row selected would otherwise leave the
        detail panel showing stale (pre-edit) values.
        """
        if self._collection_id is None:
            self._panel.set_cards([])
            self._detail_panel.show_empty()
            return
        self._panel.set_cards(self._service.list_cards(self._collection_id))
        self._sync_detail_panel()

    def add_from_catalog(self, catalog_card: CatalogCard) -> None:
        """Start the add-card flow for a catalogue match the user picked."""
        if self._collection_id is None:
            self._panel.show_error("Bitte zuerst eine Sammlung auswählen.")
            return
        self._panel.prompt_add_from_catalog(catalog_card)

    def _on_add_confirmed(self, catalog_card: CatalogCard, values: CardDetailsValues) -> None:
        if self._collection_id is None:
            return
        try:
            card = self._service.add_card_from_catalog(self._collection_id, catalog_card, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        self.refresh()
        self._panel.select_card(card.id)
        self._sync_detail_panel()

    def _on_edit(self, card_id: int, values: CardDetailsValues) -> None:
        try:
            self._service.update_card_details(card_id, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_delete(self, card_id: int) -> None:
        try:
            self._service.remove_card(card_id)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_selection_changed(self, card_id: int) -> None:
        if card_id == -1:
            self._detail_panel.show_empty()
            return
        self._detail_panel.show_card(self._service.get_card(card_id))

    def _sync_detail_panel(self) -> None:
        selected_id = self._panel.selected_card_id()
        if selected_id is None:
            self._detail_panel.show_empty()
        else:
            self._detail_panel.show_card(self._service.get_card(selected_id))
