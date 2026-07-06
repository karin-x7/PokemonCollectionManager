"""Tests for CardmarketSearchWorker's signal wiring.

``run()`` is called directly (rather than ``start()``) so the worker body
executes synchronously in the test thread — deterministic, no real
threading/timing involved. Mirrors ``test_product_info_worker.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import CardmarketSearchResult
from app.ui.app import build_application
from app.ui.workers import cardmarket_search_worker as worker_module
from app.ui.workers.cardmarket_search_worker import CardmarketSearchWorker

_RESULT = CardmarketSearchResult(
    name="Poké Pad",
    set_name="Perfect Order",
    card_number="POR 113",
    price_hint="9,00 €",
    raw_text="Poké Pad Perfect Order \xa0Poké Pad (POR 113) From 9,00 €",
)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_search_results(qapp, monkeypatch) -> None:
    monkeypatch.setattr(worker_module, "search_cardmarket", lambda name: [_RESULT])
    worker = CardmarketSearchWorker("Poke Pad")
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [[_RESULT]]
    assert failed == []


def test_succeeded_emitted_with_empty_list_when_nothing_found(qapp, monkeypatch) -> None:
    monkeypatch.setattr(worker_module, "search_cardmarket", lambda name: [])
    worker = CardmarketSearchWorker("Totally Unknown Card")
    succeeded = []
    worker.succeeded.connect(succeeded.append)

    worker.run()

    assert succeeded == [[]]


def test_failed_emitted_on_reader_error(qapp, monkeypatch) -> None:
    def _raise(name: str) -> None:
        raise BrowserPriceReaderError("Tab nicht gefunden.")

    monkeypatch.setattr(worker_module, "search_cardmarket", _raise)
    worker = CardmarketSearchWorker("Poke Pad")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == ["Tab nicht gefunden."]


def test_unexpected_exception_emits_failed_not_a_crash(qapp, monkeypatch) -> None:
    def _raise(name: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker_module, "search_cardmarket", _raise)
    worker = CardmarketSearchWorker("Poke Pad")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "boom" in failed[0]
