"""Dialog collecting a single, user-supplied price override.

Presentation-only: :meth:`get_price` hands back the entered value -- actually
persisting it (and recording it in the price history) is the caller's job
via :meth:`~app.services.card_service.CardService.set_manual_price`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox, QDoubleSpinBox, QFormLayout, QVBoxLayout

from app.i18n import tr
from app.ui.dialogs.dimmed_dialog import DimmedDialog

_MAX_PRICE = 1_000_000.0


class ManualPriceDialog(DimmedDialog):
    """Asks for a price to use instead of the automatically determined one.

    For cases where the automatic Cardmarket matching picked a mislabeled
    listing (e.g. a seller listing a PSA 1 graded card as "Near Mint"
    condition) and the user wants to override it with the price they
    already know is right.
    """

    def __init__(self, current_price: float | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Preis manuell bearbeiten"))
        self._build(current_price)

    def _build(self, current_price: float | None) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._price_spin = QDoubleSpinBox()
        self._price_spin.setRange(0.01, _MAX_PRICE)
        self._price_spin.setDecimals(2)
        self._price_spin.setSuffix(" EUR")
        self._price_spin.setValue(current_price if current_price else 0.01)
        form.addRow(tr("Preis:"), self._price_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_price(self) -> float:
        """The entered price (call after ``exec()`` returns Accepted)."""
        return self._price_spin.value()
