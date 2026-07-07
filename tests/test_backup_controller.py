"""Tests for BackupController: dialog selection -> confirm -> restore_backup().

QMessageBox.question/information are monkeypatched so no real modal appears
-- mirrors test_export_controller.py's approach to QMessageBox.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QMessageBox

from app.database.backup import BackupInfo
from app.ui.app import build_application
from app.ui.controllers.backup_controller import BackupController
from app.ui.dialogs.backup_restore_dialog import BackupRestoreDialog
from app.ui.main_window import MainWindow

_BACKUP = BackupInfo(path=Path("/tmp/collection_20260101_000000.db"), created_at=datetime(2026, 1, 1), size_bytes=1024)


class FakeDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class FakeSignal:
    def connect(self, slot) -> None:
        self._slot = slot


class FakeRestoreDialog:
    instances: list["FakeRestoreDialog"] = []

    def __init__(self, parent=None) -> None:
        self.backups_set: list[BackupInfo] | None = None
        self.restore_requested = FakeSignal()
        self.exec_calls = 0
        self.accept_calls = 0
        FakeRestoreDialog.instances.append(self)

    def set_backups(self, backups: list[BackupInfo]) -> None:
        self.backups_set = backups

    def exec(self) -> int:
        self.exec_calls += 1
        return 0

    def accept(self) -> None:
        self.accept_calls += 1


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def main_window(qapp) -> MainWindow:
    window = MainWindow()
    yield window
    window.close()


@pytest.fixture(autouse=True)
def _reset_fake_dialog():
    FakeRestoreDialog.instances.clear()
    yield


def test_start_populates_the_dialog_with_existing_backups(
    monkeypatch, main_window: MainWindow, tmp_path
) -> None:
    monkeypatch.setattr(
        "app.ui.controllers.backup_controller.BackupRestoreDialog", FakeRestoreDialog
    )
    monkeypatch.setattr(
        "app.ui.controllers.backup_controller.list_backups", lambda db_path: [_BACKUP]
    )
    database = FakeDatabase(tmp_path / "collection.db")
    controller = BackupController(main_window, database)

    controller.start()

    assert len(FakeRestoreDialog.instances) == 1
    assert FakeRestoreDialog.instances[0].backups_set == [_BACKUP]
    assert FakeRestoreDialog.instances[0].exec_calls == 1


def test_confirmed_restore_closes_database_and_calls_restore_backup(
    monkeypatch, main_window: MainWindow, tmp_path
) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", MagicMock())
    restore_calls = []
    monkeypatch.setattr(
        "app.ui.controllers.backup_controller.restore_backup",
        lambda backup_path, db_path: restore_calls.append((backup_path, db_path)),
    )
    database = FakeDatabase(tmp_path / "collection.db")
    controller = BackupController(main_window, database)
    dialog = FakeRestoreDialog()

    controller._on_restore_requested(dialog, _BACKUP)

    assert database.close_calls == 1
    assert restore_calls == [(_BACKUP.path, database.path)]
    assert dialog.accept_calls == 1


def test_declined_confirmation_does_not_restore(monkeypatch, main_window: MainWindow, tmp_path) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.No)
    restore_calls = []
    monkeypatch.setattr(
        "app.ui.controllers.backup_controller.restore_backup",
        lambda backup_path, db_path: restore_calls.append((backup_path, db_path)),
    )
    database = FakeDatabase(tmp_path / "collection.db")
    controller = BackupController(main_window, database)
    dialog = FakeRestoreDialog()

    controller._on_restore_requested(dialog, _BACKUP)

    assert database.close_calls == 0
    assert restore_calls == []
    assert dialog.accept_calls == 0


def test_failed_restore_shows_a_warning_instead_of_closing_the_window(
    monkeypatch, main_window: MainWindow, tmp_path
) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)
    warning = MagicMock()
    monkeypatch.setattr(QMessageBox, "warning", warning)

    def _raise(backup_path, db_path):
        raise OSError("disk full")

    monkeypatch.setattr("app.ui.controllers.backup_controller.restore_backup", _raise)
    database = FakeDatabase(tmp_path / "collection.db")
    controller = BackupController(main_window, database)
    dialog = FakeRestoreDialog()

    controller._on_restore_requested(dialog, _BACKUP)  # must not raise

    warning.assert_called_once()
    assert dialog.accept_calls == 0
