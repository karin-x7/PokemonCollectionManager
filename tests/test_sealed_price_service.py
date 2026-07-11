"""Tests for the sealed-product price matching (simplified: language only,
no condition ladder, no shortlink resolution)."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.models.enums import Language, PriceQuality
from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.models import SealedOffer
from app.services.exceptions import SealedProductNotFoundError
from app.services.sealed_price_service import SealedPriceService

_URL = "https://www.cardmarket.com/en/Pokemon/Products/Booster-Boxes/Base-Set-Booster-Box"


class FakeOfferReader:
    def __init__(self, *responses: list[SealedOffer] | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, url: str, match_hint: str) -> list[SealedOffer]:
        self.calls.append((url, match_hint))
        response = self._responses.pop(0) if self._responses else []
        if isinstance(response, Exception):
            raise response
        return response


def _product(temp_db: Database, **overrides):
    from app.models.sealed_product import SealedProduct

    base = dict(
        id=None,
        name="Base Set Booster Box",
        category="Booster Box",
        language=Language.GERMAN,
        cardmarket_url=_URL,
    )
    base.update(overrides)
    return SealedProductRepository(temp_db).create(SealedProduct(**base))


def _service(temp_db: Database, offer_reader) -> SealedPriceService:
    return SealedPriceService(
        SealedProductRepository(temp_db),
        SealedPriceRepository(temp_db),
        offer_reader=offer_reader,
    )


def test_missing_product_raises_not_found(temp_db: Database) -> None:
    service = _service(temp_db, FakeOfferReader())
    with pytest.raises(SealedProductNotFoundError):
        service.update_price_for_product(999)


def test_no_cardmarket_url_yields_no_price_without_reading(
    temp_db: Database
) -> None:
    product = _product(temp_db, cardmarket_url=None)
    reader = FakeOfferReader()
    service = _service(temp_db, reader)

    updated = service.update_price_for_product(product.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
    assert reader.calls == []


def test_exact_match_picks_cheapest_offer_in_the_requested_language(
    temp_db: Database
) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    offers = [
        SealedOffer(seller="a", language=Language.GERMAN, price=150.0),
        SealedOffer(seller="b", language=Language.GERMAN, price=120.0),
        SealedOffer(seller="c", language=Language.ENGLISH, price=90.0),
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 120.0
    assert updated.price_quality is PriceQuality.EXACT


def test_falls_back_to_cheapest_any_language_when_none_match(
    temp_db: Database
) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    offers = [
        SealedOffer(seller="a", language=Language.ENGLISH, price=90.0),
        SealedOffer(seller="b", language=Language.FRENCH, price=80.0),
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 80.0
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_LANGUAGE


def test_offers_with_unrecognised_language_still_count_for_the_any_language_fallback(
    temp_db: Database
) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    offers = [SealedOffer(seller="a", language=None, price=999.0)]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 999.0
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_LANGUAGE


def test_japanese_product_never_falls_back_to_a_different_language(
    temp_db: Database
) -> None:
    # Even though sealed products' Japanese/Korean/Chinese offers live on
    # the same Cardmarket page (filterable via ?language=N, unlike single
    # cards), a page with only Korean offers for a Japanese product must
    # never be silently reported as an "estimated" Japanese price --
    # Korean vs. Japanese exclusives can have wildly different market
    # prices, so "no current sellers in the requested language" should
    # stay NO_PRICE rather than guess from a different language.
    product = _product(temp_db, language=Language.JAPANESE)
    offers = [
        SealedOffer(seller="a", language=Language.KOREAN, price=45.20),
        SealedOffer(seller="b", language=Language.KOREAN, price=50.0),
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
    assert "Japanese" in updated.price_rationale


def test_korean_product_with_an_exact_match_still_works(temp_db: Database) -> None:
    # The "no fallback" rule only kicks in when there's no exact match --
    # a correctly-linked Korean product page still prices normally.
    product = _product(temp_db, language=Language.KOREAN)
    offers = [SealedOffer(seller="a", language=Language.KOREAN, price=45.20)]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 45.20
    assert updated.price_quality is PriceQuality.EXACT


def test_no_offers_at_all_yields_no_price(temp_db: Database) -> None:
    product = _product(temp_db)
    service = _service(temp_db, FakeOfferReader([]))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE


def test_reader_error_yields_no_price_with_its_own_message(
    temp_db: Database
) -> None:
    product = _product(temp_db)
    service = _service(temp_db, FakeOfferReader(BrowserPriceReaderError("Tab nicht gefunden.")))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
    assert updated.price_rationale == "Tab nicht gefunden."


def test_reads_the_products_own_cardmarket_url_with_its_language_filter_applied(
    temp_db: Database
) -> None:
    # No resolution step (unlike cards' pokemontcg.io shortlink) -- but the
    # language filter is (re-)applied fresh at read time, see the next two
    # tests for why.
    product = _product(temp_db, cardmarket_url=_URL, language=Language.GERMAN)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.GERMAN, price=100.0)])
    service = _service(temp_db, reader)

    service.update_price_for_product(product.id)

    assert reader.calls == [(f"{_URL}?language=3", "Base Set Booster Box")]


def test_a_stored_url_missing_the_language_filter_gets_it_applied_at_lookup_time(
    temp_db: Database
) -> None:
    # Real, live-confirmed bug: products added/edited before the sealed
    # language filter existed (or before it covered Japanese/Korean/
    # Chinese) have a stored URL with no ?language= filter at all. Rather
    # than requiring the user to re-add or re-edit every such product, the
    # filter is derived fresh from product.language on every price lookup.
    product = _product(temp_db, cardmarket_url=_URL, language=Language.JAPANESE)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.JAPANESE, price=45.0)])
    service = _service(temp_db, reader)

    service.update_price_for_product(product.id)

    assert reader.calls == [(f"{_URL}?language=7", "Base Set Booster Box")]


def test_an_already_filtered_stored_url_does_not_get_a_duplicated_filter(
    temp_db: Database
) -> None:
    # A product added after the write-time filter existed already has
    # ?language=N in its stored URL -- re-deriving it at read time must not
    # stack a second one on top.
    product = _product(temp_db, cardmarket_url=f"{_URL}?language=3", language=Language.GERMAN)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.GERMAN, price=100.0)])
    service = _service(temp_db, reader)

    service.update_price_for_product(product.id)

    assert reader.calls == [(f"{_URL}?language=3", "Base Set Booster Box")]


def test_successful_price_lookup_appends_a_history_record(temp_db: Database) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    offers = [SealedOffer(seller="a", language=Language.GERMAN, price=120.0)]
    service = _service(temp_db, FakeOfferReader(offers))

    service.update_price_for_product(product.id)

    records = SealedPriceRepository(temp_db).list_for_product(product.id)
    assert len(records) == 1
    assert records[0].price == 120.0
    assert records[0].price_quality is PriceQuality.EXACT


def test_no_price_found_does_not_append_a_history_record(temp_db: Database) -> None:
    product = _product(temp_db)
    service = _service(temp_db, FakeOfferReader([]))

    service.update_price_for_product(product.id)

    assert SealedPriceRepository(temp_db).list_for_product(product.id) == []
