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
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.models.card import Card
from app.ui.set_icon_provider import get_set_icon
from app.ui.theme import apply_elevation
from app.ui.widgets.card_artwork_view import CardArtworkView
from app.utils.formatting import format_price
from app.utils.time import format_display_datetime

#: Internal field identifiers -- also used as ``self._value_labels`` keys and
#: to spot the "Set" row for its icon, so these stay untranslated; only the
#: displayed label text (built from them via ``tr()``) changes with the UI
#: language.
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
        labels.append(tr("Reverse Holo"))
    if card.is_signed:
        labels.append(tr("Signiert"))
    if card.is_first_edition:
        labels.append("1st Edition")
    if card.is_altered:
        labels.append(tr("Altered"))
    return ", ".join(labels) if labels else "—"


class CardDetailPanel(QWidget):
    """Detail view for a single card."""

    #: Emitted with the currently shown card's id.
    price_lookup_requested = Signal(int)
    #: Emitted with the currently shown card's id when "Preisverlauf
    #: anzeigen" is clicked.
    history_panel_requested = Signal(int)
    #: Emitted with the currently shown card's id when "Cardmarket-Link
    #: suchen" is clicked.
    cardmarket_search_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        apply_elevation(self)
        self._value_labels: dict[str, QLabel] = {}
        self._current_card_id: int | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(tr("Kartendetails"))
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._artwork = CardArtworkView()
        # No stretch factor: CardArtworkView now has a fixed height of its
        # own (see its own docstring/comment), so a stretch weight here
        # would be meaningless -- keeping it would misleadingly suggest this
        # widget still grows to fill leftover space.
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
            if field == "Set":
                self._set_icon_label = QLabel()
                self._set_icon_label.setFixedSize(18, 18)
                # No setScaledContents(True): live-reported bug, a visible
                # dark box around the set icon here (but not in the card
                # table, which never stretches its icon this way) -- letting
                # QLabel itself additionally stretch an already-sized pixmap
                # is a second, redundant scale on top of QIcon.pixmap()'s own
                # (see below), and doesn't go through the same alpha-aware
                # scaling path the table's own icon rendering does. Asking
                # the QIcon for exactly the label's own size and displaying
                # it as-is (QLabel's default centred alignment) mirrors what
                # item views already do internally, and needs no stretch at
                # all.
                self._set_icon_label.hide()
                row = QWidget()
                row.setObjectName("TransparentGroup")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                row_layout.addWidget(self._set_icon_label)
                row_layout.addWidget(value, stretch=1)
                form.addRow(key, row)
            else:
                form.addRow(key, value)
        layout.addLayout(form)
        layout.addSpacing(20)

        # Stacked, not side-by-side: two German button labels this long
        # (~28 and ~20 characters) never fit next to each other once the
        # panel wasn't very wide, truncating both.
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

        # Backs "Cardmarket-Link suchen": for a card whose catalogue source
        # has no Cardmarket cross-reference at all (a real, live-confirmed
        # gap for newly released sets), this searches Cardmarket's own site
        # search directly instead of requiring the user to paste a link by
        # hand -- see CardmarketSearchController.
        self._cardmarket_search_button = QPushButton(tr("Cardmarket-Link suchen"))
        self._cardmarket_search_button.setObjectName("Secondary")
        self._cardmarket_search_button.setEnabled(False)
        self._cardmarket_search_button.clicked.connect(self._on_cardmarket_search_button_clicked)
        layout.addWidget(self._cardmarket_search_button)

        # Claims all leftover vertical space on a panel taller than its
        # content needs. Without this, Qt distributes that leftover space
        # among the header/artwork/form/buttons themselves (none of them
        # fixed-size except the artwork) -- live-reported: the artwork's
        # position visibly shifted up/down between cards depending on how
        # many lines the "Price quality" rationale wrapped to, since a
        # longer rationale left less surplus to redistribute above it. A
        # trailing stretch absorbs that surplus itself instead, so every
        # widget above it keeps its natural size regardless of how much
        # blank space remains at the bottom.
        layout.addStretch(1)

    def show_empty(self) -> None:
        """Reset all fields to the empty placeholder value."""
        self._current_card_id = None
        self._price_button.setEnabled(False)
        self._history_button.setEnabled(False)
        self._cardmarket_search_button.setEnabled(False)
        for label in self._value_labels.values():
            label.setText("—")
        self._set_icon_label.hide()
        self._artwork.show_empty()

    def show_card(self, card: Card) -> None:
        """Populate all fields from a real, owned card."""
        self._current_card_id = card.id
        self._price_button.setEnabled(True)
        self._history_button.setEnabled(True)
        self._cardmarket_search_button.setEnabled(True)
        self._artwork.show_photo(card.photo_path, card.is_reverse_holo)
        price = (
            format_price(card.current_price, card.price_currency)
            if card.current_price is not None
            else "—"
        )
        self._value_labels["Name"].setText(card.name)
        self._value_labels["Set"].setText(card.set_name or "—")
        set_icon = get_set_icon(card.set_code, card.set_name)
        if set_icon is not None:
            self._set_icon_label.setPixmap(set_icon.pixmap(18, 18))
            self._set_icon_label.show()
        else:
            self._set_icon_label.hide()
        self._value_labels["Kartennummer"].setText(card.card_number or "—")
        self._value_labels["Extra"].setText(_extras_text(card))
        self._value_labels["Sprache"].setText(card.language.label)
        self._value_labels["Zustand"].setText(card.condition.label)
        self._value_labels["Menge"].setText(str(card.quantity))
        self._value_labels["Preis"].setText(price)
        # The rationale explains *why* (e.g. which language/condition an
        # estimate was actually taken from, or "no price found" for a Base
        # Set card with ambiguous Cardmarket variants) -- shown inline, not
        # just as a hover tooltip, since a user reported the generic quality
        # label alone ("Estimated from a different condition") didn't say
        # *which* condition it used. Skipped when it's just a restatement of
        # the label itself (e.g. MANUAL's rationale is literally "Manually
        # set"), to avoid showing the same phrase twice.
        quality_label = tr(card.price_quality.label)
        rationale = card.price_rationale or ""
        self._value_labels["Preisqualität"].setText(
            f"{quality_label} — {rationale}" if rationale and rationale != quality_label
            else quality_label
        )
        self._value_labels["Preisqualität"].setToolTip(rationale)
        self._value_labels["Letzte Aktualisierung"].setText(
            format_display_datetime(card.price_updated_at) if card.price_updated_at else "—"
        )
        self._value_labels["Notizen"].setText(card.notes or "—")

    def set_price_lookup_running(self, running: bool) -> None:
        """Disable the price button while a lookup is in progress."""
        self._price_button.setEnabled(not running and self._current_card_id is not None)

    def set_cardmarket_search_running(self, running: bool) -> None:
        """Disable the Cardmarket-search button while a search is in progress."""
        self._cardmarket_search_button.setEnabled(
            not running and self._current_card_id is not None
        )

    def set_history_panel_visible(self, visible: bool) -> None:
        """Update the toggle button's label to match the dock's actual state."""
        self._history_button.setText(
            tr("Preisverlauf ausblenden") if visible else tr("Preisverlauf anzeigen")
        )

    def _on_price_button_clicked(self) -> None:
        if self._current_card_id is not None:
            self.price_lookup_requested.emit(self._current_card_id)

    def _on_history_button_clicked(self) -> None:
        if self._current_card_id is not None:
            self.history_panel_requested.emit(self._current_card_id)

    def _on_cardmarket_search_button_clicked(self) -> None:
        if self._current_card_id is not None:
            self.cardmarket_search_requested.emit(self._current_card_id)
