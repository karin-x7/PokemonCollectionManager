"""Tests for PriceLookupWorker's signal wiring.

``run()`` is called directly (rather than ``start()``) so the worker body
executes synchronously in the test thread — deterministic, no real
threading/timing involved.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.card import Card
from app.services.exceptions import CardNotFoundError
from app.ui.app import build_application
from app.ui.workers.price_lookup_worker import PriceLookupWorker

_CARD = Card(id=1, collection_id=1, name="Xatu")


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


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_updated_card(qapp) -> None:
    service = FakePriceService(card=_CARD)
    worker = PriceLookupWorker(lambda: (service, None), card_id=1)
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [_CARD]
    assert failed == []
    assert service.calls == [1]


def test_failed_emitted_on_service_error(qapp) -> None:
    service = FakePriceService(error=CardNotFoundError(1))
    worker = PriceLookupWorker(lambda: (service, None), card_id=1)
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == []
    assert len(failed) == 1
    assert "1" in failed[0]


def test_unexpected_exception_emits_failed_not_a_crash(qapp) -> None:
    # A SQLite-connections-across-threads error (or any other bug) must be
    # caught and surfaced, not just propagate out of the thread silently --
    # this runs under pythonw with no console to print an uncaught traceback.
    service = FakePriceService(error=RuntimeError("boom"))
    worker = PriceLookupWorker(lambda: (service, None), card_id=1)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "boom" in failed[0]


class _FakeDatabase:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_database_is_closed_after_a_successful_lookup(qapp) -> None:
    service = FakePriceService(card=_CARD)
    database = _FakeDatabase()
    worker = PriceLookupWorker(lambda: (service, database), card_id=1)

    worker.run()

    assert database.closed is True


def test_database_is_closed_even_after_a_failed_lookup(qapp) -> None:
    service = FakePriceService(error=CardNotFoundError(1))
    database = _FakeDatabase()
    worker = PriceLookupWorker(lambda: (service, database), card_id=1)

    worker.run()

    assert database.closed is True
