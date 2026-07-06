"""Headless tests for CardListPanel's presentation logic and signals.

Modal dialogs (CardDetailsDialog, QMessageBox) are monkeypatched so the tests
run non-interactively under the ``offscreen`` Qt platform.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QMessageBox,
    QTableWidgetSelectionRange,
)

from PySide6.QtGui import QColor

from app.catalog.models import CatalogCard
from app.models.card import Card, CardDetailsValues
from app.models.enums import Condition, Language
from app.ui.app import build_application
from app.ui.theme import PALETTE
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


def _column_texts(panel: CardListPanel, column: int) -> list[str]:
    return [panel._table.item(row, column).text() for row in range(panel._table.rowCount())]


def test_clicking_name_header_sorts_alphabetically(panel: CardListPanel) -> None:
    panel._table.horizontalHeader().sectionClicked.emit(0)  # Name column

    assert _column_texts(panel, 0) == ["Charizard", "Xatu"]


def test_clicking_name_header_again_reverses_order(panel: CardListPanel) -> None:
    panel._table.horizontalHeader().sectionClicked.emit(0)
    panel._table.horizontalHeader().sectionClicked.emit(0)

    assert _column_texts(panel, 0) == ["Xatu", "Charizard"]


def test_sort_is_case_insensitive(panel: CardListPanel) -> None:
    panel.set_cards([_card(id=1, name="eevee"), _card(id=2, name="Zebra"), _card(id=3, name="Absol")])

    panel._table.horizontalHeader().sectionClicked.emit(0)

    assert _column_texts(panel, 0) == ["Absol", "eevee", "Zebra"]


def test_every_column_is_sortable(panel: CardListPanel) -> None:
    # All 8 columns (Name/Set/Nr./Extra/Sprache/Zustand/Menge/Preis) --
    # user request, previously only Name/Set/Sprache/Zustand were.
    for column in range(8):
        panel._table.horizontalHeader().sectionClicked.emit(column)


def test_quantity_column_sorts_numerically_not_alphabetically(panel: CardListPanel) -> None:
    panel.set_cards([
        _card(id=1, name="Ten", quantity=10),
        _card(id=2, name="Two", quantity=2),
        _card(id=3, name="One", quantity=1),
    ])

    panel._table.horizontalHeader().sectionClicked.emit(6)  # Menge

    # A plain text sort would put "1" < "10" < "2"; numeric sort is 1, 2, 10.
    assert _column_texts(panel, 0) == ["One", "Two", "Ten"]


def test_price_column_sorts_numerically_not_alphabetically(panel: CardListPanel) -> None:
    panel.set_cards([
        _card(id=1, name="Cheap", current_price=5.0),
        _card(id=2, name="Pricey", current_price=1550.0),
        _card(id=3, name="Mid", current_price=20.0),
    ])

    panel._table.horizontalHeader().sectionClicked.emit(7)  # Preis

    # A plain text sort would put "1550.00" before "20.00"; numeric sort
    # ranks 5, 20, 1550.
    assert _column_texts(panel, 0) == ["Cheap", "Mid", "Pricey"]


def test_price_column_sorts_unpriced_cards_below_priced_ones(panel: CardListPanel) -> None:
    panel.set_cards([
        _card(id=1, name="Priced", current_price=5.0),
        _card(id=2, name="Unpriced", current_price=None),
    ])

    panel._table.horizontalHeader().sectionClicked.emit(7)  # Preis

    assert _column_texts(panel, 0) == ["Unpriced", "Priced"]


def test_sort_is_reapplied_after_set_cards_is_called_again(panel: CardListPanel) -> None:
    """A sort chosen by the user must survive the next refresh (e.g. after

    editing a card) instead of silently reverting to insertion order."""
    panel._table.horizontalHeader().sectionClicked.emit(0)  # Name, ascending

    panel.set_cards([_card(id=1, name="Xatu"), _card(id=2, name="Charizard")])

    assert _column_texts(panel, 0) == ["Charizard", "Xatu"]


def test_sorting_by_set_column_preserves_selection(panel: CardListPanel) -> None:
    panel.set_cards([
        _card(id=1, name="Xatu", set_name="Skyridge"),
        _card(id=2, name="Charizard", set_name="Base"),
    ])
    panel._table.setCurrentCell(0, 0)  # Xatu, id=1

    panel._table.horizontalHeader().sectionClicked.emit(1)  # Set column

    assert panel.selected_card_id() == 1


def test_price_column_shows_dash_without_a_price(panel: CardListPanel) -> None:
    panel.set_cards([_card(id=1, current_price=None)])

    assert panel._table.item(0, 7).text() == "—"


def test_price_column_shows_no_reminder_for_a_fresh_price(panel: CardListPanel) -> None:
    from datetime import datetime, timezone

    fresh = datetime.now(timezone.utc).isoformat()
    panel.set_cards([_card(id=1, current_price=10.0, price_updated_at=fresh)])

    assert "⚠️" not in panel._table.item(0, 7).text()


def test_price_column_shows_reminder_for_a_stale_price(panel: CardListPanel) -> None:
    from datetime import datetime, timedelta, timezone

    stale = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    panel.set_cards([_card(id=1, current_price=10.0, price_updated_at=stale)])

    assert "⚠️" in panel._table.item(0, 7).text()
    assert panel._table.item(0, 7).foreground().color() == QColor(PALETTE.negative)


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
    received: list[list[int]] = []
    panel.delete_requested.connect(received.append)

    panel._table.selectRow(1)  # Charizard, id=2
    panel._prompt_delete_selected()

    assert received == [[2]]


def test_delete_declined_emits_nothing(monkeypatch, panel: CardListPanel) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    received: list[list[int]] = []
    panel.delete_requested.connect(received.append)

    panel._table.selectRow(1)
    panel._prompt_delete_selected()

    assert received == []


def test_multi_select_delete_confirmed_emits_all_selected_ids(
    monkeypatch, panel: CardListPanel
) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    received: list[list[int]] = []
    panel.delete_requested.connect(received.append)

    panel._table.setRangeSelected(
        QTableWidgetSelectionRange(0, 0, 1, panel._table.columnCount() - 1), True
    )
    panel._prompt_delete_selected()

    assert sorted(received[0]) == [1, 2]


def test_selection_mode_allows_selecting_multiple_rows(panel: CardListPanel) -> None:
    assert panel._table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection


def test_edit_confirmed_emits_id_and_prefilled_values(monkeypatch, panel: CardListPanel) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    new_values = CardDetailsValues(
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
    assert captured_kwargs["initial"].language is Language.ENGLISH  # prefilled from the card


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


def test_prompt_edit_price_confirmed_emits_id_and_price(
    monkeypatch, panel: CardListPanel
) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.get_price.return_value = 199.99
    captured_kwargs = {}

    def fake_dialog(**kwargs):
        captured_kwargs.update(kwargs)
        return dialog

    monkeypatch.setattr("app.ui.widgets.card_list_panel.ManualPriceDialog", fake_dialog)
    received: list[tuple[int, float]] = []
    panel.price_edit_requested.connect(lambda cid, price: received.append((cid, price)))

    panel._prompt_edit_price(1)  # Charizard, id=2

    assert received == [(2, 199.99)]
    assert "current_price" in captured_kwargs


def test_prompt_edit_price_cancelled_emits_nothing(monkeypatch, panel: CardListPanel) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    monkeypatch.setattr(
        "app.ui.widgets.card_list_panel.ManualPriceDialog", lambda **kwargs: dialog
    )

    received = []
    panel.price_edit_requested.connect(lambda *a: received.append(a))

    panel._prompt_edit_price(0)

    assert received == []


def test_prompt_add_from_catalog_emits_add_confirmed(monkeypatch, panel: CardListPanel) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    values = CardDetailsValues(
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
