"""Tests for card business logic: validation and friendly errors."""

from __future__ import annotations

import pytest

from app.catalog.models import CatalogCard
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.models.card import CardDetailsValues
from app.models.enums import Condition, Language, Variant
from app.services.card_service import CardService
from app.services.exceptions import CardNotFoundError, ValidationError

_CATALOG_CARD = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
    cardmarket_url="https://prices.pokemontcg.io/cardmarket/skg-h32",
)


def _values(**overrides) -> CardDetailsValues:
    base = dict(
        variant=Variant.HOLO,
        language=Language.ENGLISH,
        condition=Condition.NEAR_MINT,
        quantity=1,
        notes="",
    )
    base.update(overrides)
    return CardDetailsValues(**base)


@pytest.fixture
def service(temp_db: Database) -> CardService:
    # No real network/filesystem access in unit tests.
    return CardService(CardRepository(temp_db), image_downloader=lambda _card: None)


@pytest.fixture
def collection_id(temp_db: Database) -> int:
    return CollectionRepository(temp_db).create("Binder").id


def test_add_card_from_catalog_maps_catalog_fields(
    service: CardService, collection_id: int
) -> None:
    card = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    assert card.name == "Xatu"
    assert card.set_name == "Skyridge"
    assert card.set_code == "skg"
    assert card.card_number == "H32"
    assert card.external_card_id == "skg-h32"
    assert card.variant is Variant.HOLO
    assert card.collection_id == collection_id
    assert card.cardmarket_url == "https://prices.pokemontcg.io/cardmarket/skg-h32"


def test_add_card_from_catalog_sets_photo_path_from_image_downloader(
    temp_db: Database, collection_id: int
) -> None:
    service = CardService(
        CardRepository(temp_db), image_downloader=lambda _card: "/tmp/skg-h32.png"
    )

    card = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    assert card.photo_path == "/tmp/skg-h32.png"


def test_add_card_from_catalog_with_no_image_leaves_photo_path_none(
    service: CardService, collection_id: int
) -> None:
    # The `service` fixture's image_downloader always returns None, mirroring
    # a failed/missing download — the card must still be added successfully.
    card = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    assert card.photo_path is None


def test_add_card_from_catalog_rejects_invalid_quantity(
    service: CardService, collection_id: int
) -> None:
    with pytest.raises(ValidationError):
        service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values(quantity=0))


def test_get_card_missing_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.get_card(999)


def test_list_cards_returns_only_own_collection(
    service: CardService, temp_db: Database, collection_id: int
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage").id
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())
    service.add_card_from_catalog(other_id, _CATALOG_CARD, _values())

    assert len(service.list_cards(collection_id)) == 1


def test_update_card_details_persists_changes(service: CardService, collection_id: int) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values(quantity=1))

    service.update_card_details(created.id, _values(quantity=5, notes="PSA 9"))

    updated = service.get_card(created.id)
    assert updated.quantity == 5
    assert updated.notes == "PSA 9"


def test_update_card_details_rejects_invalid_quantity(
    service: CardService, collection_id: int
) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())
    with pytest.raises(ValidationError):
        service.update_card_details(created.id, _values(quantity=0))


def test_update_card_details_missing_card_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.update_card_details(999, _values())


def test_remove_card_deletes_it(service: CardService, collection_id: int) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())
    service.remove_card(created.id)
    with pytest.raises(CardNotFoundError):
        service.get_card(created.id)


def test_remove_card_missing_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.remove_card(999)
