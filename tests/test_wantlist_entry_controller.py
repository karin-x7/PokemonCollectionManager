"""Tests for WantlistEntryController: add dialog -> ProductInfoWorker -> wantlist controller.

Mirrors ``test_sealed_entry_controller.py``. Both the add dialog and the
worker's ``start()`` are monkeypatched so this runs headlessly/
deterministically, without a real modal or a real Chrome tab ever appearing.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QDialog, QMainWindow, QStatusBar

from app.models.enums import Condition, Language
from app.models.wantlist import WantlistItemDetailsValues
from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import ProductInfo
from app.ui.controllers.wantlist_entry_controller import WantlistEntryController
from app.ui.workers.product_info_worker import ProductInfoWorker

_INFO = ProductInfo(name="Charizard", set_name="Base Set", card_number="4", photo_path=None)
_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard"
_VALUES = WantlistItemDetailsValues(
    language=Language.GERMAN, condition=Condition.NEAR_MINT, target_price=300.0, notes="want it"
)


class FakeAcceptedDialog:
    def __init__(self, url: str = _URL, values: WantlistItemDetailsValues = _VALUES) -> None:
        self._url = url
        self._values = values

    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_url(self) -> str:
        return self._url

    def get_values(self) -> WantlistItemDetailsValues:
        return self._values


class FakeCancelledDialog:
    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Rejected

    def get_url(self):  # pragma: no cover -- must never be called
        raise AssertionError("get_url() should not be called after a cancelled dialog")


class FakeWantlistController:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def add_item(
        self, name: str, set_name: str, card_number: str, values: WantlistItemDetailsValues
    ) -> None:
        self.calls.append((name, set_name, card_number, values))


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(ProductInfoWorker, "start", fake_start)


@pytest.fixture
def main_window() -> QMainWindow:
    window = QMainWindow()
    window.setStatusBar(QStatusBar())
    yield window
    window.close()


def test_cancelling_the_add_dialog_does_nothing(monkeypatch, main_window) -> None:
    wantlist_controller = FakeWantlistController()
    controller = WantlistEntryController(main_window, wantlist_controller)
    monkeypatch.setattr(
        "app.ui.controllers.wantlist_entry_controller.WantlistAddDialog", FakeCancelledDialog()
    )

    controller.start()

    assert wantlist_controller.calls == []


def test_successful_lookup_adds_the_item_directly(monkeypatch, main_window) -> None:
    wantlist_controller = FakeWantlistController()
    controller = WantlistEntryController(main_window, wantlist_controller)
    monkeypatch.setattr(
        "app.ui.controllers.wantlist_entry_controller.WantlistAddDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.product_info_worker.read_product_info",
        lambda url, capture_image=False: _INFO,
    )

    controller.start()

    assert len(wantlist_controller.calls) == 1
    name, set_name, card_number, values = wantlist_controller.calls[0]
    assert name == "Charizard"
    assert set_name == "Base Set"
    assert card_number == "4"
    # The dialog's own language/condition/target price/notes are preserved,
    # and the URL (not asked for in the dialog's own get_values()) is filled
    # in from what was actually looked up.
    assert values.language is Language.GERMAN
    assert values.target_price == 300.0
    assert values.notes == "want it"
    assert values.cardmarket_url == _URL


def test_failed_lookup_shows_message_and_does_not_add(monkeypatch, main_window) -> None:
    wantlist_controller = FakeWantlistController()
    controller = WantlistEntryController(main_window, wantlist_controller)
    monkeypatch.setattr(
        "app.ui.controllers.wantlist_entry_controller.WantlistAddDialog", FakeAcceptedDialog()
    )

    def _raise(url: str, capture_image: bool = False) -> None:
        raise BrowserPriceReaderError("Page not recognised.")

    monkeypatch.setattr("app.ui.workers.product_info_worker.read_product_info", _raise)

    controller.start()

    assert wantlist_controller.calls == []
    assert "Page not recognised." in main_window.statusBar().currentMessage()


def test_a_second_request_while_running_is_ignored(monkeypatch, main_window) -> None:
    wantlist_controller = FakeWantlistController()
    controller = WantlistEntryController(main_window, wantlist_controller)
    monkeypatch.setattr(
        "app.ui.controllers.wantlist_entry_controller.WantlistAddDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.product_info_worker.read_product_info",
        lambda url, capture_image=False: _INFO,
    )
    monkeypatch.setattr(ProductInfoWorker, "start", lambda self: self.run())

    controller.start()
    controller.start()

    assert len(wantlist_controller.calls) == 1
