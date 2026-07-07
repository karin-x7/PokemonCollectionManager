"""Dialog collecting everything needed to add a wantlist item, upfront.

Mirrors ``sealed_product_add_dialog.py``: name/set/card_number aren't asked
here -- they're filled in automatically from the pasted Cardmarket link via
a background lookup once this dialog closes (see
``app.ui.controllers.wantlist_entry_controller.WantlistEntryController``),
with no second confirmation dialog.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from app.models.enums import Condition, Language
from app.models.wantlist import WantlistItemDetailsValues
from app.ui.dialogs.dimmed_dialog import DimmedDialog

_DEFAULT_LANGUAGE = Language.ENGLISH
_DEFAULT_CONDITION = Condition.NEAR_MINT
_DEFAULT_TARGET_PRICE = 1.0


class WantlistAddDialog(DimmedDialog):
    """Collects a Cardmarket link + language/condition/target price/notes upfront."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add to wantlist")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://www.cardmarket.com/.../Products/Singles/...")
        self._url_edit.setMinimumWidth(400)
        form.addRow("Cardmarket link:", self._url_edit)

        self._language_combo = QComboBox()
        for language in Language:
            self._language_combo.addItem(language.label, language)
        self._language_combo.setCurrentIndex(self._language_combo.findData(_DEFAULT_LANGUAGE))
        form.addRow("Language:", self._language_combo)

        self._condition_combo = QComboBox()
        for condition in Condition:
            self._condition_combo.addItem(condition.label, condition)
        self._condition_combo.setCurrentIndex(self._condition_combo.findData(_DEFAULT_CONDITION))
        form.addRow("Condition:", self._condition_combo)

        self._target_price_spin = QDoubleSpinBox()
        self._target_price_spin.setDecimals(2)
        self._target_price_spin.setMinimum(0.01)
        self._target_price_spin.setMaximum(999999.0)
        self._target_price_spin.setValue(_DEFAULT_TARGET_PRICE)
        self._target_price_spin.setSuffix(" EUR")
        form.addRow("Target price:", self._target_price_spin)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(60)
        form.addRow("Notes:", self._notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_url(self) -> str:
        """The trimmed Cardmarket link (call after ``exec()`` returns Accepted)."""
        return self._url_edit.text().strip()

    def get_values(self) -> WantlistItemDetailsValues:
        """Language/condition/target price/notes (call after ``exec()``

        returns Accepted). ``cardmarket_url`` is left ``None`` here -- the
        caller fills it in from :meth:`get_url` once the background lookup
        has run.
        """
        return WantlistItemDetailsValues(
            language=self._language_combo.currentData(),
            condition=self._condition_combo.currentData(),
            target_price=self._target_price_spin.value(),
            notes=self._notes_edit.toPlainText().strip(),
            cardmarket_url=None,
        )
