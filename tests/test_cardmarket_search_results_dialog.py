"""Tests for CardmarketSearchResultsDialog's selection/confirm-button behaviour."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.pricing.models import CardmarketSearchResult
from app.ui.app import build_application
from app.ui.dialogs.cardmarket_search_results_dialog import CardmarketSearchResultsDialog

_PERFECT_ORDER = CardmarketSearchResult(
    name="Poké Pad",
    set_name="Perfect Order",
    card_number="POR 113",
    price_hint="9,00 €",
    raw_text="Poké Pad Perfect Order \xa0Poké Pad (POR 113) From 9,00 €",
)
_ASCENDED_HEROES = CardmarketSearchResult(
    name="Poké Pad",
    set_name="Ascended Heroes",
    card_number="ASC 198",
    price_hint="0,02 €",
    raw_text="Poké Pad Ascended Heroes \xa0Poké Pad (ASC 198) From 0,02 €",
)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def dialog(qapp) -> CardmarketSearchResultsDialog:
    d = CardmarketSearchResultsDialog()
    d.set_results([_PERFECT_ORDER, _ASCENDED_HEROES])
    return d


def test_confirm_button_disabled_without_selection(dialog: CardmarketSearchResultsDialog) -> None:
    assert not dialog._confirm_button.isEnabled()


def test_confirm_button_enabled_after_selection(dialog: CardmarketSearchResultsDialog) -> None:
    dialog._table.setCurrentCell(1, 0)
    assert dialog._confirm_button.isEnabled()


def test_confirm_clicked_emits_selected_result(dialog: CardmarketSearchResultsDialog) -> None:
    dialog._table.setCurrentCell(1, 0)  # Ascended Heroes
    received = []
    dialog.result_confirmed.connect(received.append)

    dialog._on_confirm_clicked()

    assert received == [_ASCENDED_HEROES]


def test_set_results_with_empty_list_shows_empty_state(qapp) -> None:
    dialog = CardmarketSearchResultsDialog()
    dialog.set_results([])
    assert not dialog._empty_label.isHidden()
    assert not dialog._confirm_button.isEnabled()


def test_shows_a_loading_state_before_any_results_arrive(qapp) -> None:
    dialog = CardmarketSearchResultsDialog()

    assert not dialog._loading_label.isHidden()
    assert not dialog._loading_bar.isHidden()
    assert dialog._table.isHidden()


def test_set_results_hides_the_loading_state(dialog: CardmarketSearchResultsDialog) -> None:
    assert dialog._loading_label.isHidden()
    assert dialog._loading_bar.isHidden()
