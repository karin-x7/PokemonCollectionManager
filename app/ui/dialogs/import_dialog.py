"""Dialog collecting the two choices an import needs: target and format.

Mirrors ``export_dialog.py``, minus the collection-scope row: unlike
export, an import doesn't target one existing collection -- each row
brings its own "Sammlung" (for cards; sealed products aren't collection-
scoped at all), creating one if it doesn't exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout, QVBoxLayout

from app.i18n import tr
from app.models.enums import ExportFormat, ExportTarget
from app.ui.dialogs.dimmed_dialog import DimmedDialog

#: PDF is a rendered, one-way document -- not a reasonable import source,
#: see app/imports/__init__.py's own docstring.
_IMPORTABLE_FORMATS = tuple(f for f in ExportFormat if f is not ExportFormat.PDF)


@dataclass(frozen=True, slots=True)
class ImportChoice:
    """The user's confirmed target/format choice."""

    target: ExportTarget
    import_format: ExportFormat


class ImportDialog(DimmedDialog):
    """Lets the user pick what to import and from which file format."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._target_combo = QComboBox()
        for target in ExportTarget:
            self._target_combo.addItem(tr(target.label), target)
        form.addRow("What:", self._target_combo)

        self._format_combo = QComboBox()
        for import_format in _IMPORTABLE_FORMATS:
            self._format_combo.addItem(import_format.label, import_format)
        form.addRow("Format:", self._format_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Import")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> ImportChoice:
        """The form's current choice (call after ``exec()`` returns Accepted)."""
        return ImportChoice(
            target=self._target_combo.currentData(),
            import_format=self._format_combo.currentData(),
        )
