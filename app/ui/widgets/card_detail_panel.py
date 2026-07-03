"""Right panel: details of the selected card.

Presentation-only shell showing the fields the application tracks for a card,
plus placeholder action buttons. Wiring to real card data and to the price
engine happens in later steps. Emits ``open_on_cardmarket_requested`` for the
future controller to handle.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_FIELDS = [
    "Name",
    "Set",
    "Kartennummer",
    "Variante",
    "Sprache",
    "Zustand",
    "Menge",
    "Preis",
    "Preisqualität",
    "Letzte Aktualisierung",
    "Notizen",
]


class CardDetailPanel(QWidget):
    """Detail view for a single card."""

    open_on_cardmarket_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._value_labels: dict[str, QLabel] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Kartendetails")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        photo = QFrame()
        photo.setObjectName("Panel")
        photo.setMinimumHeight(180)
        photo_layout = QVBoxLayout(photo)
        placeholder = QLabel("Kein Foto")
        placeholder.setObjectName("EmptyState")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_layout.addWidget(placeholder)
        layout.addWidget(photo)

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

        layout.addStretch(1)

        open_button = QPushButton("Auf Cardmarket öffnen")
        open_button.setObjectName("Secondary")
        open_button.clicked.connect(self.open_on_cardmarket_requested)
        layout.addWidget(open_button)

    def show_empty(self) -> None:
        """Reset all fields to the empty placeholder value."""
        for label in self._value_labels.values():
            label.setText("—")
