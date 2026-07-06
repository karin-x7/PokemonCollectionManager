"""Tests for SealedPriceLookupWorker's signal wiring.

Mirrors ``test_price_lookup_worker.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.sealed_product import SealedProduct
from app.services.exceptions import SealedProductNotFoundError
from app.ui.app import build_application
from app.ui.workers.sealed_price_lookup_worker import SealedPriceLookupWorker

_PRODUCT = SealedProduct(id=1, name="Base Set Booster Box")


class FakeSealedPriceService:
    def __init__(self, product: SealedProduct | None = None, error: Exception | None = None) -> None:
        self._product = product
        self._error = error
        self.calls: list[int] = []

    def update_price_for_product(self, product_id: int) -> SealedProduct:
        self.calls.append(product_id)
        if self._error is not None:
            raise self._error
        return self._product


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_updated_product(qapp) -> None:
    service = FakeSealedPriceService(product=_PRODUCT)
    worker = SealedPriceLookupWorker(lambda: (service, None), product_id=1)
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [_PRODUCT]
    assert failed == []
    assert service.calls == [1]


def test_failed_emitted_on_service_error(qapp) -> None:
    service = FakeSealedPriceService(error=SealedProductNotFoundError(1))
    worker = SealedPriceLookupWorker(lambda: (service, None), product_id=1)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "1" in failed[0]


def test_unexpected_exception_emits_failed_not_a_crash(qapp) -> None:
    service = FakeSealedPriceService(error=RuntimeError("boom"))
    worker = SealedPriceLookupWorker(lambda: (service, None), product_id=1)
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
    service = FakeSealedPriceService(product=_PRODUCT)
    database = _FakeDatabase()
    worker = SealedPriceLookupWorker(lambda: (service, database), product_id=1)

    worker.run()

    assert database.closed is True


def test_database_is_closed_even_after_a_failed_lookup(qapp) -> None:
    service = FakeSealedPriceService(error=SealedProductNotFoundError(1))
    database = _FakeDatabase()
    worker = SealedPriceLookupWorker(lambda: (service, database), product_id=1)

    worker.run()

    assert database.closed is True
