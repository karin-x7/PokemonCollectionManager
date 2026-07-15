"""Tests for StatisticsPanel's display logic."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import Card
from app.models.enums import Condition, Language
from app.models.sealed_product import SealedProduct
from app.services.statistics_service import (
    CollectionValueSummary,
    PriceIncreaseHighlight,
    StaleSealedPriceEntry,
    StalePriceEntry,
    StatisticsOverview,
    ValueBreakdownEntry,
    ValueOverTimePoint,
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


def _sealed(**overrides) -> SealedProduct:
    base = dict(
        id=1,
        name="Base Set Booster Box",
        category="Booster Box",
        language=Language.ENGLISH,
        quantity=1,
        current_price=5000.0,
    )
    base.update(overrides)
    return SealedProduct(**base)


def _overview(**overrides) -> StatisticsOverview:
    base = dict(
        per_collection=[],
        grand_total=0.0,
        combined_total=0.0,
        as_of=None,
        value_by_set=[],
        value_by_language=[],
        value_by_condition=[],
        most_expensive_cards=[],
        biggest_price_increase=None,
        stale_price_cards=[],
        sealed_total_value=0.0,
        sealed_item_count=0,
        sealed_as_of=None,
        value_by_sealed_category=[],
        most_expensive_sealed_products=[],
        sealed_stale_price_products=[],
        value_over_time=[],
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
    assert "25,00" in panel._per_collection_table.item(0, 2).text()
    assert "25,00" in panel._grand_total_label.text()


def test_shows_combined_total_and_stat_tiles(panel: StatisticsPanel) -> None:
    overview = _overview(
        per_collection=[
            CollectionValueSummary(collection_id=1, name="Binder", card_count=3, total_value=25.0)
        ],
        grand_total=25.0,
        sealed_total_value=5000.0,
        sealed_item_count=2,
        combined_total=5025.0,
    )

    panel.show_overview(overview)

    assert "5.025,00" in panel._combined_total_label.text()
    assert "25,00" in panel._cards_tile_value.text()
    assert "3" in panel._cards_tile_subtext.text()
    assert "5.000,00" in panel._sealed_tile_value.text()
    assert "2" in panel._sealed_tile_subtext.text()


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
    assert "500,00" in panel._expensive_table.item(0, 2).text()


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
    assert "10,00" in text
    assert "20,00" in text
    assert "100,0" in text


def test_shows_placeholder_when_no_price_increase(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview())

    assert "No card" in panel._price_increase_label.text()


def test_shows_as_of_date_and_disclaimer(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview(as_of="2026-07-04T10:00:00+00:00"))

    text = panel._as_of_label.text()
    assert "04.07.2026" in text
    assert "outdated" in text


def test_shows_as_of_placeholder_when_never_updated(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview(as_of=None))

    assert "never updated" in panel._as_of_label.text()


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
    assert "never updated" in panel._stale_table.item(0, 2).text()
    assert panel._stale_table.item(1, 0).text() == "VeryStale"
    assert "120" in panel._stale_table.item(1, 2).text()


def test_per_collection_table_sorts_numerically_by_card_count(panel: StatisticsPanel) -> None:
    overview = _overview(
        per_collection=[
            CollectionValueSummary(collection_id=1, name="A", card_count=10, total_value=1.0),
            CollectionValueSummary(collection_id=2, name="B", card_count=2, total_value=1.0),
        ]
    )
    panel.show_overview(overview)

    panel._per_collection_table.sortItems(1)

    # A plain text sort would put "10" before "2"; numeric sort is 2, 10.
    assert panel._per_collection_table.item(0, 1).text() == "2"
    assert panel._per_collection_table.item(1, 1).text() == "10"


def test_breakdown_table_sorts_numerically_by_value(panel: StatisticsPanel) -> None:
    overview = _overview(
        value_by_set=[
            ValueBreakdownEntry(label="Pricey", total_value=1550.0),
            ValueBreakdownEntry(label="Cheap", total_value=5.0),
        ]
    )
    panel.show_overview(overview)

    panel._set_table.sortItems(1)

    assert panel._set_table.item(0, 0).text() == "Cheap"
    assert panel._set_table.item(1, 0).text() == "Pricey"


def test_stale_table_header_click_sorts_by_days_never_updated_last(
    panel: StatisticsPanel,
) -> None:
    overview = _overview(
        stale_price_cards=[
            StalePriceEntry(card=_card(name="NeverPriced"), days_since_update=None),
            StalePriceEntry(card=_card(name="VeryStale"), days_since_update=120),
            StalePriceEntry(card=_card(name="Stale"), days_since_update=10),
        ]
    )
    panel.show_overview(overview)

    panel._on_stale_header_clicked(2)  # Zuletzt aktualisiert, ascending

    assert [panel._stale_table.item(row, 0).text() for row in range(3)] == [
        "Stale",
        "VeryStale",
        "NeverPriced",
    ]


def test_stale_table_header_click_twice_reverses_order(panel: StatisticsPanel) -> None:
    overview = _overview(
        stale_price_cards=[
            StalePriceEntry(card=_card(name="B"), days_since_update=None),
            StalePriceEntry(card=_card(name="A"), days_since_update=None),
        ]
    )
    panel.show_overview(overview)

    panel._on_stale_header_clicked(0)
    panel._on_stale_header_clicked(0)

    assert [panel._stale_table.item(row, 0).text() for row in range(2)] == ["B", "A"]


def test_stale_table_header_click_preserves_action_buttons(panel: StatisticsPanel) -> None:
    """Sorting must not desync the per-row "Preis aktualisieren" button from

    its card -- since Qt's built-in sort leaves cell widgets in place, this
    table sorts manually (see _render_stale_table) instead."""
    overview = _overview(
        stale_price_cards=[
            StalePriceEntry(card=_card(id=1, name="Zebra"), days_since_update=5),
            StalePriceEntry(card=_card(id=2, name="Absol"), days_since_update=10),
        ]
    )
    panel.show_overview(overview)

    panel._on_stale_header_clicked(0)  # Name, ascending -> Absol, Zebra

    assert panel._stale_table.item(0, 0).text() == "Absol"
    received: list[int] = []
    panel.price_lookup_requested.connect(received.append)
    panel._stale_table.cellWidget(0, 3).click()
    assert received == [2]  # Absol's card id, not the row's original occupant


def test_sealed_stale_table_header_click_sorts_by_name(panel: StatisticsPanel) -> None:
    overview = _overview(
        sealed_stale_price_products=[
            StaleSealedPriceEntry(product=_sealed(name="Zebra Box"), days_since_update=5),
            StaleSealedPriceEntry(product=_sealed(name="Absol Box"), days_since_update=10),
        ]
    )
    panel.show_overview(overview)

    panel._on_sealed_stale_header_clicked(0)

    assert [panel._sealed_stale_table.item(row, 0).text() for row in range(2)] == [
        "Absol Box",
        "Zebra Box",
    ]


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


# --- Sealed products ------------------------------------------------------- #


def test_shows_sealed_category_breakdown(panel: StatisticsPanel) -> None:
    overview = _overview(
        value_by_sealed_category=[ValueBreakdownEntry(label="Booster Box", total_value=5000.0)]
    )

    panel.show_overview(overview)

    assert panel._sealed_category_table.item(0, 0).text() == "Booster Box"
    assert "5.000,00" in panel._sealed_category_table.item(0, 1).text()


def test_shows_most_expensive_sealed_products(panel: StatisticsPanel) -> None:
    overview = _overview(
        most_expensive_sealed_products=[_sealed(name="Base Set Booster Box", current_price=5000.0)]
    )

    panel.show_overview(overview)

    assert panel._sealed_expensive_table.rowCount() == 1
    assert panel._sealed_expensive_table.item(0, 0).text() == "Base Set Booster Box"
    assert panel._sealed_expensive_table.item(0, 1).text() == "Booster Box"
    assert "5.000,00" in panel._sealed_expensive_table.item(0, 2).text()


def test_shows_sealed_stale_price_products_with_days_and_never_updated(
    panel: StatisticsPanel,
) -> None:
    overview = _overview(
        sealed_stale_price_products=[
            StaleSealedPriceEntry(product=_sealed(name="NeverPriced"), days_since_update=None),
            StaleSealedPriceEntry(product=_sealed(name="VeryStale"), days_since_update=120),
        ]
    )

    panel.show_overview(overview)

    assert panel._sealed_stale_table.rowCount() == 2
    assert panel._sealed_stale_table.item(0, 0).text() == "NeverPriced"
    assert "never updated" in panel._sealed_stale_table.item(0, 2).text()
    assert panel._sealed_stale_table.item(1, 0).text() == "VeryStale"
    assert "120" in panel._sealed_stale_table.item(1, 2).text()


def test_sealed_stale_price_row_has_update_button_emitting_product_id(
    panel: StatisticsPanel,
) -> None:
    overview = _overview(
        sealed_stale_price_products=[
            StaleSealedPriceEntry(product=_sealed(id=42), days_since_update=100)
        ]
    )
    panel.show_overview(overview)
    received: list[int] = []
    panel.sealed_price_lookup_requested.connect(received.append)

    button = panel._sealed_stale_table.cellWidget(0, 3)
    button.click()

    assert received == [42]


# --- Bulk "Alle aktualisieren" buttons -------------------------------------- #


def test_bulk_update_button_emits_all_stale_card_ids(panel: StatisticsPanel) -> None:
    overview = _overview(
        stale_price_cards=[
            StalePriceEntry(card=_card(id=1), days_since_update=100),
            StalePriceEntry(card=_card(id=2), days_since_update=200),
        ]
    )
    panel.show_overview(overview)
    received: list[list[int]] = []
    panel.bulk_price_lookup_requested.connect(received.append)

    panel._bulk_update_button.click()

    assert received == [[1, 2]]


def test_sealed_bulk_update_button_emits_all_stale_product_ids(panel: StatisticsPanel) -> None:
    overview = _overview(
        sealed_stale_price_products=[
            StaleSealedPriceEntry(product=_sealed(id=1), days_since_update=100),
            StaleSealedPriceEntry(product=_sealed(id=2), days_since_update=200),
        ]
    )
    panel.show_overview(overview)
    received: list[list[int]] = []
    panel.sealed_bulk_price_lookup_requested.connect(received.append)

    panel._sealed_bulk_update_button.click()

    assert received == [[1, 2]]


def test_bulk_update_button_disabled_when_no_stale_cards(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview(stale_price_cards=[]))

    assert not panel._bulk_update_button.isEnabled()


def test_bulk_update_button_enabled_when_stale_cards_exist(panel: StatisticsPanel) -> None:
    overview = _overview(
        stale_price_cards=[StalePriceEntry(card=_card(id=1), days_since_update=100)]
    )

    panel.show_overview(overview)

    assert panel._bulk_update_button.isEnabled()


def test_sealed_bulk_update_button_disabled_when_no_stale_products(
    panel: StatisticsPanel,
) -> None:
    panel.show_overview(_overview(sealed_stale_price_products=[]))

    assert not panel._sealed_bulk_update_button.isEnabled()


def test_bulk_update_button_does_not_emit_when_no_stale_cards(panel: StatisticsPanel) -> None:
    panel.show_overview(_overview(stale_price_cards=[]))
    received: list[list[int]] = []
    panel.bulk_price_lookup_requested.connect(received.append)

    panel._on_bulk_update_clicked()

    assert received == []


def test_set_bulk_update_running_disables_button(panel: StatisticsPanel) -> None:
    overview = _overview(
        stale_price_cards=[StalePriceEntry(card=_card(id=1), days_since_update=100)]
    )
    panel.show_overview(overview)

    panel.set_bulk_update_running(True)
    assert not panel._bulk_update_button.isEnabled()

    panel.set_bulk_update_running(False)
    assert panel._bulk_update_button.isEnabled()


def test_set_sealed_bulk_update_running_disables_button(panel: StatisticsPanel) -> None:
    overview = _overview(
        sealed_stale_price_products=[
            StaleSealedPriceEntry(product=_sealed(id=1), days_since_update=100)
        ]
    )
    panel.show_overview(overview)

    panel.set_sealed_bulk_update_running(True)
    assert not panel._sealed_bulk_update_button.isEnabled()

    panel.set_sealed_bulk_update_running(False)
    assert panel._sealed_bulk_update_button.isEnabled()


def test_value_over_time_chart_hidden_with_fewer_than_two_points(panel: StatisticsPanel) -> None:
    overview = _overview(
        value_over_time=[ValueOverTimePoint(recorded_at="2026-01-01T00:00:00+00:00", total_value=10.0)]
    )
    panel.show_overview(overview)

    assert panel._value_chart_view.isHidden()
    assert not panel._value_chart_placeholder.isHidden()


def test_value_over_time_chart_shown_with_two_or_more_points(panel: StatisticsPanel) -> None:
    overview = _overview(
        value_over_time=[
            ValueOverTimePoint(recorded_at="2026-01-01T00:00:00+00:00", total_value=10.0),
            ValueOverTimePoint(recorded_at="2026-01-02T00:00:00+00:00", total_value=15.0),
        ]
    )
    panel.show_overview(overview)

    assert not panel._value_chart_view.isHidden()
    assert panel._value_chart_placeholder.isHidden()
    assert len(panel._value_chart.series()) == 1
