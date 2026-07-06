"""Tests for DimmedDialog's parent-window dim overlay."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QMainWindow

from app.ui.app import build_application
from app.ui.dialogs.dimmed_dialog import DimmedDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def window(qapp) -> QMainWindow:
    win = QMainWindow()
    win.resize(400, 300)
    win.show()
    yield win
    win.close()


def test_shows_a_dim_overlay_on_the_parent_window(window: QMainWindow) -> None:
    dialog = DimmedDialog(parent=window)

    dialog.show()

    assert dialog._dim_overlay is not None
    assert dialog._dim_overlay.parent() is window


def test_removes_the_overlay_on_close(window: QMainWindow) -> None:
    dialog = DimmedDialog(parent=window)
    dialog.show()

    dialog.close()

    assert dialog._dim_overlay is None


def test_does_not_crash_without_a_parent(qapp) -> None:
    dialog = DimmedDialog(parent=None)

    dialog.show()

    assert dialog._dim_overlay is None
    dialog.close()


def test_reshowing_does_not_stack_multiple_overlays(window: QMainWindow) -> None:
    dialog = DimmedDialog(parent=window)
    dialog.show()
    first_overlay = dialog._dim_overlay

    dialog.show()

    assert dialog._dim_overlay is first_overlay
