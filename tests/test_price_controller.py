"""Tests for PriceController wiring: panel -> PriceLookupWorker -> CardController.refresh().

``PriceLookupWorker.start`` is monkeypatched to run synchronously (``run()``
then emit ``finished``) instead of spawning a real background thread —
deterministic, no event-loop juggling needed.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import Card
from app.services.exceptions import CardNotFoundError
from app.ui.app import build_application
from app.ui.controllers.price_controller import PriceController
from app.ui.main_window import MainWindow
from app.ui.workers.price_lookup_worker import PriceLookupWorker

_PRICED_CARD = Card(id=1, collection_id=1, name="Xatu", current_price=13.90, price_currency="EUR")
_UNPRICED_CARD = Card(id=1, collection_id=1, name="Xatu", current_price=None)


class FakePriceService:
    def __init__(self, card: Card | None = None, error: Exception | None = None) -> None:
        self._card = card
        self._error = error
        self.calls: list[int] = []

    def update_price_for_card(self, card_id: int) -> Card:
        self.calls.append(card_id)
        if self._error is not None:
            raise self._error
        return self._card


class FakeCardController:
    def __init__(self) -> None:
        self.refresh_calls = 0

    def refresh(self) -> None:
        self.refresh_calls += 1


class FakeStatisticsController:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self.bulk_running_calls: list[bool] = []

    def refresh(self) -> None:
        self.refresh_calls += 1

    def set_bulk_card_update_running(self, running: bool) -> None:
        self.bulk_running_calls.append(running)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(PriceLookupWorker, "start", fake_start)


@pytest.fixture
def main_window(qapp) -> MainWindow:
    window = MainWindow()
    yield window
    window.close()


def _controller(main_window: MainWindow, service, card_controller) -> PriceController:
    return PriceController(
        main_window, main_window.card_detail_panel, lambda: (service, None), card_controller
    )


def test_successful_lookup_refreshes_card_controller_and_shows_price(
    main_window: MainWindow,
) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    _controller(main_window, service, card_controller)

    main_window.card_detail_panel.price_lookup_requested.emit(1)

    assert service.calls == [1]
    assert card_controller.refresh_calls == 1
    assert "13.90" in main_window.statusBar().currentMessage()


def test_lookup_with_no_price_found_still_refreshes(main_window: MainWindow) -> None:
    service = FakePriceService(card=_UNPRICED_CARD)
    card_controller = FakeCardController()
    _controller(main_window, service, card_controller)

    main_window.card_detail_panel.price_lookup_requested.emit(1)

    assert card_controller.refresh_calls == 1
    assert "No price found" in main_window.statusBar().currentMessage()


def test_service_error_shows_message_and_does_not_refresh(main_window: MainWindow) -> None:
    service = FakePriceService(error=CardNotFoundError(1))
    card_controller = FakeCardController()
    _controller(main_window, service, card_controller)

    main_window.card_detail_panel.price_lookup_requested.emit(1)

    assert card_controller.refresh_calls == 0
    assert "1" in main_window.statusBar().currentMessage()


def test_button_is_reenabled_after_a_completed_lookup(main_window: MainWindow) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    _controller(main_window, service, card_controller)
    main_window.card_detail_panel._price_button.setEnabled(True)
    main_window.card_detail_panel._current_card_id = 1

    main_window.card_detail_panel.price_lookup_requested.emit(1)

    assert main_window.card_detail_panel._price_button.isEnabled()


def test_a_second_request_while_running_is_ignored(monkeypatch, main_window: MainWindow) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    controller = _controller(main_window, service, card_controller)

    # start() runs synchronously but (unlike the autouse fixture) never
    # emits `finished`, simulating a lookup that's still in progress.
    monkeypatch.setattr(PriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.start_lookup(1)

    assert service.calls == [1]


def test_successful_lookup_also_refreshes_statistics_controller_if_given(
    main_window: MainWindow,
) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    statistics_controller = FakeStatisticsController()
    PriceController(
        main_window,
        main_window.card_detail_panel,
        lambda: (service, None),
        card_controller,
        statistics_controller=statistics_controller,
    )

    main_window.card_detail_panel.price_lookup_requested.emit(1)

    assert statistics_controller.refresh_calls == 1


def test_bulk_update_looks_up_every_card_in_order_and_refreshes_each_time(
    main_window: MainWindow,
) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    controller = _controller(main_window, service, card_controller)

    controller.start_bulk_update([1, 2, 3])

    assert service.calls == [1, 2, 3]
    assert card_controller.refresh_calls == 3
    assert "aktualisiert" in main_window.statusBar().currentMessage()


def test_bulk_update_toggles_statistics_controller_running_state(
    main_window: MainWindow,
) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    statistics_controller = FakeStatisticsController()
    controller = PriceController(
        main_window,
        main_window.card_detail_panel,
        lambda: (service, None),
        card_controller,
        statistics_controller=statistics_controller,
    )

    controller.start_bulk_update([1, 2])

    assert statistics_controller.bulk_running_calls == [True, False]


def test_bulk_update_is_ignored_while_a_lookup_is_already_running(
    monkeypatch, main_window: MainWindow
) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    controller = _controller(main_window, service, card_controller)

    monkeypatch.setattr(PriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.start_bulk_update([2, 3])

    assert service.calls == [1]


def test_bulk_update_with_empty_list_does_nothing(main_window: MainWindow) -> None:
    service = FakePriceService(card=_PRICED_CARD)
    card_controller = FakeCardController()
    controller = _controller(main_window, service, card_controller)

    controller.start_bulk_update([])

    assert service.calls == []


def test_statistics_panel_button_triggers_the_same_lookup(main_window: MainWindow) -> None:
    # Wired for real in MainWindow's own construction -- verifies the
    # inline "Preis aktualisieren" button in the Statistiken tab reaches
    # the real PriceController, not just CardDetailPanel's own button.
    #
    # Reassigning an *instance* attribute (e.g.
    # ``main_window.price_controller.start_lookup = ...``) would NOT
    # actually intercept this: the signal was already connected to the
    # original bound method inside MainWindow's own construction, and Qt
    # keeps that reference regardless of what the attribute is reassigned
    # to afterwards. A first, flawed version of this test relied on exactly
    # that and ended up triggering a *real* Cardmarket lookup (real Chrome,
    # real network) for a nonexistent card id during test runs. Disconnect
    # the real slot and attach a spy instead, the same pattern already used
    # for the toolbar search button in test_ui_smoke.py.
    main_window.statistics_panel.price_lookup_requested.disconnect(
        main_window.price_controller.start_lookup
    )
    calls: list[int] = []
    main_window.statistics_panel.price_lookup_requested.connect(calls.append)

    main_window.statistics_panel.price_lookup_requested.emit(7)

    assert calls == [7]
