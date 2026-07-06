"""Tests for SealedEntryController: add dialog -> SealedProductInfoWorker -> product controller.

Both the add dialog and the worker's ``start()`` are monkeypatched so this
runs headlessly/deterministically, without a real modal or a real Chrome
tab ever appearing.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QDialog, QMainWindow

from app.models.enums import Language
from app.models.sealed_product import SealedProductDetailsValues
from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import SealedProductInfo
from app.ui.app import build_application
from app.ui.controllers.sealed_entry_controller import SealedEntryController
from app.ui.workers.sealed_product_info_worker import SealedProductInfoWorker

_INFO = SealedProductInfo(name="Base Set Booster Box", category="Booster Box", photo_path="/tmp/x.png")
_URL = "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box"
_VALUES = SealedProductDetailsValues(language=Language.GERMAN, quantity=3, notes="OVP")


class FakeAcceptedDialog:
    def __init__(self, url: str = _URL, values: SealedProductDetailsValues = _VALUES) -> None:
        self._url = url
        self._values = values

    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_url(self) -> str:
        return self._url

    def get_values(self) -> SealedProductDetailsValues:
        return self._values


class FakeCancelledDialog:
    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Rejected

    def get_url(self):  # pragma: no cover -- must never be called
        raise AssertionError("get_url() should not be called after a cancelled dialog")


class FakeProductController:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def add_product(
        self, name: str, category: str, values: SealedProductDetailsValues, photo_path
    ) -> None:
        self.calls.append((name, category, values, photo_path))


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_worker(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(SealedProductInfoWorker, "start", fake_start)


@pytest.fixture
def main_window(qapp) -> QMainWindow:
    window = QMainWindow()
    from PySide6.QtWidgets import QStatusBar

    window.setStatusBar(QStatusBar())
    yield window
    window.close()


def test_cancelling_the_add_dialog_does_nothing(monkeypatch, main_window) -> None:
    product_controller = FakeProductController()
    controller = SealedEntryController(main_window, product_controller)
    monkeypatch.setattr(
        "app.ui.controllers.sealed_entry_controller.SealedProductAddDialog", FakeCancelledDialog()
    )

    controller.start()

    assert product_controller.calls == []


def test_successful_lookup_creates_the_product_directly(monkeypatch, main_window) -> None:
    product_controller = FakeProductController()
    controller = SealedEntryController(main_window, product_controller)
    monkeypatch.setattr(
        "app.ui.controllers.sealed_entry_controller.SealedProductAddDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.sealed_product_info_worker.read_sealed_product_info",
        lambda url, capture_image=False: _INFO,
    )

    controller.start()

    assert len(product_controller.calls) == 1
    name, category, values, photo_path = product_controller.calls[0]
    assert name == "Base Set Booster Box"
    assert category == "Booster Box"
    assert photo_path == "/tmp/x.png"
    # The dialog's own language/quantity/notes are preserved, and the URL
    # (not asked for in the dialog's own get_values()) is filled in from
    # what was actually looked up.
    assert values.language is Language.GERMAN
    assert values.quantity == 3
    assert values.notes == "OVP"
    assert values.cardmarket_url == _URL


def test_failed_lookup_shows_message_and_does_not_create(monkeypatch, main_window) -> None:
    product_controller = FakeProductController()
    controller = SealedEntryController(main_window, product_controller)
    monkeypatch.setattr(
        "app.ui.controllers.sealed_entry_controller.SealedProductAddDialog", FakeAcceptedDialog()
    )

    def _raise(url: str, capture_image: bool = False) -> None:
        raise BrowserPriceReaderError("Seite nicht erkannt.")

    monkeypatch.setattr("app.ui.workers.sealed_product_info_worker.read_sealed_product_info", _raise)

    controller.start()

    assert product_controller.calls == []
    assert "Seite nicht erkannt." in main_window.statusBar().currentMessage()


def test_a_second_request_while_running_is_ignored(monkeypatch, main_window) -> None:
    product_controller = FakeProductController()
    controller = SealedEntryController(main_window, product_controller)
    monkeypatch.setattr(
        "app.ui.controllers.sealed_entry_controller.SealedProductAddDialog", FakeAcceptedDialog()
    )
    monkeypatch.setattr(
        "app.ui.workers.sealed_product_info_worker.read_sealed_product_info",
        lambda url, capture_image=False: _INFO,
    )
    monkeypatch.setattr(SealedProductInfoWorker, "start", lambda self: self.run())

    controller.start()
    controller.start()

    assert len(product_controller.calls) == 1
