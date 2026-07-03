"""Tests for PriceHistoryChartView's empty/single-point/multi-point states."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import PriceQuality
from app.models.price import PriceRecord
from app.ui.app import build_application
from app.ui.widgets.price_history_chart import PriceHistoryChartView


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def _record(price: float, recorded_at: str, **overrides) -> PriceRecord:
    base = dict(
        id=None,
        card_id=1,
        price=price,
        currency="EUR",
        price_quality=PriceQuality.EXACT,
        rationale="",
        source="cardmarket",
        recorded_at=recorded_at,
    )
    base.update(overrides)
    return PriceRecord(**base)


def test_no_history_shows_placeholder(qapp) -> None:
    view = PriceHistoryChartView()

    view.show_history([])

    assert not view._placeholder.isHidden()
    assert view._chart_view.isHidden()
    assert "kein Preisverlauf" in view._placeholder.text()


def test_single_record_shows_placeholder_with_the_price(qapp) -> None:
    view = PriceHistoryChartView()

    view.show_history([_record(13.90, "2026-07-01T10:00:00+00:00")])

    assert not view._placeholder.isHidden()
    assert view._chart_view.isHidden()
    assert "13.90" in view._placeholder.text()


def test_two_or_more_records_show_the_chart(qapp) -> None:
    view = PriceHistoryChartView()
    records = [
        _record(10.0, "2026-06-01T10:00:00+00:00"),
        _record(15.0, "2026-07-01T10:00:00+00:00"),
    ]

    view.show_history(records)

    assert not view._chart_view.isHidden()
    assert view._placeholder.isHidden()
    assert len(view._chart.series()) == 1
    assert view._chart.series()[0].count() == 2


def test_show_empty_resets_to_placeholder(qapp) -> None:
    view = PriceHistoryChartView()
    view.show_history(
        [_record(10.0, "2026-06-01T10:00:00+00:00"), _record(15.0, "2026-07-01T10:00:00+00:00")]
    )

    view.show_empty()

    assert not view._placeholder.isHidden()
    assert view._chart_view.isHidden()


def test_switching_from_chart_back_to_placeholder_clears_old_series(qapp) -> None:
    view = PriceHistoryChartView()
    view.show_history(
        [_record(10.0, "2026-06-01T10:00:00+00:00"), _record(15.0, "2026-07-01T10:00:00+00:00")]
    )

    view.show_history([_record(20.0, "2026-07-02T10:00:00+00:00")])

    assert len(view._chart.series()) == 0


def test_paint_event_does_not_crash_in_any_state(qapp) -> None:
    view = PriceHistoryChartView()
    view.resize(300, 200)

    view.show_empty()
    assert not view.grab().isNull()

    view.show_history(
        [_record(10.0, "2026-06-01T10:00:00+00:00"), _record(15.0, "2026-07-01T10:00:00+00:00")]
    )
    assert not view.grab().isNull()
