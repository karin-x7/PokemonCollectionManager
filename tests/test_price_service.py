"""Tests for the Cardmarket price matching ladder and persistence."""

from __future__ import annotations

import pytest

from app.catalog.models import CatalogCard
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality, Variant
from app.pricing.browser_price_reader import BrowserPriceReaderError, build_filtered_url
from app.pricing.models import CardmarketOffer
from app.services.exceptions import CardNotFoundError
from app.services.price_service import PriceService

_CARDMARKET_URL = "https://prices.pokemontcg.io/cardmarket/skg-h32"


class FakeOfferReader:
    """Returns one queued response per call, in order.

    Each queued item is either a list of offers or an exception instance to
    raise. Once the queue is exhausted, further calls return an empty list —
    convenient for tests where only the first tier(s) matter and later,
    looser ladder steps are expected to just find nothing.
    """

    def __init__(self, *responses: list[CardmarketOffer] | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, url: str, match_hint: str) -> list[CardmarketOffer]:
        self.calls.append((url, match_hint))
        response: list[CardmarketOffer] | Exception = (
            self._responses.pop(0) if self._responses else []
        )
        if isinstance(response, Exception):
            raise response
        return response


class FakePokemonTcgClient:
    def __init__(self, catalog_card: CatalogCard | None = None) -> None:
        self._catalog_card = catalog_card

    def get_card_by_id(self, external_id: str) -> CatalogCard | None:
        return self._catalog_card


@pytest.fixture
def collection_id(temp_db: Database) -> int:
    return CollectionRepository(temp_db).create("Binder").id


def _card(temp_db: Database, collection_id: int, **overrides) -> Card:
    base = dict(
        id=None,
        collection_id=collection_id,
        name="Xatu",
        variant=Variant.HOLO,
        language=Language.GERMAN,
        condition=Condition.GOOD,
        cardmarket_url=_CARDMARKET_URL,
        external_card_id="skg-h32",
    )
    base.update(overrides)
    return CardRepository(temp_db).create(Card(**base))


def _service(temp_db: Database, offer_reader, pokemontcg=None, url_resolver=None) -> PriceService:
    return PriceService(
        CardRepository(temp_db),
        PriceRepository(temp_db),
        pokemontcg or FakePokemonTcgClient(),
        offer_reader=offer_reader,
        # Identity by default: these tests care about the matching ladder,
        # not redirect resolution, and must never make a real HTTP request.
        url_resolver=url_resolver or (lambda url: url),
    )


def test_missing_card_raises_not_found(temp_db: Database) -> None:
    service = _service(temp_db, FakeOfferReader())
    with pytest.raises(CardNotFoundError):
        service.update_price_for_card(999)


def test_shortlink_is_resolved_before_building_filtered_urls(
    temp_db: Database, collection_id: int
) -> None:
    """cardmarket_url is a pokemontcg.io tracking shortlink whose redirect

    target is fixed on their end -- any ?language=/minCondition= filter
    appended to the *shortlink* is silently dropped during the redirect,
    landing on the fully unfiltered page regardless of what was requested.
    The ladder must build its filtered URLs from the *resolved* real
    cardmarket.com URL, not the shortlink.
    """
    real_url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.GERMAN, price=15.0)
    ]
    reader = FakeOfferReader(offers)
    service = _service(temp_db, reader, url_resolver=lambda url: real_url)

    service.update_price_for_card(card.id)

    expected_url = build_filtered_url(real_url, language=Language.GERMAN, min_condition=Condition.GOOD)
    assert reader.calls == [(expected_url, "Xatu")]


def test_resolved_url_is_persisted_back_to_the_card(
    temp_db: Database, collection_id: int
) -> None:
    real_url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    card = _card(temp_db, collection_id, cardmarket_url=_CARDMARKET_URL)
    service = _service(
        temp_db, FakeOfferReader([]), url_resolver=lambda url: real_url
    )

    service.update_price_for_card(card.id)

    assert CardRepository(temp_db).get(card.id).cardmarket_url == real_url


def test_already_resolved_url_is_not_rewritten(temp_db: Database, collection_id: int) -> None:
    real_url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    card = _card(temp_db, collection_id, cardmarket_url=real_url)
    service = _service(temp_db, FakeOfferReader([]), url_resolver=lambda url: url)

    service.update_price_for_card(card.id)

    assert CardRepository(temp_db).get(card.id).cardmarket_url == real_url


def test_exact_match_picks_cheapest_matching_offer(temp_db: Database, collection_id: int) -> None:
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.GERMAN, price=20.0),
        CardmarketOffer(seller="b", condition=Condition.GOOD, language=Language.GERMAN, price=15.0),
        CardmarketOffer(
            seller="c", condition=Condition.NEAR_MINT, language=Language.GERMAN, price=5.0
        ),
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 15.0
    assert updated.price_quality is PriceQuality.EXACT


def test_estimated_from_condition_picks_nearest_condition_same_language(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    offers = [
        CardmarketOffer(
            seller="a", condition=Condition.NEAR_MINT, language=Language.GERMAN, price=50.0
        ),
        CardmarketOffer(
            seller="b", condition=Condition.LIGHT_PLAYED, language=Language.GERMAN, price=10.0
        ),
        CardmarketOffer(seller="c", condition=Condition.POOR, language=Language.GERMAN, price=1.0),
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    updated = service.update_price_for_card(card.id)

    # LIGHT_PLAYED (distance 1) is nearer to GOOD than NEAR_MINT (2) or POOR (3).
    assert updated.current_price == 10.0
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_CONDITION


def test_falls_back_to_worse_condition_same_language_when_nothing_at_or_better(
    temp_db: Database, collection_id: int
) -> None:
    """Tier 1 (language + at-or-better condition) finds nothing -- only

    worse-than-requested stock exists in this language. Tier 2 (language,
    every condition) must be tried before giving up on the language
    entirely and moving on to tier 3 (other languages).
    """
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    tier2_offers = [
        CardmarketOffer(
            seller="a", condition=Condition.LIGHT_PLAYED, language=Language.GERMAN, price=10.0
        ),
        CardmarketOffer(seller="b", condition=Condition.POOR, language=Language.GERMAN, price=1.0),
    ]
    reader = FakeOfferReader([], tier2_offers)
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 10.0  # LIGHT_PLAYED is nearer to GOOD than POOR
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_CONDITION
    assert len(reader.calls) == 2
    assert reader.calls[0][0] == build_filtered_url(
        _CARDMARKET_URL, language=Language.GERMAN, min_condition=Condition.GOOD
    )
    assert reader.calls[1][0] == build_filtered_url(_CARDMARKET_URL, language=Language.GERMAN)


def test_estimated_from_language_picks_cheapest_same_condition_other_language(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    # Tier 1 (language=German + minCondition=Good): no stock at all.
    # Tier 2 (language=German, any condition): still no German stock at all.
    # Tier 3 (minCondition=Good, any language): other-language GOOD offers.
    tier3_offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.ENGLISH, price=8.0),
        CardmarketOffer(seller="b", condition=Condition.GOOD, language=Language.FRENCH, price=6.0),
    ]
    reader = FakeOfferReader([], [], tier3_offers)
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 6.0
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_LANGUAGE
    assert len(reader.calls) == 3
    assert reader.calls[0][0] == build_filtered_url(
        _CARDMARKET_URL, language=Language.GERMAN, min_condition=Condition.GOOD
    )
    assert reader.calls[1][0] == build_filtered_url(_CARDMARKET_URL, language=Language.GERMAN)
    assert reader.calls[2][0] == build_filtered_url(_CARDMARKET_URL, min_condition=Condition.GOOD)


def test_average_used_when_nothing_matches_language_or_condition(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    # Tier 1 (language=German + minCondition=Good): nothing. Tier 2
    # (language=German, any condition): still nothing. Tier 3
    # (minCondition=Good, any language): nothing exactly GOOD either.
    # Tier 4 (fully unfiltered): everything found so far, averaged.
    unfiltered_offers = [
        CardmarketOffer(
            seller="a", condition=Condition.NEAR_MINT, language=Language.ENGLISH, price=10.0
        ),
        CardmarketOffer(seller="b", condition=Condition.POOR, language=Language.FRENCH, price=20.0),
    ]
    reader = FakeOfferReader([], [], [], unfiltered_offers)
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 15.0
    assert updated.price_quality is PriceQuality.AVERAGE
    assert len(reader.calls) == 4
    assert reader.calls[3][0] == _CARDMARKET_URL


def test_unmapped_language_falls_back_to_client_side_filtering(
    temp_db: Database, collection_id: int
) -> None:
    """Japanese/Korean/Chinese have no Cardmarket URL filter id (separate

    products there, not a language filter) — the base URL is fetched
    unfiltered instead, and matching by language falls back to filtering the
    returned offers in Python.
    """
    card = _card(temp_db, collection_id, language=Language.JAPANESE, condition=Condition.GOOD)
    offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.JAPANESE, price=9.0),
        CardmarketOffer(seller="b", condition=Condition.GOOD, language=Language.ENGLISH, price=1.0),
    ]
    reader = FakeOfferReader(offers)
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 9.0  # the cheap English one must be ignored
    assert updated.price_quality is PriceQuality.EXACT
    # No language id to filter by, but the condition filter still applies.
    expected_url = build_filtered_url(_CARDMARKET_URL, min_condition=Condition.GOOD)
    assert reader.calls == [(expected_url, "Xatu")]


def test_no_offers_found_yields_no_price(temp_db: Database, collection_id: int) -> None:
    card = _card(temp_db, collection_id)
    service = _service(temp_db, FakeOfferReader([]))

    updated = service.update_price_for_card(card.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE


def test_browser_price_reader_error_yields_no_price_not_a_crash(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id)
    reader = FakeOfferReader(BrowserPriceReaderError("Tab nicht gefunden."))
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.NO_PRICE
    assert updated.price_rationale == "Tab nicht gefunden."
    # A browser/window failure aborts immediately -- it means the read itself
    # failed, not that this tier had no matching offers, so retrying a
    # looser filter wouldn't help.
    assert len(reader.calls) == 1


def test_missing_cardmarket_url_is_backfilled_from_external_card_id(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id, cardmarket_url=None, external_card_id="skg-h32")
    catalog_card = CatalogCard(
        external_id="skg-h32",
        name="Xatu",
        set_name="Skyridge",
        set_code="skg",
        card_number="H32",
        rarity="Rare Holo",
        image_small_url=None,
        image_large_url=None,
        cardmarket_url=_CARDMARKET_URL,
    )
    offer_reader = FakeOfferReader(
        [CardmarketOffer(seller="a", condition=card.condition, language=card.language, price=5.0)]
    )
    service = _service(temp_db, offer_reader, FakePokemonTcgClient(catalog_card=catalog_card))

    updated = service.update_price_for_card(card.id)

    assert updated.cardmarket_url == _CARDMARKET_URL
    assert updated.price_quality is PriceQuality.EXACT
    expected_url = build_filtered_url(
        _CARDMARKET_URL, language=card.language, min_condition=card.condition
    )
    assert offer_reader.calls == [(expected_url, "Xatu")]


def test_no_cardmarket_url_and_no_external_id_yields_no_price_without_calling_reader(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id, cardmarket_url=None, external_card_id=None)
    offer_reader = FakeOfferReader()
    service = _service(temp_db, offer_reader)

    updated = service.update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.NO_PRICE
    assert offer_reader.calls == []


def test_price_history_record_is_written_on_success(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.GERMAN, price=12.5)
    ]
    service = _service(temp_db, FakeOfferReader(offers))

    service.update_price_for_card(card.id)

    history = PriceRepository(temp_db).list_for_card(card.id)
    assert len(history) == 1
    assert history[0].price == 12.5
    assert history[0].source == "cardmarket"
