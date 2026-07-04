"""Right panel: details of the selected card.

Presentation-only shell showing the fields the application tracks for a
card. Emits ``price_lookup_requested`` (the shown card's id) when the user
clicks "Preis von Cardmarket abrufen" — the controller drives the actual
lookup and calls :meth:`set_price_lookup_running` to disable the button
meanwhile. Emits ``history_panel_requested`` when the user clicks the
history button -- the price-history chart itself lives in the separate
:class:`~app.ui.widgets.price_history_dock.PriceHistoryDock` (a dockable
side panel), not here, so a single card's artwork has room to be the
dominant visual element instead of competing with a chart for space. That
button is a toggle: :class:`~app.ui.main_window.MainWindow` decides whether
each click should show or hide the dock, and calls back into
:meth:`set_history_panel_visible` so the button's label always matches
the dock's actual current visibility (including when it was closed via its
own title-bar close button, not this one).
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
from app.ui.widgets.card_artwork_view import CardArtworkView

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
    #: Emitted with the currently shown card's id when "Preisverlauf
    #: anzeigen" is clicked.
    history_panel_requested = Signal(int)

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
        layout.addWidget(self._artwork, stretch=1)
        layout.addSpacing(20)

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
        layout.addSpacing(20)

        # Stacked, not side-by-side: two German button labels this long
        # (~28 and ~20 characters) never fit next to each other once the
        # panel wasn't very wide, truncating both.
        self._price_button = QPushButton("Preis von Cardmarket abrufen")
        self._price_button.setObjectName("Secondary")
        self._price_button.setEnabled(False)
        self._price_button.clicked.connect(self._on_price_button_clicked)
        layout.addWidget(self._price_button)

        self._history_button = QPushButton("Preisverlauf anzeigen")
        self._history_button.setObjectName("Secondary")
        self._history_button.setEnabled(False)
        self._history_button.clicked.connect(self._on_history_button_clicked)
        layout.addWidget(self._history_button)

    def show_empty(self) -> None:
        """Reset all fields to the empty placeholder value."""
        self._current_card_id = None
        self._price_button.setEnabled(False)
        self._history_button.setEnabled(False)
        for label in self._value_labels.values():
            label.setText("—")
        self._artwork.show_empty()

    def show_card(self, card: Card) -> None:
        """Populate all fields from a real, owned card."""
        self._current_card_id = card.id
        self._price_button.setEnabled(True)
        self._history_button.setEnabled(True)
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

    def set_price_lookup_running(self, running: bool) -> None:
        """Disable the price button while a lookup is in progress."""
        self._price_button.setEnabled(not running and self._current_card_id is not None)

    def set_history_panel_visible(self, visible: bool) -> None:
        """Update the toggle button's label to match the dock's actual state."""
        self._history_button.setText(
            "Preisverlauf ausblenden" if visible else "Preisverlauf anzeigen"
        )

    def _on_price_button_clicked(self) -> None:
        if self._current_card_id is not None:
            self.price_lookup_requested.emit(self._current_card_id)

    def _on_history_button_clicked(self) -> None:
        if self._current_card_id is not None:
            self.history_panel_requested.emit(self._current_card_id)
