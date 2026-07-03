"""Integration tests: CardController wiring panel/detail panel <-> service <-> DB."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.catalog.models import CatalogCard
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language, PriceQuality, Variant
from app.models.price import PriceRecord
from app.services.card_service import CardService
from app.ui.app import build_application
from app.ui.controllers.card_controller import CardController
from app.ui.widgets.card_detail_panel import CardDetailPanel
from app.ui.widgets.card_list_panel import CardListPanel

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
    variant=Variant.HOLO,
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
    panel = CardListPanel()
    detail_panel = CardDetailPanel()
    return CardController(panel, detail_panel, service)


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
        variant=Variant.REVERSE_HOLO,
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        quantity=5,
        notes="PSA 9",
    )
    controller._panel.edit_requested.emit(card_id, new_values)

    table = controller._panel._table
    assert table.item(0, 6).text() == "5"  # Menge column


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
        variant=Variant.REVERSE_HOLO,
        language=Language.GERMAN,
        condition=Condition.EXCELLENT,
        quantity=5,
        notes="PSA 9",
    )
    controller._panel.edit_requested.emit(card_id, new_values)

    assert controller._detail_panel._value_labels["Menge"].text() == "5"
    assert controller._detail_panel._value_labels["Variante"].text() == "Reverse Holo"


def test_delete_requested_removes_card(controller: CardController, collection_id: int) -> None:
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()

    controller._panel.delete_requested.emit(card_id)

    assert _names(controller) == []


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
    monkeypatch, controller: CardController, collection_id: int
) -> None:
    # The `controller` fixture builds a CardController with no
    # price_repository -- showing a card must not try to fetch history.
    controller.set_collection(collection_id)
    controller._panel.add_confirmed.emit(_CATALOG_CARD, _VALUES)
    card_id = controller._panel.selected_card_id()
    calls = []
    monkeypatch.setattr(controller._detail_panel, "show_price_history", calls.append)

    controller._panel.selection_changed.emit(card_id)

    assert calls == []


def test_showing_a_card_also_shows_its_price_history_when_repository_given(
    qapp, temp_db: Database, collection_id: int
) -> None:
    service = CardService(CardRepository(temp_db), image_downloader=lambda _card: None)
    prices = PriceRepository(temp_db)
    panel = CardListPanel()
    detail_panel = CardDetailPanel()
    controller = CardController(panel, detail_panel, service, prices)
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

    assert not detail_panel._price_history._chart_view.isHidden()
    assert detail_panel._price_history._chart.series()[0].count() == 2


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
