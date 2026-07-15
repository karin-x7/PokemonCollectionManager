"""Wires the "Info and help" toolbar action to SettingsDialog, and the

always-visible "Settings" tab (:class:`~app.ui.widgets.settings_panel.
SettingsPanel`) to persisted preferences.

SettingsDialog (FAQ/Help/Info) is otherwise purely informational -- there
used to be a UI language setting here too, but the app is English-only now.
The "Restore from backup" button is wired here to
:class:`~app.ui.controllers.backup_controller.BackupController` on every
open, since a new dialog instance is created each time.

The "Only sellers from Germany" checkbox lives on the permanent Settings tab
instead (unlike the dialog, built once at startup, not re-created on every
open), so its initial state and persistence are wired once via
:meth:`wire_settings_panel`, not inside :meth:`start`.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow

from app.database.repositories.settings_repository import SettingsRepository
from app.pricing.seller_location import is_germany_only_enabled, set_germany_only_enabled
from app.ui.controllers.backup_controller import BackupController
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.widgets.settings_panel import SettingsPanel


class SettingsController(QObject):
    """Starts the "Info and help" flow; wires the permanent Settings tab."""

    def __init__(
        self,
        main_window: QMainWindow,
        backup_controller: BackupController,
        settings_repository: SettingsRepository,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._backup_controller = backup_controller
        self._settings = settings_repository

    def start(self) -> None:
        dialog = SettingsDialog(parent=self._main_window)
        dialog.restore_backup_requested.connect(self._backup_controller.start)
        dialog.exec()

    def wire_settings_panel(self, panel: SettingsPanel) -> None:
        """Called once at startup -- unlike ``start()``'s dialog, the

        Settings tab is a permanent widget, so its initial state is set
        once here rather than every time it becomes visible.
        """
        panel.set_germany_only(is_germany_only_enabled(self._settings))
        panel.germany_only_changed.connect(self._on_germany_only_changed)

    def _on_germany_only_changed(self, enabled: bool) -> None:
        set_germany_only_enabled(self._settings, enabled)
