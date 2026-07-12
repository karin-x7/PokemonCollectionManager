"""Middle panel: the list of cards in the selected collection.

Bound to real ``Card`` data via :meth:`set_cards`. Emits ``selection_changed``
(card id, ``-1`` for none), and only emits ``delete_requested``/
``edit_requested``/``add_confirmed`` once the user has confirmed the
corresponding dialog — dialogs are interaction, not business logic; real
validation/persistence runs exclusively via
:class:`~app.services.card_service.CardService` through
:class:`~app.ui.controllers.card_controller.CardController`.

The table allows selecting multiple rows (Shift/Ctrl-click, like a normal
spreadsheet) -- ``delete_requested``/``move_requested`` always carry a list
of card ids (one or more), never a bare id, so the controller only has to
handle one shape. "Bearbeiten" only makes sense for a single card, so it's
left out of the context menu whenever more than one row is selected.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.catalog.models import CatalogCard
from app.i18n import tr
from app.models.card import Card, CardDetailsValues
from app.models.enums import Condition, Language
from app.pricing.models import ProductInfo
from app.services.statistics_service import is_price_stale
from app.ui.condition_icon_provider import get_condition_icon
from app.ui.dialogs.card_details_dialog import CardDetailsDialog
from app.ui.dialogs.manual_price_dialog import ManualPriceDialog
from app.ui.language_icon_provider import get_language_icon
from app.ui.theme import apply_elevation
from app.ui.set_icon_provider import get_set_icon
from app.ui.theme import PALETTE
from app.ui.widgets.card_filter_bar import CardFilterBar
from app.ui.widgets.centered_icon_delegate import CenteredIconDelegate


def _columns() -> list[str]:
    # A function, not a module-level constant: tr() must run once the UI
    # language has been loaded (see app/i18n.py), not at import time.
    # Sprache/Zustand/Menge are abbreviated ("Spr."/"Zust."/"Anz.") rather
    # than spelled out in full: those three columns are deliberately narrow
    # (see the header's own resize setup below), and the full words got
    # truncated by the header itself (user-reported).
    return [
        "Name",
        "Set",
        "Nr.",
        tr("Extra"),
        tr("Spr."),
        tr("Zust."),
        tr("Anz."),
        tr("Preis"),
    ]


_ID_ROLE = Qt.ItemDataRole.UserRole
_QUANTITY_COLUMN = 6
_PRICE_COLUMN = 7
_SET_COLUMN = 1
_LANGUAGE_COLUMN = 4
_CONDITION_COLUMN = 5
#: Every column can be sorted by clicking its header (user request).
_SORTABLE_COLUMNS = {0, 1, 2, 3, _LANGUAGE_COLUMN, _CONDITION_COLUMN, _QUANTITY_COLUMN, _PRICE_COLUMN}
#: Menge/Preis sort by an actual number (see _NumericItem below), not their
#: displayed text -- a plain alphabetical sort would otherwise rank "10"
#: before "2", and "1550.00 EUR" before "20.00 EUR".
_NUMERIC_COLUMNS = {_QUANTITY_COLUMN, _PRICE_COLUMN}
#: Fully transparent -- used to hide the Sprache column's text (kept only so
#: the existing case-insensitive alphabetical sort still has something to
#: compare) once its flag icon replaces it visually.
_TRANSPARENT = QColor(0, 0, 0, 0)
#: Fixed row height (see _build()) -- comfortably fits the tallest fixed-
#: size icon (the 18px condition badge) plus the QSS's own 8px top/bottom
#: item padding, regardless of the actual set icon's own resolution.
_ROW_HEIGHT = 36


class _CaseInsensitiveItem(QTableWidgetItem):
    """Sorts alphabetically by its own text, ignoring case (e.g. "eevee"

    and "Zebra" sort by letter, not by ASCII case) -- the default
    QTableWidgetItem comparison is case-sensitive."""

    def __lt__(self, other: object) -> bool:
        if isinstance(other, QTableWidgetItem):
            return self.text().casefold() < other.text().casefold()
        return super().__lt__(other)


class _NumericItem(QTableWidgetItem):
    """Sorts by a separately-stored number, not its displayed text (e.g.

    "1550.00 EUR" or "—" for no price) -- text-based sorting would rank
    these alphabetically, which is meaningless for a mixed number/
    placeholder column."""

    def __init__(self, text: str, sort_value: float) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: object) -> bool:
        if isinstance(other, _NumericItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


def _price_text(card: Card) -> str:
    if card.current_price is None:
        return "—"
    price = f"{card.current_price:.2f} {card.price_currency}"
    # A warning emoji, not just "!" -- reuses the exact same threshold as
    # the Statistiken tab's "Karten mit veraltetem Preis" list, one
    # definition of "stale", not two.
    return f"{price}  ⚠️" if is_price_stale(card) else price


def _price_sort_value(card: Card) -> float:
    # Unpriced cards sort as the cheapest, not wherever "—" would fall
    # alphabetically -- an arbitrary but consistent choice.
    return card.current_price if card.current_price is not None else -1.0


def _extras_text(card: Card) -> str:
    labels = []
    if card.is_reverse_holo:
        labels.append(tr("Rev. Holo"))
    if card.is_signed:
        labels.append(tr("Sign."))
    if card.is_first_edition:
        labels.append("1st Ed.")
    if card.is_altered:
        labels.append(tr("Alt."))
    return ", ".join(labels) if labels else "—"


class CardListPanel(QWidget):
    """Tabular list of the cards in the current collection."""

    #: Emitted whenever the selected card changes; -1 means "none".
    selection_changed = Signal(int)
    #: Emitted with a list of card ids (one or more) once the user confirms
    #: deletion.
    delete_requested = Signal(list)
    #: Emitted with (card_id, CardDetailsValues) once the user confirms edits.
    edit_requested = Signal(int, object)
    #: Emitted with (CatalogCard, CardDetailsValues) once the user confirms
    #: adding a catalogue match.
    add_confirmed = Signal(object, object)
    #: Emitted with (name, set_name, card_number, CardDetailsValues,
    #: photo_path, set_code) once the user confirms adding a manually-entered
    #: (Cardmarket-link) card. ``photo_path`` is the temp screenshot capture
    #: from the lookup (see ``ProductInfo.photo_path``), or ``None``.
    #: ``set_code`` is the best-effort catalogue set id resolved from
    #: ``set_name`` (see ``ProductInfo.set_code``), or ``""``.
    manual_add_confirmed = Signal(str, str, str, object, object, str)
    #: Emitted with a list of card ids (one or more) when "Verschieben" is
    #: chosen from the context menu -- the controller owns picking/showing
    #: the target collection, since this panel doesn't know about other
    #: collections.
    move_requested = Signal(list)
    #: Emitted with (card_id, price) once the user confirms a manual price
    #: override -- only offered for a single selected row (like
    #: "Bearbeiten"), since overriding several cards' prices to the same
    #: value at once wouldn't make sense.
    price_edit_requested = Signal(int, float)
    #: Emitted with a card id when "Open Cardmarket link" is chosen from the
    #: context menu -- only offered for a single selected row, same reasoning
    #: as "Bearbeiten"/"Preis manuell bearbeiten". Distinct from the "Preis
    #: von Cardmarket abrufen" button, which reads and closes the tab
    #: automatically: this leaves the tab open for the user to browse.
    open_cardmarket_link_requested = Signal(int)
    #: Emitted with a card id when "Fix Cardmarket link" is chosen from the
    #: context menu -- same action, same signal name, as the "Cardmarket-Link
    #: suchen" button already offers in the card detail panel (see
    #: ``CardDetailPanel.cardmarket_search_requested``); only offered for a
    #: single selected row, same reasoning as "Bearbeiten". Live-reported
    #: request: this was previously only reachable via the detail panel, one
    #: card at a time, with no context-menu shortcut from the list itself.
    cardmarket_search_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        apply_elevation(self)
        self._cards_by_id: dict[int, Card] = {}
        self._sort_column: int | None = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel(tr("Karten"))
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self.filter_bar = CardFilterBar()
        layout.addWidget(self.filter_bar)

        columns = _columns()
        self._table = QTableWidget(0, len(columns))
        self._table.setHorizontalHeaderLabels(columns)
        self._table.verticalHeader().setVisible(False)
        # Fixed, uniform row height instead of resizeRowsToContents() (user-
        # reported: rows all came out different heights) -- set icons are
        # downloaded from pokemontcg.io/tcgdex at whatever resolution the
        # source happened to serve, so per-row auto-sizing picked a
        # different height depending on which set icon (if any) landed in
        # that row. A single fixed height sidesteps that entirely, matching
        # every icon column's own actual render size (tallest: the
        # condition badge at 18px, see condition_icon_provider.py).
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._table.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        # Native cell-grid replaced by a single, subtler per-row bottom
        # border in theme.py (QTableWidget::item) -- no vertical lines, a
        # cleaner "list" look instead of a spreadsheet-style full grid.
        self._table.setShowGrid(False)

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(columns)):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        # Sprache/Zustand show only a small centered icon and Menge only a
        # 1-2 digit number, but ResizeToContents sizes them by their (longer)
        # header label instead -- squeezing Name's share of the stretch
        # column unnecessarily (user request). Narrower fixed start width,
        # still user-resizable via Interactive rather than locked.
        for col in (_LANGUAGE_COLUMN, _CONDITION_COLUMN, _QUANTITY_COLUMN):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header_view.resizeSection(col, 60)
        header_view.setSectionsClickable(True)
        header_view.setSortIndicatorShown(True)
        header_view.sectionClicked.connect(self._on_header_clicked)

        self._table.currentCellChanged.connect(self._on_current_cell_changed)
        self._table.itemDoubleClicked.connect(lambda item: self._prompt_edit(item.row()))
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        # Both columns show an icon with no visible text -- center it, since
        # the default item delegate hugs the icon to the cell's left edge.
        centered_icon_delegate = CenteredIconDelegate(self._table)
        self._table.setItemDelegateForColumn(_LANGUAGE_COLUMN, centered_icon_delegate)
        self._table.setItemDelegateForColumn(_CONDITION_COLUMN, centered_icon_delegate)

        layout.addWidget(self._table, stretch=1)

    # -- Public API (called by the controller) ----------------------------- #

    def set_cards(self, cards: list[Card]) -> None:
        """Replace the displayed list, preserving the selection if possible."""
        previous_id = self.selected_card_id()
        self._cards_by_id = {card.id: card for card in cards if card.id is not None}

        self._table.blockSignals(True)
        self._table.setRowCount(len(cards))
        for row, card in enumerate(cards):
            values = [
                card.name,
                card.set_name,
                card.card_number,
                _extras_text(card),
                card.language.code,
                card.condition.code,
                str(card.quantity),
                _price_text(card),
            ]
            for col, value in enumerate(values):
                if col == _QUANTITY_COLUMN:
                    item = _NumericItem(value, sort_value=card.quantity)
                elif col == _PRICE_COLUMN:
                    item = _NumericItem(value, sort_value=_price_sort_value(card))
                elif col in _SORTABLE_COLUMNS:
                    item = _CaseInsensitiveItem(value)
                else:
                    item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setData(_ID_ROLE, card.id)
                if col == _SET_COLUMN:
                    set_icon = get_set_icon(card.set_code, card.set_name)
                    if set_icon is not None:
                        item.setIcon(set_icon)
                if col == _LANGUAGE_COLUMN:
                    # Flag icon instead of the "DE"/"EN"/... text (user
                    # request) -- the text itself stays (invisible) so the
                    # existing alphabetical sort keeps working unchanged.
                    item.setIcon(get_language_icon(card.language))
                    item.setForeground(_TRANSPARENT)
                if col == _CONDITION_COLUMN:
                    # Cardmarket-style badge icon instead of colouring the
                    # whole cell -- text stays (invisible) for sorting, same
                    # trick as the Sprache column above.
                    item.setIcon(get_condition_icon(card.condition))
                    item.setForeground(_TRANSPARENT)
                if col == _PRICE_COLUMN and card.current_price is not None and is_price_stale(card):
                    item.setForeground(QColor(PALETTE.negative))
                self._table.setItem(row, col, item)
        if self._sort_column is not None:
            self._table.sortItems(self._sort_column, self._sort_order)
        self._table.blockSignals(False)

        self._restore_selection(previous_id)

    def selected_card_id(self) -> int | None:
        """The currently selected card's id, or ``None``."""
        item = self._table.item(self._table.currentRow(), 0)
        return item.data(_ID_ROLE) if item is not None else None

    def selected_card_ids(self) -> list[int]:
        """Every card id currently selected (possibly more than one)."""
        ids = []
        for index in sorted(self._table.selectionModel().selectedRows(), key=lambda i: i.row()):
            item = self._table.item(index.row(), 0)
            if item is not None:
                ids.append(item.data(_ID_ROLE))
        return ids

    def select_card(self, card_id: int | None) -> None:
        """Programmatically select a card by id (no-op if not found)."""
        self._restore_selection(card_id)

    def show_error(self, message: str) -> None:
        """Display a friendly error message to the user."""
        QMessageBox.warning(self, tr("Karten"), message)

    def prompt_add_from_catalog(self, catalog_card: CatalogCard) -> None:
        """Open the add-card dialog prefilled from a catalogue match."""
        dialog = CardDetailsDialog(
            title=tr("Karte hinzufügen"),
            accept_label=tr("Hinzufügen"),
            display_name=catalog_card.name,
            display_set=catalog_card.set_name,
            display_number=catalog_card.card_number,
            display_rarity=catalog_card.rarity,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.add_confirmed.emit(catalog_card, dialog.get_values())

    def prompt_add_manual(self, info: ProductInfo, url: str) -> None:
        """Open the add-card dialog prefilled from a manually-entered Cardmarket link.

        Unlike a catalogue match, name/set/card-number here come from
        parsing the product page's own title, not a confirmed catalogue
        record -- editable, so the user can correct them before saving. The
        link itself is prefilled into "Eigener Cardmarket-Link" so price
        lookups use exactly the page the user pasted.

        The language dropdown starts on ``info.detected_language`` (the most
        common language among the page's own offer rows) rather than always
        defaulting to English -- a real user reported this always silently
        defaulting to English regardless of what was actually pasted (this
        flow's whole purpose is JP/KO/ZH/vintage prints), which then
        mis-filtered later price lookups. Still just a starting point, fully
        editable, and falls back to English if no offers could be parsed at
        all (e.g. currently out of stock).
        """
        dialog = CardDetailsDialog(
            title=tr("Karte manuell eintragen"),
            accept_label=tr("Hinzufügen"),
            display_name=info.name,
            display_set=info.set_name,
            display_number=info.card_number,
            initial=CardDetailsValues(
                language=info.detected_language or Language.ENGLISH,
                condition=Condition.NEAR_MINT,
                quantity=1,
                notes="",
                manual_cardmarket_url=url,
            ),
            editable_identity=True,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, set_name, card_number = dialog.get_identity()
            self.manual_add_confirmed.emit(
                name, set_name, card_number, dialog.get_values(), info.photo_path, info.set_code
            )
        elif info.photo_path:
            # Cancelling here leaves nothing else to reference this temp
            # capture -- live-reported: it was previously left behind
            # forever (see cleanup_orphaned_temp_photos's own docstring for
            # the full story). Best-effort: a missing/locked file must
            # never turn a cancelled dialog into an error.
            Path(info.photo_path).unlink(missing_ok=True)

    # -- Internals ---------------------------------------------------------- #

    def _on_header_clicked(self, column: int) -> None:
        """Sort by ``column`` if it's one of the sortable ones (see

        ``_SORTABLE_COLUMNS``); clicking the same column again reverses the
        order, like a normal spreadsheet. The chosen sort is remembered and
        reapplied on every subsequent ``set_cards`` call (e.g. after editing
        a card), so it isn't silently lost on the next refresh."""
        if column not in _SORTABLE_COLUMNS:
            return
        if self._sort_column == column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        previous_id = self.selected_card_id()
        self._table.sortItems(self._sort_column, self._sort_order)
        self._table.horizontalHeader().setSortIndicator(self._sort_column, self._sort_order)
        self._restore_selection(previous_id)

    def _restore_selection(self, card_id: int | None) -> None:
        if card_id is None:
            return
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(_ID_ROLE) == card_id:
                self._table.setCurrentCell(row, 0)
                return

    def _on_current_cell_changed(self, row: int, *_args) -> None:
        item = self._table.item(row, 0)
        card_id = item.data(_ID_ROLE) if item is not None else None
        self.selection_changed.emit(card_id if card_id is not None else -1)

    def _prompt_edit(self, row: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        card_id = item.data(_ID_ROLE)
        card = self._cards_by_id.get(card_id)
        if card is None:
            return
        dialog = CardDetailsDialog(
            title=tr("Karte bearbeiten"),
            accept_label=tr("Speichern"),
            display_name=card.name,
            display_set=card.set_name,
            display_number=card.card_number,
            initial=CardDetailsValues(
                language=card.language,
                condition=card.condition,
                is_reverse_holo=card.is_reverse_holo,
                is_signed=card.is_signed,
                is_first_edition=card.is_first_edition,
                is_altered=card.is_altered,
                quantity=card.quantity,
                notes=card.notes,
                # Live-reported bug: missing here, this silently wiped the
                # card's own Cardmarket-link override on every edit (the
                # dialog's field always started empty, so saving wrote back
                # None) -- breaking price lookups for any manually-added
                # card the very next time it was edited.
                manual_cardmarket_url=card.manual_cardmarket_url,
            ),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.edit_requested.emit(card_id, dialog.get_values())

    def _prompt_edit_price(self, row: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        card_id = item.data(_ID_ROLE)
        card = self._cards_by_id.get(card_id)
        if card is None:
            return
        dialog = ManualPriceDialog(current_price=card.current_price, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.price_edit_requested.emit(card_id, dialog.get_price())

    def _prompt_delete_selected(self) -> None:
        ids = self.selected_card_ids()
        if not ids:
            return
        if len(ids) == 1:
            card = self._cards_by_id.get(ids[0])
            name = card.name if card is not None else ""
            message = tr("Soll die Karte „{name}“ wirklich aus der Sammlung gelöscht werden?").format(
                name=name
            )
        else:
            message = tr(
                "Sollen die {count} ausgewählten Karten wirklich aus der Sammlung "
                "gelöscht werden?"
            ).format(count=len(ids))
        answer = QMessageBox.question(
            self,
            tr("Karte löschen"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(ids)

    def _show_context_menu(self, position) -> None:
        row = self._table.rowAt(position.y())
        if row < 0:
            return
        item = self._table.item(row, 0)
        # Right-clicking a row outside the current multi-selection starts a
        # fresh single-row selection instead of acting on a stale selection
        # elsewhere -- mirrors standard file-manager behaviour.
        if item is not None and not item.isSelected():
            self._table.selectRow(row)
        ids = self.selected_card_ids()
        if not ids:
            return
        menu = QMenu(self)
        edit_action = menu.addAction(tr("Bearbeiten")) if len(ids) == 1 else None
        price_edit_action = (
            menu.addAction(tr("Preis manuell bearbeiten")) if len(ids) == 1 else None
        )
        open_link_action = (
            menu.addAction(tr("Cardmarket-Link öffnen")) if len(ids) == 1 else None
        )
        fix_link_action = (
            menu.addAction(tr("Fix Cardmarket-Link")) if len(ids) == 1 else None
        )
        move_action = menu.addAction(tr("Verschieben"))
        delete_action = menu.addAction(tr("Löschen"))
        chosen = menu.exec(self._table.viewport().mapToGlobal(position))
        if edit_action is not None and chosen is edit_action:
            self._prompt_edit(row)
        elif price_edit_action is not None and chosen is price_edit_action:
            self._prompt_edit_price(row)
        elif open_link_action is not None and chosen is open_link_action:
            self.open_cardmarket_link_requested.emit(ids[0])
        elif fix_link_action is not None and chosen is fix_link_action:
            self.cardmarket_search_requested.emit(ids[0])
        elif chosen is move_action:
            self.move_requested.emit(ids)
        elif chosen is delete_action:
            self._prompt_delete_selected()
