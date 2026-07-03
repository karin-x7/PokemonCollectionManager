"""Connects :class:`CollectionPanel` to :class:`CollectionService`.

Every panel signal is handled here: the service call is made, the panel is
refreshed from the (now authoritative) database state, and any
:class:`~app.services.exceptions.ServiceError` is surfaced as a friendly
message box instead of propagating as an exception.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtCore import QObject

from app.logging_config import get_logger
from app.services.collection_service import CollectionService
from app.services.exceptions import ServiceError
from app.ui.widgets.collection_panel import CollectionPanel

logger = get_logger(__name__)


class CollectionController(QObject):
    """Wires a :class:`CollectionPanel` to a :class:`CollectionService`."""

    #: Re-emitted from the panel so the rest of the app can react without
    #: depending on the panel directly.
    selection_changed = Signal(int)

    def __init__(
        self,
        panel: CollectionPanel,
        service: CollectionService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._service = service

        panel.create_requested.connect(self._on_create)
        panel.rename_requested.connect(self._on_rename)
        panel.delete_requested.connect(self._on_delete)
        panel.reorder_requested.connect(self._on_reorder)
        panel.selection_changed.connect(self.selection_changed)

        self.refresh()

    def refresh(self) -> None:
        """Reload the collection list from the database into the panel."""
        self._panel.set_collections(self._service.list_collections())

    def _on_create(self, name: str) -> None:
        try:
            created = self._service.create_collection(name)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
            self.refresh()
            return
        # A freshly created collection becomes the selected one so the user
        # can act on it immediately (e.g. rename it, or later add cards).
        self.refresh()
        self._panel.select_collection(created.id)

    def _on_rename(self, collection_id: int, new_name: str) -> None:
        try:
            self._service.rename_collection(collection_id, new_name)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_delete(self, collection_id: int) -> None:
        try:
            self._service.delete_collection(collection_id)
        except ServiceError as exc:
            self._panel.show_error(str(exc))
        self.refresh()

    def _on_reorder(self, ordered_ids: list[int]) -> None:
        try:
            self._service.reorder_collections(ordered_ids)
        except ServiceError as exc:
            logger.error("Reorder failed: %s", exc)
            self._panel.show_error(str(exc))
            self.refresh()
