"""Tests for SealedPriceController wiring: panel -> SealedPriceLookupWorker -> refresh.

Mirrors ``test_price_controller.py``. ``SealedPriceLookupWorker.start`` is
monkeypatched to run synchronously instead of spawning a real background
thread.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QMainWindow, QStatusBar

from app.models.sealed_product import SealedProduct
from app.services.exceptions import SealedProductNotFoundError
from app.ui.app import build_application
from app.ui.controllers.sealed_price_controller import SealedPriceController
from app.ui.widgets.busy_overlay import BusyOverlay
from app.ui.widgets.sealed_product_detail_panel import SealedProductDetailPanel
from app.ui.widgets.sealed_product_list_panel import SealedProductListPanel
from app.ui.workers.open_sealed_cardmarket_link_worker import OpenSealedCardmarketLinkWorker
from app.ui.workers.sealed_price_lookup_worker import SealedPriceLookupWorker

_PRICED = SealedProduct(
    id=1, name="Base Set Booster Box", current_price=5000.0, price_currency="EUR"
)
_UNPRICED = SealedProduct(id=1, name="Base Set Booster Box", current_price=None)


class FakeSealedPriceService:
    def __init__(
        self,
        product: SealedProduct | None = None,
        error: Exception | None = None,
        display_url: str | None = "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box",
    ) -> None:
        self._product = product
        self._error = error
        self._display_url = display_url
        self.calls: list[int] = []
        self.link_calls: list[int] = []

    def update_price_for_product(self, product_id: int) -> SealedProduct:
        self.calls.append(product_id)
        if self._error is not None:
            raise self._error
        return self._product

    def resolve_display_url(self, product_id: int) -> str | None:
        self.link_calls.append(product_id)
        if self._error is not None:
            raise self._error
        return self._display_url


class FakeProductController:
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

    def set_bulk_sealed_update_running(self, running: bool) -> None:
        self.bulk_running_calls.append(running)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(SealedPriceLookupWorker, "start", fake_start)
    monkeypatch.setattr(OpenSealedCardmarketLinkWorker, "start", fake_start)


@pytest.fixture(autouse=True)
def fake_open_cardmarket_link(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "app.ui.workers.open_sealed_cardmarket_link_worker.open_cardmarket_link",
        lambda url: calls.append(url),
    )
    return calls


@pytest.fixture
def main_window(qapp) -> QMainWindow:
    window = QMainWindow()
    window.setStatusBar(QStatusBar())
    window.busy_overlay = BusyOverlay(window)
    yield window
    window.close()


def _controller(main_window, service, product_controller) -> SealedPriceController:
    return SealedPriceController(main_window, lambda: (service, None), product_controller)


def test_successful_lookup_refreshes_and_shows_price(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    controller.start_lookup(1)

    assert service.calls == [1]
    assert product_controller.refresh_calls == 1
    assert "5.000,00" in main_window.statusBar().currentMessage()


def test_lookup_with_no_price_found_still_refreshes(main_window) -> None:
    service = FakeSealedPriceService(product=_UNPRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    controller.start_lookup(1)

    assert product_controller.refresh_calls == 1
    assert "No price found" in main_window.statusBar().currentMessage()


def test_service_error_shows_message_and_does_not_refresh(main_window) -> None:
    service = FakeSealedPriceService(error=SealedProductNotFoundError(1))
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    controller.start_lookup(1)

    assert product_controller.refresh_calls == 0
    assert "1" in main_window.statusBar().currentMessage()


def test_successful_lookup_also_refreshes_statistics_controller_if_given(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    statistics_controller = FakeStatisticsController()
    controller = SealedPriceController(
        main_window,
        lambda: (service, None),
        product_controller,
        statistics_controller=statistics_controller,
    )

    controller.start_lookup(1)

    assert statistics_controller.refresh_calls == 1


def test_a_second_request_while_running_is_ignored(monkeypatch, main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    monkeypatch.setattr(SealedPriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.start_lookup(1)

    assert service.calls == [1]


def test_bulk_update_looks_up_every_product_in_order_and_refreshes_each_time(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    controller.start_bulk_update([1, 2, 3])

    assert service.calls == [1, 2, 3]
    assert product_controller.refresh_calls == 3
    assert "updated" in main_window.statusBar().currentMessage()


def test_bulk_update_toggles_statistics_controller_running_state(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    statistics_controller = FakeStatisticsController()
    controller = SealedPriceController(
        main_window,
        lambda: (service, None),
        product_controller,
        statistics_controller=statistics_controller,
    )

    controller.start_bulk_update([1, 2])

    assert statistics_controller.bulk_running_calls == [True, False]


def test_bulk_update_is_ignored_while_a_lookup_is_already_running(
    monkeypatch, main_window
) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    monkeypatch.setattr(SealedPriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.start_bulk_update([2, 3])

    assert service.calls == [1]


def test_bulk_update_with_empty_list_does_nothing(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    controller.start_bulk_update([])

    assert service.calls == []


def test_detail_panel_price_button_click_triggers_lookup(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    detail_panel = SealedProductDetailPanel()
    SealedPriceController(
        main_window, lambda: (service, None), product_controller, detail_panel=detail_panel
    )

    detail_panel.price_lookup_requested.emit(1)

    assert service.calls == [1]


def test_button_is_reenabled_after_a_completed_lookup(main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    detail_panel = SealedProductDetailPanel()
    SealedPriceController(
        main_window, lambda: (service, None), product_controller, detail_panel=detail_panel
    )
    detail_panel._price_button.setEnabled(True)
    detail_panel._current_product_id = 1

    detail_panel.price_lookup_requested.emit(1)

    assert detail_panel._price_button.isEnabled()


def test_context_menu_signal_triggers_open_cardmarket_link(main_window, fake_open_cardmarket_link) -> None:
    service = FakeSealedPriceService()
    product_controller = FakeProductController()
    list_panel = SealedProductListPanel()
    SealedPriceController(
        main_window, lambda: (service, None), product_controller, list_panel=list_panel
    )

    list_panel.open_cardmarket_link_requested.emit(1)

    assert service.link_calls == [1]
    assert fake_open_cardmarket_link == [service._display_url]
    assert "opened" in main_window.statusBar().currentMessage()


def test_open_cardmarket_link_with_no_known_url_shows_message(main_window, fake_open_cardmarket_link) -> None:
    service = FakeSealedPriceService(display_url=None)
    product_controller = FakeProductController()
    controller = SealedPriceController(main_window, lambda: (service, None), product_controller)

    controller.open_cardmarket_link(1)

    assert fake_open_cardmarket_link == []
    assert "No Cardmarket link known" in main_window.statusBar().currentMessage()


def test_open_cardmarket_link_is_ignored_while_a_lookup_is_running(monkeypatch, main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    monkeypatch.setattr(SealedPriceLookupWorker, "start", lambda self: self.run())
    controller.start_lookup(1)
    controller.open_cardmarket_link(1)

    assert service.link_calls == []


def test_lookup_is_ignored_while_open_cardmarket_link_is_running(monkeypatch, main_window) -> None:
    service = FakeSealedPriceService(product=_PRICED)
    product_controller = FakeProductController()
    controller = _controller(main_window, service, product_controller)

    monkeypatch.setattr(OpenSealedCardmarketLinkWorker, "start", lambda self: self.run())
    controller.open_cardmarket_link(1)
    controller.start_lookup(1)

    assert service.calls == []
