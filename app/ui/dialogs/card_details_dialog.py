"""Form dialog for the owned-copy attributes of a card.

Presentation-only: shows read-only catalogue info (name/set/number/rarity)
and lets the user set the editable attributes (language/condition/extras/
quantity/notes). Used both to add a new card (no ``initial`` values, i.e.
sensible defaults) and to edit an existing one (``initial`` prefills the
form). Reading the confirmed values back is the caller's job via
:meth:`get_values`.

The four "extras" (Reverse Holo/Signed/1st Edition/Altered) are plain
checkboxes — each a definite yes/no, exactly like Cardmarket treats them for
an actual physical card (its own "Egal" is only a *search* option, not
something a real card can *be*). Cardmarket's per-card filters
(``extra[isSigned]`` etc.) need a definite Y/N to match exactly.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language

_DEFAULT_LANGUAGE = Language.ENGLISH
_DEFAULT_CONDITION = Condition.NEAR_MINT
_DEFAULT_QUANTITY = 1


class CardDetailsDialog(QDialog):
    """Collects language/condition/extras/quantity/notes for a card."""

    def __init__(
        self,
        *,
        title: str,
        accept_label: str,
        display_name: str,
        display_set: str,
        display_number: str,
        display_rarity: str = "",
        initial: CardDetailsValues | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._build(
            accept_label=accept_label,
            display_name=display_name,
            display_set=display_set,
            display_number=display_number,
            display_rarity=display_rarity,
            initial=initial,
        )

    def _build(
        self,
        *,
        accept_label: str,
        display_name: str,
        display_set: str,
        display_number: str,
        display_rarity: str,
        initial: CardDetailsValues | None,
    ) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Name:", QLabel(display_name))
        form.addRow("Set:", QLabel(display_set))
        form.addRow("Kartennummer:", QLabel(display_number))
        if display_rarity:
            form.addRow("Rarität:", QLabel(display_rarity))

        self._language_combo = QComboBox()
        for language in Language:
            self._language_combo.addItem(language.label, language)
        form.addRow("Sprache:", self._language_combo)

        self._condition_combo = QComboBox()
        for condition in Condition:
            self._condition_combo.addItem(condition.label, condition)
        form.addRow("Zustand:", self._condition_combo)

        self._reverse_holo_check = QCheckBox("Reverse Holo")
        self._signed_check = QCheckBox("Signiert")
        self._first_edition_check = QCheckBox("1st Edition")
        self._altered_check = QCheckBox("Altered")
        form.addRow("Extra:", self._reverse_holo_check)
        form.addRow("", self._signed_check)
        form.addRow("", self._first_edition_check)
        form.addRow("", self._altered_check)

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setMinimum(1)
        self._quantity_spin.setMaximum(999)
        form.addRow("Menge:", self._quantity_spin)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(60)
        form.addRow("Notizen:", self._notes_edit)

        layout.addLayout(form)

        values = initial or CardDetailsValues(
            language=_DEFAULT_LANGUAGE,
            condition=_DEFAULT_CONDITION,
            quantity=_DEFAULT_QUANTITY,
            notes="",
        )
        self._language_combo.setCurrentIndex(self._language_combo.findData(values.language))
        self._condition_combo.setCurrentIndex(self._condition_combo.findData(values.condition))
        self._reverse_holo_check.setChecked(values.is_reverse_holo)
        self._signed_check.setChecked(values.is_signed)
        self._first_edition_check.setChecked(values.is_first_edition)
        self._altered_check.setChecked(values.is_altered)
        self._quantity_spin.setValue(values.quantity)
        self._notes_edit.setPlainText(values.notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(accept_label)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> CardDetailsValues:
        """The form's current values (call after ``exec()`` returns Accepted)."""
        return CardDetailsValues(
            language=self._language_combo.currentData(),
            condition=self._condition_combo.currentData(),
            is_reverse_holo=self._reverse_holo_check.isChecked(),
            is_signed=self._signed_check.isChecked(),
            is_first_edition=self._first_edition_check.isChecked(),
            is_altered=self._altered_check.isChecked(),
            quantity=self._quantity_spin.value(),
            notes=self._notes_edit.toPlainText().strip(),
        )
