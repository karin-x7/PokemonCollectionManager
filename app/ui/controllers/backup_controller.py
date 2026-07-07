"""Wires the "Restore from backup" button to BackupRestoreDialog + the restore itself.

Restoring replaces the live database file on disk, which the running
:class:`~app.database.connection.Database` connection (and every
repository/service built on top of it throughout the app) has no way to
pick up without rebuilding the entire object graph -- so this deliberately
asks the user to restart the app afterwards rather than attempting an
in-place reconnect.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMainWindow, QMessageBox

from app.database.backup import BackupInfo, list_backups, restore_backup
from app.database.connection import Database
from app.logging_config import get_logger
from app.ui.dialogs.backup_restore_dialog import BackupRestoreDialog

logger = get_logger(__name__)


class BackupController(QObject):
    """Starts the "Restore from backup" flow."""

    def __init__(
        self,
        main_window: QMainWindow,
        database: Database,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._database = database

    def start(self) -> None:
        dialog = BackupRestoreDialog(parent=self._main_window)
        dialog.set_backups(list_backups(self._database.path))
        dialog.restore_requested.connect(
            lambda backup: self._on_restore_requested(dialog, backup)
        )
        dialog.exec()

    def _on_restore_requested(self, dialog: BackupRestoreDialog, backup: BackupInfo) -> None:
        confirmed = QMessageBox.question(
            dialog,
            "Restore from backup",
            (
                f"This replaces your current collection with the backup from "
                f"{backup.created_at:%Y-%m-%d %H:%M}. Your current data is backed "
                "up first, but the app must be restarted afterwards to see the "
                "restored collection.\n\nContinue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        db_path = self._database.path
        self._database.close()
        try:
            restore_backup(backup.path, db_path)
        except OSError as exc:
            logger.exception("Restoring backup %s failed", backup.path)
            QMessageBox.warning(
                dialog, "Restore failed", f"The backup could not be restored:\n{exc}"
            )
            return

        dialog.accept()
        QMessageBox.information(
            self._main_window,
            "Restore complete",
            "The backup was restored. The app will now close -- start it again to "
            "see the restored collection.",
        )
        self._main_window.close()
