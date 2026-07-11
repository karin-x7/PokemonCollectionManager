"""Tests for CardDetailPanel's delegation to CardArtworkView."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QLabel

from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality
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
        is_reverse_holo=True,
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

    panel.show_card(_card(is_reverse_holo=False))

    assert calls == [False]


def test_field_labels_are_all_translated_to_english(panel: CardDetailPanel) -> None:
    # Real, live-reported bug: the "Sprache" field label had no matching
    # bare (no-colon) entry in the translation table (only "Sprache:", used
    # by a different dialog) -- tr()'s "no entry -> return input unchanged"
    # fallback silently left it as German in an otherwise all-English panel.
    label_texts = {label.text() for label in panel.findChildren(QLabel)}
    assert "Language:" in label_texts
    assert "Sprache:" not in label_texts


def test_extras_field_lists_active_flags(panel: CardDetailPanel) -> None:
    panel.show_card(_card(is_reverse_holo=True, is_signed=True, is_altered=True))

    assert panel._value_labels["Extra"].text() == "Reverse Holo, Signed, Altered"


def test_extras_field_shows_dash_when_none_apply(panel: CardDetailPanel) -> None:
    panel.show_card(_card(is_reverse_holo=False))

    assert panel._value_labels["Extra"].text() == "—"


def test_show_empty_resets_artwork(monkeypatch, panel: CardDetailPanel) -> None:
    calls = []
    monkeypatch.setattr(panel._artwork, "show_empty", lambda: calls.append(True))

    panel.show_empty()

    assert calls == [True]


def test_history_button_disabled_until_a_card_is_shown(panel: CardDetailPanel) -> None:
    assert not panel._history_button.isEnabled()

    panel.show_card(_card(id=5))

    assert panel._history_button.isEnabled()

    panel.show_empty()

    assert not panel._history_button.isEnabled()


def test_history_button_click_emits_current_card_id(panel: CardDetailPanel) -> None:
    panel.show_card(_card(id=7))
    received = []
    panel.history_panel_requested.connect(received.append)

    panel._on_history_button_clicked()

    assert received == [7]


def test_history_button_click_without_a_shown_card_emits_nothing(panel: CardDetailPanel) -> None:
    received = []
    panel.history_panel_requested.connect(received.append)

    panel._on_history_button_clicked()

    assert received == []


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


def test_artwork_position_is_unaffected_by_price_quality_text_length(
    qapp, panel: CardDetailPanel
) -> None:
    # Live-reported bug: on a panel taller than its content needed, the
    # header (the only non-fixed widget above the artwork) absorbed the
    # leftover vertical space -- and *how much* leftover space there was
    # depended on how many lines the "Price quality" rationale wrapped to,
    # so the artwork's position visibly shifted between cards even though
    # its own size stayed fixed. A trailing stretch should now claim that
    # leftover space instead, keeping the artwork's position constant.
    panel.show()
    panel.resize(300, 900)
    for _ in range(5):
        qapp.processEvents()

    panel.show_card(_card(price_rationale="Japanese, Near Mint."))
    for _ in range(5):
        qapp.processEvents()
    short_rationale_y = panel._artwork.geometry().y()

    panel.show_card(
        _card(
            id=2,
            price_quality=PriceQuality.ESTIMATED_FROM_CONDITION,
            price_rationale=(
                "Estimated from a different condition and language: English, "
                "Excellent instead of Japanese, Near Mint, because no matching "
                "offer was found."
            ),
        )
    )
    for _ in range(5):
        qapp.processEvents()
    long_rationale_y = panel._artwork.geometry().y()

    assert short_rationale_y == long_rationale_y
    panel.close()
