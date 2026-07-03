"""Headless tests for CollectionPanel's presentation logic and signals.

Modal dialogs (QInputDialog, QMessageBox) are monkeypatched so the tests run
non-interactively under the ``offscreen`` Qt platform.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from app.models.collection import Collection
from app.ui.app import build_application
from app.ui.widgets.collection_panel import CollectionPanel


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def panel(qapp) -> CollectionPanel:
    p = CollectionPanel()
    p.set_collections(
        [
            Collection(id=1, name="Binder"),
            Collection(id=2, name="Vintage"),
        ]
    )
    return p


def test_set_collections_preserves_selection_by_id(panel: CollectionPanel) -> None:
    panel._list.setCurrentRow(1)  # "Vintage", id=2
    panel.set_collections(
        [Collection(id=2, name="Vintage"), Collection(id=1, name="Binder")]
    )
    assert panel.selected_collection_id() == 2


def test_create_requested_emits_trimmed_name(monkeypatch, panel: CollectionPanel) -> None:
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: (" Neu ", True))
    received: list[str] = []
    panel.create_requested.connect(received.append)

    panel._prompt_create()

    assert received == ["Neu"]


def test_create_cancelled_emits_nothing(monkeypatch, panel: CollectionPanel) -> None:
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("", False))
    received: list[str] = []
    panel.create_requested.connect(received.append)

    panel._prompt_create()

    assert received == []


def test_rename_emits_id_and_new_name(monkeypatch, panel: CollectionPanel) -> None:
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Ordner", True))
    received: list[tuple[int, str]] = []
    panel.rename_requested.connect(lambda cid, name: received.append((cid, name)))

    item = panel._list.item(0)  # "Binder", id=1
    panel._prompt_rename(item)

    assert received == [(1, "Ordner")]


def test_rename_to_same_name_emits_nothing(monkeypatch, panel: CollectionPanel) -> None:
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Binder", True))
    received: list[tuple[int, str]] = []
    panel.rename_requested.connect(lambda cid, name: received.append((cid, name)))

    panel._prompt_rename(panel._list.item(0))

    assert received == []


def test_delete_confirmed_emits_id(monkeypatch, panel: CollectionPanel) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    received: list[int] = []
    panel.delete_requested.connect(received.append)

    panel._prompt_delete(panel._list.item(1))  # "Vintage", id=2

    assert received == [2]


def test_delete_declined_emits_nothing(monkeypatch, panel: CollectionPanel) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    received: list[int] = []
    panel.delete_requested.connect(received.append)

    panel._prompt_delete(panel._list.item(1))

    assert received == []


def test_reorder_emits_current_visual_order(panel: CollectionPanel) -> None:
    received: list[list[int]] = []
    panel.reorder_requested.connect(received.append)

    # Simulate a drag-reorder by physically moving the row, then trigger the
    # handler exactly like the model's rowsMoved signal would.
    item = panel._list.takeItem(0)  # "Binder"
    panel._list.addItem(item)  # now Vintage(2), Binder(1)
    panel._on_rows_moved()

    assert received == [[2, 1]]


def test_selection_changed_emits_minus_one_when_cleared(panel: CollectionPanel) -> None:
    received: list[int] = []
    panel.selection_changed.connect(received.append)

    panel._list.setCurrentRow(0)
    panel._list.clearSelection()
    panel._list.setCurrentItem(None)

    assert received[-1] == -1
