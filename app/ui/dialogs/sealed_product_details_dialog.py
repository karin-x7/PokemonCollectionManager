"""Form dialog for a sealed product's attributes.

Mirrors ``card_details_dialog.py``, minus everything sealed products don't
have (card number, condition, extras). Name/category are always editable
here (unlike a catalogue card match, there's no guaranteed-correct source
for them -- they're parsed off a Cardmarket page title/breadcrumb).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.i18n import tr
from app.models.enums import Language, SealedCategory
from app.models.sealed_product import SealedProductDetailsValues
from app.ui.dialogs.dimmed_dialog import DimmedDialog

_DEFAULT_LANGUAGE = Language.ENGLISH
_DEFAULT_QUANTITY = 1


class SealedProductDetailsDialog(DimmedDialog):
    """Collects name/category/language/quantity/notes/link for a sealed product."""

    def __init__(
        self,
        *,
        title: str,
        accept_label: str,
        display_name: str,
        display_category: str,
        initial: SealedProductDetailsValues | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._build(
            accept_label=accept_label,
            display_name=display_name,
            display_category=display_category,
            initial=initial,
        )

    def _build(
        self,
        *,
        accept_label: str,
        display_name: str,
        display_category: str,
        initial: SealedProductDetailsValues | None,
    ) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name_edit = QLineEdit(display_name)
        form.addRow(tr("Name:"), self._name_edit)

        # Editable combo, not a plain text field: a fixed list of known
        # categories (see SealedCategory) makes the Sealed tab's category
        # column meaningfully sortable/groupable -- but still editable in
        # case a genuinely new product type doesn't fit any of them.
        self._category_combo = QComboBox()
        self._category_combo.setEditable(True)
        for category in SealedCategory:
            if category is not SealedCategory.OTHER:
                self._category_combo.addItem(category.label, category)
        guessed = SealedCategory.guess_from_text(display_category)
        if guessed is not SealedCategory.OTHER:
            self._category_combo.setCurrentText(guessed.label)
        else:
            # Not recognised -- keep whatever text was actually found
            # (Cardmarket breadcrumb or the existing stored value) rather
            # than silently replacing it with "Sonstiges".
            self._category_combo.setCurrentText(display_category)
        form.addRow(tr("Kategorie:"), self._category_combo)

        self._language_combo = QComboBox()
        for language in Language:
            self._language_combo.addItem(language.label, language)
        form.addRow(tr("Sprache:"), self._language_combo)

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setMinimum(1)
        self._quantity_spin.setMaximum(999)
        form.addRow(tr("Menge:"), self._quantity_spin)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(60)
        form.addRow(tr("Notizen:"), self._notes_edit)

        self._cardmarket_url_edit = QLineEdit()
        self._cardmarket_url_edit.setPlaceholderText(
            "https://www.cardmarket.com/.../Products/..."
        )
        form.addRow(tr("Cardmarket-Link:"), self._cardmarket_url_edit)

        layout.addLayout(form)

        values = initial or SealedProductDetailsValues(
            language=_DEFAULT_LANGUAGE, quantity=_DEFAULT_QUANTITY, notes=""
        )
        self._language_combo.setCurrentIndex(self._language_combo.findData(values.language))
        self._quantity_spin.setValue(values.quantity)
        self._notes_edit.setPlainText(values.notes)
        self._cardmarket_url_edit.setText(values.cardmarket_url or "")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(accept_label)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_identity(self) -> tuple[str, str]:
        """The confirmed (name, category); call after ``exec()`` returns Accepted."""
        return self._name_edit.text().strip(), self._category_combo.currentText().strip()

    def get_values(self) -> SealedProductDetailsValues:
        """The form's current values (call after ``exec()`` returns Accepted)."""
        return SealedProductDetailsValues(
            language=self._language_combo.currentData(),
            quantity=self._quantity_spin.value(),
            notes=self._notes_edit.toPlainText().strip(),
            cardmarket_url=self._cardmarket_url_edit.text().strip() or None,
        )
