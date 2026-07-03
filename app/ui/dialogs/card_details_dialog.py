"""Form dialog for the owned-copy attributes of a card.

Presentation-only: shows read-only catalogue info (name/set/number/rarity)
and lets the user set the editable attributes (variant/language/condition/
quantity/notes). Used both to add a new card (no ``initial`` values, i.e.
sensible defaults) and to edit an existing one (``initial`` prefills the
form). Reading the confirmed values back is the caller's job via
:meth:`get_values`.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
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
from app.models.enums import Condition, Language, Variant

_DEFAULT_VARIANT = Variant.NORMAL
_DEFAULT_LANGUAGE = Language.ENGLISH
_DEFAULT_CONDITION = Condition.NEAR_MINT
_DEFAULT_QUANTITY = 1


class CardDetailsDialog(QDialog):
    """Collects variant/language/condition/quantity/notes for a card."""

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

        self._variant_combo = QComboBox()
        for variant in Variant:
            self._variant_combo.addItem(variant.value, variant)
        form.addRow("Variante:", self._variant_combo)

        self._language_combo = QComboBox()
        for language in Language:
            self._language_combo.addItem(language.label, language)
        form.addRow("Sprache:", self._language_combo)

        self._condition_combo = QComboBox()
        for condition in Condition:
            self._condition_combo.addItem(condition.label, condition)
        form.addRow("Zustand:", self._condition_combo)

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setMinimum(1)
        self._quantity_spin.setMaximum(999)
        form.addRow("Menge:", self._quantity_spin)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(60)
        form.addRow("Notizen:", self._notes_edit)

        layout.addLayout(form)

        values = initial or CardDetailsValues(
            variant=_DEFAULT_VARIANT,
            language=_DEFAULT_LANGUAGE,
            condition=_DEFAULT_CONDITION,
            quantity=_DEFAULT_QUANTITY,
            notes="",
        )
        self._variant_combo.setCurrentIndex(self._variant_combo.findData(values.variant))
        self._language_combo.setCurrentIndex(self._language_combo.findData(values.language))
        self._condition_combo.setCurrentIndex(self._condition_combo.findData(values.condition))
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
            # Variant is a ``str``-subclassed Enum, so Qt's item-data
            # marshalling silently coerces it down to a plain ``str`` on the
            # way out of the combo box (measured live) — resolve it back
            # through ``from_value`` rather than trusting ``currentData()``'s
            # type. Language/Condition are plain Enums and round-trip fine.
            variant=Variant.from_value(self._variant_combo.currentData()),
            language=self._language_combo.currentData(),
            condition=self._condition_combo.currentData(),
            quantity=self._quantity_spin.value(),
            notes=self._notes_edit.toPlainText().strip(),
        )
