"""Right panel: details of the selected sealed product.

Mirrors ``card_detail_panel.py``: presentation-only shell showing the
fields the application tracks for a sealed product, with the same
price-lookup/price-history button pair. No "Kartennummer"/"Extra"/"Zustand"
fields -- sealed products have no card number and no condition ladder
(Cardmarket only ever sells them sealed).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.i18n import tr
from app.models.sealed_product import SealedProduct
from app.ui.theme import apply_elevation
from app.ui.widgets.sealed_artwork_view import SealedArtworkView
from app.utils.time import format_display_datetime

_FIELDS = [
    "Name",
    "Kategorie",
    "Sprache",
    "Menge",
    "Preis",
    "Preisqualität",
    "Letzte Aktualisierung",
    "Notizen",
]


class SealedProductDetailPanel(QWidget):
    """Detail view for a single sealed product."""

    #: Emitted with the currently shown product's id.
    price_lookup_requested = Signal(int)
    #: Emitted with the currently shown product's id when "Preisverlauf
    #: anzeigen" is clicked.
    history_panel_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        apply_elevation(self)
        self._value_labels: dict[str, QLabel] = {}
        self._current_product_id: int | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(tr("Produktdetails"))
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._artwork = SealedArtworkView()
        # No stretch factor: SealedArtworkView now has a fixed height of its
        # own (see its own docstring/comment), so a stretch weight here
        # would be meaningless.
        layout.addWidget(self._artwork)
        layout.addSpacing(20)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        for field in _FIELDS:
            key = QLabel(f"{tr(field)}:")
            key.setObjectName("FieldLabel")
            value = QLabel("—")
            value.setObjectName("FieldValue")
            value.setWordWrap(True)
            self._value_labels[field] = value
            form.addRow(key, value)
        layout.addLayout(form)
        layout.addSpacing(20)

        self._price_button = QPushButton(tr("Preis von Cardmarket abrufen"))
        self._price_button.setObjectName("Secondary")
        self._price_button.setEnabled(False)
        self._price_button.clicked.connect(self._on_price_button_clicked)
        layout.addWidget(self._price_button)

        self._history_button = QPushButton(tr("Preisverlauf anzeigen"))
        self._history_button.setObjectName("Secondary")
        self._history_button.setEnabled(False)
        self._history_button.clicked.connect(self._on_history_button_clicked)
        layout.addWidget(self._history_button)

        # See card_detail_panel.py's identical trailing stretch for why:
        # claims leftover vertical space itself so the header/artwork/form
        # above it don't shift position depending on how many lines the
        # "Price quality" rationale wraps to.
        layout.addStretch(1)

    def show_empty(self) -> None:
        """Reset all fields to the empty placeholder value."""
        self._current_product_id = None
        self._price_button.setEnabled(False)
        self._history_button.setEnabled(False)
        for label in self._value_labels.values():
            label.setText("—")
        self._artwork.show_empty()

    def show_product(self, product: SealedProduct) -> None:
        """Populate all fields from a real, owned sealed product."""
        self._current_product_id = product.id
        self._price_button.setEnabled(True)
        self._history_button.setEnabled(True)
        self._artwork.show_photo(product.photo_path)
        price = (
            f"{product.current_price:.2f} {product.price_currency}"
            if product.current_price is not None
            else "—"
        )
        self._value_labels["Name"].setText(product.name)
        self._value_labels["Kategorie"].setText(product.category or "—")
        self._value_labels["Sprache"].setText(product.language.label)
        self._value_labels["Menge"].setText(str(product.quantity))
        self._value_labels["Preis"].setText(price)
        # Shown inline, not just as a hover tooltip -- see card_detail_panel.py's
        # matching change for why (a generic quality label alone doesn't say
        # *which* language an estimate was actually taken from).
        quality_label = tr(product.price_quality.label)
        rationale = product.price_rationale or ""
        self._value_labels["Preisqualität"].setText(
            f"{quality_label} — {rationale}" if rationale and rationale != quality_label
            else quality_label
        )
        self._value_labels["Preisqualität"].setToolTip(rationale)
        self._value_labels["Letzte Aktualisierung"].setText(
            format_display_datetime(product.price_updated_at) if product.price_updated_at else "—"
        )
        self._value_labels["Notizen"].setText(product.notes or "—")

    def set_price_lookup_running(self, running: bool) -> None:
        """Disable the price button while a lookup is in progress."""
        self._price_button.setEnabled(not running and self._current_product_id is not None)

    def set_history_panel_visible(self, visible: bool) -> None:
        """Update the toggle button's label to match the dock's actual state."""
        self._history_button.setText(
            tr("Preisverlauf ausblenden") if visible else tr("Preisverlauf anzeigen")
        )

    def _on_price_button_clicked(self) -> None:
        if self._current_product_id is not None:
            self.price_lookup_requested.emit(self._current_product_id)

    def _on_history_button_clicked(self) -> None:
        if self._current_product_id is not None:
            self.history_panel_requested.emit(self._current_product_id)
