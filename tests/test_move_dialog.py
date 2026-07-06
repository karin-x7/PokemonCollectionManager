"""Tests for MoveDialog's target-collection selection."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.collection import Collection
from app.ui.app import build_application
from app.ui.dialogs.move_dialog import MoveDialog

_COLLECTIONS = [
    Collection(id=1, name="Vintage"),
    Collection(id=2, name="Modern"),
]


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_lists_every_given_collection_by_name(qapp) -> None:
    dialog = MoveDialog(_COLLECTIONS)

    items = [dialog._target_combo.itemText(i) for i in range(dialog._target_combo.count())]

    assert items == ["Vintage", "Modern"]


def test_defaults_to_the_first_collection(qapp) -> None:
    dialog = MoveDialog(_COLLECTIONS)

    assert dialog.get_target_collection_id() == 1


def test_selecting_a_collection_returns_its_id(qapp) -> None:
    dialog = MoveDialog(_COLLECTIONS)
    dialog._target_combo.setCurrentIndex(1)

    assert dialog.get_target_collection_id() == 2
