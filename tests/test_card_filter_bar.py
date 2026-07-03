"""Tests for CardFilterBar: control state -> CardFilter, reset, signals."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import CardFilter
from app.models.enums import Condition, Language, Variant
from app.ui.app import build_application
from app.ui.widgets.card_filter_bar import CardFilterBar


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def bar(qapp) -> CardFilterBar:
    return CardFilterBar()


def test_default_filter_is_empty(bar: CardFilterBar) -> None:
    assert bar.current_filter() == CardFilter()


def test_search_text_is_reflected_in_filter(bar: CardFilterBar) -> None:
    bar._search.setText("xatu")
    assert bar.current_filter().search_text == "xatu"


def test_set_combo_alle_means_unset(bar: CardFilterBar) -> None:
    bar.set_available_sets(["Base", "Skyridge"])
    assert bar.current_filter().set_name is None

    bar._set_combo.setCurrentIndex(1)
    assert bar.current_filter().set_name == "Base"


def test_language_variant_condition_combos(bar: CardFilterBar) -> None:
    bar._language_combo.setCurrentIndex(
        bar._language_combo.findData(Language.GERMAN)
    )
    bar._variant_combo.setCurrentIndex(bar._variant_combo.findData(Variant.HOLO))
    bar._condition_combo.setCurrentIndex(
        bar._condition_combo.findData(Condition.EXCELLENT)
    )

    result = bar.current_filter()

    assert result.language is Language.GERMAN
    assert result.variant is Variant.HOLO
    assert result.condition is Condition.EXCELLENT


def test_price_range_parses_valid_numbers(bar: CardFilterBar) -> None:
    bar._min_price.setText("10")
    bar._max_price.setText("99,50")

    result = bar.current_filter()

    assert result.min_price == 10.0
    assert result.max_price == 99.5


def test_price_range_ignores_invalid_input(bar: CardFilterBar) -> None:
    bar._min_price.setText("abc")

    assert bar.current_filter().min_price is None


def test_filter_changed_emitted_on_search_text_change(bar: CardFilterBar) -> None:
    received: list[CardFilter] = []
    bar.filter_changed.connect(received.append)

    bar._search.setText("charizard")

    assert received
    assert received[-1].search_text == "charizard"


def test_scope_changed_emitted_on_checkbox_toggle(bar: CardFilterBar) -> None:
    received: list[bool] = []
    bar.scope_changed.connect(received.append)

    bar._all_collections.setChecked(True)

    assert received == [True]


def test_reset_clears_every_field(bar: CardFilterBar) -> None:
    bar._search.setText("xatu")
    bar.set_available_sets(["Base"])
    bar._set_combo.setCurrentIndex(1)
    bar._min_price.setText("5")

    bar.reset()

    assert bar.current_filter() == CardFilter()


def test_set_available_sets_preserves_current_pick_if_still_present(bar: CardFilterBar) -> None:
    bar.set_available_sets(["Base", "Skyridge"])
    bar._set_combo.setCurrentIndex(2)  # "Skyridge"

    bar.set_available_sets(["Skyridge", "Jungle"])

    assert bar.current_filter().set_name == "Skyridge"


def test_set_available_sets_falls_back_to_alle_if_pick_is_gone(bar: CardFilterBar) -> None:
    bar.set_available_sets(["Base"])
    bar._set_combo.setCurrentIndex(1)  # "Base"

    bar.set_available_sets(["Skyridge"])

    assert bar.current_filter().set_name is None
