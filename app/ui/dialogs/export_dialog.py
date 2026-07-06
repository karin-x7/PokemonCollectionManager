"""Dialog collecting the three choices an export needs: target, format, scope.

Presentation-only: :meth:`get_values` hands back the chosen
:class:`~app.models.enums.ExportTarget`/:class:`~app.models.enums.
ExportFormat` and collection id (``None`` for "every collection") —
actually resolving cards/sealed products and writing the file is the
caller's job via :class:`~app.services.export_service.ExportService`.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout, QVBoxLayout

from app.i18n import tr
from app.models.collection import Collection
from app.models.enums import ExportFormat, ExportTarget
from app.ui.dialogs.dimmed_dialog import DimmedDialog

_ALL_COLLECTIONS_ROLE_VALUE = None


@dataclass(frozen=True, slots=True)
class ExportChoice:
    """The user's confirmed target/format/scope choice."""

    target: ExportTarget
    export_format: ExportFormat
    collection_id: int | None


class ExportDialog(DimmedDialog):
    """Lets the user pick what to export, in which format, and which collection(s)."""

    def __init__(self, collections: list[Collection], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Exportieren"))
        self._build(collections)

    def _build(self, collections: list[Collection]) -> None:
        layout = QVBoxLayout(self)
        self._form = QFormLayout()

        self._target_combo = QComboBox()
        for target in ExportTarget:
            self._target_combo.addItem(tr(target.label), target)
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        self._form.addRow(tr("Was:"), self._target_combo)

        self._format_combo = QComboBox()
        for export_format in ExportFormat:
            self._format_combo.addItem(export_format.label, export_format)
        self._form.addRow(tr("Format:"), self._format_combo)

        self._scope_combo = QComboBox()
        self._scope_combo.addItem(tr("Alle Sammlungen"), _ALL_COLLECTIONS_ROLE_VALUE)
        for collection in collections:
            self._scope_combo.addItem(collection.name, collection.id)
        self._form.addRow(tr("Sammlung:"), self._scope_combo)
        self._on_target_changed()

        layout.addLayout(self._form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Exportieren"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_target_changed(self) -> None:
        # Sealed products aren't collection-scoped (unlike cards, kept in
        # physical folders/binders) -- the "Sammlung" row doesn't apply.
        is_sealed = self._target_combo.currentData() == ExportTarget.SEALED
        self._form.setRowVisible(self._scope_combo, not is_sealed)

    def get_values(self) -> ExportChoice:
        """The form's current choice (call after ``exec()`` returns Accepted)."""
        target = self._target_combo.currentData()
        collection_id = (
            None if target == ExportTarget.SEALED else self._scope_combo.currentData()
        )
        return ExportChoice(
            target=target,
            export_format=self._format_combo.currentData(),
            collection_id=collection_id,
        )
