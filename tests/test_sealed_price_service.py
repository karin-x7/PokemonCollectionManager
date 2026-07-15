"""Tests for the sealed-product price matching (simplified: language only,
no condition ladder, no shortlink resolution)."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.models.enums import Language, PriceQuality
from app.pricing.browser_price_reader import BrowserPriceReaderError
from app.pricing.cardmarket_parsing import SELLER_COUNTRY_GERMANY_ID
from app.pricing.models import SealedOffer
from app.pricing.seller_location import set_germany_only_enabled
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


def _service(
    temp_db: Database, offer_reader, settings_repository=None, request_delay: float = 0
) -> SealedPriceService:
    return SealedPriceService(
        SealedProductRepository(temp_db),
        SealedPriceRepository(temp_db),
        offer_reader=offer_reader,
        settings_repository=settings_repository,
        # No real delay by default -- these tests must run fast; the real,
        # deliberately noticeable pause is exercised/verified separately.
        request_delay=request_delay,
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


# --- Seller-location preference (Germany-only) ----------------------------- #


def _germany_only_settings(temp_db: Database) -> SettingsRepository:
    settings = SettingsRepository(temp_db)
    set_germany_only_enabled(settings, True)
    return settings


def test_seller_location_off_by_default_builds_no_country_filter(temp_db: Database) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.GERMAN, price=120.0)])
    service = _service(temp_db, reader)

    service.update_price_for_product(product.id)

    assert "sellerCountry" not in reader.calls[0][0]


def test_seller_location_exact_match_in_preferred_country_returns_immediately(
    temp_db: Database,
) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.GERMAN, price=120.0)])
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 120.0
    assert updated.price_quality is PriceQuality.EXACT
    assert len(reader.calls) == 1
    assert f"sellerCountry={SELLER_COUNTRY_GERMANY_ID}" in reader.calls[0][0]


def test_seller_location_falls_back_to_exact_match_across_all_countries(
    temp_db: Database,
) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    offers = [SealedOffer(seller="a", language=Language.GERMAN, price=99.0)]
    reader = FakeOfferReader([], offers)
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 99.0
    assert updated.price_quality is PriceQuality.EXACT
    assert len(reader.calls) == 2
    assert f"sellerCountry={SELLER_COUNTRY_GERMANY_ID}" in reader.calls[0][0]
    assert "sellerCountry" not in reader.calls[1][0]


def test_seller_location_falls_back_to_the_buffer_ladder_unfiltered_by_country(
    temp_db: Database,
) -> None:
    # Deliberately *not* a country-filtered buffer phase (an earlier version
    # had one) -- see _determine_price's own docstring: needlessly more
    # Cardmarket tabs for one lookup, live-reported to have triggered a
    # Cloudflare block.
    product = _product(temp_db, language=Language.GERMAN)
    buffer_offer = SealedOffer(seller="a", language=Language.ENGLISH, price=80.0)
    reader = FakeOfferReader(
        [],  # phase 1: exact (same language), preferred country
        [],  # phase 2: exact (same language), all countries
        [buffer_offer],  # phase 3: buffer (any language), unfiltered by country
    )
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 80.0
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_LANGUAGE
    assert len(reader.calls) == 3
    assert f"sellerCountry={SELLER_COUNTRY_GERMANY_ID}" in reader.calls[0][0]
    assert "sellerCountry" not in reader.calls[1][0]
    assert "sellerCountry" not in reader.calls[2][0]


def test_seller_location_note_says_germany_when_the_exact_country_match_wins(
    temp_db: Database,
) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.GERMAN, price=120.0)])
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.price_rationale.endswith("Seller location: Germany.")


def test_seller_location_note_says_all_countries_when_falling_back(temp_db: Database) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    offers = [SealedOffer(seller="a", language=Language.GERMAN, price=99.0)]
    reader = FakeOfferReader([], offers)
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.price_rationale.endswith("Seller location: all countries.")


def test_seller_location_note_absent_when_the_setting_is_off(temp_db: Database) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    reader = FakeOfferReader([SealedOffer(seller="a", language=Language.GERMAN, price=120.0)])
    service = _service(temp_db, reader)

    updated = service.update_price_for_product(product.id)

    assert "Seller location:" not in updated.price_rationale


def test_seller_location_no_price_anywhere_still_yields_no_price(temp_db: Database) -> None:
    product = _product(temp_db, language=Language.GERMAN)
    reader = FakeOfferReader([], [], [])
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
    assert len(reader.calls) == 3


def test_seller_location_a_raised_zero_offers_error_still_falls_through_to_the_next_phase(
    temp_db: Database,
) -> None:
    # Live-reported regression: the *real* offer reader
    # (read_sealed_offers_for_card) raises BrowserPriceReaderError, not an
    # empty list, when a filtered page genuinely has zero matching offers
    # (see its own docstring) -- Cardmarket itself said "Due to your filter
    # settings, no available offers are shown." for a sellerCountry=7 page
    # that loaded perfectly fine. Before this fix, that raise propagated
    # straight out of _check_same_language and aborted the whole lookup
    # after a single read instead of trying the next, broader phase.
    product = _product(temp_db, language=Language.GERMAN)
    offers = [SealedOffer(seller="a", language=Language.GERMAN, price=333.74)]
    reader = FakeOfferReader(
        BrowserPriceReaderError("Keine Angebote auf der Cardmarket-Seite erkannt."), offers
    )
    service = _service(temp_db, reader, settings_repository=_germany_only_settings(temp_db))

    updated = service.update_price_for_product(product.id)

    assert updated.current_price == 333.74
    assert updated.price_quality is PriceQuality.EXACT
    assert len(reader.calls) == 2
    assert f"sellerCountry={SELLER_COUNTRY_GERMANY_ID}" in reader.calls[0][0]
    assert "sellerCountry" not in reader.calls[1][0]
