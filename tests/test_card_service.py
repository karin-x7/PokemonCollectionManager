"""Tests for card business logic: validation and friendly errors."""

from __future__ import annotations

import pytest

from app.catalog.models import CatalogCard
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import CardDetailsValues, CardFilter
from app.models.enums import Condition, Language, PriceQuality
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


def test_add_card_manual_stores_identity_and_manual_url_no_photo(
    service: CardService, collection_id: int
) -> None:
    url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Legendary-Collection/Venusaur-LC18"
    card = service.add_card_manual(
        collection_id, "Venusaur", "Legendary Collection", "18", _values(manual_cardmarket_url=url)
    )

    assert card.name == "Venusaur"
    assert card.set_name == "Legendary Collection"
    assert card.card_number == "18"
    assert card.manual_cardmarket_url == url
    assert card.cardmarket_url is None
    assert card.external_card_id is None
    assert card.photo_path is None


def test_add_card_manual_stores_a_resolved_set_code(
    service: CardService, collection_id: int
) -> None:
    # Lets a manually-entered card show the same set icon a catalogue-
    # matched card gets (see PokemonTcgClient.resolve_set_code).
    card = service.add_card_manual(
        collection_id, "Venusaur", "Legendary Collection", "18", _values(), set_code="ecard3"
    )

    assert card.set_code == "ecard3"


def test_add_card_manual_rejects_invalid_quantity(service: CardService, collection_id: int) -> None:
    with pytest.raises(ValidationError):
        service.add_card_manual(
            collection_id, "Venusaur", "Legendary Collection", "18", _values(quantity=0)
        )


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


def test_search_cards_delegates_to_repository(
    service: CardService, temp_db: Database, collection_id: int
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage 4").id
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())
    service.add_card_from_catalog(other_id, _CATALOG_CARD, _values())

    assert len(service.search_cards(CardFilter(collection_id=collection_id))) == 1
    assert len(service.search_cards(CardFilter(collection_id=None))) == 2


def test_list_set_names_delegates_to_repository(
    service: CardService, collection_id: int
) -> None:
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    assert service.list_set_names(collection_id) == ["Skyridge"]


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


def test_set_manual_cardmarket_url_persists(service: CardService, collection_id: int) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())
    url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Perfect-Order/Poke-Pad-V2-POR113"

    service.set_manual_cardmarket_url(created.id, url)

    updated = service.get_card(created.id)
    assert updated.manual_cardmarket_url == url


def test_set_manual_cardmarket_url_missing_card_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.set_manual_cardmarket_url(999, "https://www.cardmarket.com/x")


def test_set_manual_price_persists_price_and_quality(
    service: CardService, collection_id: int
) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    updated = service.set_manual_price(created.id, 42.5)

    assert updated.current_price == 42.5
    assert updated.price_currency == "EUR"
    assert updated.price_quality is PriceQuality.MANUAL
    assert updated.price_updated_at is not None


def test_set_manual_price_missing_card_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.set_manual_price(999, 10.0)


def test_set_manual_price_rejects_zero_or_negative(
    service: CardService, collection_id: int
) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    with pytest.raises(ValidationError):
        service.set_manual_price(created.id, 0)
    with pytest.raises(ValidationError):
        service.set_manual_price(created.id, -5.0)


def test_set_manual_price_adds_a_price_history_record(
    temp_db: Database, collection_id: int
) -> None:
    price_repository = PriceRepository(temp_db)
    service = CardService(
        CardRepository(temp_db), image_downloader=lambda _card: None, price_repository=price_repository
    )
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    service.set_manual_price(created.id, 99.0)

    records = price_repository.list_for_card(created.id)
    assert len(records) == 1
    assert records[0].price == 99.0
    assert records[0].price_quality is PriceQuality.MANUAL


def test_remove_card_deletes_it(service: CardService, collection_id: int) -> None:
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())
    service.remove_card(created.id)
    with pytest.raises(CardNotFoundError):
        service.get_card(created.id)


def test_remove_card_missing_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.remove_card(999)


def test_move_card_changes_its_collection(
    service: CardService, temp_db: Database, collection_id: int
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage 5").id
    created = service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    service.move_card(created.id, other_id)

    assert service.get_card(created.id).collection_id == other_id


def test_move_card_missing_raises_not_found(service: CardService) -> None:
    with pytest.raises(CardNotFoundError):
        service.move_card(999, 1)


def test_find_duplicates_matches_identical_identity_fields(
    service: CardService, collection_id: int
) -> None:
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    duplicates = service.find_duplicates("Xatu", "Skyridge", "H32", _values())

    assert len(duplicates) == 1
    assert duplicates[0].name == "Xatu"


def test_find_duplicates_matches_case_insensitively_on_name_and_set(
    service: CardService, collection_id: int
) -> None:
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    duplicates = service.find_duplicates("XATU", "skyridge", "H32", _values())

    assert len(duplicates) == 1


def test_find_duplicates_ignores_a_different_language(
    service: CardService, collection_id: int
) -> None:
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values(language=Language.ENGLISH))

    duplicates = service.find_duplicates(
        "Xatu", "Skyridge", "H32", _values(language=Language.GERMAN)
    )

    assert duplicates == []


def test_find_duplicates_ignores_a_different_condition(
    service: CardService, collection_id: int
) -> None:
    service.add_card_from_catalog(
        collection_id, _CATALOG_CARD, _values(condition=Condition.NEAR_MINT)
    )

    duplicates = service.find_duplicates(
        "Xatu", "Skyridge", "H32", _values(condition=Condition.PLAYED)
    )

    assert duplicates == []


def test_find_duplicates_ignores_a_different_extra(service: CardService, collection_id: int) -> None:
    service.add_card_from_catalog(
        collection_id, _CATALOG_CARD, _values(is_reverse_holo=False)
    )

    duplicates = service.find_duplicates(
        "Xatu", "Skyridge", "H32", _values(is_reverse_holo=True)
    )

    assert duplicates == []


def test_find_duplicates_ignores_a_different_card_number(
    service: CardService, collection_id: int
) -> None:
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    duplicates = service.find_duplicates("Xatu", "Skyridge", "H33", _values())

    assert duplicates == []


def test_find_duplicates_searches_across_all_collections(
    service: CardService, temp_db: Database, collection_id: int
) -> None:
    other_id = CollectionRepository(temp_db).create("Vintage 5").id
    service.add_card_from_catalog(collection_id, _CATALOG_CARD, _values())

    duplicates = service.find_duplicates("Xatu", "Skyridge", "H32", _values())

    assert len(duplicates) == 1
    assert duplicates[0].collection_id != other_id  # sanity: found in the original collection


def test_find_duplicates_returns_empty_list_when_nothing_owned(service: CardService) -> None:
    assert service.find_duplicates("Xatu", "Skyridge", "H32", _values()) == []
