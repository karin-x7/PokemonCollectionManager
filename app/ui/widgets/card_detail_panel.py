"""Right panel: details of the selected card.

Presentation-only shell showing the fields the application tracks for a
card. Emits ``price_lookup_requested`` (the shown card's id) when the user
clicks "Preis von Cardmarket abrufen" — the controller drives the actual
lookup and calls :meth:`set_price_lookup_running` to disable the button
meanwhile.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.card import Card
from app.models.price import PriceRecord
from app.ui.widgets.card_artwork_view import CardArtworkView
from app.ui.widgets.price_history_chart import PriceHistoryChartView

_FIELDS = [
    "Name",
    "Set",
    "Kartennummer",
    "Extra",
    "Sprache",
    "Zustand",
    "Menge",
    "Preis",
    "Preisqualität",
    "Letzte Aktualisierung",
    "Notizen",
]


def _extras_text(card: Card) -> str:
    labels = []
    if card.is_reverse_holo:
        labels.append("Reverse Holo")
    if card.is_signed:
        labels.append("Signiert")
    if card.is_first_edition:
        labels.append("1st Edition")
    if card.is_altered:
        labels.append("Altered")
    return ", ".join(labels) if labels else "—"


class CardDetailPanel(QWidget):
    """Detail view for a single card."""

    #: Emitted with the currently shown card's id.
    price_lookup_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._value_labels: dict[str, QLabel] = {}
        self._current_card_id: int | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Kartendetails")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._artwork = CardArtworkView()
        layout.addWidget(self._artwork)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        for field in _FIELDS:
            key = QLabel(f"{field}:")
            key.setObjectName("FieldLabel")
            value = QLabel("—")
            value.setObjectName("FieldValue")
            value.setWordWrap(True)
            self._value_labels[field] = value
            form.addRow(key, value)
        layout.addLayout(form)

        history_header = QLabel("Preisverlauf:")
        history_header.setObjectName("FieldLabel")
        layout.addWidget(history_header)
        self._price_history = PriceHistoryChartView()
        layout.addWidget(self._price_history)

        layout.addStretch(1)

        self._price_button = QPushButton("Preis von Cardmarket abrufen")
        self._price_button.setObjectName("Secondary")
        self._price_button.setEnabled(False)
        self._price_button.clicked.connect(self._on_price_button_clicked)
        layout.addWidget(self._price_button)

    def show_empty(self) -> None:
        """Reset all fields to the empty placeholder value."""
        self._current_card_id = None
        self._price_button.setEnabled(False)
        for label in self._value_labels.values():
            label.setText("—")
        self._artwork.show_empty()
        self._price_history.show_empty()

    def show_card(self, card: Card) -> None:
        """Populate all fields from a real, owned card."""
        self._current_card_id = card.id
        self._price_button.setEnabled(True)
        self._artwork.show_photo(card.photo_path, card.is_reverse_holo)
        price = (
            f"{card.current_price:.2f} {card.price_currency}"
            if card.current_price is not None
            else "—"
        )
        self._value_labels["Name"].setText(card.name)
        self._value_labels["Set"].setText(card.set_name or "—")
        self._value_labels["Kartennummer"].setText(card.card_number or "—")
        self._value_labels["Extra"].setText(_extras_text(card))
        self._value_labels["Sprache"].setText(card.language.label)
        self._value_labels["Zustand"].setText(card.condition.label)
        self._value_labels["Menge"].setText(str(card.quantity))
        self._value_labels["Preis"].setText(price)
        self._value_labels["Preisqualität"].setText(card.price_quality.label)
        self._value_labels["Letzte Aktualisierung"].setText(card.price_updated_at or "—")
        self._value_labels["Notizen"].setText(card.notes or "—")

    def show_price_history(self, records: list[PriceRecord]) -> None:
        """Render the currently shown card's price history."""
        self._price_history.show_history(records)

    def set_price_lookup_running(self, running: bool) -> None:
        """Disable the price button while a lookup is in progress."""
        self._price_button.setEnabled(not running and self._current_card_id is not None)

    def _on_price_button_clicked(self) -> None:
        if self._current_card_id is not None:
            self.price_lookup_requested.emit(self._current_card_id)
