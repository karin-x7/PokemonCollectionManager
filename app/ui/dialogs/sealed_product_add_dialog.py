"""Dialog collecting everything needed to add a sealed product, upfront.

Unlike ``sealed_product_details_dialog.py`` (used for *editing* an
already-known product), name and category aren't asked here at all: they
aren't known yet at this point (that needs a background Cardmarket lookup
after this dialog closes) and, per explicit user preference, shouldn't
require typing/picking anything manually either -- both are filled in
automatically from the scraped page once the lookup succeeds, with no
second confirmation step. A wrong auto-guessed category (or, more rarely,
name) is fixed the same way any other detail is: via "Bearbeiten" afterward.
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
from app.models.enums import Language
from app.models.sealed_product import SealedProductDetailsValues
from app.ui.dialogs.dimmed_dialog import DimmedDialog

_DEFAULT_LANGUAGE = Language.ENGLISH
_DEFAULT_QUANTITY = 1


class SealedProductAddDialog(DimmedDialog):
    """Collects a Cardmarket link + language/quantity/notes upfront."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Sealed-Produkt eintragen"))
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://www.cardmarket.com/.../Products/...")
        self._url_edit.setMinimumWidth(400)
        form.addRow(tr("Cardmarket-Link:"), self._url_edit)

        self._language_combo = QComboBox()
        for language in Language:
            self._language_combo.addItem(language.label, language)
        self._language_combo.setCurrentIndex(self._language_combo.findData(_DEFAULT_LANGUAGE))
        form.addRow(tr("Sprache:"), self._language_combo)

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setMinimum(1)
        self._quantity_spin.setMaximum(999)
        self._quantity_spin.setValue(_DEFAULT_QUANTITY)
        form.addRow(tr("Menge:"), self._quantity_spin)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(60)
        form.addRow(tr("Notizen:"), self._notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Hinzufügen"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_url(self) -> str:
        """The trimmed Cardmarket link (call after ``exec()`` returns Accepted)."""
        return self._url_edit.text().strip()

    def get_values(self) -> SealedProductDetailsValues:
        """Language/quantity/notes (call after ``exec()`` returns Accepted).

        ``cardmarket_url`` is left ``None`` here -- the caller fills it in
        from :meth:`get_url` once the background lookup has run.
        """
        return SealedProductDetailsValues(
            language=self._language_combo.currentData(),
            quantity=self._quantity_spin.value(),
            notes=self._notes_edit.toPlainText().strip(),
            cardmarket_url=None,
        )
