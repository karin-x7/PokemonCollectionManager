"""Tests for CatalogSearchResultsDialog's selection/add-button behaviour."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.catalog.models import CatalogCard
from app.ui.app import build_application
from app.ui.dialogs.catalog_search_results_dialog import CatalogSearchResultsDialog

_XATU = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)
_CHARIZARD = CatalogCard(
    external_id="base1-4",
    name="Charizard",
    set_name="Base",
    set_code="base1",
    card_number="4",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def dialog(qapp) -> CatalogSearchResultsDialog:
    d = CatalogSearchResultsDialog()
    d.set_results([_XATU, _CHARIZARD])
    return d


def test_add_button_disabled_without_selection(dialog: CatalogSearchResultsDialog) -> None:
    assert not dialog._add_button.isEnabled()


def test_add_button_enabled_after_selection(dialog: CatalogSearchResultsDialog) -> None:
    dialog._table.setCurrentCell(1, 0)
    assert dialog._add_button.isEnabled()


def test_add_clicked_emits_selected_catalog_card(dialog: CatalogSearchResultsDialog) -> None:
    dialog._table.setCurrentCell(1, 0)  # Charizard
    received = []
    dialog.add_requested.connect(received.append)

    dialog._on_add_clicked()

    assert received == [_CHARIZARD]


def test_set_results_with_empty_list_shows_empty_state(qapp) -> None:
    dialog = CatalogSearchResultsDialog()
    dialog.set_results([])
    # isHidden() reflects the explicit setVisible() call regardless of
    # whether the (never-shown, headless) top-level dialog itself is visible.
    assert not dialog._empty_label.isHidden()
    assert not dialog._add_button.isEnabled()


def test_shows_a_loading_state_before_any_results_arrive(qapp) -> None:
    dialog = CatalogSearchResultsDialog()

    assert not dialog._loading_label.isHidden()
    assert not dialog._loading_bar.isHidden()
    assert dialog._table.isHidden()


def test_set_results_hides_the_loading_state(dialog: CatalogSearchResultsDialog) -> None:
    assert dialog._loading_label.isHidden()
    assert dialog._loading_bar.isHidden()
