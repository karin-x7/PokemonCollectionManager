"""Dialog for picking which collection to move a card/sealed product into.

Presentation-only: :meth:`get_target_collection_id` hands back the chosen
id -- actually persisting the move is the caller's job via
:meth:`~app.services.card_service.CardService.move_card`/
:meth:`~app.services.sealed_product_service.SealedProductService.
move_product`. Shared by both the card and the sealed-product list panel.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout, QVBoxLayout

from app.i18n import tr
from app.models.collection import Collection
from app.ui.dialogs.dimmed_dialog import DimmedDialog


class MoveDialog(DimmedDialog):
    """Lets the user pick which collection to move an item into.

    ``collections`` should already exclude the item's current collection --
    there's nothing to "move to" there.
    """

    def __init__(self, collections: list[Collection], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Verschieben"))
        self._build(collections)

    def _build(self, collections: list[Collection]) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._target_combo = QComboBox()
        for collection in collections:
            self._target_combo.addItem(collection.name, collection.id)
        form.addRow(tr("Zielsammlung:"), self._target_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Verschieben"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_target_collection_id(self) -> int:
        """The chosen target collection's id (call after ``exec()`` returns Accepted)."""
        return self._target_combo.currentData()
