"""Integration tests: CollectionController wiring panel <-> service <-> DB."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.database.connection import Database
from app.database.repositories.collection_repository import CollectionRepository
from app.services.collection_service import CollectionService
from app.ui.app import build_application
from app.ui.controllers.collection_controller import CollectionController
from app.ui.widgets.collection_panel import CollectionPanel


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def controller(qapp, temp_db: Database) -> CollectionController:
    service = CollectionService(CollectionRepository(temp_db))
    panel = CollectionPanel()
    return CollectionController(panel, service)


def _names(controller: CollectionController) -> list[str]:
    return [controller._panel._list.item(row).text() for row in range(controller._panel._list.count())]


def test_create_via_signal_persists_and_refreshes_panel(controller: CollectionController) -> None:
    controller._panel.create_requested.emit("Binder")
    assert _names(controller) == ["Binder"]


def test_duplicate_create_shows_error_and_keeps_panel_consistent(
    monkeypatch, controller: CollectionController
) -> None:
    controller._panel.create_requested.emit("Binder")
    errors: list[str] = []
    monkeypatch.setattr(controller._panel, "show_error", errors.append)

    controller._panel.create_requested.emit("Binder")

    assert len(errors) == 1
    assert "Binder" in errors[0]
    assert _names(controller) == ["Binder"]  # unchanged, no duplicate row


def test_rename_via_signal_persists(controller: CollectionController) -> None:
    controller._panel.create_requested.emit("Binder")
    collection_id = controller._panel.selected_collection_id()

    controller._panel.rename_requested.emit(collection_id, "Ordner")

    assert _names(controller) == ["Ordner"]


def test_delete_via_signal_persists(controller: CollectionController) -> None:
    controller._panel.create_requested.emit("Binder")
    collection_id = controller._panel.selected_collection_id()

    controller._panel.delete_requested.emit(collection_id)

    assert _names(controller) == []


def test_reorder_via_signal_persists_across_refresh(controller: CollectionController) -> None:
    controller._panel.create_requested.emit("A")
    controller._panel.create_requested.emit("B")
    a_id, b_id = (
        controller._service.list_collections()[0].id,
        controller._service.list_collections()[1].id,
    )

    controller._panel.reorder_requested.emit([b_id, a_id])
    controller.refresh()

    assert _names(controller) == ["B", "A"]


def test_selection_changed_is_forwarded_by_controller(controller: CollectionController) -> None:
    controller._panel.create_requested.emit("Binder")
    received: list[int] = []
    controller.selection_changed.connect(received.append)

    controller._panel.selection_changed.emit(42)

    assert received == [42]


def test_select_first_collection_selects_the_first_one(
    controller: CollectionController,
) -> None:
    controller._panel.create_requested.emit("Binder")
    controller._panel.create_requested.emit("Vintage")
    received: list[int] = []
    controller.selection_changed.connect(received.append)
    first_id = controller._service.list_collections()[0].id

    controller.select_first_collection()

    assert controller._panel.selected_collection_id() == first_id
    assert received == [first_id]


def test_select_first_collection_is_a_no_op_when_none_exist(
    controller: CollectionController,
) -> None:
    received: list[int] = []
    controller.selection_changed.connect(received.append)

    controller.select_first_collection()

    assert received == []
    assert controller._panel.selected_collection_id() is None
