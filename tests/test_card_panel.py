"""Headless tests for CardListPanel's presentation logic and signals.

Modal dialogs (CardDetailsDialog, QMessageBox) are monkeypatched so the tests
run non-interactively under the ``offscreen`` Qt platform.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from app.catalog.models import CatalogCard
from app.models.card import Card, CardDetailsValues
from app.models.enums import Condition, Language, Variant
from app.ui.app import build_application
from app.ui.widgets.card_list_panel import CardListPanel

_CATALOG_CARD = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)


def _card(**overrides) -> Card:
    base = dict(
        id=1,
        collection_id=1,
        name="Xatu",
        set_name="Skyridge",
        set_code="skg",
        card_number="H32",
        variant=Variant.HOLO,
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
    )
    base.update(overrides)
    return Card(**base)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> CardListPanel:
    p = CardListPanel()
    p.set_cards([_card(id=1, name="Xatu"), _card(id=2, name="Charizard")])
    return p


def test_set_cards_preserves_selection_by_id(panel: CardListPanel) -> None:
    panel._table.setCurrentCell(1, 0)  # Charizard, id=2
    panel.set_cards([_card(id=2, name="Charizard"), _card(id=1, name="Xatu")])
    assert panel.selected_card_id() == 2


def test_selection_changed_emits_minus_one_when_cleared(panel: CardListPanel) -> None:
    received: list[int] = []
    panel.selection_changed.connect(received.append)

    panel._table.setCurrentCell(0, 0)
    panel._table.setCurrentCell(-1, -1)

    assert received[-1] == -1


def test_delete_confirmed_emits_id(monkeypatch, panel: CardListPanel) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    received: list[int] = []
    panel.delete_requested.connect(received.append)

    panel._prompt_delete(1)  # Charizard, id=2

    assert received == [2]


def test_delete_declined_emits_nothing(monkeypatch, panel: CardListPanel) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    received: list[int] = []
    panel.delete_requested.connect(received.append)

    panel._prompt_delete(1)

    assert received == []


def test_edit_confirmed_emits_id_and_prefilled_values(monkeypatch, panel: CardListPanel) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    new_values = CardDetailsValues(
        variant=Variant.REVERSE_HOLO,
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        quantity=3,
        notes="PSA 9",
    )
    dialog.get_values.return_value = new_values
    captured_kwargs = {}

    def fake_dialog(**kwargs):
        captured_kwargs.update(kwargs)
        return dialog

    monkeypatch.setattr("app.ui.widgets.card_list_panel.CardDetailsDialog", fake_dialog)

    received: list[tuple[int, CardDetailsValues]] = []
    panel.edit_requested.connect(lambda cid, values: received.append((cid, values)))

    panel._prompt_edit(0)  # Xatu, id=1

    assert received == [(1, new_values)]
    assert captured_kwargs["initial"].variant is Variant.HOLO  # prefilled from the card


def test_edit_cancelled_emits_nothing(monkeypatch, panel: CardListPanel) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    monkeypatch.setattr(
        "app.ui.widgets.card_list_panel.CardDetailsDialog", lambda **kwargs: dialog
    )

    received = []
    panel.edit_requested.connect(lambda *a: received.append(a))

    panel._prompt_edit(0)

    assert received == []


def test_prompt_add_from_catalog_emits_add_confirmed(monkeypatch, panel: CardListPanel) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    values = CardDetailsValues(
        variant=Variant.NORMAL,
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
    )
    dialog.get_values.return_value = values
    monkeypatch.setattr(
        "app.ui.widgets.card_list_panel.CardDetailsDialog", lambda **kwargs: dialog
    )

    received = []
    panel.add_confirmed.connect(lambda card, vals: received.append((card, vals)))

    panel.prompt_add_from_catalog(_CATALOG_CARD)

    assert received == [(_CATALOG_CARD, values)]


def test_prompt_add_from_catalog_cancelled_emits_nothing(
    monkeypatch, panel: CardListPanel
) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    monkeypatch.setattr(
        "app.ui.widgets.card_list_panel.CardDetailsDialog", lambda **kwargs: dialog
    )

    received = []
    panel.add_confirmed.connect(lambda *a: received.append(a))

    panel.prompt_add_from_catalog(_CATALOG_CARD)

    assert received == []
