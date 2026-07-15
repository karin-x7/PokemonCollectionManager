"""Tests for SettingsController: ``start()`` opens the FAQ/Help/Info dialog,

``wire_settings_panel()`` wires the permanent Settings tab's "Only sellers
from Germany" checkbox to persisted preferences. The dialog is monkeypatched
so this runs headlessly/deterministically, without a real modal ever
appearing -- mirrors ``test_export_controller.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.ui.app import build_application
from app.ui.controllers.settings_controller import SettingsController
from app.ui.main_window import MainWindow
from app.ui.widgets.settings_panel import SettingsPanel


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


class FakeSettingsRepository:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._values.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._values[key] = value


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
    controller = SettingsController(main_window, FakeBackupController(), FakeSettingsRepository())

    controller.start()

    assert len(FakeDialog.instances) == 1
    assert FakeDialog.instances[0].exec_calls == 1


def test_wire_settings_panel_reflects_a_previously_saved_preference(qapp) -> None:
    settings = FakeSettingsRepository()
    settings.set("seller_location_germany_only", "1")
    controller = SettingsController.__new__(SettingsController)
    controller._settings = settings
    panel = SettingsPanel()

    controller.wire_settings_panel(panel)

    assert panel._germany_only_checkbox.isChecked() is True


def test_toggling_the_panel_checkbox_persists_the_preference(qapp) -> None:
    settings = FakeSettingsRepository()
    controller = SettingsController.__new__(SettingsController)
    controller._settings = settings
    panel = SettingsPanel()
    controller.wire_settings_panel(panel)

    panel._germany_only_checkbox.setChecked(True)

    assert settings.get("seller_location_germany_only") == "1"
