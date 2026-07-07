"""Connects :class:`WantlistPanel` to :class:`WantlistService`.

Mirrors ``sealed_product_controller.py``, minus the detail panel/history
dock (a wantlist entry is just tracked against a target price, no "owned
copy" detail to show -- kept intentionally simple, see wantlist_panel.py's
own docstring). There is no "current collection" to react to either
(a wantlist is global, like sealed products), so ``refresh()`` always
reloads the full list.

Also owns the "Add to collection" conversion: once a wanted card is
actually bought, it becomes an owned :class:`~app.models.card.Card` (via
``CardService``, the same manual-link path used for cards entered by
Cardmarket URL) and drops out of the wantlist. This needs both
``CardService`` and ``CollectionService`` alongside ``WantlistService``,
mirroring how ``CardController`` itself already depends on both a card and
a collection service.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog

from app.logging_config import get_logger
from app.models.card import CardDetailsValues
from app.models.wantlist import WantlistItemDetailsValues
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.exceptions import ServiceError
from app.services.wantlist_service import WantlistService
from app.ui.dialogs.move_dialog import MoveDialog
from app.ui.widgets.wantlist_panel import WantlistPanel

logger = get_logger(__name__)


class WantlistController(QObject):
    """Wires a :class:`WantlistPanel` to a :class:`WantlistService`."""

    def __init__(
        self,
        panel: WantlistPanel,
        service: WantlistService,
        card_service: CardService,
        collection_service: CollectionService,
        on_converted: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._service = service
        self._cards = card_service
        self._collections = collection_service
        self._on_converted = on_converted

        panel.edit_requested.connect(self._on_edit)
        panel.delete_requested.connect(self._on_delete)
        panel.convert_to_owned_requested.connect(self._on_convert_to_owned)

    def refresh(self) -> None:
        """Reload every wantlist item from the database."""
        self._panel.set_items(self._service.list_items())

    def add_item(
        self, name: str, set_name: str, card_number: str, values: WantlistItemDetailsValues
    ) -> None:
        """Persist a new wantlist item once its Cardmarket lookup has

        resolved a name/set -- called directly by
        :class:`~app.ui.controllers.wantlist_entry_controller.
        WantlistEntryController`, no confirmation dialog in between (mirrors
        SealedProductController.add_product's own reasoning)."""
        try:
            item = self._service.add_item(name, set_name, card_number, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        self.refresh()
        self._panel.select_item(item.id)

    def _on_edit(self, item_id: int, values: WantlistItemDetailsValues) -> None:
        try:
            self._service.update_item_details(item_id, values)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_delete(self, item_ids: list[int]) -> None:
        errors: list[str] = []
        for item_id in item_ids:
            try:
                self._service.remove_item(item_id)
            except ServiceError as exc:
                errors.append(str(exc))
        if errors:
            self._panel.show_error("\n".join(errors))
        self.refresh()

    def _on_convert_to_owned(self, item_id: int) -> None:
        """Turn a wantlist entry into an owned card once it's actually bought.

        Prompts for the target collection (there's no "current" collection
        to exclude, unlike ``MoveDialog``'s other uses), adds the card via
        the same manual-Cardmarket-link path used for cards without a
        catalogue match, and removes the wantlist entry only after that
        succeeds.
        """
        try:
            item = self._service.get_item(item_id)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        collections = self._collections.list_collections()
        if not collections:
            self._panel.show_error("There is no collection to add this card to yet.")
            return
        dialog = MoveDialog(collections, parent=self._panel)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        target_id = dialog.get_target_collection_id()
        values = CardDetailsValues(
            language=item.language,
            condition=item.condition,
            quantity=1,
            notes=item.notes,
            manual_cardmarket_url=item.cardmarket_url,
        )
        try:
            self._cards.add_card_manual(target_id, item.name, item.set_name, item.card_number, values)
            self._service.remove_item(item_id)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            return
        self.refresh()
        if self._on_converted is not None:
            # Lets MainWindow refresh the card tab too -- it owns a separate
            # CardController the new card doesn't otherwise show up in
            # (mirrors ImportController's own on_imported callback).
            self._on_converted()
