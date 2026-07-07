"""Tests for the Cardmarket price matching ladder and persistence."""

from __future__ import annotations

import pytest

from app.catalog.models import CatalogCard
from app.database.connection import Database
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.collection_repository import CollectionRepository
from app.database.repositories.price_repository import PriceRepository
from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality
from app.pricing.browser_price_reader import BrowserPriceReaderError, build_filtered_url
from app.pricing.models import CardmarketOffer
from app.services.exceptions import CardNotFoundError
from app.services.price_service import PriceService

_CARDMARKET_URL = "https://prices.pokemontcg.io/cardmarket/skg-h32"
#: Cards built by ``_card()`` below default every extra to False -- every
#: expected-URL assertion needs the same, since the ladder now filters by
#: these on every tier.
_NO_EXTRAS = {
    "signed": False,
    "first_edition": False,
    "altered": False,
    "reverse_holo": False,
}


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
        language=Language.GERMAN,
        condition=Condition.GOOD,
        cardmarket_url=_CARDMARKET_URL,
        external_card_id="skg-h32",
    )
    base.update(overrides)
    return CardRepository(temp_db).create(Card(**base))


def _service(
    temp_db: Database,
    offer_reader,
    pokemontcg=None,
    url_resolver=None,
    designation_lookup=None,
    version_switch_delay: float = 0,
) -> PriceService:
    return PriceService(
        CardRepository(temp_db),
        PriceRepository(temp_db),
        pokemontcg or FakePokemonTcgClient(),
        offer_reader=offer_reader,
        # Identity by default: these tests care about the matching ladder,
        # not redirect resolution, and must never make a real HTTP request.
        url_resolver=url_resolver or (lambda url: url),
        # "No suggestion" by default -- must never make a real HTTP request.
        designation_lookup=designation_lookup or (lambda external_id, language: None),
        # No real delay by default -- these tests must run fast; the real,
        # deliberately noticeable pause is exercised/verified separately.
        version_switch_delay=version_switch_delay,
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

    expected_url = build_filtered_url(
        real_url, language=Language.GERMAN, min_condition=Condition.GOOD, **_NO_EXTRAS
    )
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
        _CARDMARKET_URL, language=Language.GERMAN, min_condition=Condition.GOOD, **_NO_EXTRAS
    )
    assert reader.calls[1][0] == build_filtered_url(
        _CARDMARKET_URL, language=Language.GERMAN, **_NO_EXTRAS
    )


# -- alternate-version fallback (vintage multi-product sets) --------------- #
# Real, confirmed case: Cardmarket lists a vintage set's language as an
# entirely separate product under a sibling "-V<n>-" URL, not a filter on
# one shared page (Base Set's Venusaur: "-V2-" English-only vs. "-V1-"
# multi-language). This ladder step tries exactly one alternate version --
# never more -- after a deliberate pause, since this exact kind of
# candidate-guessing previously triggered a real Cardmarket account
# lockout when it opened up to 6 tabs with no delay (see
# PROJECT_PROGRESS.md, "Verworfener Versuch").
_VINTAGE_URL = "https://cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V2-BS15"
_VINTAGE_ALTERNATE_URL = "https://cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V1-BS15"


def test_alternate_version_is_tried_when_language_has_zero_offers_at_all(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(
        temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD,
        cardmarket_url=_VINTAGE_URL,
    )
    # Tier 1 + tier 2 on the (wrong) V2 product: zero German offers at all.
    # Alternate (V1) tier 1: nothing at-or-better. Alternate tier 2: a match.
    alt_offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.GERMAN, price=250.0)
    ]
    reader = FakeOfferReader([], [], [], alt_offers)
    service = _service(temp_db, reader, version_switch_delay=0)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 250.0
    assert updated.price_quality is PriceQuality.EXACT
    assert len(reader.calls) == 4
    assert reader.calls[2][0] == build_filtered_url(
        _VINTAGE_ALTERNATE_URL, language=Language.GERMAN, min_condition=Condition.GOOD, **_NO_EXTRAS
    )
    assert reader.calls[3][0] == build_filtered_url(
        _VINTAGE_ALTERNATE_URL, language=Language.GERMAN, **_NO_EXTRAS
    )
    # The corrected URL is persisted so every future lookup goes straight
    # to the right product.
    assert updated.cardmarket_url == _VINTAGE_ALTERNATE_URL


def test_alternate_version_not_tried_for_a_modern_card_without_a_version_suffix(
    temp_db: Database, collection_id: int
) -> None:
    """``_CARDMARKET_URL`` (used by the default ``_card()`` fixture) has no

    "-V<n>-" suffix at all -- must never invent one to try."""
    card = _card(temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD)
    reader = FakeOfferReader([], [], [])  # tier 1, tier 2, tier 3 (any language) all empty

    updated = _service(temp_db, reader).update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.NO_PRICE
    assert len(reader.calls) == 4  # tiers 1-4, no extra alternate-version call


def test_alternate_version_not_tried_when_step_two_already_found_offers(
    temp_db: Database, collection_id: int
) -> None:
    """Reaching tier 2 with *some* offers (even if none match condition

    exactly) means the language genuinely has stock on this product -- not
    the "wrong product entirely" signature this fallback looks for."""
    card = _card(
        temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD,
        cardmarket_url=_VINTAGE_URL,
    )
    tier2_offers = [
        CardmarketOffer(seller="a", condition=Condition.POOR, language=Language.GERMAN, price=1.0)
    ]
    reader = FakeOfferReader([], tier2_offers)
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 1.0
    assert len(reader.calls) == 2  # no alternate-version attempt made
    assert updated.cardmarket_url == _VINTAGE_URL  # unchanged


def test_alternate_version_failing_too_falls_through_to_any_language_step(
    temp_db: Database, collection_id: int
) -> None:
    card = _card(
        temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD,
        cardmarket_url=_VINTAGE_URL,
    )
    tier3_offers = [
        CardmarketOffer(seller="a", condition=Condition.GOOD, language=Language.ENGLISH, price=99.0)
    ]
    # tier1, tier2 (V2, empty), alt tier1, alt tier2 (V1, empty too), tier3 (any language, V2)
    reader = FakeOfferReader([], [], [], [], tier3_offers)
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price == 99.0
    assert updated.price_quality is PriceQuality.ESTIMATED_FROM_LANGUAGE
    assert len(reader.calls) == 5
    # The original (unconfirmed) URL is used for tier 3 -- the alternate
    # never panned out, so it must not be adopted.
    assert reader.calls[4][0] == build_filtered_url(
        _VINTAGE_URL, min_condition=Condition.GOOD, **_NO_EXTRAS
    )
    assert updated.cardmarket_url == _VINTAGE_URL


def test_alternate_version_switch_applies_a_deliberate_delay(
    temp_db: Database, collection_id: int, monkeypatch
) -> None:
    """This exact kind of candidate-guessing previously triggered a real

    Cardmarket account lockout (see PROJECT_PROGRESS.md) because it opened
    several tabs with *no* delay at all -- the fix must always pause first,
    never fire the alternate tab instantly.
    """
    import app.services.price_service as price_service_module

    card = _card(
        temp_db, collection_id, language=Language.GERMAN, condition=Condition.GOOD,
        cardmarket_url=_VINTAGE_URL,
    )
    reader = FakeOfferReader([], [], [], [])
    sleep_calls = []
    monkeypatch.setattr(price_service_module.time, "sleep", sleep_calls.append)
    service = _service(temp_db, reader, version_switch_delay=3.0)

    service.update_price_for_card(card.id)

    assert sleep_calls == [3.0]


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
        _CARDMARKET_URL, language=Language.GERMAN, min_condition=Condition.GOOD, **_NO_EXTRAS
    )
    assert reader.calls[1][0] == build_filtered_url(
        _CARDMARKET_URL, language=Language.GERMAN, **_NO_EXTRAS
    )
    assert reader.calls[2][0] == build_filtered_url(
        _CARDMARKET_URL, min_condition=Condition.GOOD, **_NO_EXTRAS
    )


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
    assert reader.calls[3][0] == build_filtered_url(_CARDMARKET_URL, **_NO_EXTRAS)


def test_unmapped_language_without_manual_url_bails_with_clear_message(
    temp_db: Database, collection_id: int
) -> None:
    """Japanese/Korean/Chinese prints are entirely separate Cardmarket

    products (e.g. Neo Revelation's Ho-Oh is listed under "Awakening
    Legends"), not a language filter on the Western product's page.
    pokemontcg.io's own cardmarket_url always points at that Western
    product, so falling through the ladder against it would misprice the
    card from unrelated offers -- this must bail out instead of guessing,
    and never even touch the reader.
    """
    card = _card(temp_db, collection_id, language=Language.JAPANESE, condition=Condition.GOOD)
    reader = FakeOfferReader()
    service = _service(temp_db, reader)

    updated = service.update_price_for_card(card.id)

    assert updated.current_price is None
    assert updated.price_quality is PriceQuality.NO_PRICE
    assert "Japanese" in updated.price_rationale
    assert "Cardmarket link" in updated.price_rationale
    assert reader.calls == []


def test_unmapped_language_bail_out_includes_a_designation_hint_when_found(
    temp_db: Database, collection_id: int
) -> None:
    """Names/labels only, never a price -- see tcgdex_designation_lookup's

    own docstring for why tcgdex is not trusted for pricing.
    """
    from app.catalog.tcgdex_designation_lookup import LocalizedDesignation

    card = _card(
        temp_db,
        collection_id,
        language=Language.JAPANESE,
        condition=Condition.GOOD,
        external_card_id="neo3-7",
    )
    designation = LocalizedDesignation(
        card_name="ho-oh", set_name="めざめる伝説", set_id="neo3", local_id="011"
    )
    calls = []

    def fake_lookup(external_id, language):
        calls.append((external_id, language))
        return designation

    service = _service(temp_db, FakeOfferReader(), designation_lookup=fake_lookup)

    updated = service.update_price_for_card(card.id)

    assert calls == [("neo3-7", Language.JAPANESE)]
    assert "めざめる伝説" in updated.price_rationale
    assert "011" in updated.price_rationale
    assert updated.current_price is None  # a designation hint is never a price
    assert updated.price_quality is PriceQuality.NO_PRICE


def test_unmapped_language_bail_out_survives_a_designation_lookup_failure(
    temp_db: Database, collection_id: int
) -> None:
    from app.catalog.tcgdex_designation_lookup import TcgdexDesignationLookupError

    def raising_lookup(external_id, language):
        raise TcgdexDesignationLookupError("boom")

    card = _card(temp_db, collection_id, language=Language.JAPANESE, condition=Condition.GOOD)
    service = _service(temp_db, FakeOfferReader(), designation_lookup=raising_lookup)

    updated = service.update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.NO_PRICE
    assert "Japanese" in updated.price_rationale


def test_manual_cardmarket_url_override_is_used_for_unmapped_language(
    temp_db: Database, collection_id: int
) -> None:
    """Once the user supplies the correct (Japanese-product) Cardmarket URL

    themselves, the ladder runs against *that* instead, with the same
    client-side language filtering as any other unmapped-language lookup.
    """
    manual_url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Awakening-Legends/Ho-Oh-AL"
    card = _card(
        temp_db,
        collection_id,
        language=Language.JAPANESE,
        condition=Condition.GOOD,
        manual_cardmarket_url=manual_url,
    )
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
    expected_url = build_filtered_url(manual_url, min_condition=Condition.GOOD, **_NO_EXTRAS)
    assert reader.calls == [(expected_url, "Xatu")]


def test_extras_are_included_in_every_tier_url(temp_db: Database, collection_id: int) -> None:
    """A signed/1st-edition/altered/reverse-holo card must never be priced

    against offers lacking those exact same extras — Cardmarket's own
    filters (``isSigned``/``isFirstEd``/``isAltered``/``isReverseHolo``,
    all bare top-level params) enforce this server-side, so every ladder
    tier's URL must carry them, not just the first one.
    """
    card = _card(
        temp_db,
        collection_id,
        language=Language.GERMAN,
        condition=Condition.GOOD,
        is_signed=True,
        is_first_edition=True,
        is_altered=True,
        is_reverse_holo=True,
    )
    reader = FakeOfferReader([], [], [], [])
    service = _service(temp_db, reader)

    service.update_price_for_card(card.id)

    assert len(reader.calls) == 4
    for url, _hint in reader.calls:
        assert "isSigned=Y" in url
        assert "isFirstEd=Y" in url
        assert "isAltered=Y" in url
        assert "isReverseHolo=Y" in url


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
        _CARDMARKET_URL, language=card.language, min_condition=card.condition, **_NO_EXTRAS
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


def test_base_set_card_without_a_link_gets_a_specific_ambiguous_variant_message(
    temp_db: Database, collection_id: int
) -> None:
    # Real, live-reported case: Base Set splits into Normal/Shadowless
    # Cardmarket products pokemontcg.io can't tell apart -- a card with no
    # link at all in an ambiguous set should get a specific, actionable
    # message, not the generic "no cardmarket link known" one, and never
    # fall through to backfilling (which would just be pokemontcg.io's
    # single, arbitrary link again).
    card = _card(
        temp_db,
        collection_id,
        cardmarket_url=None,
        external_card_id=None,
        set_code="base1",
        set_name="Base",
    )
    offer_reader = FakeOfferReader()
    service = _service(temp_db, offer_reader)

    updated = service.update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.NO_PRICE
    assert offer_reader.calls == []
    assert "Custom Cardmarket link" in updated.price_rationale
    assert "Shadowless" in updated.price_rationale


def test_base_set_card_with_an_unresolved_shortlink_is_still_treated_as_ambiguous(
    temp_db: Database, collection_id: int
) -> None:
    # A card added before the variant-splitting existed (or otherwise never
    # routed through CatalogSearchService's splitting) can already have
    # pokemontcg.io's own unresolved, variant-ambiguous shortlink stored --
    # that must not be blindly trusted just because *a* URL is present.
    card = _card(
        temp_db,
        collection_id,
        cardmarket_url="https://prices.pokemontcg.io/cardmarket/base1-4",
        external_card_id=None,
        set_code="base1",
        set_name="Base",
    )
    offer_reader = FakeOfferReader()
    service = _service(temp_db, offer_reader)

    updated = service.update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.NO_PRICE
    assert offer_reader.calls == []
    assert "Custom Cardmarket link" in updated.price_rationale


def test_base_set_card_with_an_already_resolved_link_is_used_directly(
    temp_db: Database, collection_id: int
) -> None:
    # A card added via CatalogSearchService's variant-splitting (or with a
    # manually-set link) already has a specific, resolved cardmarket.com URL
    # -- not pokemontcg.io's own shortlink -- and should be used as normal.
    resolved_url = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard-V1-BS4"
    card = _card(
        temp_db,
        collection_id,
        cardmarket_url=resolved_url,
        external_card_id=None,
        set_code="base1",
        set_name="Base",
        language=Language.ENGLISH,
    )
    offer_reader = FakeOfferReader(
        [CardmarketOffer(seller="a", condition=card.condition, language=card.language, price=200.0)]
    )
    service = _service(temp_db, offer_reader)

    updated = service.update_price_for_card(card.id)

    assert updated.price_quality is PriceQuality.EXACT
    assert offer_reader.calls
    assert offer_reader.calls[0][0].startswith(resolved_url)


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
