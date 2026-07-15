"""Headless tests for SealedProductListPanel's presentation logic.

Modal dialogs (SealedProductDetailsDialog, QMessageBox) are monkeypatched so
the tests run non-interactively under the ``offscreen`` Qt platform.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

from PySide6.QtWidgets import QAbstractItemView, QDialog, QMessageBox, QTableWidgetSelectionRange

from app.models.enums import Language
from app.models.sealed_product import SealedProduct
from app.ui.app import build_application
from app.ui.widgets.sealed_product_list_panel import SealedProductListPanel

import pytest


def _product(**overrides) -> SealedProduct:
    base = dict(
        id=1,
        name="Booster Box",
        category="Booster Box",
        language=Language.ENGLISH,
        quantity=1,
        notes="",
    )
    base.update(overrides)
    return SealedProduct(**base)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> SealedProductListPanel:
    p = SealedProductListPanel()
    p.set_products([_product(id=1, name="Xatu Box"), _product(id=2, name="Charizard Box")])
    return p


def _column_texts(panel: SealedProductListPanel, column: int) -> list[str]:
    return [panel._table.item(row, column).text() for row in range(panel._table.rowCount())]


def test_quantity_column_sorts_numerically_not_alphabetically(
    panel: SealedProductListPanel,
) -> None:
    panel.set_products([
        _product(id=1, name="Ten", quantity=10),
        _product(id=2, name="Two", quantity=2),
        _product(id=3, name="One", quantity=1),
    ])

    panel._table.sortItems(3)  # Menge

    # A plain text sort would put "1" < "10" < "2"; numeric sort is 1, 2, 10.
    assert _column_texts(panel, 0) == ["One", "Two", "Ten"]


def test_price_column_sorts_numerically_not_alphabetically(
    panel: SealedProductListPanel,
) -> None:
    panel.set_products([
        _product(id=1, name="Cheap", current_price=5.0),
        _product(id=2, name="Pricey", current_price=1550.0),
        _product(id=3, name="Mid", current_price=20.0),
    ])

    panel._table.sortItems(4)  # Preis

    # A plain text sort would put "1550.00" before "20.00"; numeric sort
    # ranks 5, 20, 1550.
    assert _column_texts(panel, 0) == ["Cheap", "Mid", "Pricey"]


def test_price_column_sorts_unpriced_products_below_priced_ones(
    panel: SealedProductListPanel,
) -> None:
    panel.set_products([
        _product(id=1, name="Priced", current_price=5.0),
        _product(id=2, name="Unpriced", current_price=None),
    ])

    panel._table.sortItems(4)  # Preis

    assert _column_texts(panel, 0) == ["Unpriced", "Priced"]


def test_total_price_column_is_price_times_quantity(panel: SealedProductListPanel) -> None:
    from datetime import datetime, timezone

    fresh = datetime.now(timezone.utc).isoformat()
    panel.set_products(
        [_product(id=1, name="Box", current_price=10.0, quantity=3, price_updated_at=fresh)]
    )

    assert panel._table.item(0, 5).text() == "30,00 EUR"  # Gesamtpreis


def test_total_price_column_shows_dash_without_a_price(panel: SealedProductListPanel) -> None:
    panel.set_products([_product(id=1, current_price=None, quantity=5)])

    assert panel._table.item(0, 5).text() == "—"


def test_total_price_column_sorts_numerically_not_alphabetically(
    panel: SealedProductListPanel,
) -> None:
    panel.set_products([
        _product(id=1, name="Cheap", current_price=5.0, quantity=1),
        _product(id=2, name="Pricey", current_price=1550.0, quantity=1),
        _product(id=3, name="Mid", current_price=20.0, quantity=1),
    ])

    panel._table.sortItems(5)  # Gesamtpreis

    assert _column_texts(panel, 0) == ["Cheap", "Mid", "Pricey"]


def test_total_price_column_reflects_quantity_not_just_unit_price(
    panel: SealedProductListPanel,
) -> None:
    # A cheaper unit price but a much larger quantity should sort as more
    # valuable overall -- this is the entire point of a separate total-price
    # column (user request: multiple copies should be directly comparable).
    panel.set_products([
        _product(id=1, name="FewExpensive", current_price=100.0, quantity=1),
        _product(id=2, name="ManyCheap", current_price=10.0, quantity=50),
    ])

    panel._table.sortItems(5)  # Gesamtpreis, ascending

    assert _column_texts(panel, 0) == ["FewExpensive", "ManyCheap"]


def test_sorting_preserves_selection(panel: SealedProductListPanel) -> None:
    panel.set_products([
        _product(id=1, name="Xatu Box"),
        _product(id=2, name="Charizard Box"),
    ])
    panel._table.setCurrentCell(0, 0)  # Xatu Box, id=1

    panel._table.sortItems(0)  # Name column

    assert panel.selected_product_id() == 1


def test_selection_mode_allows_selecting_multiple_rows(panel: SealedProductListPanel) -> None:
    assert panel._table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection


def test_multi_select_delete_confirmed_emits_all_selected_ids(
    monkeypatch, panel: SealedProductListPanel
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


def test_single_select_delete_confirmed_emits_one_id(
    monkeypatch, panel: SealedProductListPanel
) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    received: list[list[int]] = []
    panel.delete_requested.connect(received.append)

    panel._table.selectRow(1)  # Charizard Box, id=2
    panel._prompt_delete_selected()

    assert received == [[2]]


def test_prompt_edit_price_confirmed_emits_id_and_price(
    monkeypatch, panel: SealedProductListPanel
) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.get_price.return_value = 199.99
    captured_kwargs = {}

    def fake_dialog(**kwargs):
        captured_kwargs.update(kwargs)
        return dialog

    monkeypatch.setattr("app.ui.widgets.sealed_product_list_panel.ManualPriceDialog", fake_dialog)
    received: list[tuple[int, float]] = []
    panel.price_edit_requested.connect(lambda pid, price: received.append((pid, price)))

    panel._prompt_edit_price(1)  # Charizard Box, id=2

    assert received == [(2, 199.99)]
    assert "current_price" in captured_kwargs


def test_prompt_edit_price_cancelled_emits_nothing(
    monkeypatch, panel: SealedProductListPanel
) -> None:
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.DialogCode.Rejected
    monkeypatch.setattr(
        "app.ui.widgets.sealed_product_list_panel.ManualPriceDialog", lambda **kwargs: dialog
    )

    received = []
    panel.price_edit_requested.connect(lambda *a: received.append(a))

    panel._prompt_edit_price(0)

    assert received == []
