"""Filter/search bar shown above the card list.

Presentation-only: emits the current filter state whenever any control
changes, and a separate scope toggle for "search every collection" vs. just
the currently selected one. The controller combines this with whichever
collection is selected and calls
:meth:`~app.services.card_service.CardService.search_cards`; no filtering
logic or persistence lives here.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.card import CardFilter
from app.models.enums import Condition, Language

_ALL = "Alle"


class CardFilterBar(QWidget):
    """Text search + dropdown/range filters for the owned-card list."""

    #: Emitted with the current filter whenever any field changes.
    #: ``collection_id`` is always left at its default (``None``) here — the
    #: controller fills it in based on the selected collection / scope toggle.
    filter_changed = Signal(object)
    #: Emitted with the "search every collection" checkbox's new state.
    scope_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        # Two rows instead of one long one: cramming search + three combos +
        # two price fields + a checkbox + a button into a single row forced
        # every control below its natural width once the panel wasn't very
        # wide, truncating their text/placeholders.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        outer.addLayout(top_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Suche (Name, Set, Nummer, Notizen) …")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(160)
        self._search.textChanged.connect(self._emit_filter_changed)
        top_row.addWidget(self._search, stretch=2)

        self._set_combo = QComboBox()
        self._set_combo.addItem(_ALL)
        self._set_combo.setMinimumWidth(110)
        self._set_combo.currentIndexChanged.connect(self._emit_filter_changed)
        top_row.addWidget(self._set_combo, stretch=1)

        self._language_combo = QComboBox()
        self._language_combo.addItem(_ALL)
        for language in Language:
            self._language_combo.addItem(language.label, language)
        self._language_combo.setMinimumWidth(110)
        self._language_combo.currentIndexChanged.connect(self._emit_filter_changed)
        top_row.addWidget(self._language_combo, stretch=1)

        self._condition_combo = QComboBox()
        self._condition_combo.addItem(_ALL)
        for condition in Condition:
            self._condition_combo.addItem(condition.label, condition)
        self._condition_combo.setMinimumWidth(110)
        self._condition_combo.currentIndexChanged.connect(self._emit_filter_changed)
        top_row.addWidget(self._condition_combo, stretch=1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        outer.addLayout(bottom_row)

        self._min_price = QLineEdit()
        self._min_price.setPlaceholderText("Preis von")
        self._min_price.setMinimumWidth(90)
        self._min_price.setMaximumWidth(110)
        self._min_price.textChanged.connect(self._emit_filter_changed)
        bottom_row.addWidget(self._min_price)

        self._max_price = QLineEdit()
        self._max_price.setPlaceholderText("bis")
        self._max_price.setMinimumWidth(90)
        self._max_price.setMaximumWidth(110)
        self._max_price.textChanged.connect(self._emit_filter_changed)
        bottom_row.addWidget(self._max_price)

        self._all_collections = QCheckBox("Alle Sammlungen")
        self._all_collections.toggled.connect(self.scope_changed)
        bottom_row.addWidget(self._all_collections)

        bottom_row.addStretch(1)

        reset_button = QPushButton("Zurücksetzen")
        reset_button.setObjectName("Secondary")
        reset_button.clicked.connect(self.reset)
        bottom_row.addWidget(reset_button)

    # -- Public API ---------------------------------------------------------- #

    def set_available_sets(self, set_names: list[str]) -> None:
        """Repopulate the Set dropdown, preserving the current pick if possible."""
        current = self._set_combo.currentText()
        self._set_combo.blockSignals(True)
        self._set_combo.clear()
        self._set_combo.addItem(_ALL)
        self._set_combo.addItems(set_names)
        index = self._set_combo.findText(current)
        self._set_combo.setCurrentIndex(index if index >= 0 else 0)
        self._set_combo.blockSignals(False)

    def current_filter(self) -> CardFilter:
        """The filter fields currently selected (``collection_id`` left unset)."""
        return CardFilter(
            search_text=self._search.text(),
            set_name=self._set_combo.currentText() if self._set_combo.currentIndex() > 0 else None,
            language=self._language_combo.currentData(),
            condition=self._condition_combo.currentData(),
            min_price=_parse_float(self._min_price.text()),
            max_price=_parse_float(self._max_price.text()),
        )

    def reset(self) -> None:
        """Clear every field back to "no filter"."""
        self._search.clear()
        self._set_combo.setCurrentIndex(0)
        self._language_combo.setCurrentIndex(0)
        self._condition_combo.setCurrentIndex(0)
        self._min_price.clear()
        self._max_price.clear()

    # -- Internals ------------------------------------------------------------ #

    def _emit_filter_changed(self, *_args) -> None:
        self.filter_changed.emit(self.current_filter())


def _parse_float(text: str) -> float | None:
    text = text.strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
