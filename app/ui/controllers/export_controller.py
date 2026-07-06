"""Wires the toolbar's "Export" action to :class:`ExportService`.

Presentation-adjacent glue: shows :class:`~app.ui.dialogs.export_dialog.
ExportDialog` to collect format/scope, then a native "Save As" dialog for
the destination path, then calls the service and reports success/failure —
no business logic of its own.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QDialog, QFileDialog, QMainWindow, QMessageBox

from app.i18n import tr
from app.logging_config import get_logger
from app.models.enums import ExportTarget
from app.services.collection_service import CollectionService
from app.services.export_service import ExportService
from app.ui.dialogs.export_dialog import ExportDialog

logger = get_logger(__name__)

#: Suggested file name stem per target -- keeps a Karten- and a
#: Sealed-Produkte-Export from silently overwriting each other if both are
#: saved into the same folder back to back.
_FILENAME_STEMS = {
    ExportTarget.CARDS: "pokemon_sammlung",
    ExportTarget.SEALED: "pokemon_sealed",
}


def _file_filters() -> dict[str, str]:
    # A function, not a module-level constant: tr() must run once the UI
    # language has been loaded (see app/i18n.py), not at import time.
    # QFileDialog name filters, keyed by the same ExportFormat.extension the
    # dialog already carries -- lets the save dialog show/enforce the right
    # file type without a second format-to-filter mapping living elsewhere.
    return {
        "csv": tr("CSV-Datei (*.csv)"),
        "xlsx": tr("Excel-Datei (*.xlsx)"),
        "json": tr("JSON-Datei (*.json)"),
        "pdf": tr("PDF-Datei (*.pdf)"),
    }


class ExportController(QObject):
    """Handles the toolbar's "Export" action end to end."""

    def __init__(
        self,
        main_window: QMainWindow,
        export_service: ExportService,
        collection_service: CollectionService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._export_service = export_service
        self._collections = collection_service

    def handle_export_requested(self) -> None:
        dialog = ExportDialog(self._collections.list_collections(), parent=self._main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        choice = dialog.get_values()

        suggested_name = f"{_FILENAME_STEMS[choice.target]}.{choice.export_format.extension}"
        path_str, _ = QFileDialog.getSaveFileName(
            self._main_window,
            tr("Exportieren"),
            suggested_name,
            _file_filters()[choice.export_format.extension],
        )
        if not path_str:
            return
        path = Path(path_str)
        if path.suffix.casefold() != f".{choice.export_format.extension}":
            path = path.with_suffix(f".{choice.export_format.extension}")

        try:
            count = self._export_service.export(
                choice.export_format, path, choice.target, choice.collection_id
            )
        except OSError as exc:
            logger.error("Export to %s failed: %s", path, exc)
            QMessageBox.warning(
                self._main_window,
                tr("Export fehlgeschlagen"),
                tr("Die Datei konnte nicht geschrieben werden:\n{error}").format(error=exc),
            )
            return

        logger.info("Exported %d row(s) to %s", count, path)
        unit = tr("Karte(n)") if choice.target is ExportTarget.CARDS else tr("Sealed-Produkt(e)")
        self._main_window.statusBar().showMessage(
            tr("{count} {unit} nach „{name}“ exportiert.").format(
                count=count, unit=unit, name=path.name
            ),
            5000,
        )
