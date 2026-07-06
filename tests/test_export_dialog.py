"""Tests for ExportDialog's format/scope choices."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.collection import Collection
from app.models.enums import ExportFormat, ExportTarget
from app.ui.app import build_application
from app.ui.dialogs.export_dialog import ExportDialog

_COLLECTIONS = [
    Collection(id=1, name="Binder"),
    Collection(id=2, name="Vintage"),
]


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_defaults_to_cards_csv_and_all_collections(qapp) -> None:
    dialog = ExportDialog(_COLLECTIONS)

    values = dialog.get_values()

    assert values.target is ExportTarget.CARDS
    assert values.export_format is ExportFormat.CSV
    assert values.collection_id is None


def test_selecting_sealed_target_returns_it(qapp) -> None:
    dialog = ExportDialog(_COLLECTIONS)
    index = dialog._target_combo.findData(ExportTarget.SEALED)
    dialog._target_combo.setCurrentIndex(index)

    assert dialog.get_values().target is ExportTarget.SEALED


def test_selecting_sealed_target_hides_scope_row_and_forces_no_collection(qapp) -> None:
    # Sealed products aren't collection-scoped -- the "Sammlung" row doesn't
    # apply and collection_id must come back None regardless of whatever
    # the (now hidden) scope combo still has selected underneath.
    dialog = ExportDialog(_COLLECTIONS)
    dialog._scope_combo.setCurrentIndex(1)  # "Binder"
    index = dialog._target_combo.findData(ExportTarget.SEALED)
    dialog._target_combo.setCurrentIndex(index)

    assert not dialog._form.isRowVisible(dialog._scope_combo)
    assert dialog.get_values().collection_id is None


def test_lists_every_collection_by_name(qapp) -> None:
    dialog = ExportDialog(_COLLECTIONS)

    items = [dialog._scope_combo.itemText(i) for i in range(dialog._scope_combo.count())]

    assert items == ["All collections", "Binder", "Vintage"]


def test_selecting_a_collection_returns_its_id(qapp) -> None:
    dialog = ExportDialog(_COLLECTIONS)
    dialog._scope_combo.setCurrentIndex(2)  # "Vintage"

    assert dialog.get_values().collection_id == 2


def test_selecting_a_format_returns_it(qapp) -> None:
    dialog = ExportDialog(_COLLECTIONS)
    index = dialog._format_combo.findData(ExportFormat.PDF)
    dialog._format_combo.setCurrentIndex(index)

    assert dialog.get_values().export_format is ExportFormat.PDF


def test_works_with_no_collections_at_all(qapp) -> None:
    dialog = ExportDialog([])

    values = dialog.get_values()

    assert values.collection_id is None
    assert dialog._scope_combo.count() == 1
