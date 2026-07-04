"""Tests for StatisticsPanel's display logic."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import Card
from app.models.enums import Condition, Language
from app.services.statistics_service import (
    CollectionValueSummary,
    PriceIncreaseHighlight,
    StalePriceEntry,
    StatisticsOverview,
    ValueBreakdownEntry,
)
from app.ui.app import build_application
from app.ui.widgets.statistics_panel import StatisticsPanel


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> StatisticsPanel:
    return StatisticsPanel()


def _card(**overrides) -> Card:
    base = dict(
        id=1,
        collection_id=1,
        name="Xatu",
        set_name="Skyridge",
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        current_price=15.0,
    )
    base.update(overrides)
    return Card(**base)


def _overview(**overrides) -> StatisticsOverview:
    base = dict(
        per_collection=[],
        grand_total=0.0,
        as_of=None,
        value_by_set=[],
        value_by_language=[],
        value_by_condition=[],
        most_expensive_cards=[],
        biggest_price_increase=None,
        stale_price_cards=[],
    )
    base.update(overrides)
    return StatisticsOverview(**base)


def test_shows_per_collection_rows_and_grand_total(panel: StatisticsPanel) -> None:
    overview = _overview(
        per_collection=[
            CollectionValueSummary(collection_id=1, name="Binder", card_count=2, total_value=25.0)
        ],
        grand_total=25.0,
    )

    panel.show_overview(overview)

    assert panel._per_collection_table.rowCount() == 1
    assert panel._per_collection_table.item(0, 0).text() == "Binder"
    assert panel._per_collection_table.item(0, 1).text() == "2"
    assert "25.00" in panel._per_collection_table.item(0, 2).text()
    assert "25.00" in panel._grand_total_label.text()


def test_shows_value_breakdowns(panel: StatisticsPanel) -> None:
    overview = _overview(
        value_by_set=[ValueBreakdownEntry(label="Base", total_value=100.0)],
        value_by_language=[ValueBreakdownEntry(label="German", total_value=50.0)],
        value_by_condition=[ValueBreakdownEntry(label="Near Mint", total_value=75.0)],
    )

    panel.show_overview(overview)

    assert panel._set_table.item(0, 0).text() == "Base"
    assert panel._language_table.item(0, 0).text() == "German"
    assert panel._condition_table.item(0, 0).text() == "Near Mint"


def test_shows_most_expensive_cards(panel: StatisticsPanel) -> None:
    overview = _overview(most_expensive_cards=[_card(name="Charizard", current_price=500.0)])

    panel.show_overview(overview)

    assert panel._expensive_table.rowCount() == 1
    assert panel._expensive_table.item(0, 0).text() == "Charizard"
    assert "500.00" in panel._expensive_table.item(0, 2).text()


def test_shows_price_increase_highlight(panel: StatisticsPanel) -> None:
    overview = _overview(
        biggest_price_increase=PriceIncreaseHighlight(
            card=_card(name="Venusaur"),
            previous_price=10.0,
            latest_price=20.0,
            percent_change=100.0,
        )
    )

    panel.show_overview(overview)

    text = panel._price_increase_label.text()
    assert "Venusaur" in text
    assert "10.00" in text
    assert "20.00" in text
    assert "100.0" in text


def test_shows_placeholder_when_no_price_increase(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview())

    assert "Keine" in panel._price_increase_label.text()


def test_shows_as_of_date_and_disclaimer(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview(as_of="2026-07-04T10:00:00+00:00"))

    text = panel._as_of_label.text()
    assert "04.07.2026" in text
    assert "veraltet" in text


def test_shows_as_of_placeholder_when_never_updated(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview(as_of=None))

    assert "noch nie aktualisiert" in panel._as_of_label.text()


def test_shows_stale_price_cards_with_days_and_never_updated(panel: StatisticsPanel) -> None:
    overview = _overview(
        stale_price_cards=[
            StalePriceEntry(card=_card(name="NeverPriced"), days_since_update=None),
            StalePriceEntry(card=_card(name="VeryStale"), days_since_update=120),
        ]
    )

    panel.show_overview(overview)

    assert panel._stale_table.rowCount() == 2
    assert panel._stale_table.item(0, 0).text() == "NeverPriced"
    assert "noch nie" in panel._stale_table.item(0, 2).text()
    assert panel._stale_table.item(1, 0).text() == "VeryStale"
    assert "120" in panel._stale_table.item(1, 2).text()


def test_stale_price_row_has_update_button_emitting_card_id(panel: StatisticsPanel) -> None:
    overview = _overview(
        stale_price_cards=[StalePriceEntry(card=_card(id=42), days_since_update=100)]
    )
    panel.show_overview(overview)
    received: list[int] = []
    panel.price_lookup_requested.connect(received.append)

    button = panel._stale_table.cellWidget(0, 3)
    button.click()

    assert received == [42]
