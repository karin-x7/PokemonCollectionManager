"""Form dialog for editing a wantlist item's attributes.

Mirrors ``sealed_product_details_dialog.py``, with name/set shown read-only
(unlike a sealed product, name/set/card_number come straight from the
initial Cardmarket lookup and aren't meant to change afterward -- delete and
re-add if they're ever wrong) and a condition field added (a single card,
unlike a sealed product, has a Cardmarket condition ladder).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
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


class WantlistItemDetailsDialog(DimmedDialog):
    """Collects language/condition/target price/notes/link for a wantlist item."""

    def __init__(
        self,
        *,
        title: str,
        accept_label: str,
        display_name: str,
        display_set: str,
        initial: WantlistItemDetailsValues | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._build(accept_label=accept_label, display_name=display_name, display_set=display_set, initial=initial)

    def _build(
        self,
        *,
        accept_label: str,
        display_name: str,
        display_set: str,
        initial: WantlistItemDetailsValues | None,
    ) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        name_label = QLabel(display_name)
        form.addRow("Name:", name_label)
        set_label = QLabel(display_set or "—")
        form.addRow("Set:", set_label)

        self._language_combo = QComboBox()
        for language in Language:
            self._language_combo.addItem(language.label, language)
        form.addRow("Language:", self._language_combo)

        self._condition_combo = QComboBox()
        for condition in Condition:
            self._condition_combo.addItem(condition.label, condition)
        form.addRow("Condition:", self._condition_combo)

        self._target_price_spin = QDoubleSpinBox()
        self._target_price_spin.setDecimals(2)
        self._target_price_spin.setMinimum(0.01)
        self._target_price_spin.setMaximum(999999.0)
        self._target_price_spin.setSuffix(" EUR")
        form.addRow("Target price:", self._target_price_spin)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(60)
        form.addRow("Notes:", self._notes_edit)

        self._cardmarket_url_edit = QLineEdit()
        self._cardmarket_url_edit.setPlaceholderText(
            "https://www.cardmarket.com/.../Products/Singles/..."
        )
        form.addRow("Cardmarket link:", self._cardmarket_url_edit)

        layout.addLayout(form)

        values = initial or WantlistItemDetailsValues(
            language=_DEFAULT_LANGUAGE, condition=_DEFAULT_CONDITION, target_price=_DEFAULT_TARGET_PRICE
        )
        self._language_combo.setCurrentIndex(self._language_combo.findData(values.language))
        self._condition_combo.setCurrentIndex(self._condition_combo.findData(values.condition))
        self._target_price_spin.setValue(values.target_price)
        self._notes_edit.setPlainText(values.notes)
        self._cardmarket_url_edit.setText(values.cardmarket_url or "")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(accept_label)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> WantlistItemDetailsValues:
        """The form's current values (call after ``exec()`` returns Accepted)."""
        return WantlistItemDetailsValues(
            language=self._language_combo.currentData(),
            condition=self._condition_combo.currentData(),
            target_price=self._target_price_spin.value(),
            notes=self._notes_edit.toPlainText().strip(),
            cardmarket_url=self._cardmarket_url_edit.text().strip() or None,
        )
