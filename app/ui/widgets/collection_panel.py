"""Left panel: the list of collections.

Presentation-only: this widget knows nothing about the database or business
rules. It renders whatever :class:`~app.models.collection.Collection` list it
is given, lets the user interact (select, create, rename, delete, reorder via
drag & drop), and turns those interactions into signals. A controller
(:class:`app.ui.controllers.collection_controller.CollectionController`)
listens to the signals, calls the service layer, and feeds the result back
via :meth:`set_collections` / :meth:`show_error`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.collection import Collection

_ID_ROLE = Qt.ItemDataRole.UserRole


class CollectionPanel(QWidget):
    """Sidebar listing the user's collections."""

    #: Emitted whenever the selected collection changes; -1 means "none".
    selection_changed = Signal(int)
    #: Emitted with the trimmed name once the user confirms the "new" dialog.
    create_requested = Signal(str)
    #: Emitted with (collection_id, new_name) once the user confirms a rename.
    rename_requested = Signal(int, str)
    #: Emitted with collection_id once the user confirms deletion.
    delete_requested = Signal(int)
    #: Emitted with the new ordered list of collection ids after a drag-reorder.
    reorder_requested = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Sammlungen")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.currentItemChanged.connect(self._on_current_item_changed)
        self._list.itemDoubleClicked.connect(lambda item: self._prompt_rename(item))
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self._list, stretch=1)

        add_button = QPushButton("+ Neue Sammlung")
        add_button.clicked.connect(self._prompt_create)
        layout.addWidget(add_button)

    # -- Public API (called by the controller) ----------------------------- #

    def set_collections(self, collections: list[Collection]) -> None:
        """Replace the displayed list, preserving the selection if possible."""
        previous_id = self.selected_collection_id()

        self._list.blockSignals(True)
        self._list.clear()
        for collection in collections:
            item = QListWidgetItem(collection.name)
            item.setData(_ID_ROLE, collection.id)
            self._list.addItem(item)
        self._list.blockSignals(False)

        self._restore_selection(previous_id)

    def selected_collection_id(self) -> int | None:
        """The currently selected collection's id, or ``None``."""
        item = self._list.currentItem()
        return item.data(_ID_ROLE) if item is not None else None

    def select_collection(self, collection_id: int | None) -> None:
        """Programmatically select a collection by id (no-op if not found)."""
        self._restore_selection(collection_id)

    def show_error(self, message: str) -> None:
        """Display a friendly error message to the user."""
        QMessageBox.warning(self, "Sammlungen", message)

    # -- Internals ---------------------------------------------------------- #

    def _restore_selection(self, collection_id: int | None) -> None:
        if collection_id is None:
            return
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(_ID_ROLE) == collection_id:
                self._list.setCurrentItem(item)
                return

    def _on_current_item_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        collection_id = current.data(_ID_ROLE) if current is not None else -1
        self.selection_changed.emit(collection_id if collection_id is not None else -1)

    def _prompt_create(self) -> None:
        name, ok = QInputDialog.getText(self, "Neue Sammlung", "Name der Sammlung:")
        if ok and name.strip():
            self.create_requested.emit(name.strip())

    def _prompt_rename(self, item: QListWidgetItem) -> None:
        collection_id = item.data(_ID_ROLE)
        new_name, ok = QInputDialog.getText(
            self, "Sammlung umbenennen", "Neuer Name:", text=item.text()
        )
        if ok and new_name.strip() and new_name.strip() != item.text():
            self.rename_requested.emit(collection_id, new_name.strip())

    def _prompt_delete(self, item: QListWidgetItem) -> None:
        collection_id = item.data(_ID_ROLE)
        answer = QMessageBox.question(
            self,
            "Sammlung löschen",
            f"Soll die Sammlung „{item.text()}“ wirklich gelöscht werden?\n"
            "Alle enthaltenen Karten werden dabei ebenfalls gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(collection_id)

    def _show_context_menu(self, position) -> None:
        item = self._list.itemAt(position)
        if item is None:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Umbenennen")
        delete_action = menu.addAction("Löschen")
        chosen = menu.exec(self._list.viewport().mapToGlobal(position))
        if chosen is rename_action:
            self._prompt_rename(item)
        elif chosen is delete_action:
            self._prompt_delete(item)

    def _on_rows_moved(self, *_args) -> None:
        ordered_ids = [
            self._list.item(row).data(_ID_ROLE) for row in range(self._list.count())
        ]
        self.reorder_requested.emit(ordered_ids)
