"""Tests for CardmarketSearchController: search -> results dialog -> resolve ->

CardService.set_manual_cardmarket_url + CardController.refresh().

Both worker classes' ``start()`` are monkeypatched to run synchronously, and
``CardmarketSearchResultsDialog.exec()`` is monkeypatched to auto-confirm
(or cancel) instead of blocking on a real modal -- mirrors
``test_manual_entry_controller.py``/``test_sealed_entry_controller.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QDialog, QMainWindow, QMessageBox

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language
from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import CardmarketSearchResult
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.ui.app import build_application
from app.ui.controllers.card_controller import CardController
from app.ui.controllers.cardmarket_search_controller import CardmarketSearchController
from app.ui.dialogs.cardmarket_search_results_dialog import CardmarketSearchResultsDialog
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel
from app.ui.workers.cardmarket_search_resolve_worker import CardmarketSearchResolveWorker
from app.ui.workers.cardmarket_search_worker import CardmarketSearchWorker

_RESULT = CardmarketSearchResult(
    name="Poké Pad",
    set_name="Perfect Order",
    card_number="POR 113",
    price_hint="9,00 €",
    raw_text="Poké Pad Perfect Order \xa0Poké Pad (POR 113) From 9,00 €",
)
_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Perfect-Order/Poke-Pad-V2-POR113"

_VALUES = CardDetailsValues(
    language=Language.ENGLISH, condition=Condition.NEAR_MINT, quantity=1, notes=""
)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture(autouse=True)
def synchronous_workers(monkeypatch):
    def fake_start(self):
        self.run()
        self.finished.emit()

    monkeypatch.setattr(CardmarketSearchWorker, "start", fake_start)
    monkeypatch.setattr(CardmarketSearchResolveWorker, "start", fake_start)


@pytest.fixture(autouse=True)
def auto_confirm_save(monkeypatch):
    """The final "save this link?" confirmation defaults to Yes -- tests

    that want to exercise a decline override this per-test."""
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes
    )


@pytest.fixture
def collection_id(temp_db: Database) -> int:
    return CollectionRepository(temp_db).create("Binder").id


@pytest.fixture
def card_service(temp_db: Database) -> CardService:
    return CardService(CardRepository(temp_db), image_downloader=lambda _card: None)


@pytest.fixture
def card_controller(qapp, temp_db: Database, card_service: CardService) -> CardController:
    collection_service = CollectionService(CollectionRepository(temp_db))
    panel = CardListPanel()
    detail_panel = CardDetailPanel()
    return CardController(panel, detail_panel, card_service, collection_service)


@pytest.fixture
def card_id(card_service: CardService, collection_id: int) -> int:
    card = card_service.add_card_manual(
        collection_id, "Poké Pad", "Perfect Order", "113", _VALUES
    )
    return card.id


@pytest.fixture
def main_window(qapp) -> QMainWindow:
    window = QMainWindow()
    yield window
    window.close()


@pytest.fixture
def controller(
    main_window: QMainWindow, card_service: CardService, card_controller: CardController
) -> CardmarketSearchController:
    return CardmarketSearchController(
        main_window,
        card_controller._detail_panel,
        card_service,
        card_controller,
        list_panel=card_controller._panel,
    )


def _auto_confirm(result: CardmarketSearchResult):
    def fake_exec(self):
        self.result_confirmed.emit(result)
        return QDialog.DialogCode.Accepted

    return fake_exec


def _auto_cancel(self):
    return QDialog.DialogCode.Rejected


def test_full_flow_persists_the_resolved_url_and_refreshes(
    monkeypatch, controller: CardmarketSearchController, card_service: CardService, card_id: int
) -> None:
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_resolve_worker.resolve_cardmarket_search_result",
        lambda name, chosen: _URL,
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_confirm(_RESULT))

    controller.start(card_id)

    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url == _URL


def test_confirming_the_save_still_works_if_cleanup_races_in_during_the_question(
    monkeypatch, controller: CardmarketSearchController, card_service: CardService, card_id: int
) -> None:
    # Live-reported bug: confirming the "save this link?" dialog silently
    # did nothing. Root cause: QMessageBox.question() runs its own nested
    # Qt event loop while it waits for the user -- the worker's own
    # `finished` signal (queued right behind `succeeded`, since the thread
    # emits it immediately after run() returns) got processed during that
    # wait, resetting self._card_id/self._card_name to None via
    # _cleanup_resolve *before* the user ever clicked Yes. Simulated here by
    # having the (monkeypatched) confirmation itself trigger that same
    # cleanup as a side effect before returning Yes -- exactly what the real
    # nested event loop does -- to prove the save survives it.
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_resolve_worker.resolve_cardmarket_search_result",
        lambda name, chosen: _URL,
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_confirm(_RESULT))

    def _question_with_interleaved_cleanup(*_args, **_kwargs):
        controller._cleanup_resolve()
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", _question_with_interleaved_cleanup)

    controller.start(card_id)

    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url == _URL


def test_link_saved_is_emitted_for_immediate_price_lookup(
    monkeypatch, controller: CardmarketSearchController, card_id: int
) -> None:
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_resolve_worker.resolve_cardmarket_search_result",
        lambda name, chosen: _URL,
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_confirm(_RESULT))
    received: list[int] = []
    controller.link_saved.connect(received.append)

    controller.start(card_id)

    assert received == [card_id]


def test_declining_the_save_confirmation_does_not_persist_the_url(
    monkeypatch, controller: CardmarketSearchController, card_service: CardService, card_id: int
) -> None:
    # The confirmation added after the results dialog's own "Übernehmen" only
    # confirms *which candidate* to resolve -- this is a separate, final
    # check before the just-discovered URL is actually saved.
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_resolve_worker.resolve_cardmarket_search_result",
        lambda name, chosen: _URL,
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_confirm(_RESULT))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.No)

    controller.start(card_id)

    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url is None


def test_list_panel_cardmarket_search_requested_starts_the_flow(
    monkeypatch,
    main_window: QMainWindow,
    card_service: CardService,
    card_controller: CardController,
    card_id: int,
) -> None:
    # "Fix Cardmarket-Link" context-menu action in the card list, wired to
    # the exact same flow the detail-panel button already offers.
    controller = CardmarketSearchController(
        main_window,
        card_controller._detail_panel,
        card_service,
        card_controller,
        list_panel=card_controller._panel,
    )
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_resolve_worker.resolve_cardmarket_search_result",
        lambda name, chosen: _URL,
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_confirm(_RESULT))

    card_controller._panel.cardmarket_search_requested.emit(card_id)

    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url == _URL


def test_manual_search_requested_opens_cardmarket_search_for_the_card_name(
    monkeypatch, controller: CardmarketSearchController, card_id: int
) -> None:
    # Empty-state fallback: the automated search found nothing, so the user
    # can search Cardmarket themselves in a real browser window instead.
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [],
    )
    opened: list[str] = []
    monkeypatch.setattr(
        "app.ui.controllers.cardmarket_search_controller.open_cardmarket_search",
        opened.append,
    )
    dialog = CardmarketSearchResultsDialog()

    def fake_exec(self):
        self.manual_search_requested.emit()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", fake_exec)

    controller.start(card_id)

    assert opened == ["Poké Pad"]


def test_cancelling_the_results_dialog_does_not_persist_anything(
    monkeypatch, controller: CardmarketSearchController, card_service: CardService, card_id: int
) -> None:
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_cancel)

    controller.start(card_id)

    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url is None


def test_search_failure_shows_status_message_and_does_not_persist(
    monkeypatch,
    controller: CardmarketSearchController,
    card_service: CardService,
    card_id: int,
    main_window: QMainWindow,
) -> None:
    def _raise(name: str):
        raise BrowserPriceReaderError("Cardmarket-Tab nicht gefunden.")

    monkeypatch.setattr("app.ui.workers.cardmarket_search_worker.search_cardmarket", _raise)

    controller.start(card_id)

    assert "Cardmarket-Tab nicht gefunden." in main_window.statusBar().currentMessage()
    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url is None


def test_resolve_failure_shows_status_message_and_does_not_persist(
    monkeypatch,
    controller: CardmarketSearchController,
    card_service: CardService,
    card_id: int,
    main_window: QMainWindow,
) -> None:
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )

    def _raise(name: str, chosen: CardmarketSearchResult):
        raise BrowserPriceReaderError("Treffer nicht wiedergefunden.")

    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_resolve_worker.resolve_cardmarket_search_result", _raise
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_confirm(_RESULT))

    controller.start(card_id)

    assert "Treffer nicht wiedergefunden." in main_window.statusBar().currentMessage()
    card = card_service.get_card(card_id)
    assert card.manual_cardmarket_url is None


def test_a_second_request_while_running_is_ignored(
    monkeypatch, controller: CardmarketSearchController, card_id: int
) -> None:
    monkeypatch.setattr(
        "app.ui.workers.cardmarket_search_worker.search_cardmarket",
        lambda name: [_RESULT],
    )
    monkeypatch.setattr(CardmarketSearchResultsDialog, "exec", _auto_cancel)
    # start() runs synchronously but (unlike the autouse fixture) never emits
    # `finished`, simulating a search that's still in progress.
    monkeypatch.setattr(CardmarketSearchWorker, "start", lambda self: self.run())

    controller.start(card_id)
    controller.start(card_id)

    assert controller._search_worker is not None
