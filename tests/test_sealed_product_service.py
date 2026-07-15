"""Tests for sealed product business logic: validation and friendly errors."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.enums import Language, PriceQuality
from app.models.sealed_product import SealedProductDetailsValues, SealedProductFilter
from app.services.exceptions import SealedProductNotFoundError, ValidationError
from app.services.sealed_product_service import SealedProductService

_URL = "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box"


def _values(**overrides) -> SealedProductDetailsValues:
    base = dict(language=Language.ENGLISH, quantity=1, notes="", cardmarket_url=_URL)
    base.update(overrides)
    return SealedProductDetailsValues(**base)


@pytest.fixture
def service(temp_db: Database) -> SealedProductService:
    return SealedProductService(SealedProductRepository(temp_db))


def test_add_product_manual_stores_identity_and_url(service: SealedProductService) -> None:
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values())

    assert product.name == "Base Set Booster Box"
    assert product.category == "Booster Box"
    # English (the fixture's default language) supports a Cardmarket language
    # filter, so the stored URL gains ?language=1 -- see
    # test_add_product_manual_rewrites_url_with_language_filter below.
    assert product.cardmarket_url == f"{_URL}?language=1"
    assert product.id is not None


def test_add_product_manual_rewrites_url_with_language_filter(
    service: SealedProductService,
) -> None:
    product = service.add_product_manual(
        "Base Set Booster Box", "Booster Box", _values(language=Language.GERMAN)
    )

    assert product.cardmarket_url == f"{_URL}?language=3"


def test_add_product_manual_rewrites_url_for_japanese_too(
    service: SealedProductService,
) -> None:
    # Unlike single cards, a sealed product's Japanese/Korean/Traditional
    # Chinese offers live on the same Cardmarket page as everything else
    # (live-confirmed against a real Asian-exclusive set, see
    # sealed_supports_language_filter's docstring), so these three get
    # filtered here too -- language id 7 for Japanese.
    product = service.add_product_manual(
        "Base Set Booster Box", "Booster Box", _values(language=Language.JAPANESE)
    )

    assert product.cardmarket_url == f"{_URL}?language=7"


def test_add_product_manual_rewrites_url_for_korean_and_t_chinese(
    service: SealedProductService,
) -> None:
    korean = service.add_product_manual(
        "Base Set Booster Box", "Booster Box", _values(language=Language.KOREAN)
    )
    chinese = service.add_product_manual(
        "Base Set Booster Box", "Booster Box", _values(language=Language.CHINESE)
    )

    assert korean.cardmarket_url == f"{_URL}?language=10"
    assert chinese.cardmarket_url == f"{_URL}?language=11"


def test_update_product_details_rewrites_url_with_language_filter(
    service: SealedProductService,
) -> None:
    product = service.add_product_manual(
        "Base Set Booster Box", "Booster Box", _values(language=Language.JAPANESE)
    )

    service.update_product_details(product.id, _values(language=Language.GERMAN))

    updated = service.get_product(product.id)
    assert updated.cardmarket_url == f"{_URL}?language=3"


def test_add_product_manual_rejects_invalid_quantity(service: SealedProductService) -> None:
    with pytest.raises(ValidationError):
        service.add_product_manual("Base Set Booster Box", "Booster Box", _values(quantity=0))


def test_get_product_raises_when_missing(service: SealedProductService) -> None:
    with pytest.raises(SealedProductNotFoundError):
        service.get_product(999)


def test_search_products_returns_every_owned_product(service: SealedProductService) -> None:
    service.add_product_manual("Base Set Booster Box", "Booster Box", _values())
    service.add_product_manual("Evolutions ETB", "Elite Trainer Box", _values())

    assert len(service.search_products(SealedProductFilter())) == 2


def test_update_product_details_persists_new_values(service: SealedProductService) -> None:
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values(quantity=1))

    service.update_product_details(product.id, _values(language=Language.GERMAN, quantity=3))

    updated = service.get_product(product.id)
    assert updated.language is Language.GERMAN
    assert updated.quantity == 3


def test_update_product_details_rejects_invalid_quantity(service: SealedProductService) -> None:
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values())
    with pytest.raises(ValidationError):
        service.update_product_details(product.id, _values(quantity=0))


def test_update_product_details_raises_when_missing(service: SealedProductService) -> None:
    with pytest.raises(SealedProductNotFoundError):
        service.update_product_details(999, _values())


def test_remove_product_deletes_it(service: SealedProductService) -> None:
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values())

    service.remove_product(product.id)

    with pytest.raises(SealedProductNotFoundError):
        service.get_product(product.id)


def test_remove_product_raises_when_missing(service: SealedProductService) -> None:
    with pytest.raises(SealedProductNotFoundError):
        service.remove_product(999)


def test_set_manual_price_persists_price_and_quality(service: SealedProductService) -> None:
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values())

    updated = service.set_manual_price(product.id, 42.5)

    assert updated.current_price == 42.5
    assert updated.price_currency == "EUR"
    assert updated.price_quality is PriceQuality.MANUAL
    assert updated.price_updated_at is not None


def test_set_manual_price_missing_product_raises_not_found(service: SealedProductService) -> None:
    with pytest.raises(SealedProductNotFoundError):
        service.set_manual_price(999, 10.0)


def test_set_manual_price_rejects_zero_or_negative(service: SealedProductService) -> None:
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values())

    with pytest.raises(ValidationError):
        service.set_manual_price(product.id, 0)
    with pytest.raises(ValidationError):
        service.set_manual_price(product.id, -5.0)


def test_set_manual_price_adds_a_price_history_record(temp_db: Database) -> None:
    price_repository = SealedPriceRepository(temp_db)
    service = SealedProductService(SealedProductRepository(temp_db), price_repository)
    product = service.add_product_manual("Base Set Booster Box", "Booster Box", _values())

    service.set_manual_price(product.id, 99.0)

    records = price_repository.list_for_product(product.id)
    assert len(records) == 1
    assert records[0].price == 99.0
    assert records[0].price_quality is PriceQuality.MANUAL
