"""Tests for CardmarketSearchResolveWorker's signal wiring.

``run()`` is called directly (rather than ``start()``) so the worker body
executes synchronously in the test thread — deterministic, no real
threading/timing involved. Mirrors ``test_cardmarket_search_worker.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import CardmarketSearchResult
from app.ui.app import build_application
from app.ui.workers import cardmarket_search_resolve_worker as worker_module
from app.ui.workers.cardmarket_search_resolve_worker import CardmarketSearchResolveWorker

_RESULT = CardmarketSearchResult(
    name="Poké Pad",
    set_name="Perfect Order",
    card_number="POR 113",
    price_hint="9,00 €",
    raw_text="Poké Pad Perfect Order \xa0Poké Pad (POR 113) From 9,00 €",
)
_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Perfect-Order/Poke-Pad-V2-POR113"


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_resolved_url(qapp, monkeypatch) -> None:
    monkeypatch.setattr(
        worker_module, "resolve_cardmarket_search_result", lambda name, chosen: _URL
    )
    worker = CardmarketSearchResolveWorker("Poke Pad", _RESULT)
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [_URL]
    assert failed == []


def test_failed_emitted_on_reader_error(qapp, monkeypatch) -> None:
    def _raise(name: str, chosen: CardmarketSearchResult) -> None:
        raise BrowserPriceReaderError("Treffer nicht wiedergefunden.")

    monkeypatch.setattr(worker_module, "resolve_cardmarket_search_result", _raise)
    worker = CardmarketSearchResolveWorker("Poke Pad", _RESULT)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == ["Treffer nicht wiedergefunden."]


def test_unexpected_exception_emits_failed_not_a_crash(qapp, monkeypatch) -> None:
    def _raise(name: str, chosen: CardmarketSearchResult) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker_module, "resolve_cardmarket_search_result", _raise)
    worker = CardmarketSearchResolveWorker("Poke Pad", _RESULT)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "boom" in failed[0]
