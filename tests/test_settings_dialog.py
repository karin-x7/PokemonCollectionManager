"""Tests for SettingsDialog's info/help tabs."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QLabel, QTabWidget, QTextBrowser

from app.ui.app import build_application
from app.ui.dialogs.settings_dialog import SettingsDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_has_an_info_and_a_help_tab(qapp) -> None:
    dialog = SettingsDialog()

    tabs = dialog.findChild(QTabWidget)

    assert tabs is not None
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Info", "Help"]


def test_info_tab_credits_the_author_with_a_github_link(qapp) -> None:
    dialog = SettingsDialog()

    labels = dialog.findChildren(QLabel)
    author_label = next((l for l in labels if "Codeon" in l.text()), None)

    assert author_label is not None
    assert "github.com/codeonexe" in author_label.text()


def test_help_tab_mentions_the_asian_language_manual_entry_situation(qapp) -> None:
    dialog = SettingsDialog()

    browser = dialog.findChild(QTextBrowser)

    assert browser is not None
    text = browser.toPlainText()
    assert "Japanese" in text
    assert "Korean" in text
    assert "Traditional Chinese" in text


def test_help_tab_mentions_manual_cardmarket_link_entry(qapp) -> None:
    dialog = SettingsDialog()

    browser = dialog.findChild(QTextBrowser)

    assert "Cardmarket link" in browser.toPlainText()


def test_help_tab_mentions_manual_price_editing(qapp) -> None:
    dialog = SettingsDialog()

    browser = dialog.findChild(QTextBrowser)

    assert "Edit price manually" in browser.toPlainText()


def test_help_tab_mentions_base_set_variants(qapp) -> None:
    dialog = SettingsDialog()

    browser = dialog.findChild(QTextBrowser)

    text = browser.toPlainText()
    assert "Shadowless" in text
    assert "Base Set" in text
