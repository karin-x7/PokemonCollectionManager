"""Modal dialog listing existing database backups, selectable to restore.

Presentation-only: displays whatever :class:`~app.database.backup.BackupInfo`
list it is given. The actual confirmation prompt ("this overwrites your
current collection") and the restore itself live in
:class:`~app.ui.controllers.backup_controller.BackupController`, not here --
mirrors :class:`~app.ui.dialogs.catalog_search_results_dialog.
CatalogSearchResultsDialog`'s split between "pick a row" and "act on it".
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.database.backup import BackupInfo
from app.ui.dialogs.dimmed_dialog import DimmedDialog

_COLUMNS = ["Created", "Size"]
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


def _format_size(size_bytes: int) -> str:
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.1f} MB" if size_mb >= 0.1 else f"{size_bytes} B"


class BackupRestoreDialog(DimmedDialog):
    """Read-only list of database backups, selectable to restore."""

    #: Emitted with the selected BackupInfo when "Restore" is clicked --
    #: the dialog itself does not overwrite anything or ask for
    #: confirmation, see module docstring.
    restore_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Restore from backup")
        self.resize(480, 360)
        self._backups: list[BackupInfo] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        self._empty_label = QLabel("No backups found yet.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._update_restore_button_enabled)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        self._restore_button = buttons.addButton(
            "Restore", QDialogButtonBox.ButtonRole.ActionRole
        )
        self._restore_button.clicked.connect(self._on_restore_clicked)
        layout.addWidget(buttons)

        self.set_backups([])

    def set_backups(self, backups: list[BackupInfo]) -> None:
        self._backups = backups
        self._empty_label.setVisible(not backups)
        self._table.setVisible(bool(backups))
        self._table.setRowCount(len(backups))
        for row, backup in enumerate(backups):
            created = QTableWidgetItem(backup.created_at.strftime(_TIMESTAMP_FORMAT))
            size = QTableWidgetItem(_format_size(backup.size_bytes))
            size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, created)
            self._table.setItem(row, 1, size)
        self._update_restore_button_enabled()

    def _update_restore_button_enabled(self) -> None:
        self._restore_button.setEnabled(self._table.currentRow() >= 0)

    def _on_restore_clicked(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._backups):
            return
        self.restore_requested.emit(self._backups[row])
