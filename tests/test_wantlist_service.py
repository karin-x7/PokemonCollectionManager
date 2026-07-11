"""Tests for wantlist business logic: validation and friendly errors."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.wantlist_repository import WantlistRepository
from app.models.enums import Condition, Language
from app.models.wantlist import WantlistItemDetailsValues
from app.services.exceptions import ValidationError, WantlistItemNotFoundError
from app.services.wantlist_service import WantlistService

_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard"


def _values(**overrides) -> WantlistItemDetailsValues:
    base = dict(
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        target_price=500.0,
        notes="",
        cardmarket_url=_URL,
    )
    base.update(overrides)
    return WantlistItemDetailsValues(**base)


@pytest.fixture
def service(temp_db: Database) -> WantlistService:
    return WantlistService(WantlistRepository(temp_db))


def test_add_item_stores_identity_and_url(service: WantlistService) -> None:
    item = service.add_item("Charizard", "Base Set", "4", _values())

    assert item.name == "Charizard"
    assert item.set_name == "Base Set"
    assert item.card_number == "4"
    assert item.target_price == 500.0
    # English (the fixture's default language) supports a Cardmarket
    # language filter, so the stored URL gains ?language=1.
    assert item.cardmarket_url == f"{_URL}?language=1"
    assert item.id is not None


def test_add_item_rewrites_url_with_language_filter(service: WantlistService) -> None:
    item = service.add_item("Charizard", "Base Set", "4", _values(language=Language.GERMAN))

    assert item.cardmarket_url == f"{_URL}?language=3"


def test_add_item_applies_the_language_filter_for_japanese_too(
    service: WantlistService,
) -> None:
    # Live-reported correction: Cardmarket's own ?language= filter works for
    # Japanese/Korean/Chinese too on a single card's page, same as any other
    # language -- see supports_language_filter's own docstring.
    item = service.add_item("Pikachu", "Base Set", "58", _values(language=Language.JAPANESE))

    assert item.cardmarket_url == f"{_URL}?language=7"


def test_add_item_rejects_non_positive_target_price(service: WantlistService) -> None:
    with pytest.raises(ValidationError):
        service.add_item("Charizard", "Base Set", "4", _values(target_price=0))


def test_get_item_raises_when_missing(service: WantlistService) -> None:
    with pytest.raises(WantlistItemNotFoundError):
        service.get_item(999)


def test_list_items_returns_every_added_item(service: WantlistService) -> None:
    service.add_item("Charizard", "Base Set", "4", _values())
    service.add_item("Blastoise", "Base Set", "2", _values())

    assert len(service.list_items()) == 2


def test_update_item_details_persists_new_values(service: WantlistService) -> None:
    item = service.add_item("Charizard", "Base Set", "4", _values(target_price=500.0))

    service.update_item_details(
        item.id, _values(language=Language.GERMAN, target_price=300.0, notes="cheaper now")
    )

    updated = service.get_item(item.id)
    assert updated.language is Language.GERMAN
    assert updated.target_price == 300.0
    assert updated.notes == "cheaper now"
    assert updated.cardmarket_url == f"{_URL}?language=3"


def test_update_item_details_rejects_non_positive_target_price(service: WantlistService) -> None:
    item = service.add_item("Charizard", "Base Set", "4", _values())
    with pytest.raises(ValidationError):
        service.update_item_details(item.id, _values(target_price=0))


def test_update_item_details_raises_when_missing(service: WantlistService) -> None:
    with pytest.raises(WantlistItemNotFoundError):
        service.update_item_details(999, _values())


def test_remove_item_deletes_it(service: WantlistService) -> None:
    item = service.add_item("Charizard", "Base Set", "4", _values())

    service.remove_item(item.id)

    with pytest.raises(WantlistItemNotFoundError):
        service.get_item(item.id)


def test_remove_item_raises_when_missing(service: WantlistService) -> None:
    with pytest.raises(WantlistItemNotFoundError):
        service.remove_item(999)
