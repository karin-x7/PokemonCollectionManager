"""Tests for ProductInfoWorker's signal wiring.

``run()`` is called directly (rather than ``start()``) so the worker body
executes synchronously in the test thread — deterministic, no real
threading/timing involved. Mirrors ``test_price_lookup_worker.py``.
"""

from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.catalog.pokemontcg_client import PokemonTcgClientError
from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import ProductInfo
from app.ui.app import build_application
from app.ui.workers import product_info_worker as worker_module
from app.ui.workers.product_info_worker import ProductInfoWorker

_INFO = ProductInfo(name="Venusaur", set_name="Legendary Collection", card_number="18")


class FakePokemonTcgClient:
    def __init__(self, set_code: str | None = "", error: Exception | None = None) -> None:
        self._set_code = set_code
        self._error = error
        self.calls: list[str] = []

    def resolve_set_code(self, set_name: str) -> str:
        self.calls.append(set_name)
        if self._error is not None:
            raise self._error
        return self._set_code


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_succeeded_emitted_with_parsed_info(qapp, monkeypatch) -> None:
    monkeypatch.setattr(worker_module, "read_product_info", lambda url, **kwargs: _INFO)
    worker = ProductInfoWorker("https://cardmarket.com/x")
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [_INFO]
    assert failed == []


def test_failed_emitted_on_reader_error(qapp, monkeypatch) -> None:
    def _raise(url: str, **kwargs) -> None:
        raise BrowserPriceReaderError("Tab nicht gefunden.")

    monkeypatch.setattr(worker_module, "read_product_info", _raise)
    worker = ProductInfoWorker("https://cardmarket.com/x")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert failed == ["Tab nicht gefunden."]


def test_unexpected_exception_emits_failed_not_a_crash(qapp, monkeypatch) -> None:
    def _raise(url: str, **kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker_module, "read_product_info", _raise)
    worker = ProductInfoWorker("https://cardmarket.com/x")
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert len(failed) == 1
    assert "boom" in failed[0]


def test_resolves_and_attaches_set_code_when_a_client_is_given(qapp, monkeypatch) -> None:
    monkeypatch.setattr(worker_module, "read_product_info", lambda url, **kwargs: _INFO)
    client = FakePokemonTcgClient(set_code="ex2")
    worker = ProductInfoWorker("https://cardmarket.com/x", client)
    succeeded = []
    worker.succeeded.connect(succeeded.append)

    worker.run()

    assert succeeded == [replace(_INFO, set_code="ex2")]
    assert client.calls == ["Legendary Collection"]


def test_no_client_given_leaves_set_code_blank(qapp, monkeypatch) -> None:
    monkeypatch.setattr(worker_module, "read_product_info", lambda url, **kwargs: _INFO)
    worker = ProductInfoWorker("https://cardmarket.com/x")
    succeeded = []
    worker.succeeded.connect(succeeded.append)

    worker.run()

    assert succeeded == [_INFO]


def test_set_code_lookup_failure_does_not_fail_the_whole_lookup(qapp, monkeypatch) -> None:
    # Best-effort: pokemontcg.io can be slow/unreachable (a live request has
    # taken 20+ seconds during a slow period) -- a failed set_code lookup
    # must never turn an otherwise-successful page read into a failure.
    monkeypatch.setattr(worker_module, "read_product_info", lambda url, **kwargs: _INFO)
    client = FakePokemonTcgClient(error=PokemonTcgClientError("boom"))
    worker = ProductInfoWorker("https://cardmarket.com/x", client)
    succeeded = []
    worker.succeeded.connect(succeeded.append)
    failed = []
    worker.failed.connect(failed.append)

    worker.run()

    assert succeeded == [_INFO]
    assert failed == []
