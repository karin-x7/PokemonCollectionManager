"""Tests for SettingsDialog's info/help/FAQ tabs."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QLabel, QTabWidget, QTextBrowser

from app.ui.app import build_application
from app.ui.dialogs.settings_dialog import _FAQ_HTML, _HELP_HTML, _HELP_INDEX, SettingsDialog
from app.ui.theme import PALETTE


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def _tab_text(dialog: SettingsDialog, tab_label: str) -> str:
    """Return the plain text of the QTextBrowser inside the named tab page.

    Looking a QTextBrowser up from the dialog with a plain ``findChild``
    is ambiguous once more than one tab has one (Help and FAQ both do) --
    Qt's own child-traversal order does not match tab insertion order, so
    this looks the browser up scoped to its own tab's page widget instead.
    """
    tabs = dialog.findChild(QTabWidget)
    for i in range(tabs.count()):
        if tabs.tabText(i) == tab_label:
            browser = tabs.widget(i).findChild(QTextBrowser)
            assert browser is not None
            return browser.toPlainText()
    raise AssertionError(f"No tab named {tab_label!r}")


def test_has_faq_help_and_info_tabs_in_that_order(qapp) -> None:
    dialog = SettingsDialog()

    tabs = dialog.findChild(QTabWidget)

    assert tabs is not None
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["FAQ", "Help", "Info"]


def test_info_tab_credits_karin_with_no_link(qapp) -> None:
    dialog = SettingsDialog()

    labels = dialog.findChildren(QLabel)
    author_label = next((l for l in labels if "Karin" in l.text()), None)

    assert author_label is not None
    assert "<a " not in author_label.text()


def test_help_tab_mentions_the_asian_language_manual_entry_situation(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Japanese" in text
    assert "Korean" in text
    assert "Traditional Chinese" in text


def test_help_tab_mentions_multi_language_search_is_not_guaranteed(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "best-effort" in text
    assert "German" in text


def test_help_tab_mentions_manual_cardmarket_link_entry(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Cardmarket link" in text


def test_help_tab_mentions_manual_price_editing(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Edit price manually" in text


def test_help_tab_mentions_base_set_variants(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Shadowless" in text
    assert "Base Set" in text


def test_help_tab_mentions_collection_management(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "New collection" in text
    assert "Rename" in text


def test_help_tab_mentions_multi_select_and_sorting(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Shift-click" in text
    assert "sort" in text.lower()


def test_help_tab_mentions_moving_cards_between_collections(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Move" in text


def test_help_tab_mentions_duplicate_warning(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "already matches one you own" in text


def test_help_tab_mentions_fix_cardmarket_link(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Fix Cardmarket link" in text


def test_help_and_faq_use_the_translated_search_button_label_not_the_german_source(qapp) -> None:
    # "Cardmarket-Link suchen" is only the internal, German tr() source
    # string for the detail-panel button -- the label actually shown to the
    # user is its English translation, "Search Cardmarket link" (see
    # app/i18n.py). Live-reported: an earlier draft of this text used the
    # raw German source string instead of what the button really says.
    for tab in ("Help", "FAQ"):
        text = _tab_text(SettingsDialog(), tab)
        assert "suchen" not in text
        assert "Search Cardmarket link" in text


def test_help_tab_mentions_wantlist_add_to_collection(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Add to collection" in text


def test_help_tab_mentions_statistics_breakdowns(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "Most expensive" in text
    assert "biggest jump" in text.lower()


def test_help_tab_mentions_export_scope(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "All collections" in text


def test_help_tab_mentions_backup_restore_mechanics(qapp) -> None:
    text = _tab_text(SettingsDialog(), "Help")

    assert "restarted" in text.lower()


def test_faq_tab_mentions_why_not_automatic(qapp) -> None:
    text = _tab_text(SettingsDialog(), "FAQ")

    assert "automatically" in text.lower()
    assert "no public API" in text


def test_faq_tab_mentions_asian_language_cards(qapp) -> None:
    text = _tab_text(SettingsDialog(), "FAQ")

    assert "Japanese" in text
    assert "Korean" in text


def test_faq_tab_mentions_windows_only(qapp) -> None:
    text = _tab_text(SettingsDialog(), "FAQ")

    assert "Windows-only" in text


def test_help_dialog_is_sized_generously(qapp) -> None:
    dialog = SettingsDialog()

    assert dialog.size().width() >= 800
    assert dialog.size().height() >= 600


def test_help_and_faq_browsers_use_a_bigger_font(qapp) -> None:
    dialog = SettingsDialog()

    assert dialog._help_browser.font().pointSize() >= 15
    assert dialog._faq_browser.font().pointSize() >= 15


def test_help_and_faq_links_use_the_app_accent_color_not_the_os_default(qapp) -> None:
    dialog = SettingsDialog()

    for browser in (dialog._help_browser, dialog._faq_browser):
        assert PALETTE.accent in browser.document().defaultStyleSheet()


def test_help_index_contains_every_section_as_a_working_anchor(qapp) -> None:
    for _category, entries in _HELP_INDEX:
        for anchor, _label in entries:
            assert f'href="#{anchor}"' in _HELP_HTML
            assert f'name="{anchor}"' in _HELP_HTML


def test_clicking_a_help_index_link_scrolls_to_its_own_anchor(qapp) -> None:
    dialog = SettingsDialog()
    scrolled = []
    dialog._help_browser.scrollToAnchor = scrolled.append

    dialog._on_anchor_clicked(dialog._help_browser, QUrl("#cards-fix-link"))

    assert scrolled == ["cards-fix-link"]


def test_clicking_a_faq_cross_link_switches_to_help_and_scrolls(qapp) -> None:
    dialog = SettingsDialog()
    scrolled = []
    dialog._help_browser.scrollToAnchor = scrolled.append
    dialog._tabs.setCurrentIndex(0)  # FAQ

    dialog._on_anchor_clicked(dialog._faq_browser, QUrl("help:#cards-search-accuracy"))

    assert dialog._tabs.currentIndex() == dialog._help_tab_index
    assert scrolled == ["cards-search-accuracy"]


def test_faq_tab_links_to_relevant_help_sections(qapp) -> None:
    assert 'href="help:#cards-fix-link"' in _FAQ_HTML
    assert 'href="help:#cards-search-accuracy"' in _FAQ_HTML
    assert 'href="help:#general-backups"' in _FAQ_HTML
