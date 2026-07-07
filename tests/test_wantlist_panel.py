"""Headless tests for WantlistPanel's presentation logic.

Mirrors ``test_sealed_product_list_panel.py``. Modal dialogs
(WantlistItemDetailsDialog, QMessageBox) are monkeypatched so the tests run
non-interactively under the ``offscreen`` Qt platform.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QAbstractItemView, QMessageBox, QTableWidgetSelectionRange

from app.models.enums import Condition, Language
from app.models.wantlist import WantlistItem
from app.ui.app import build_application
from app.ui.widgets.wantlist_panel import WantlistPanel


def _item(**overrides) -> WantlistItem:
    base = dict(
        id=1,
        name="Charizard",
        set_name="Base Set",
        card_number="4",
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        target_price=500.0,
        notes="",
    )
    base.update(overrides)
    return WantlistItem(**base)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> WantlistPanel:
    p = WantlistPanel()
    p.set_items([_item(id=1, name="Charizard"), _item(id=2, name="Blastoise")])
    return p


def _column_texts(panel: WantlistPanel, column: int) -> list[str]:
    return [panel._table.item(row, column).text() for row in range(panel._table.rowCount())]


def test_target_price_column_sorts_numerically_not_alphabetically(panel: WantlistPanel) -> None:
    panel.set_items([
        _item(id=1, name="Cheap", target_price=5.0),
        _item(id=2, name="Pricey", target_price=1550.0),
        _item(id=3, name="Mid", target_price=20.0),
    ])

    panel._table.sortItems(3)  # Target

    assert _column_texts(panel, 0) == ["Cheap", "Mid", "Pricey"]


def test_current_price_column_sorts_unpriced_items_below_priced_ones(panel: WantlistPanel) -> None:
    panel.set_items([
        _item(id=1, name="Priced", current_price=5.0),
        _item(id=2, name="Unpriced", current_price=None),
    ])

    panel._table.sortItems(4)  # Current

    assert _column_texts(panel, 0) == ["Unpriced", "Priced"]


def test_status_column_shows_not_checked_yet_without_a_price(panel: WantlistPanel) -> None:
    panel.set_items([_item(id=1, current_price=None)])

    assert panel._table.item(0, 5).text() == "not checked yet"


def test_status_column_shows_below_target_alert(panel: WantlistPanel) -> None:
    panel.set_items([_item(id=1, current_price=100.0, target_price=200.0)])

    assert panel._table.item(0, 5).text() == "Below target!"


def test_status_column_shows_above_target_without_alert(panel: WantlistPanel) -> None:
    panel.set_items([_item(id=1, current_price=300.0, target_price=200.0)])

    assert panel._table.item(0, 5).text() == "above target"


def test_selection_mode_allows_selecting_multiple_rows(panel: WantlistPanel) -> None:
    assert panel._table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection


def test_sorting_preserves_selection(panel: WantlistPanel) -> None:
    panel._table.setCurrentCell(0, 0)  # Charizard, id=1

    panel._table.sortItems(0)  # Name column

    assert panel.selected_item_id() == 1


def test_multi_select_delete_confirmed_emits_all_selected_ids(
    monkeypatch, panel: WantlistPanel
) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    received: list[list[int]] = []
    panel.delete_requested.connect(received.append)

    panel._table.setRangeSelected(
        QTableWidgetSelectionRange(0, 0, 1, panel._table.columnCount() - 1), True
    )
    panel._prompt_delete_selected()

    assert sorted(received[0]) == [1, 2]


def test_single_select_delete_confirmed_emits_one_id(monkeypatch, panel: WantlistPanel) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    received: list[list[int]] = []
    panel.delete_requested.connect(received.append)

    panel._table.selectRow(1)  # Blastoise, id=2
    panel._prompt_delete_selected()

    assert received == [[2]]


def test_add_button_emits_add_requested(panel: WantlistPanel) -> None:
    received = []
    panel.add_requested.connect(lambda: received.append(True))

    panel._add_button.click()

    assert received == [True]


def test_check_all_button_emits_every_item_id(panel: WantlistPanel) -> None:
    received: list[list[int]] = []
    panel.bulk_price_lookup_requested.connect(received.append)

    panel._check_all_button.click()

    assert sorted(received[0]) == [1, 2]


def test_check_all_button_disabled_while_running(panel: WantlistPanel) -> None:
    panel.set_bulk_check_running(True)
    assert not panel._check_all_button.isEnabled()

    panel.set_bulk_check_running(False)
    assert panel._check_all_button.isEnabled()
