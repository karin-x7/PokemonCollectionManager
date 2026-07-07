"""Tests for MainWindow's update-check wiring: worker result -> status bar hint.

``UpdateCheckWorker.start`` is monkeypatched to run synchronously (mirrors
``test_price_controller.py``) -- deterministic, no real network/thread involved.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.services.update_check_service import UpdateInfo
from app.ui.app import build_application
from app.ui.main_window import MainWindow
from app.ui.workers.update_check_worker import UpdateCheckWorker


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()

    monkeypatch.setattr(UpdateCheckWorker, "start", fake_start)


@pytest.fixture
def main_window(qapp) -> MainWindow:
    window = MainWindow()
    yield window
    window.close()


def test_no_update_leaves_the_status_bar_hint_empty(monkeypatch, main_window: MainWindow) -> None:
    monkeypatch.setattr(
        "app.ui.workers.update_check_worker.check_for_update", lambda current_version: None
    )

    main_window.start_update_check()

    assert main_window._update_hint_label.text() == ""


def test_available_update_shows_a_clickable_hint(monkeypatch, main_window: MainWindow) -> None:
    monkeypatch.setattr(
        "app.ui.workers.update_check_worker.check_for_update",
        lambda current_version: UpdateInfo(version="9.9.9", url="https://example.com/release"),
    )

    main_window.start_update_check()

    label_text = main_window._update_hint_label.text()
    assert "9.9.9" in label_text
    assert "https://example.com/release" in label_text
