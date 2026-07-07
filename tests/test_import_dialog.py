"""Tests for ImportDialog's target/format choices."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import ExportFormat, ExportTarget
from app.ui.app import build_application
from app.ui.dialogs.import_dialog import ImportDialog


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def test_defaults_to_cards_and_csv(qapp) -> None:
    dialog = ImportDialog()

    values = dialog.get_values()

    assert values.target is ExportTarget.CARDS
    assert values.import_format is ExportFormat.CSV


def test_selecting_sealed_target_returns_it(qapp) -> None:
    dialog = ImportDialog()
    index = dialog._target_combo.findData(ExportTarget.SEALED)
    dialog._target_combo.setCurrentIndex(index)

    assert dialog.get_values().target is ExportTarget.SEALED


def test_selecting_a_format_returns_it(qapp) -> None:
    dialog = ImportDialog()
    index = dialog._format_combo.findData(ExportFormat.JSON)
    dialog._format_combo.setCurrentIndex(index)

    assert dialog.get_values().import_format is ExportFormat.JSON


def test_pdf_is_not_offered_as_an_import_format(qapp) -> None:
    dialog = ImportDialog()

    formats = [dialog._format_combo.itemData(i) for i in range(dialog._format_combo.count())]

    assert ExportFormat.PDF not in formats
