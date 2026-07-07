"""Tests for SettingsController: opens SettingsDialog, nothing to persist.

The dialog is monkeypatched so this runs headlessly/deterministically,
without a real modal ever appearing -- mirrors ``test_export_controller.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.ui.app import build_application
from app.ui.controllers.settings_controller import SettingsController
from app.ui.main_window import MainWindow


class FakeSignal:
    def connect(self, slot) -> None:
        pass


class FakeDialog:
    instances: list["FakeDialog"] = []

    def __init__(self, parent=None) -> None:
        self.exec_calls = 0
        self.restore_backup_requested = FakeSignal()
        FakeDialog.instances.append(self)

    def exec(self) -> int:
        self.exec_calls += 1
        return 0


class FakeBackupController:
    def start(self) -> None:
        pass


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
    FakeDialog.instances.clear()
    yield


def test_start_opens_the_settings_dialog(monkeypatch, main_window: MainWindow) -> None:
    monkeypatch.setattr("app.ui.controllers.settings_controller.SettingsDialog", FakeDialog)
    controller = SettingsController(main_window, FakeBackupController())

    controller.start()

    assert len(FakeDialog.instances) == 1
    assert FakeDialog.instances[0].exec_calls == 1
