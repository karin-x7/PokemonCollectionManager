"""Tests for SealedProductDetailsDialog's default values and prefill behaviour."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import Language
from app.models.sealed_product import SealedProductDetailsValues
from app.ui.app import build_application
from app.ui.dialogs.sealed_product_details_dialog import SealedProductDetailsDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_defaults_without_initial(qapp) -> None:
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt eintragen",
        accept_label="Hinzufügen",
        display_name="Base Set Booster Box",
        display_category="Booster Box",
    )

    values = dialog.get_values()

    assert values == SealedProductDetailsValues(language=Language.ENGLISH, quantity=1, notes="")


def test_prefills_from_initial(qapp) -> None:
    initial = SealedProductDetailsValues(
        language=Language.GERMAN,
        quantity=3,
        notes="OVP",
        cardmarket_url="https://example.com/box",
    )
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt bearbeiten",
        accept_label="Speichern",
        display_name="Base Set Booster Box",
        display_category="Booster Box",
        initial=initial,
    )

    assert dialog.get_values() == initial


def test_identity_is_editable(qapp) -> None:
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt eintragen",
        accept_label="Hinzufügen",
        display_name="Base Set Booster Box",
        display_category="Booster Box",
    )

    assert dialog.get_identity() == ("Base Set Booster Box", "Booster Box")

    dialog._name_edit.setText("  Evolutions ETB  ")
    dialog._category_combo.setCurrentText(" Elite Trainer Box ")

    assert dialog.get_identity() == ("Evolutions ETB", "Elite Trainer Box")


def test_category_combo_is_prefilled_from_a_recognised_breadcrumb(qapp) -> None:
    # "Booster Boxes" (Cardmarket's own plural breadcrumb wording) should
    # be normalised to the canonical "Booster Box" label, not shown raw.
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt eintragen",
        accept_label="Hinzufügen",
        display_name="Base Set Booster Box",
        display_category="Booster Boxes",
    )

    assert dialog.get_identity()[1] == "Booster Box"


def test_category_combo_keeps_unrecognised_text_as_is(qapp) -> None:
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt eintragen",
        accept_label="Hinzufügen",
        display_name="Some Product",
        display_category="Some Weird New Product Type",
    )

    assert dialog.get_identity()[1] == "Some Weird New Product Type"


def test_category_combo_offers_every_known_category(qapp) -> None:
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt eintragen",
        accept_label="Hinzufügen",
        display_name="Base Set Booster Box",
        display_category="Booster Box",
    )

    items = [dialog._category_combo.itemText(i) for i in range(dialog._category_combo.count())]

    assert "Elite Trainer Box" in items
    assert "Tin" in items
    assert "Sonstiges" not in items  # deliberate catch-all, not a pickable option


def test_cardmarket_url_round_trips_and_blank_becomes_none(qapp) -> None:
    dialog = SealedProductDetailsDialog(
        title="Sealed-Produkt eintragen",
        accept_label="Hinzufügen",
        display_name="Base Set Booster Box",
        display_category="Booster Box",
    )

    dialog._cardmarket_url_edit.setText("  https://example.com/box  ")
    assert dialog.get_values().cardmarket_url == "https://example.com/box"

    dialog._cardmarket_url_edit.setText("   ")
    assert dialog.get_values().cardmarket_url is None
