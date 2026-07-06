"""Tests for SealedProductDetailPanel's delegation to SealedArtworkView.

Mirrors ``test_card_detail_panel.py``, minus the Reverse Holo overlay and
card-only fields (Kartennummer/Extra/Zustand).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import Language
from app.models.sealed_product import SealedProduct
from app.ui.app import build_application
from app.ui.widgets.sealed_product_detail_panel import SealedProductDetailPanel


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> SealedProductDetailPanel:
    return SealedProductDetailPanel()


def _product(**overrides) -> SealedProduct:
    base = dict(
        id=1,
        name="Base Set Booster Box",
        category="Booster Box",
        language=Language.ENGLISH,
        quantity=1,
        notes="",
        photo_path="/tmp/box.png",
    )
    base.update(overrides)
    return SealedProduct(**base)


def test_show_product_forwards_photo(monkeypatch, panel: SealedProductDetailPanel) -> None:
    calls = []
    monkeypatch.setattr(panel._artwork, "show_photo", lambda path: calls.append(path))

    panel.show_product(_product())

    assert calls == ["/tmp/box.png"]


def test_show_product_populates_fields(panel: SealedProductDetailPanel) -> None:
    panel.show_product(_product(name="Evolutions ETB", category="Elite Trainer Box", quantity=3))

    assert panel._value_labels["Name"].text() == "Evolutions ETB"
    assert panel._value_labels["Kategorie"].text() == "Elite Trainer Box"
    assert panel._value_labels["Menge"].text() == "3"


def test_show_product_shows_dash_for_missing_category(panel: SealedProductDetailPanel) -> None:
    panel.show_product(_product(category=""))

    assert panel._value_labels["Kategorie"].text() == "—"


def test_show_empty_resets_artwork(monkeypatch, panel: SealedProductDetailPanel) -> None:
    calls = []
    monkeypatch.setattr(panel._artwork, "show_empty", lambda: calls.append(True))

    panel.show_empty()

    assert calls == [True]


def test_history_button_disabled_until_a_product_is_shown(panel: SealedProductDetailPanel) -> None:
    assert not panel._history_button.isEnabled()

    panel.show_product(_product(id=5))

    assert panel._history_button.isEnabled()

    panel.show_empty()

    assert not panel._history_button.isEnabled()


def test_history_button_click_emits_current_product_id(panel: SealedProductDetailPanel) -> None:
    panel.show_product(_product(id=7))
    received = []
    panel.history_panel_requested.connect(received.append)

    panel._on_history_button_clicked()

    assert received == [7]


def test_history_button_click_without_a_shown_product_emits_nothing(
    panel: SealedProductDetailPanel,
) -> None:
    received = []
    panel.history_panel_requested.connect(received.append)

    panel._on_history_button_clicked()

    assert received == []


def test_price_button_disabled_until_a_product_is_shown(panel: SealedProductDetailPanel) -> None:
    assert not panel._price_button.isEnabled()

    panel.show_product(_product(id=5))

    assert panel._price_button.isEnabled()

    panel.show_empty()

    assert not panel._price_button.isEnabled()


def test_price_button_click_emits_current_product_id(panel: SealedProductDetailPanel) -> None:
    panel.show_product(_product(id=7))
    received = []
    panel.price_lookup_requested.connect(received.append)

    panel._on_price_button_clicked()

    assert received == [7]


def test_price_button_click_without_a_shown_product_emits_nothing(
    panel: SealedProductDetailPanel,
) -> None:
    received = []
    panel.price_lookup_requested.connect(received.append)

    panel._on_price_button_clicked()

    assert received == []


def test_set_price_lookup_running_disables_and_restores_button(
    panel: SealedProductDetailPanel,
) -> None:
    panel.show_product(_product(id=5))

    panel.set_price_lookup_running(True)
    assert not panel._price_button.isEnabled()

    panel.set_price_lookup_running(False)
    assert panel._price_button.isEnabled()
