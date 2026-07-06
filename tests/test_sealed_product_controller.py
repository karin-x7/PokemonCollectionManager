"""Integration tests: SealedProductController wiring panel <-> service <-> DB."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.database.connection import Database
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.enums import Language
from app.models.sealed_product import SealedProductDetailsValues
from app.services.sealed_product_service import SealedProductService
from app.ui.app import build_application
from app.ui.controllers.sealed_product_controller import SealedProductController
from app.ui.widgets.sealed_product_list_panel import SealedProductListPanel

_VALUES = SealedProductDetailsValues(
    language=Language.ENGLISH, quantity=1, notes="", cardmarket_url="https://example.com/box"
)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def controller(qapp, temp_db: Database) -> SealedProductController:
    service = SealedProductService(SealedProductRepository(temp_db))
    panel = SealedProductListPanel()
    return SealedProductController(panel, service)


def _names(controller: SealedProductController) -> list[str]:
    table = controller._panel._table
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def test_add_product_persists_and_refreshes_panel(controller: SealedProductController) -> None:
    controller.add_product("Base Set Booster Box", "Booster Box", _VALUES, None)

    assert _names(controller) == ["Base Set Booster Box"]


def test_refresh_shows_every_owned_product(controller: SealedProductController) -> None:
    controller.add_product("Base Set Booster Box", "Booster Box", _VALUES, None)
    controller.add_product("Evolutions ETB", "Elite Trainer Box", _VALUES, None)

    controller.refresh()

    assert set(_names(controller)) == {"Base Set Booster Box", "Evolutions ETB"}


def test_edit_requested_persists_changes(controller: SealedProductController) -> None:
    controller.add_product("Base Set Booster Box", "Booster Box", _VALUES, None)
    product_id = controller._panel.selected_product_id()

    new_values = SealedProductDetailsValues(language=Language.GERMAN, quantity=5, notes="OVP")
    controller._panel.edit_requested.emit(product_id, new_values)

    table = controller._panel._table
    assert table.item(0, 3).text() == "5"  # Menge column


def test_delete_requested_removes_product(controller: SealedProductController) -> None:
    controller.add_product("Base Set Booster Box", "Booster Box", _VALUES, None)
    product_id = controller._panel.selected_product_id()

    controller._panel.delete_requested.emit([product_id])

    assert _names(controller) == []


def test_delete_requested_with_multiple_ids_removes_all(
    controller: SealedProductController,
) -> None:
    controller.add_product("Base Set Booster Box", "Booster Box", _VALUES, None)
    first_id = controller._panel.selected_product_id()
    controller.add_product("Jungle Booster Box", "Booster Box", _VALUES, None)
    second_id = controller._panel.selected_product_id()

    controller._panel.delete_requested.emit([first_id, second_id])

    assert _names(controller) == []
