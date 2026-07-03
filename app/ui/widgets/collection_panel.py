"""Left panel: the list of collections.

This is a presentation-only shell. It emits high-level signals
(``collection_selected``, ``new_collection_requested``) that a controller/
service will connect to in later steps — no persistence or business logic
lives here. The sample entries are placeholder content that will be replaced
by real data from the collection service in Step 3.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Placeholder collections, purely to visualise the layout (Step 3 replaces this).
_DEMO_COLLECTIONS = ["Order 1", "Order 2", "Binder", "PSA Submission", "Vintage", "Verkauf"]


class CollectionPanel(QWidget):
    """Sidebar listing the user's collections."""

    collection_selected = Signal(str)
    new_collection_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("Sammlungen")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._list = QListWidget()
        for name in _DEMO_COLLECTIONS:  # placeholder content
            self._list.addItem(QListWidgetItem(name))
        self._list.currentTextChanged.connect(self.collection_selected)
        layout.addWidget(self._list, stretch=1)

        add_button = QPushButton("+ Neue Sammlung")
        add_button.clicked.connect(self.new_collection_requested)
        layout.addWidget(add_button)
