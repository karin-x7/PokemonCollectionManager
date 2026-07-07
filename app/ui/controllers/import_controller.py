"""Wires the toolbar's "Import" action to :class:`ImportService`.

Mirrors ``export_controller.py``: shows :class:`~app.ui.dialogs.
import_dialog.ImportDialog` to collect target/format, then a native "Open"
dialog for the source file, then calls the service and reports a summary
(imported count + any per-row errors) instead of propagating an exception.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QFileDialog, QMainWindow, QMessageBox

from app.imports.models import ImportFileError, ImportResult
from app.logging_config import get_logger
from app.models.enums import ExportTarget
from app.services.import_service import ImportService
from app.ui.dialogs.import_dialog import ImportDialog

logger = get_logger(__name__)

#: Shown to a max of this many individual row errors in the result dialog --
#: a file with hundreds of bad rows would otherwise produce an unreadable
#: wall of text; the count itself still reflects the true total.
_MAX_SHOWN_ERRORS = 20


def _file_filters() -> dict[str, str]:
    return {
        "csv": "CSV file (*.csv)",
        "xlsx": "Excel file (*.xlsx)",
        "json": "JSON file (*.json)",
    }


class ImportController(QObject):
    """Handles the toolbar's "Import" action end to end."""

    def __init__(
        self,
        main_window: QMainWindow,
        import_service: ImportService,
        on_imported=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._import_service = import_service
        self._on_imported = on_imported

    def handle_import_requested(self) -> None:
        dialog = ImportDialog(parent=self._main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        choice = dialog.get_values()

        path_str, _ = QFileDialog.getOpenFileName(
            self._main_window,
            "Import",
            "",
            _file_filters()[choice.import_format.extension],
        )
        if not path_str:
            return
        path = Path(path_str)

        try:
            if choice.target is ExportTarget.SEALED:
                result = self._import_service.import_sealed(path, choice.import_format)
            else:
                result = self._import_service.import_cards(path, choice.import_format)
        except ImportFileError as exc:
            logger.error("Import from %s failed: %s", path, exc)
            QMessageBox.warning(self._main_window, "Import failed", str(exc))
            return

        logger.info(
            "Imported %d row(s) from %s (%d error(s))", result.imported_count, path, len(result.errors)
        )
        if self._on_imported is not None and result.imported_count:
            self._on_imported()
        self._show_result(path, result)

    def _show_result(self, path: Path, result: ImportResult) -> None:
        message = f'{result.imported_count} row(s) imported from "{path.name}".'
        if result.errors:
            shown = result.errors[:_MAX_SHOWN_ERRORS]
            lines = [f"Row {e.row_number}: {e.message}" for e in shown]
            if len(result.errors) > _MAX_SHOWN_ERRORS:
                lines.append(f"...and {len(result.errors) - _MAX_SHOWN_ERRORS} more.")
            message += f"\n\n{len(result.errors)} row(s) skipped:\n" + "\n".join(lines)
            QMessageBox.warning(self._main_window, "Import finished with errors", message)
        else:
            self._main_window.statusBar().showMessage(message, 5000)
