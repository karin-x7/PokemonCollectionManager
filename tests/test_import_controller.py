"""Tests for ImportController: dialog -> file dialog -> ImportService wiring.

Mirrors ``test_export_controller.py``. Both the target/format dialog and
the native "Open" dialog are monkeypatched so this runs headlessly/
deterministically, without a real modal or filesystem picker ever appearing.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from app.imports.models import ImportFileError, ImportResult, ImportRowError
from app.models.enums import ExportFormat, ExportTarget
from app.ui.app import build_application
from app.ui.controllers.import_controller import ImportController
from app.ui.dialogs.import_dialog import ImportChoice
from app.ui.main_window import MainWindow


class FakeImportService:
    def __init__(self, result: ImportResult | None = None, error: Exception | None = None) -> None:
        self._result = result or ImportResult(imported_count=3, errors=[])
        self._error = error
        self.card_calls: list[tuple] = []
        self.sealed_calls: list[tuple] = []

    def import_cards(self, path, import_format) -> ImportResult:
        self.card_calls.append((path, import_format))
        if self._error is not None:
            raise self._error
        return self._result

    def import_sealed(self, path, import_format) -> ImportResult:
        self.sealed_calls.append((path, import_format))
        if self._error is not None:
            raise self._error
        return self._result


class FakeAcceptedDialog:
    """Stands in for ImportDialog: always "accepted" with a fixed choice."""

    def __init__(self, choice: ImportChoice) -> None:
        self._choice = choice

    def __call__(self, parent=None):
        return self

    def exec(self) -> int:
        return QDialog.DialogCode.Accepted

    def get_values(self) -> ImportChoice:
        return self._choice


class FakeCancelledDialog:
    def __call__(self, parent=None):
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


def test_cancelling_the_choice_dialog_imports_nothing(monkeypatch, main_window: MainWindow) -> None:
    import_service = FakeImportService()
    controller = ImportController(main_window, import_service)
    monkeypatch.setattr("app.ui.controllers.import_controller.ImportDialog", FakeCancelledDialog())

    controller.handle_import_requested()

    assert import_service.card_calls == []


def test_cancelling_the_open_dialog_imports_nothing(monkeypatch, main_window: MainWindow) -> None:
    import_service = FakeImportService()
    controller = ImportController(main_window, import_service)
    choice = ImportChoice(target=ExportTarget.CARDS, import_format=ExportFormat.CSV)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("", "")))

    controller.handle_import_requested()

    assert import_service.card_calls == []


def test_confirmed_card_import_calls_service_with_chosen_path_and_format(
    monkeypatch, main_window: MainWindow
) -> None:
    import_service = FakeImportService(result=ImportResult(imported_count=5, errors=[]))
    controller = ImportController(main_window, import_service)
    choice = ImportChoice(target=ExportTarget.CARDS, import_format=ExportFormat.EXCEL)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("C:/tmp/in.xlsx", ""))
    )

    controller.handle_import_requested()

    assert len(import_service.card_calls) == 1
    path, import_format = import_service.card_calls[0]
    assert Path(path) == Path("C:/tmp/in.xlsx")
    assert import_format is ExportFormat.EXCEL
    assert "5" in main_window.statusBar().currentMessage()


def test_confirmed_sealed_import_calls_the_sealed_method(monkeypatch, main_window: MainWindow) -> None:
    import_service = FakeImportService()
    controller = ImportController(main_window, import_service)
    choice = ImportChoice(target=ExportTarget.SEALED, import_format=ExportFormat.CSV)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("C:/tmp/in.csv", ""))
    )

    controller.handle_import_requested()

    assert len(import_service.sealed_calls) == 1
    assert import_service.card_calls == []


def test_on_imported_callback_runs_only_when_rows_were_actually_imported(
    monkeypatch, main_window: MainWindow
) -> None:
    on_imported = MagicMock()
    import_service = FakeImportService(result=ImportResult(imported_count=0, errors=[]))
    controller = ImportController(main_window, import_service, on_imported=on_imported)
    choice = ImportChoice(target=ExportTarget.CARDS, import_format=ExportFormat.CSV)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("C:/tmp/in.csv", ""))
    )

    controller.handle_import_requested()

    on_imported.assert_not_called()


def test_on_imported_callback_runs_when_rows_were_imported(
    monkeypatch, main_window: MainWindow
) -> None:
    on_imported = MagicMock()
    import_service = FakeImportService(result=ImportResult(imported_count=2, errors=[]))
    controller = ImportController(main_window, import_service, on_imported=on_imported)
    choice = ImportChoice(target=ExportTarget.CARDS, import_format=ExportFormat.CSV)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("C:/tmp/in.csv", ""))
    )

    controller.handle_import_requested()

    on_imported.assert_called_once()


def test_row_errors_are_shown_in_a_warning_dialog(monkeypatch, main_window: MainWindow) -> None:
    import_service = FakeImportService(
        result=ImportResult(
            imported_count=1, errors=[ImportRowError(row_number=3, message="Name is missing.")]
        )
    )
    controller = ImportController(main_window, import_service)
    choice = ImportChoice(target=ExportTarget.CARDS, import_format=ExportFormat.CSV)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("C:/tmp/in.csv", ""))
    )
    warning = MagicMock()
    monkeypatch.setattr(QMessageBox, "warning", warning)

    controller.handle_import_requested()

    warning.assert_called_once()
    message = warning.call_args[0][2]
    assert "Row 3" in message
    assert "Name is missing." in message


def test_file_read_failure_shows_a_warning_instead_of_crashing(
    monkeypatch, main_window: MainWindow
) -> None:
    import_service = FakeImportService(error=ImportFileError("not a valid file"))
    controller = ImportController(main_window, import_service)
    choice = ImportChoice(target=ExportTarget.CARDS, import_format=ExportFormat.CSV)
    monkeypatch.setattr(
        "app.ui.controllers.import_controller.ImportDialog", FakeAcceptedDialog(choice)
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **kw: ("C:/tmp/in.csv", ""))
    )
    warning = MagicMock()
    monkeypatch.setattr(QMessageBox, "warning", warning)

    controller.handle_import_requested()  # must not raise

    warning.assert_called_once()
