"""Tests for CatalogSearchWorker's signal wiring.

``run()`` is called directly (rather than ``start()``) so the worker body
executes synchronously in the test thread — deterministic, no real
threading/timing involved. Mirrors ``test_cardmarket_search_worker.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.catalog.models import CatalogCard
from app.services.exceptions import CatalogSearchError
from app.ui.app import build_application
from app.ui.workers.catalog_search_worker import CatalogSearchWorker

_XATU = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)


class FakeService:
    def __init__(self, results=None, error: Exception | None = None) -> None:
        self._results = results or []
        self._error = error
        self.queries: list[str] = []

    def search(self, query: str, is_cancelled=None):
        self.queries.append(query)
        if self._error is not None:
            raise self._error
        return self._results


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_search_results(qapp) -> None:
    service = FakeService(results=[_XATU])
    worker = CatalogSearchWorker(service, "xatu")
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [[_XATU]]
    assert failed == []
    assert service.queries == ["xatu"]


def test_succeeded_emitted_with_empty_list_when_nothing_found(qapp) -> None:
    service = FakeService(results=[])
    worker = CatalogSearchWorker(service, "does-not-exist")
    succeeded = []
    worker.succeeded.connect(succeeded.append)

    worker.run()

    assert succeeded == [[]]


def test_failed_emitted_on_service_error(qapp) -> None:
    service = FakeService(error=CatalogSearchError("Katalog nicht erreichbar."))
    worker = CatalogSearchWorker(service, "xatu")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == ["Katalog nicht erreichbar."]


def test_unexpected_exception_emits_failed_not_a_crash(qapp) -> None:
    service = FakeService(error=RuntimeError("boom"))
    worker = CatalogSearchWorker(service, "xatu")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "boom" in failed[0]


def test_run_passes_its_own_interruption_check_to_the_service(qapp) -> None:
    class RecordingService:
        def __init__(self) -> None:
            self.is_cancelled_seen = None

        def search(self, query: str, is_cancelled=None):
            self.is_cancelled_seen = is_cancelled
            return []

    service = RecordingService()
    worker = CatalogSearchWorker(service, "xatu")

    worker.run()

    assert service.is_cancelled_seen == worker.isInterruptionRequested


def test_succeeded_is_not_emitted_once_interruption_was_requested(qapp) -> None:
    # Real scenario: the results dialog was already closed (see
    # CatalogSearchController._on_dialog_finished) while the search was
    # still running -- nothing is listening for a late result anymore.
    # ``isInterruptionRequested`` is monkeypatched directly (rather than
    # calling the real ``requestInterruption()``) since Qt only honours that
    # flag while the QThread is actually running -- irrelevant here, this
    # test is only about ``run()``'s own post-search check.
    service = FakeService(results=[_XATU])
    worker = CatalogSearchWorker(service, "xatu")
    worker.isInterruptionRequested = lambda: True
    succeeded = []
    worker.succeeded.connect(succeeded.append)

    worker.run()

    assert succeeded == []


def test_failed_is_not_emitted_once_interruption_was_requested(qapp) -> None:
    service = FakeService(error=CatalogSearchError("Katalog nicht erreichbar."))
    worker = CatalogSearchWorker(service, "xatu")
    worker.isInterruptionRequested = lambda: True
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == []
