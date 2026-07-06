"""Tests for CardDetailsDialog's default values and prefill behaviour."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language
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
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
    )


def test_prefills_from_initial(qapp) -> None:
    initial = CardDetailsValues(
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        is_reverse_holo=True,
        is_signed=True,
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


def test_manual_cardmarket_url_round_trips_and_blank_becomes_none(qapp) -> None:
    dialog = CardDetailsDialog(
        title="Karte bearbeiten",
        accept_label="Speichern",
        display_name="Ho-Oh",
        display_set="Neo Revelation",
        display_number="7",
    )

    dialog._manual_cardmarket_url_edit.setText("  https://example.com/awakening-legends  ")
    assert dialog.get_values().manual_cardmarket_url == "https://example.com/awakening-legends"

    dialog._manual_cardmarket_url_edit.setText("   ")
    assert dialog.get_values().manual_cardmarket_url is None


def test_editable_identity_prefills_and_returns_edited_values(qapp) -> None:
    dialog = CardDetailsDialog(
        title="Karte manuell eintragen",
        accept_label="Hinzufügen",
        display_name="Venusaur",
        display_set="Legendary Collection",
        display_number="18",
        editable_identity=True,
    )

    assert dialog.get_identity() == ("Venusaur", "Legendary Collection", "18")

    dialog._name_edit.setText("  Bisaflor  ")
    dialog._set_edit.setText(" Legendary Collection ")
    dialog._number_edit.setText("")

    assert dialog.get_identity() == ("Bisaflor", "Legendary Collection", "")


def test_non_editable_identity_shows_plain_labels(qapp) -> None:
    dialog = CardDetailsDialog(
        title="Karte hinzufügen",
        accept_label="Hinzufügen",
        display_name="Xatu",
        display_set="Skyridge",
        display_number="H32",
    )

    assert not hasattr(dialog, "_name_edit")


def test_extras_checkboxes_round_trip(qapp) -> None:
    dialog = CardDetailsDialog(
        title="Karte hinzufügen",
        accept_label="Hinzufügen",
        display_name="Xatu",
        display_set="Skyridge",
        display_number="H32",
    )

    dialog._reverse_holo_check.setChecked(True)
    dialog._signed_check.setChecked(True)
    dialog._first_edition_check.setChecked(False)
    dialog._altered_check.setChecked(True)
    values = dialog.get_values()

    assert values.is_reverse_holo is True
    assert values.is_signed is True
    assert values.is_first_edition is False
    assert values.is_altered is True
