"""Tests for CardDetailPanel's delegation to CardArtworkView."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import Card
from app.models.enums import Condition, Language, Variant
from app.ui.app import build_application
from app.ui.widgets.card_detail_panel import CardDetailPanel


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> CardDetailPanel:
    return CardDetailPanel()


def _card(**overrides) -> Card:
    base = dict(
        id=1,
        collection_id=1,
        name="Xatu",
        set_name="Skyridge",
        set_code="skg",
        card_number="H32",
        variant=Variant.REVERSE_HOLO,
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
        photo_path="/tmp/skg-h32.png",
    )
    base.update(overrides)
    return Card(**base)


def test_show_card_forwards_photo_and_reverse_holo_flag(
    monkeypatch, panel: CardDetailPanel
) -> None:
    calls = []
    monkeypatch.setattr(
        panel._artwork, "show_photo", lambda path, reverse_holo: calls.append((path, reverse_holo))
    )

    panel.show_card(_card())

    assert calls == [("/tmp/skg-h32.png", True)]


def test_show_card_with_non_reverse_variant_passes_false(
    monkeypatch, panel: CardDetailPanel
) -> None:
    calls = []
    monkeypatch.setattr(
        panel._artwork, "show_photo", lambda path, reverse_holo: calls.append(reverse_holo)
    )

    panel.show_card(_card(variant=Variant.HOLO))

    assert calls == [False]


def test_show_empty_resets_artwork(monkeypatch, panel: CardDetailPanel) -> None:
    calls = []
    monkeypatch.setattr(panel._artwork, "show_empty", lambda: calls.append(True))

    panel.show_empty()

    assert calls == [True]


def test_price_button_disabled_until_a_card_is_shown(panel: CardDetailPanel) -> None:
    assert not panel._price_button.isEnabled()

    panel.show_card(_card(id=5))

    assert panel._price_button.isEnabled()

    panel.show_empty()

    assert not panel._price_button.isEnabled()


def test_price_button_click_emits_current_card_id(panel: CardDetailPanel) -> None:
    panel.show_card(_card(id=7))
    received = []
    panel.price_lookup_requested.connect(received.append)

    panel._on_price_button_clicked()

    assert received == [7]


def test_price_button_click_without_a_shown_card_emits_nothing(panel: CardDetailPanel) -> None:
    received = []
    panel.price_lookup_requested.connect(received.append)

    panel._on_price_button_clicked()

    assert received == []


def test_set_price_lookup_running_disables_and_restores_button(panel: CardDetailPanel) -> None:
    panel.show_card(_card(id=5))

    panel.set_price_lookup_running(True)
    assert not panel._price_button.isEnabled()

    panel.set_price_lookup_running(False)
    assert panel._price_button.isEnabled()
