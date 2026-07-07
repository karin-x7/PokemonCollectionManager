"""Headless smoke tests for the GUI shell.

These run under Qt's ``offscreen`` platform so they need no display and work in
CI. They verify the window constructs, exposes the expected structure, and
that the toolbar intents behave — without asserting pixels.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QAction

from app import config
from app.ui.app import build_application
from app.ui.main_window import MainWindow
from app.ui.theme import build_stylesheet


@pytest.fixture(scope="module")
def qapp():
    """A single QApplication shared by the UI tests."""
    return build_application([])


def test_stylesheet_is_non_empty() -> None:
    assert build_stylesheet().strip()


def test_main_window_has_three_panels(qapp) -> None:
    window = MainWindow()
    assert config.APP_NAME in window.windowTitle()
    assert window.collection_panel is not None
    assert window.card_list_panel is not None
    assert window.card_detail_panel is not None


def test_main_window_has_price_history_dock(qapp) -> None:
    window = MainWindow()
    assert window.price_history_dock is not None
    assert window.price_history_dock.isHidden()


def test_toolbar_exposes_core_actions(qapp) -> None:
    window = MainWindow()
    texts = [a.text() for a in window.findChildren(QAction)]
    assert any("Add card manually" in t for t in texts)
    assert any("Export" in t for t in texts)
    assert any("Info and help" in t for t in texts)


def test_toolbar_actions_have_no_icons(qapp) -> None:
    # Plain text buttons throughout, matching the Karten/Statistik nav
    # actions -- no standard-icon pair mismatched against them.
    window = MainWindow()
    for action in (window._act_manual_entry, window._act_export, window._act_settings):
        assert action.icon().isNull()


def test_tab_bar_is_hidden_navigation_is_toolbar_only(qapp) -> None:
    window = MainWindow()
    assert window.centralWidget().tabBar().isHidden()


def test_toolbar_nav_switches_central_tab(qapp) -> None:
    window = MainWindow()
    tabs = window.centralWidget()
    assert tabs.currentIndex() == 0
    assert window._act_tab_cards.isChecked()

    window._act_tab_sealed.trigger()

    assert tabs.currentIndex() == 1
    assert window._act_tab_sealed.isChecked()
    assert not window._act_tab_cards.isChecked()

    window._act_tab_stats.trigger()

    assert tabs.currentIndex() == 3
    assert window._act_tab_stats.isChecked()
    assert not window._act_tab_sealed.isChecked()

    window._act_tab_cards.trigger()

    assert tabs.currentIndex() == 0
    assert window._act_tab_cards.isChecked()


def test_toolbar_nav_to_statistics_refreshes_it(qapp) -> None:
    window = MainWindow()
    calls: list[bool] = []
    window.statistics_controller.refresh = lambda: calls.append(True)

    window._act_tab_stats.trigger()

    assert calls == [True]


def test_search_bar_hidden_outside_of_cards_tab(qapp) -> None:
    window = MainWindow()
    window.show()
    assert not window._search.isHidden()
    assert not window._search_button.isHidden()
    assert window._act_manual_entry.isVisible()
    assert not window._manual_entry_button.isHidden()
    assert window._sealed_add_button.isHidden()

    window._act_tab_sealed.trigger()

    assert window._search.isHidden()
    assert window._search_button.isHidden()
    assert not window._act_manual_entry.isVisible()
    assert window._manual_entry_button.isHidden()
    assert not window._sealed_add_button.isHidden()

    window._act_tab_cards.trigger()

    assert not window._search.isHidden()
    assert not window._search_button.isHidden()
    assert window._act_manual_entry.isVisible()
    assert not window._manual_entry_button.isHidden()
    assert window._sealed_add_button.isHidden()


def test_sealed_add_button_emits_signal(qapp) -> None:
    window = MainWindow()
    # Disconnect the real controller first: it would otherwise pop a real,
    # blocking ManualEntryDialog.exec() in response to the signal this test
    # triggers below (same pitfall as the search button test above).
    window.sealed_add_requested.disconnect(window.sealed_entry_controller.start)
    received: list[bool] = []
    window.sealed_add_requested.connect(lambda: received.append(True))
    window._sealed_add_button.click()
    assert received == [True]


def test_search_button_and_manual_entry_button_do_not_grow(qapp) -> None:
    # QPushButton/QToolButton must stay pinned to their own sizeHint --
    # regression test for the "Suchen" button silently expanding to fill
    # whatever leftover width the toolbar had (see main_window.py).
    window = MainWindow()
    window.show()
    assert window._search_button.width() <= window._search_button.sizeHint().width() + 2
    assert (
        window._manual_entry_button.width()
        <= window._manual_entry_button.sizeHint().width() + 2
    )


def test_search_button_submits_same_as_enter(qapp) -> None:
    window = MainWindow()
    # Disconnect the real catalog controller first: it would otherwise make
    # a real, blocking pokemontcg.io network call in response to the signal
    # this test triggers below.
    window.search_submitted.disconnect(window.catalog_search_controller.handle_search)
    received: list[str] = []
    window.search_submitted.connect(received.append)

    window._search.setText("xatu")
    window._search_button.click()

    assert received == ["xatu"]


def test_manual_entry_action_emits_signal(qapp) -> None:
    window = MainWindow()
    # Disconnect the real controller first: it would otherwise pop a real,
    # blocking ManualEntryDialog.exec() in response to the signal this test
    # triggers below (same pitfall as the search button test above).
    window.manual_entry_requested.disconnect(window.manual_entry_controller.start)
    received: list[bool] = []
    window.manual_entry_requested.connect(lambda: received.append(True))
    window._act_manual_entry.trigger()
    assert received == [True]


def test_settings_action_emits_signal(qapp) -> None:
    window = MainWindow()
    # Disconnect the real controller first: it would otherwise pop a real,
    # blocking SettingsDialog.exec() in response to the signal this test
    # triggers below (same pitfall as the search button test above).
    window.settings_requested.disconnect(window.settings_controller.start)
    received: list[bool] = []
    window.settings_requested.connect(lambda: received.append(True))
    window._act_settings.trigger()
    assert received == [True]


def test_history_button_toggles_dock_and_window_width(qapp) -> None:
    window = MainWindow()
    # QDockWidget.visibilityChanged only fires once the top-level window is
    # actually shown (even under the offscreen platform) -- without this,
    # the dock's own show()/hide() calls never reach CardDetailPanel's
    # button-label sync below.
    window.show()
    width_before = window.width()

    window.card_detail_panel.history_panel_requested.emit(1)
    assert not window.price_history_dock.isHidden()
    assert window.width() == width_before + 380
    assert window.card_detail_panel._history_button.text() == "Hide price history"

    window.card_detail_panel.history_panel_requested.emit(1)
    assert window.price_history_dock.isHidden()
    assert window.width() == width_before
    assert window.card_detail_panel._history_button.text() == "Show price history"
