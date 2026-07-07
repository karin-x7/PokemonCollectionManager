"""Wires the "Infos und Einstellungen" toolbar action to SettingsDialog.

The dialog is otherwise purely informational (app info/credits + a
help/tutorial tab) -- there used to be a UI language setting here too, but
the app is English-only now, so there's nothing left to persist. The one
exception is the "Restore from backup" button, wired here to
:class:`~app.ui.controllers.backup_controller.BackupController` on every
open, since a new dialog instance is created each time.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.ui.controllers.backup_controller import BackupController
from app.ui.dialogs.settings_dialog import SettingsDialog


class SettingsController(QObject):
    """Starts the "Infos und Einstellungen" flow."""

    def __init__(
        self,
        main_window: QMainWindow,
        backup_controller: BackupController,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._backup_controller = backup_controller

    def start(self) -> None:
        dialog = SettingsDialog(parent=self._main_window)
        dialog.restore_backup_requested.connect(self._backup_controller.start)
        dialog.exec()
