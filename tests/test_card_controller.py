"""Integration tests: CardController wiring panel/detail panel <-> service <-> DB."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.catalog.models import CatalogCard
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language, PriceQuality
from app.models.price import PriceRecord
from app.services.card_service import CardService
from app.services.collection_service import CollectionService
from app.ui.app import build_application
from app.ui.controllers.card_controller import CardController
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel
from app.ui.widgets.price_history_dock import PriceHistoryDock

_CATALOG_CARD = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)

_VALUES = CardDetailsValues(
    language=Language.ENGLISH,
    condition=Condition.NEAR_MINT,
    quantity=1,
    notes="",
)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def collection_id(temp_db: Database) -> int:
    return CollectionRepository(temp_db).create("Binder").id


@pytest.fixture
def controller(qapp, temp_db: Database) -> CardController:
    # No real network/filesystem access in unit tests.
    service = CardService(CardRepository(temp_db), image_downloader=lambda _card: None)
    collection_service = CollectionService(CollectionRepository(temp_db))
    panel = CardListPanel()
    detail_panel = CardDetailPanel()
    return CardController(panel, detail_panel, service, collection_service)


def _names(controller: CardController) -> list[str]:
    table = controller._panel._table
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def test_no_collection_selected_shows_error_and_no_op(
    monkeypatch, controller: CardController
) -> None:
    errors: list[str] = []
    monkeypatch.setattr(controller._panel, "show_error", errors.append)

    controller.add_from_catalog(_CATALOG_CARD)

    assert len(errors) == 1
    assert _names(controller) == []


def test_add_confirmed_persists_and_refreshes_panel(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)

    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)

    assert _names(controller) == ["Xatu"]


def test_prompt_add_manual_no_collection_selected_shows_error(
    monkeypatch, controller: CardController
) -> None:
    errors: list[str] = []
    monkeypatch.setattr(controller._panel, "show_error", errors.append)
    from app.pricing.models import ProductInfo

    controller.prompt_add_manual(
        ProductInfo(name="Venusaur", set_name="Legendary Collection", card_number="18"),
        "https://cardmarket.com/x",
    )

    assert len(errors) == 1


def test_manual_add_confirmed_persists_and_refreshes_panel(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)

    controller._panel.manual_add_confirmed.emit(
        "Venusaur", "Legendary Collection", "18", _VALUES, None, ""
    )

    assert _names(controller) == ["Venusaur"]


def test_manual_add_confirmed_finalizes_a_captured_photo(
    controller: CardController, collection_id: int, tmp_path, monkeypatch
) -> None:
    # Mirrors the sealed-product photo capture: a manually-entered card now
    # gets a screenshot-captured photo too (see ProductInfo.photo_path),
    # moved from its temp capture file into its final, id-based location
    # once the card's real id is known.
    from app import config

    monkeypatch.setattr(config, "PHOTOS_DIR", tmp_path / "photos")
    temp_photo = tmp_path / "tmp_capture.png"
    temp_photo.write_bytes(b"fake-png-bytes")
    controller.set_collection(collection_id)

    controller._panel.manual_add_confirmed.emit(
        "Venusaur", "Legendary Collection", "18", _VALUES, str(temp_photo), ""
    )

    cards = controller._service.list_cards(collection_id)
    assert len(cards) == 1
    assert cards[0].photo_path is not None
    assert Path(cards[0].photo_path).exists()
    assert Path(cards[0].photo_path).name == f"manual_{cards[0].id}.png"
    assert not temp_photo.exists()


def test_manual_add_confirmed_stores_the_resolved_set_code(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)

    controller._panel.manual_add_confirmed.emit(
        "Venusaur", "Legendary Collection", "18", _VALUES, None, "ex2"
    )

    cards = controller._service.list_cards(collection_id)
    assert cards[0].set_code == "ex2"


def test_collection_id_property_reflects_selection(
    controller: CardController, collection_id: int
) -> None:
    assert controller.collection_id is None

    controller.set_collection(collection_id)

    assert controller.collection_id == collection_id


def test_set_collection_minus_one_clears_panel(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)

    controller.set_collection(-1)

    assert _names(controller) == []


def test_edit_requested_persists_changes(controller: CardController, collection_id: int) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    new_values = CardDetailsValues(
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        is_reverse_holo=True,
        quantity=5,
        notes="PSA 9",
    )
    controller._panel.edit_requested.emit(card_id, new_values)

    table = controller._panel._table
    assert table.item(0, 6).text() == "5"  # Menge column


def test_price_edit_requested_persists_manual_price(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    controller._panel.price_edit_requested.emit(card_id, 123.45)

    card = controller._service.get_card(card_id)
    assert card.current_price == 123.45
    assert card.price_quality is PriceQuality.MANUAL


def test_price_edit_requested_with_invalid_price_shows_error(
    monkeypatch, controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()
    errors: list[str] = []
    monkeypatch.setattr(controller._panel, "show_error", errors.append)

    controller._panel.price_edit_requested.emit(card_id, -1.0)

    assert len(errors) == 1


def test_edit_requested_refreshes_detail_panel_even_when_row_index_is_unchanged(
    controller: CardController, collection_id: int
) -> None:
    # Regression: with a single card, the edited row stays at index 0, so
    # Qt's currentCellChanged never fires — the detail panel must still be
    # resynced, not left showing pre-edit values.
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    new_values = CardDetailsValues(
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        is_reverse_holo=True,
        quantity=5,
        notes="PSA 9",
    )
    controller._panel.edit_requested.emit(card_id, new_values)

    assert controller._detail_panel._value_labels["Menge"].text() == "5"
    assert controller._detail_panel._value_labels["Extra"].text() == "Reverse Holo"


def test_delete_requested_removes_card(controller: CardController, collection_id: int) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    controller._panel.delete_requested.emit([card_id])

    assert _names(controller) == []


def test_delete_requested_with_multiple_ids_removes_all(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    first_id = controller._panel.selected_card_id()
    controller._panel.add_confirmed.emit(
        replace(_CATALOG_CARD, external_id="skg-h33", name="Aerodactyl"), _VALUES
    )
    second_id = controller._panel.selected_card_id()

    controller._panel.delete_requested.emit([first_id, second_id])

    assert _names(controller) == []


def test_move_requested_moves_card_to_target_collection(
    monkeypatch, controller: CardController, temp_db: Database, collection_id: int
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage 4").id
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    class FakeAcceptedMoveDialog:
        def __call__(self, collections, parent=None):
            self._collections = collections
            return self

        def exec(self):
            from PySide6.QtWidgets import QDialog

            return QDialog.DialogCode.Accepted

        def get_target_collection_id(self):
            return other_id

    monkeypatch.setattr(
        "app.ui.controllers.card_controller.MoveDialog", FakeAcceptedMoveDialog()
    )

    controller._panel.move_requested.emit([card_id])

    assert _names(controller) == []  # moved away from the currently selected collection
    controller.set_collection(other_id)
    assert _names(controller) == ["Xatu"]


def test_move_requested_no_other_collection_shows_error(
    monkeypatch, controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()
    errors: list[str] = []
    monkeypatch.setattr(controller._panel, "show_error", errors.append)

    controller._panel.move_requested.emit([card_id])

    assert len(errors) == 1


def test_selection_changed_updates_detail_panel(
    monkeypatch, controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    shown = []
    monkeypatch.setattr(controller._detail_panel, "show_card", shown.append)

    controller._panel.selection_changed.emit(card_id)

    assert len(shown) == 1
    assert shown[0].id == card_id


def test_selection_changed_minus_one_shows_empty(monkeypatch, controller: CardController) -> None:
    calls = []
    monkeypatch.setattr(controller._detail_panel, "show_empty", lambda: calls.append(True))

    controller._panel.selection_changed.emit(-1)

    assert calls == [True]


def test_without_price_repository_history_is_left_untouched(
    monkeypatch, qapp, controller: CardController, collection_id: int
) -> None:
    # The `controller` fixture builds a CardController with no
    # price_repository -- showing a card must not try to fetch history, even
    # with a history dock attached.
    dock = PriceHistoryDock()
    controller._history_dock = dock
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()
    calls = []
    monkeypatch.setattr(dock, "show_history", lambda *a: calls.append(a))

    controller._panel.selection_changed.emit(card_id)

    assert calls == []


def test_showing_a_card_also_shows_its_price_history_when_repository_given(
    qapp, temp_db: Database, collection_id: int
) -> None:
    service = CardService(CardRepository(temp_db), image_downloader=lambda _card: None)
    collection_service = CollectionService(CollectionRepository(temp_db))
    prices = PriceRepository(temp_db)
    panel = CardListPanel()
    detail_panel = CardDetailPanel()
    dock = PriceHistoryDock()
    controller = CardController(
        panel, detail_panel, service, collection_service, prices, history_dock=dock
    )
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()
    prices.add_record(
        PriceRecord(id=None, card_id=card_id, price=10.0, price_quality=PriceQuality.EXACT)
    )
    prices.add_record(
        PriceRecord(id=None, card_id=card_id, price=15.0, price_quality=PriceQuality.EXACT)
    )

    controller._panel.selection_changed.emit(card_id)

    assert not dock._chart_view.isHidden()
    assert dock._chart.series()[0].count() == 2


def test_history_reset_requested_deletes_records_and_refreshes_dock(
    qapp, temp_db: Database, collection_id: int
) -> None:
    service = CardService(CardRepository(temp_db), image_downloader=lambda _card: None)
    collection_service = CollectionService(CollectionRepository(temp_db))
    prices = PriceRepository(temp_db)
    panel = CardListPanel()
    detail_panel = CardDetailPanel()
    dock = PriceHistoryDock()
    controller = CardController(
        panel, detail_panel, service, collection_service, prices, history_dock=dock
    )
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()
    prices.add_record(PriceRecord(id=None, card_id=card_id, price=10.0))
    prices.add_record(PriceRecord(id=None, card_id=card_id, price=15.0))
    controller._panel.selection_changed.emit(card_id)

    dock.history_reset_requested.emit(card_id)

    assert prices.list_for_card(card_id) == []
    assert dock._chart_view.isHidden()
    assert dock._history_list.count() == 0


# -- Filter / scope wiring (Step 9) ------------------------------------------- #


def test_filter_bar_search_text_narrows_the_list(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    controller._panel.add_confirmed.emit(
        CatalogCard(
            external_id="base-4",
            name="Charizard",
            set_name="Base",
            set_code="base",
            card_number="4",
            rarity="Rare Holo",
            image_small_url=None,
            image_large_url=None,
        ),
        _VALUES,
    )

    controller._panel.filter_bar._search.setText("xatu")

    assert _names(controller) == ["Xatu"]


def test_clearing_the_filter_shows_everything_again(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)

    controller._panel.filter_bar._search.setText("does-not-exist")
    assert _names(controller) == []

    controller._panel.filter_bar.reset()
    assert _names(controller) == ["Xatu"]


def test_search_all_collections_spans_every_collection(
    controller: CardController, temp_db: Database, collection_id: int
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage 5").id
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    controller.set_collection(other_id)
    controller._panel.add_confirmed.emit(
        CatalogCard(
            external_id="base-4",
            name="Charizard",
            set_name="Base",
            set_code="base",
            card_number="4",
            rarity="Rare Holo",
            image_small_url=None,
            image_large_url=None,
        ),
        _VALUES,
    )

    controller._panel.filter_bar._all_collections.setChecked(True)

    assert set(_names(controller)) == {"Xatu", "Charizard"}


def test_search_all_collections_works_even_without_a_selected_collection(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    controller.set_collection(-1)  # no collection selected
    assert _names(controller) == []

    controller._panel.filter_bar._all_collections.setChecked(True)

    assert _names(controller) == ["Xatu"]


def test_available_sets_are_refreshed_after_adding_a_card(
    controller: CardController, collection_id: int
) -> None:
    controller.set_collection(collection_id)

    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)

    assert controller._panel.filter_bar._set_combo.findText("Skyridge") > 0
