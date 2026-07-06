"""Tests for SealedProductInfoWorker's signal wiring.

Mirrors ``test_product_info_worker.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import SealedProductInfo
from app.ui.app import build_application
from app.ui.workers import sealed_product_info_worker as worker_module
from app.ui.workers.sealed_product_info_worker import SealedProductInfoWorker

_INFO = SealedProductInfo(name="Base Set Booster Box", category="Booster Box")


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_parsed_info(qapp, monkeypatch) -> None:
    monkeypatch.setattr(
        worker_module, "read_sealed_product_info", lambda url, capture_image=False: _INFO
    )
    worker = SealedProductInfoWorker("https://cardmarket.com/x")
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [_INFO]
    assert failed == []


def test_failed_emitted_on_reader_error(qapp, monkeypatch) -> None:
    def _raise(url: str, capture_image: bool = False) -> None:
        raise BrowserPriceReaderError("Tab nicht gefunden.")

    monkeypatch.setattr(worker_module, "read_sealed_product_info", _raise)
    worker = SealedProductInfoWorker("https://cardmarket.com/x")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == ["Tab nicht gefunden."]


def test_unexpected_exception_emits_failed_not_a_crash(qapp, monkeypatch) -> None:
    def _raise(url: str, capture_image: bool = False) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker_module, "read_sealed_product_info", _raise)
    worker = SealedProductInfoWorker("https://cardmarket.com/x")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "boom" in failed[0]
