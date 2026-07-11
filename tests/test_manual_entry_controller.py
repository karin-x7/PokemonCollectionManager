"""Tests for ManualEntryController: link dialog -> ProductInfoWorker -> CardController.

Both the link dialog and the worker's ``start()`` are monkeypatched so this
runs headlessly/deterministically, without a real modal or a real Chrome tab
ever appearing -- mirrors ``test_export_controller.py``/``test_price_controller.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import ProductInfo
from app.ui.app import build_application
from app.ui.controllers.manual_entry_controller import ManualEntryController
from app.ui.main_window import MainWindow
from app.ui.workers.product_info_worker import ProductInfoWorker

_INFO = ProductInfo(name="Venusaur", set_name="Legendary Collection", card_number="18")
_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Legendary-Collection/Venusaur-LC18"


class FakeAcceptedDialog:
    """Stands in for ManualEntryDialog: always "accepted" with a fixed URL."""

    def __init__(self, url: str = _URL) -> None:
        self._url = url

    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_url(self) -> str:
        return self._url


class FakeCancelledDialog:
    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Rejected

    def get_url(self):  # pragma: no cover -- must never be called
        raise AssertionError("get_url() should not be called after a cancelled dialog")


class FakeCardController:
    def __init__(self, collection_id: int | None = 1) -> None:
        self.collection_id = collection_id
        self.calls: list[tuple] = []

    def prompt_add_manual(self, info: ProductInfo, url: str) -> None:
        self.calls.append((info, url))


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(ProductInfoWorker, "start", fake_start)


@pytest.fixture
def main_window(qapp) -> MainWindow:
    window = MainWindow()
    yield window
    window.close()


def test_no_collection_selected_shows_message_and_no_dialog(
    monkeypatch, main_window: MainWindow
) -> None:
    card_controller = FakeCardController(collection_id=None)
    controller = ManualEntryController(main_window, card_controller)
    monkeypatch.setattr(
        "app.ui.controllers.manual_entry_controller.ManualEntryDialog", FakeCancelledDialog()
    )
    messages: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args: messages.append(args[-1])
    )

    controller.start()

    assert len(messages) == 1
    assert "collection" in messages[0]
    assert card_controller.calls == []


def test_cancelling_the_link_dialog_does_nothing(monkeypatch, main_window: MainWindow) -> None:
    card_controller = FakeCardController()
    controller = ManualEntryController(main_window, card_controller)
    monkeypatch.setattr(
        "app.ui.controllers.manual_entry_controller.ManualEntryDialog", FakeCancelledDialog()
    )

    controller.start()

    assert card_controller.calls == []


def test_successful_lookup_forwards_info_to_card_controller(
    monkeypatch, main_window: MainWindow
) -> None:
    card_controller = FakeCardController()
    controller = ManualEntryController(main_window, card_controller)
    monkeypatch.setattr(
        "app.ui.controllers.manual_entry_controller.ManualEntryDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.product_info_worker.read_product_info", lambda url, **kwargs: _INFO
    )

    controller.start()

    assert card_controller.calls == [(_INFO, _URL)]


def test_failed_lookup_shows_message_and_does_not_forward(
    monkeypatch, main_window: MainWindow
) -> None:
    card_controller = FakeCardController()
    controller = ManualEntryController(main_window, card_controller)
    monkeypatch.setattr(
        "app.ui.controllers.manual_entry_controller.ManualEntryDialog", FakeAcceptedDialog()
    )

    def _raise(url: str, **kwargs) -> None:
        raise BrowserPriceReaderError("Seite nicht erkannt.")

    monkeypatch.setattr("app.ui.workers.product_info_worker.read_product_info", _raise)

    controller.start()

    assert card_controller.calls == []
    assert "Seite nicht erkannt." in main_window.statusBar().currentMessage()


def test_busy_overlay_shown_during_lookup_and_hidden_afterward(
    monkeypatch, main_window: MainWindow
) -> None:
    # Real, live-reported bug: the only feedback during the (sometimes
    # several-seconds-long) page read was an easy-to-miss status-bar
    # message -- price lookups already show a busy overlay for the same
    # kind of browser-automation wait (see PriceController._start()).
    card_controller = FakeCardController()
    controller = ManualEntryController(main_window, card_controller)
    monkeypatch.setattr(
        "app.ui.controllers.manual_entry_controller.ManualEntryDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.product_info_worker.read_product_info", lambda url, **kwargs: _INFO
    )
    calls: list[str] = []
    monkeypatch.setattr(
        main_window.busy_overlay, "show_busy", lambda message: calls.append(("show", message))
    )
    monkeypatch.setattr(main_window.busy_overlay, "hide_busy", lambda: calls.append(("hide",)))

    controller.start()

    assert calls[0][0] == "show"
    assert calls[-1] == ("hide",)


def test_a_second_request_while_running_is_ignored(monkeypatch, main_window: MainWindow) -> None:
    card_controller = FakeCardController()
    controller = ManualEntryController(main_window, card_controller)
    monkeypatch.setattr(
        "app.ui.controllers.manual_entry_controller.ManualEntryDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.product_info_worker.read_product_info", lambda url, **kwargs: _INFO
    )
    # start() runs synchronously but (unlike the autouse fixture) never emits
    # `finished`, simulating a lookup that's still in progress.
    monkeypatch.setattr(ProductInfoWorker, "start", lambda self: self.run())

    controller.start()
    controller.start()

    assert card_controller.calls == [(_INFO, _URL)]
