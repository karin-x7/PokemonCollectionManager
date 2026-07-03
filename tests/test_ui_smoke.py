"""Headless smoke tests for the GUI shell.

These run under Qt's ``offscreen`` platform so they need no display and work in
CI. They verify the window constructs, exposes the expected structure, and that
the toolbar intents and theme toggle behave — without asserting pixels.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QAction

from app import config
from app.ui.app import build_application
from app.ui.main_window import MainWindow
from app.ui.theme import Theme, build_stylesheet


@pytest.fixture(scope="module")
def qapp():
    """A single QApplication shared by the UI tests."""
    return build_application([])


def test_stylesheets_differ_between_themes() -> None:
    assert build_stylesheet(Theme.LIGHT) != build_stylesheet(Theme.DARK)


def test_theme_toggled_is_opposite() -> None:
    assert Theme.LIGHT.toggled() is Theme.DARK
    assert Theme.DARK.toggled() is Theme.LIGHT


def test_main_window_has_three_panels(qapp) -> None:
    window = MainWindow()
    assert config.APP_NAME in window.windowTitle()
    assert window.collection_panel is not None
    assert window.card_list_panel is not None
    assert window.card_detail_panel is not None


def test_toolbar_exposes_core_actions(qapp) -> None:
    window = MainWindow()
    texts = [a.text() for a in window.findChildren(QAction)]
    assert any("Scanner" in t for t in texts)
    assert any("aktualisieren" in t for t in texts)
    assert any("Export" in t for t in texts)


def test_update_prices_action_emits_signal(qapp) -> None:
    window = MainWindow()
    received: list[bool] = []
    window.update_prices_requested.connect(lambda: received.append(True))
    window._act_update.trigger()
    assert received == [True]


def test_theme_toggle_changes_action_label(qapp) -> None:
    window = MainWindow(theme=Theme.LIGHT)
    before = window._act_theme.text()
    window.toggle_theme()
    assert window._act_theme.text() != before
