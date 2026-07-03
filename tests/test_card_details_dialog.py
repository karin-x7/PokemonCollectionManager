"""Tests for CardDetailsDialog's default values and prefill behaviour."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language, Variant
from app.ui.app import build_application
from app.ui.dialogs.card_details_dialog import CardDetailsDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_defaults_without_initial(qapp) -> None:
    dialog = CardDetailsDialog(
        title="Karte hinzufügen",
        accept_label="Hinzufügen",
        display_name="Xatu",
        display_set="Skyridge",
        display_number="H32",
    )

    values = dialog.get_values()

    assert values == CardDetailsValues(
        variant=Variant.NORMAL,
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
    )
    # Variant is a `str`-subclassed Enum: comparing with `==` above would
    # still pass even if `variant` had decayed into a plain `str` (Qt's combo
    # box item-data marshalling does exactly that — measured live, and it
    # crashed CardRepository.create, which accesses `.variant.value`).
    # Assert the real type explicitly so this regression can't hide again.
    assert type(values.variant) is Variant


def test_variant_survives_combo_box_round_trip_for_every_option(qapp) -> None:
    dialog = CardDetailsDialog(
        title="Karte hinzufügen",
        accept_label="Hinzufügen",
        display_name="Xatu",
        display_set="Skyridge",
        display_number="H32",
    )

    for index, variant in enumerate(Variant):
        dialog._variant_combo.setCurrentIndex(index)
        values = dialog.get_values()
        assert type(values.variant) is Variant
        assert values.variant is variant


def test_prefills_from_initial(qapp) -> None:
    initial = CardDetailsValues(
        variant=Variant.REVERSE_HOLO,
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        quantity=4,
        notes="PSA 9",
    )
    dialog = CardDetailsDialog(
        title="Karte bearbeiten",
        accept_label="Speichern",
        display_name="Xatu",
        display_set="Skyridge",
        display_number="H32",
        initial=initial,
    )

    values = dialog.get_values()
    assert values == initial
    assert type(values.variant) is Variant
