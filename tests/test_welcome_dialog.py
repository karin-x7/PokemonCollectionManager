"""Tests for WelcomeDialog and its "don't show again" persistence."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtWidgets import QLabel

from app import config
from app.ui.app import build_application
from app.ui.dialogs.welcome_dialog import WelcomeDialog, maybe_show_welcome_dialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def _welcome_flag_in_tmp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config, "WELCOME_DISMISSED_FLAG", tmp_path / "welcome_dismissed")


def test_accepting_without_the_checkbox_does_not_create_the_flag(qapp) -> None:
    dialog = WelcomeDialog()

    dialog.accept()

    assert not config.WELCOME_DISMISSED_FLAG.exists()


def test_accepting_with_the_checkbox_checked_creates_the_flag(qapp) -> None:
    dialog = WelcomeDialog()
    dialog._dont_show_again_check.setChecked(True)

    dialog.accept()

    assert config.WELCOME_DISMISSED_FLAG.exists()


def test_maybe_show_shows_the_dialog_when_flag_is_absent(qapp, monkeypatch) -> None:
    shown = []
    monkeypatch.setattr(WelcomeDialog, "exec", lambda self: shown.append(True))

    maybe_show_welcome_dialog()

    assert shown == [True]


def test_maybe_show_skips_the_dialog_when_flag_exists(qapp, monkeypatch) -> None:
    config.WELCOME_DISMISSED_FLAG.parent.mkdir(parents=True, exist_ok=True)
    config.WELCOME_DISMISSED_FLAG.touch()
    shown = []
    monkeypatch.setattr(WelcomeDialog, "exec", lambda self: shown.append(True))

    maybe_show_welcome_dialog()

    assert shown == []


def test_body_text_uses_a_bigger_font(qapp) -> None:
    dialog = WelcomeDialog()

    labels = [w for w in dialog.findChildren(QLabel) if w.objectName() != "PanelHeader"]

    assert labels
    assert all(label.font().pointSize() >= 15 for label in labels)
