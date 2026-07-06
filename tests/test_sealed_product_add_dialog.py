"""Tests for SealedProductAddDialog's fields and default values.

Mirrors ``test_sealed_product_details_dialog.py``, minus name/category
(genuinely not known yet at this point -- see the dialog's own docstring).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import Language
from app.models.sealed_product import SealedProductDetailsValues
from app.ui.app import build_application
from app.ui.dialogs.sealed_product_add_dialog import SealedProductAddDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_defaults(qapp) -> None:
    dialog = SealedProductAddDialog()

    assert dialog.get_url() == ""
    assert dialog.get_values() == SealedProductDetailsValues(
        language=Language.ENGLISH, quantity=1, notes="", cardmarket_url=None
    )


def test_url_is_trimmed(qapp) -> None:
    dialog = SealedProductAddDialog()
    dialog._url_edit.setText("  https://example.com/box  ")

    assert dialog.get_url() == "https://example.com/box"


def test_language_quantity_and_notes_are_editable(qapp) -> None:
    dialog = SealedProductAddDialog()
    dialog._language_combo.setCurrentIndex(dialog._language_combo.findData(Language.GERMAN))
    dialog._quantity_spin.setValue(5)
    dialog._notes_edit.setPlainText("OVP")

    values = dialog.get_values()

    assert values.language is Language.GERMAN
    assert values.quantity == 5
    assert values.notes == "OVP"


def test_get_values_never_carries_a_url_itself(qapp) -> None:
    # cardmarket_url is deliberately left None here -- the caller fills it
    # in from get_url() only once the background lookup has resolved.
    dialog = SealedProductAddDialog()
    dialog._url_edit.setText("https://example.com/box")

    assert dialog.get_values().cardmarket_url is None
