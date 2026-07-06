"""Wires the "Infos und Einstellungen" toolbar action to SettingsDialog.

The dialog is purely informational now (app info/credits + a help/tutorial
tab) -- there used to be a UI language setting here too, but the app is
English-only now, so there's nothing left to persist.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.ui.dialogs.settings_dialog import SettingsDialog


class SettingsController(QObject):
    """Starts the "Infos und Einstellungen" flow."""

    def __init__(
        self,
        main_window: QMainWindow,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window

    def start(self) -> None:
        dialog = SettingsDialog(parent=self._main_window)
        dialog.exec()
