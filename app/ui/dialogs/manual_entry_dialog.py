"""Dialog collecting a single Cardmarket product link.

Presentation-only: :meth:`get_url` hands back the trimmed link -- actually
opening it in Chrome and reading its title is the caller's job via
:class:`~app.ui.controllers.manual_entry_controller.ManualEntryController`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout

from app.i18n import tr
from app.ui.dialogs.dimmed_dialog import DimmedDialog


class ManualEntryDialog(DimmedDialog):
    """Asks for the Cardmarket product link to look up.

    ``title`` defaults to the card-entry flow's own title -- resolved at
    call time (not as a default-argument value), since a default evaluated
    once at import/def time would freeze in whatever UI language was active
    then (see app/i18n.py) regardless of the real, current setting.
    """

    def __init__(self, title: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title if title is not None else tr("Karte manuell eintragen"))
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://www.cardmarket.com/.../Products/Singles/...")
        self._url_edit.setMinimumWidth(400)
        form.addRow(tr("Cardmarket-Link:"), self._url_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Weiter"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_url(self) -> str:
        """The trimmed link (call after ``exec()`` returns Accepted)."""
        return self._url_edit.text().strip()
