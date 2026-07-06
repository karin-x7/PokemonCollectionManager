"""Tests for ExportController: dialog -> file dialog -> ExportService wiring.

Both the format/scope dialog and the native "Save As" dialog are
monkeypatched so this runs headlessly/deterministically, without a real
modal or filesystem picker ever appearing.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from app.models.collection import Collection
from app.models.enums import ExportFormat, ExportTarget
from app.ui.app import build_application
from app.ui.controllers.export_controller import ExportController
from app.ui.dialogs.export_dialog import ExportChoice
from app.ui.main_window import MainWindow


class FakeCollectionService:
    def list_collections(self) -> list[Collection]:
        return [Collection(id=1, name="Binder")]


class FakeExportService:
    def __init__(self, count: int = 3, error: Exception | None = None) -> None:
        self._count = count
        self._error = error
        self.calls: list[tuple] = []

    def export(self, export_format, path, target=ExportTarget.CARDS, collection_id=None) -> int:
        self.calls.append((export_format, path, target, collection_id))
        if self._error is not None:
            raise self._error
        return self._count


class FakeAcceptedDialog:
    """Stands in for ExportDialog: always "accepted" with a fixed choice."""

    def __init__(self, choice: ExportChoice) -> None:
        self._choice = choice

    def __call__(self, collections, parent=None):
        self._instance = self
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_values(self) -> ExportChoice:
        return self._choice


class FakeCancelledDialog:
    def __call__(self, collections, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Rejected

    def get_values(self):  # pragma: no cover -- must never be called
        raise AssertionError("get_values() should not be called after a cancelled dialog")


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def main_window(qapp) -> MainWindow:
    return MainWindow()


def test_cancelling_the_choice_dialog_exports_nothing(monkeypatch, main_window: MainWindow) -> None:
    export_service = FakeExportService()
    controller = ExportController(main_window, export_service, FakeCollectionService())
    monkeypatch.setattr(
        "app.ui.controllers.export_controller.ExportDialog", FakeCancelledDialog()
    )

    controller.handle_export_requested()

    assert export_service.calls == []


def test_cancelling_the_save_dialog_exports_nothing(monkeypatch, main_window: MainWindow) -> None:
    export_service = FakeExportService()
    controller = ExportController(main_window, export_service, FakeCollectionService())
    choice = ExportChoice(target=ExportTarget.CARDS, export_format=ExportFormat.CSV, collection_id=None)
    monkeypatch.setattr(
        "app.ui.controllers.export_controller.ExportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: ("", "")))

    controller.handle_export_requested()

    assert export_service.calls == []


def test_confirmed_export_calls_service_with_chosen_format_and_scope(
    monkeypatch, main_window: MainWindow
) -> None:
    export_service = FakeExportService(count=5)
    controller = ExportController(main_window, export_service, FakeCollectionService())
    choice = ExportChoice(target=ExportTarget.CARDS, export_format=ExportFormat.EXCEL, collection_id=1)
    monkeypatch.setattr(
        "app.ui.controllers.export_controller.ExportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: ("C:/tmp/out.xlsx", ""))
    )

    controller.handle_export_requested()

    assert len(export_service.calls) == 1
    written_format, written_path, written_target, written_collection_id = export_service.calls[0]
    assert written_format is ExportFormat.EXCEL
    assert Path(written_path) == Path("C:/tmp/out.xlsx")
    assert written_target is ExportTarget.CARDS
    assert written_collection_id == 1


def test_confirmed_export_passes_sealed_target_through(monkeypatch, main_window: MainWindow) -> None:
    export_service = FakeExportService(count=2)
    controller = ExportController(main_window, export_service, FakeCollectionService())
    choice = ExportChoice(target=ExportTarget.SEALED, export_format=ExportFormat.CSV, collection_id=None)
    monkeypatch.setattr(
        "app.ui.controllers.export_controller.ExportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: ("C:/tmp/out.csv", ""))
    )

    controller.handle_export_requested()

    written_target = export_service.calls[0][2]
    assert written_target is ExportTarget.SEALED


def test_wrong_extension_is_corrected_to_match_the_format(
    monkeypatch, main_window: MainWindow
) -> None:
    """A user could type/accept a filename without (or with the wrong)

    extension in the native save dialog -- the written file must still
    match the format actually chosen."""
    export_service = FakeExportService()
    controller = ExportController(main_window, export_service, FakeCollectionService())
    choice = ExportChoice(target=ExportTarget.CARDS, export_format=ExportFormat.PDF, collection_id=None)
    monkeypatch.setattr(
        "app.ui.controllers.export_controller.ExportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: ("C:/tmp/out.txt", ""))
    )

    controller.handle_export_requested()

    _, written_path, _, _ = export_service.calls[0]
    assert Path(written_path).suffix == ".pdf"


def test_export_failure_shows_a_warning_instead_of_crashing(
    monkeypatch, main_window: MainWindow
) -> None:
    export_service = FakeExportService(error=OSError("disk full"))
    controller = ExportController(main_window, export_service, FakeCollectionService())
    choice = ExportChoice(target=ExportTarget.CARDS, export_format=ExportFormat.CSV, collection_id=None)
    monkeypatch.setattr(
        "app.ui.controllers.export_controller.ExportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: ("C:/tmp/out.csv", ""))
    )
    warning = MagicMock()
    monkeypatch.setattr(QMessageBox, "warning", warning)

    controller.handle_export_requested()  # must not raise

    warning.assert_called_once()
