"""Tests for SealedPriceHistoryDock: chart/list population, % change, reset.

Mirrors ``test_price_history_dock.py``, ``Card``/``PriceRecord`` swapped for
``SealedProduct``/``SealedPriceRecord``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QMessageBox

from app.models.enums import PriceQuality
from app.models.sealed_price import SealedPriceRecord
from app.models.sealed_product import SealedProduct
from app.ui.app import build_application
from app.ui.widgets.sealed_price_history_dock import SealedPriceHistoryDock


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def dock(qapp) -> SealedPriceHistoryDock:
    return SealedPriceHistoryDock()


def _product(**overrides) -> SealedProduct:
    base = dict(id=1, name="Base Set Booster Box")
    base.update(overrides)
    return SealedProduct(**base)


def _record(price: float, recorded_at: str, **overrides) -> SealedPriceRecord:
    base = dict(
        id=None,
        sealed_product_id=1,
        price=price,
        price_quality=PriceQuality.EXACT,
        recorded_at=recorded_at,
    )
    base.update(overrides)
    return SealedPriceRecord(**base)


def test_fewer_than_two_records_shows_placeholder_not_chart(dock: SealedPriceHistoryDock) -> None:
    dock.show_history(_product(), [_record(10.0, "2026-07-01T00:00:00+00:00")])

    assert dock._chart_view.isHidden()
    assert not dock._placeholder.isHidden()
    assert "10.00" in dock._placeholder.text()


def test_two_or_more_records_shows_chart(dock: SealedPriceHistoryDock) -> None:
    records = [
        _record(10.0, "2026-07-01T00:00:00+00:00"),
        _record(15.0, "2026-07-02T00:00:00+00:00"),
    ]

    dock.show_history(_product(), records)

    assert not dock._chart_view.isHidden()
    assert dock._chart.series()[0].count() == 2


def test_percent_change_positive_is_labelled_and_styled(dock: SealedPriceHistoryDock) -> None:
    records = [
        _record(10.0, "2026-07-01T00:00:00+00:00"),
        _record(15.0, "2026-07-02T00:00:00+00:00"),
    ]

    dock.show_history(_product(), records)

    assert not dock._percent_label.isHidden()
    assert dock._percent_label.text().startswith("+50.0")
    assert dock._percent_label.objectName() == "PercentPositive"


def test_percent_change_negative_is_labelled_and_styled(dock: SealedPriceHistoryDock) -> None:
    records = [
        _record(20.0, "2026-07-01T00:00:00+00:00"),
        _record(15.0, "2026-07-02T00:00:00+00:00"),
    ]

    dock.show_history(_product(), records)

    assert dock._percent_label.text().startswith("−25.0")
    assert dock._percent_label.objectName() == "PercentNegative"


def test_history_list_shows_most_recent_first_capped_at_ten(dock: SealedPriceHistoryDock) -> None:
    records = [_record(float(i), f"2026-07-{i + 1:02d}T00:00:00+00:00") for i in range(12)]

    dock.show_history(_product(), records)

    assert dock._history_list.count() == 10
    assert "11.00" in dock._history_list.item(0).text()


def test_show_empty_resets_everything(dock: SealedPriceHistoryDock) -> None:
    records = [
        _record(10.0, "2026-07-01T00:00:00+00:00"),
        _record(15.0, "2026-07-02T00:00:00+00:00"),
    ]
    dock.show_history(_product(), records)

    dock.show_empty()

    assert dock._chart_view.isHidden()
    assert not dock._percent_label.isVisible()
    assert dock._history_list.count() == 0
    assert not dock._reset_button.isEnabled()


def test_reset_button_disabled_with_no_history(dock: SealedPriceHistoryDock) -> None:
    dock.show_history(_product(), [])

    assert not dock._reset_button.isEnabled()


def test_reset_confirmed_emits_product_id(monkeypatch, dock: SealedPriceHistoryDock) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dock.show_history(_product(id=42), [_record(10.0, "2026-07-01T00:00:00+00:00")])
    received: list[int] = []
    dock.history_reset_requested.connect(received.append)

    dock._on_reset_clicked()

    assert received == [42]


def test_reset_declined_emits_nothing(monkeypatch, dock: SealedPriceHistoryDock) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    dock.show_history(_product(id=42), [_record(10.0, "2026-07-01T00:00:00+00:00")])
    received: list[int] = []
    dock.history_reset_requested.connect(received.append)

    dock._on_reset_clicked()

    assert received == []
