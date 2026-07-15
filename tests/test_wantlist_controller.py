"""Integration tests: WantlistController wiring panel <-> service <-> DB."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QDialog

from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.wantlist_repository import WantlistRepository
from app.models.enums import Condition, Language
from app.models.wantlist import WantlistItemDetailsValues
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.services.wantlist_service import WantlistService
from app.ui.app import build_application
from app.ui.controllers.wantlist_controller import WantlistController
from app.ui.widgets.wantlist_panel import WantlistPanel

_VALUES = WantlistItemDetailsValues(
    language=Language.ENGLISH,
    condition=Condition.NEAR_MINT,
    target_price=500.0,
    notes="",
    cardmarket_url="https://example.com/charizard",
)


class _FakeAcceptedMoveDialog:
    """Mirrors the same fake used in test_card_controller.py's move tests."""

    def __init__(self, target_collection_id: int) -> None:
        self._target_collection_id = target_collection_id

    def __call__(self, collections, parent=None):
        self.collections = collections
        return self

    def exec(self):
        return QDialog.DialogCode.Accepted

    def get_target_collection_id(self):
        return self._target_collection_id


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def collection_id(temp_db: Database) -> int:
    return CollectionRepository(temp_db).create("Binder").id


@pytest.fixture
def controller(qapp, temp_db: Database) -> WantlistController:
    service = WantlistService(WantlistRepository(temp_db))
    card_service = CardService(CardRepository(temp_db), image_downloader=lambda _card: None)
    collection_service = CollectionService(CollectionRepository(temp_db))
    panel = WantlistPanel()
    return WantlistController(panel, service, card_service, collection_service)


def _names(controller: WantlistController) -> list[str]:
    table = controller._panel._table
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def test_add_item_persists_and_refreshes_panel(controller: WantlistController) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)

    assert _names(controller) == ["Charizard"]


def test_refresh_shows_every_wantlist_item(controller: WantlistController) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    controller.add_item("Blastoise", "Base Set", "2", _VALUES)

    controller.refresh()

    assert set(_names(controller)) == {"Charizard", "Blastoise"}


def test_edit_requested_persists_changes(controller: WantlistController) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    item_id = controller._panel.selected_item_id()

    new_values = WantlistItemDetailsValues(
        language=Language.GERMAN, condition=Condition.NEAR_MINT, target_price=300.0, notes="cheaper"
    )
    controller._panel.edit_requested.emit(item_id, new_values)

    table = controller._panel._table
    assert "300,00" in table.item(0, 3).text()  # Target column


def test_delete_requested_removes_item(controller: WantlistController) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    item_id = controller._panel.selected_item_id()

    controller._panel.delete_requested.emit([item_id])

    assert _names(controller) == []


def test_delete_requested_with_multiple_ids_removes_all(controller: WantlistController) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    first_id = controller._panel.selected_item_id()
    controller.add_item("Blastoise", "Base Set", "2", _VALUES)
    second_id = controller._panel.selected_item_id()

    controller._panel.delete_requested.emit([first_id, second_id])

    assert _names(controller) == []


def test_convert_to_owned_adds_the_card_and_drops_the_wantlist_entry(
    monkeypatch, controller: WantlistController, temp_db: Database, collection_id: int
) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    item_id = controller._panel.selected_item_id()
    monkeypatch.setattr(
        "app.ui.controllers.wantlist_controller.MoveDialog",
        _FakeAcceptedMoveDialog(collection_id),
    )

    controller._panel.convert_to_owned_requested.emit(item_id)

    assert _names(controller) == []  # gone from the wantlist
    cards = CardRepository(temp_db).list_by_collection(collection_id)
    assert [c.name for c in cards] == ["Charizard"]
    # WantlistService.add_item already appended a language filter to the
    # stored URL -- the conversion carries that filtered URL over as-is.
    assert cards[0].manual_cardmarket_url == "https://example.com/charizard?language=1"
    assert cards[0].quantity == 1


def test_convert_to_owned_cancelled_dialog_keeps_the_wantlist_entry(
    monkeypatch, controller: WantlistController, temp_db: Database, collection_id: int
) -> None:
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    item_id = controller._panel.selected_item_id()

    class _FakeCancelledMoveDialog(_FakeAcceptedMoveDialog):
        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(
        "app.ui.controllers.wantlist_controller.MoveDialog",
        _FakeCancelledMoveDialog(collection_id),
    )

    controller._panel.convert_to_owned_requested.emit(item_id)

    assert _names(controller) == ["Charizard"]
    assert CardRepository(temp_db).list_by_collection(collection_id) == []


def test_convert_to_owned_calls_on_converted_callback(
    monkeypatch, qapp, temp_db: Database, collection_id: int
) -> None:
    service = WantlistService(WantlistRepository(temp_db))
    card_service = CardService(CardRepository(temp_db), image_downloader=lambda _card: None)
    collection_service = CollectionService(CollectionRepository(temp_db))
    panel = WantlistPanel()
    calls = []
    controller = WantlistController(
        panel, service, card_service, collection_service, on_converted=lambda: calls.append(True)
    )
    controller.add_item("Charizard", "Base Set", "4", _VALUES)
    item_id = controller._panel.selected_item_id()
    monkeypatch.setattr(
        "app.ui.controllers.wantlist_controller.MoveDialog",
        _FakeAcceptedMoveDialog(collection_id),
    )

    controller._panel.convert_to_owned_requested.emit(item_id)

    assert calls == [True]
