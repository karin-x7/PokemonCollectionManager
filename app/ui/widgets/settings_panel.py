"""Top-level "Settings" tab: seller-location filter, browser (placeholder).

A permanent, always-alive central-tab page (see ``app.ui.main_window``) --
unlike :class:`~app.ui.dialogs.settings_dialog.SettingsDialog` (FAQ/Help/
Info), which is only built fresh each time "Info and help" is clicked, this
widget is constructed once at startup and just switched into view, so its
own state (the checkbox) is set once at startup rather than every time it's
opened.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QVBoxLayout, QWidget

from app.ui.theme import PALETTE


class SettingsPanel(QWidget):
    """Seller-location filter + a browser-choice placeholder."""

    #: Emitted whenever the "Only sellers from Germany" checkbox is
    #: toggled; persisted by :class:`~app.ui.controllers.settings_
    #: controller.SettingsController` via ``app.pricing.seller_location``.
    germany_only_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        location_header = QLabel("Seller location")
        location_header.setObjectName("PanelHeader")
        layout.addWidget(location_header)

        self._germany_only_checkbox = QCheckBox("Only sellers from Germany")
        self._germany_only_checkbox.toggled.connect(self.germany_only_changed)
        layout.addWidget(self._germany_only_checkbox)

        germany_only_description = QLabel(
            "Prefers German sellers for automatic price lookups (cards, sealed "
            "products, and the wantlist). Falls back to all of Europe if no "
            "match is found."
        )
        germany_only_description.setWordWrap(True)
        layout.addWidget(germany_only_description)

        more_locations_note = QLabel("<i>More locations coming soon.</i>")
        more_locations_note.setTextFormat(Qt.TextFormat.RichText)
        more_locations_note.setStyleSheet(f"color: {PALETTE.muted};")
        layout.addWidget(more_locations_note)

        browser_header = QLabel("Browser")
        browser_header.setObjectName("PanelHeader")
        browser_header.setStyleSheet("margin-top: 24px;")
        layout.addWidget(browser_header)

        # Disabled placeholder -- Chrome is the only supported browser today
        # (see PROJECT_PROGRESS.md), this just previews the planned setting
        # rather than offering a real choice yet.
        browser_combo = QComboBox()
        browser_combo.addItem("Google Chrome")
        browser_combo.setEnabled(False)
        layout.addWidget(browser_combo)

        more_browsers_note = QLabel("<i>More browsers coming soon.</i>")
        more_browsers_note.setTextFormat(Qt.TextFormat.RichText)
        more_browsers_note.setStyleSheet(f"color: {PALETTE.muted};")
        layout.addWidget(more_browsers_note)

        layout.addStretch(1)

    def set_germany_only(self, enabled: bool) -> None:
        """Set the checkbox's initial state without emitting ``germany_only_changed``."""
        self._germany_only_checkbox.blockSignals(True)
        self._germany_only_checkbox.setChecked(enabled)
        self._germany_only_checkbox.blockSignals(False)
