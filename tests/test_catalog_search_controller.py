"""Headless tests for CatalogSearchController wiring."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.catalog.models import CatalogCard
from app.services.exceptions import CatalogSearchError
from app.ui.app import build_application
from app.ui.controllers.catalog_search_controller import CatalogSearchController
from app.ui.dialogs.catalog_search_results_dialog import CatalogSearchResultsDialog
from app.ui.main_window import MainWindow

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

    def search(self, query: str):
        self.queries.append(query)
        if self._error is not None:
            raise self._error
        return self._results


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def main_window(qapp) -> MainWindow:
    window = MainWindow()
    yield window
    window.close()


def test_empty_query_shows_status_hint_and_makes_no_service_call(main_window: MainWindow) -> None:
    service = FakeService()
    controller = CatalogSearchController(main_window, service)

    controller.handle_search("   ")

    assert service.queries == []
    assert main_window.statusBar().currentMessage() == "Bitte Suchbegriff eingeben."


def test_successful_search_shows_results_via_dialog(monkeypatch, main_window: MainWindow) -> None:
    service = FakeService(results=[_XATU])
    controller = CatalogSearchController(main_window, service)
    shown: list[list[CatalogCard]] = []
    monkeypatch.setattr(controller, "_show_results", shown.append)

    controller.handle_search(" xatu skyridge ")

    assert service.queries == ["xatu skyridge"]
    assert shown == [[_XATU]]
    assert "1 Treffer" in main_window.statusBar().currentMessage()


def test_search_with_no_matches_still_shows_dialog(monkeypatch, main_window: MainWindow) -> None:
    service = FakeService(results=[])
    controller = CatalogSearchController(main_window, service)
    shown: list[list[CatalogCard]] = []
    monkeypatch.setattr(controller, "_show_results", shown.append)

    controller.handle_search("does-not-exist")

    assert shown == [[]]
    assert "Keine Treffer" in main_window.statusBar().currentMessage()


def test_service_error_shows_friendly_error_not_a_crash(
    monkeypatch, main_window: MainWindow
) -> None:
    service = FakeService(error=CatalogSearchError("Katalog nicht erreichbar."))
    controller = CatalogSearchController(main_window, service)
    errors: list[str] = []
    monkeypatch.setattr(controller, "_show_error", errors.append)

    controller.handle_search("xatu")

    assert errors == ["Katalog nicht erreichbar."]


def test_card_add_requested_forwards_from_the_real_results_dialog(
    monkeypatch, main_window: MainWindow
) -> None:
    """Exercises the real (non-monkeypatched) ``_show_results`` wiring: the
    results dialog's ``add_requested`` must reach ``card_add_requested``."""

    def fake_exec(self):
        self.add_requested.emit(_XATU)
        return CatalogSearchResultsDialog.DialogCode.Accepted

    monkeypatch.setattr(CatalogSearchResultsDialog, "exec", fake_exec)

    service = FakeService(results=[_XATU])
    controller = CatalogSearchController(main_window, service)
    received: list[CatalogCard] = []
    controller.card_add_requested.connect(received.append)

    controller.handle_search("xatu")

    assert received == [_XATU]
