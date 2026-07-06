"""Tests for ManualPriceDialog's price entry."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.ui.app import build_application
from app.ui.dialogs.manual_price_dialog import ManualPriceDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_prefills_the_current_price(qapp) -> None:
    dialog = ManualPriceDialog(current_price=42.5)

    assert dialog.get_price() == 42.5


def test_defaults_to_a_minimal_positive_price_when_there_is_none(qapp) -> None:
    dialog = ManualPriceDialog(current_price=None)

    assert dialog.get_price() > 0


def test_entered_price_is_returned(qapp) -> None:
    dialog = ManualPriceDialog()

    dialog._price_spin.setValue(199.99)

    assert dialog.get_price() == 199.99
