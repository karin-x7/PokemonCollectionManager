"""Tests for WantlistPriceController wiring: panel -> WantlistPriceLookupWorker -> refresh.

Mirrors ``test_sealed_price_controller.py``. ``WantlistPriceLookupWorker.start``
is monkeypatched to run synchronously instead of spawning a real background
thread.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QMainWindow, QStatusBar

from app.models.wantlist import WantlistItem
from app.services.exceptions import WantlistItemNotFoundError
from app.ui.app import build_application
from app.ui.controllers.wantlist_price_controller import WantlistPriceController
from app.ui.widgets.busy_overlay import BusyOverlay
from app.ui.widgets.wantlist_panel import WantlistPanel
from app.ui.workers.wantlist_price_lookup_worker import WantlistPriceLookupWorker

_PRICED = WantlistItem(id=1, name="Charizard", current_price=450.0, price_currency="EUR", target_price=500.0)
_BELOW_TARGET = WantlistItem(id=1, name="Charizard", current_price=450.0, price_currency="EUR", target_price=500.0)
_UNPRICED = WantlistItem(id=1, name="Charizard", current_price=None, target_price=500.0)


class FakeWantlistPriceService:
    def __init__(self, item: WantlistItem | None = None, error: Exception | None = None) -> None:
        self._item = item
        self._error = error
        self.calls: list[int] = []

    def update_price_for_item(self, item_id: int) -> WantlistItem:
        self.calls.append(item_id)
        if self._error is not None:
            raise self._error
        return self._item


class FakeWantlistController:
    def __init__(self) -> None:
        self.refresh_calls = 0

    def refresh(self) -> None:
        self.refresh_calls += 1


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(WantlistPriceLookupWorker, "start", fake_start)


@pytest.fixture
def main_window(qapp) -> QMainWindow:
    window = QMainWindow()
    window.setStatusBar(QStatusBar())
    window.busy_overlay = BusyOverlay(window)
    yield window
    window.close()


def _controller(main_window, service, wantlist_controller) -> WantlistPriceController:
    panel = WantlistPanel()
    return WantlistPriceController(main_window, panel, lambda: (service, None), wantlist_controller)


def test_successful_lookup_refreshes_and_shows_price(main_window) -> None:
    service = FakeWantlistPriceService(item=_PRICED)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    controller.start_lookup(1)

    assert service.calls == [1]
    assert wantlist_controller.refresh_calls == 1
    assert "450.00" in main_window.statusBar().currentMessage()


def test_below_target_price_is_flagged_in_the_status_message(main_window) -> None:
    service = FakeWantlistPriceService(item=_BELOW_TARGET)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    controller.start_lookup(1)

    assert "Below target" in main_window.statusBar().currentMessage()


def test_lookup_with_no_price_found_still_refreshes(main_window) -> None:
    service = FakeWantlistPriceService(item=_UNPRICED)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    controller.start_lookup(1)

    assert wantlist_controller.refresh_calls == 1
    assert "No price found" in main_window.statusBar().currentMessage()


def test_service_error_shows_message_and_does_not_refresh(main_window) -> None:
    service = FakeWantlistPriceService(error=WantlistItemNotFoundError(1))
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    controller.start_lookup(1)

    assert wantlist_controller.refresh_calls == 0
    assert "1" in main_window.statusBar().currentMessage()


def test_a_second_request_while_running_is_ignored(monkeypatch, main_window) -> None:
    service = FakeWantlistPriceService(item=_PRICED)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    monkeypatch.setattr(WantlistPriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.start_lookup(1)

    assert service.calls == [1]


def test_bulk_update_looks_up_every_item_in_order_and_refreshes_each_time(main_window) -> None:
    service = FakeWantlistPriceService(item=_PRICED)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    controller.start_bulk_update([1, 2, 3])

    assert service.calls == [1, 2, 3]
    assert wantlist_controller.refresh_calls == 3
    assert "checked" in main_window.statusBar().currentMessage().lower()


def test_bulk_update_is_ignored_while_a_lookup_is_already_running(
    monkeypatch, main_window
) -> None:
    service = FakeWantlistPriceService(item=_PRICED)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    monkeypatch.setattr(WantlistPriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.start_bulk_update([2, 3])

    assert service.calls == [1]


def test_bulk_update_with_empty_list_does_nothing(main_window) -> None:
    service = FakeWantlistPriceService(item=_PRICED)
    wantlist_controller = FakeWantlistController()
    controller = _controller(main_window, service, wantlist_controller)

    controller.start_bulk_update([])

    assert service.calls == []
