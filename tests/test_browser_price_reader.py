"""Tests for the pure offer-parsing logic in browser_price_reader.

Only ``_parse_offer_lines`` is tested here: a window-reading function has no
deterministic, sandboxable behaviour to test against (it depends on a real
browser window actually being open on screen), so it's verified manually
instead (see PROJECT_PROGRESS.md).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from app.models.enums import Condition, Language
from app.pricing.browser_price_reader import (
    _parse_offer_lines,
    build_filtered_url,
    resolve_cardmarket_url,
    supports_language_filter,
)
from app.pricing.models import CardmarketOffer


def test_parses_a_realistic_page_dump_into_offers() -> None:
    # Mirrors the real token sequence observed live on a Cardmarket product
    # page (seller rating, seller name, condition, [comment], price, qty),
    # with a language flag's accessible name inline as its own token, plus
    # unrelated summary-stat prices (e.g. "7-days average price") before the
    # real offer rows that must be ignored as noise.
    lines = [
        "Available items", "78", "From", "13,90 €",
        "7-days average price", "185,65 €",
        "159", "K", "CardGameCorner", "Italian", "PO", "13,90 €", "1",
        "66", "pokerina", "German", "PO", "Ask for more photos", "24,99 €", "1",
        "14", "K", "LevelUp-Wehavefun", "German", "GD", "front NM", "47,45 €", "1",
        "952", "M2workshop", "English", "NM", "59,90 €", "1",
    ]

    offers = _parse_offer_lines(lines)

    assert offers == [
        CardmarketOffer(
            seller="CardGameCorner",
            condition=Condition.POOR,
            language=Language.ITALIAN,
            price=13.90,
        ),
        CardmarketOffer(
            seller="pokerina", condition=Condition.POOR, language=Language.GERMAN, price=24.99
        ),
        CardmarketOffer(
            seller="LevelUp-Wehavefun",
            condition=Condition.GOOD,
            language=Language.GERMAN,
            price=47.45,
        ),
        CardmarketOffer(
            seller="M2workshop",
            condition=Condition.NEAR_MINT,
            language=Language.ENGLISH,
            price=59.90,
        ),
    ]


def test_mint_condition_code_is_mt_not_m() -> None:
    lines = ["1", "Seller", "German", "MT", "100,00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers == [
        CardmarketOffer(
            seller="Seller", condition=Condition.MINT, language=Language.GERMAN, price=100.0
        )
    ]


def test_unrecognised_language_flag_yields_none_but_keeps_the_offer() -> None:
    lines = ["1", "Seller", "Klingon", "NM", "10,00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers == [
        CardmarketOffer(seller="Seller", condition=Condition.NEAR_MINT, language=None, price=10.0)
    ]


def test_row_without_a_condition_badge_is_dropped_as_noise() -> None:
    lines = ["7-days average price", "185,65 €", "1-day average price", "404,70 €"]

    assert _parse_offer_lines(lines) == []


def test_thousands_separator_price_is_parsed_correctly() -> None:
    lines = ["1", "Seller", "German", "MT", "1.049,00 €", "1"]

    offers = _parse_offer_lines(lines)

    assert offers[0].price == 1049.0


def test_empty_input_returns_empty_list() -> None:
    assert _parse_offer_lines([]) == []


# --- build_filtered_url / supports_language_filter ------------------------ #
# Ids confirmed live by reading Cardmarket's own filter form inputs (not
# documented anywhere public) — see PROJECT_PROGRESS.md, Schritt 7 follow-up.


def test_supports_language_filter_true_for_western_languages() -> None:
    assert supports_language_filter(Language.GERMAN) is True
    assert supports_language_filter(Language.ENGLISH) is True


def test_supports_language_filter_false_for_asian_languages() -> None:
    # Japanese/Korean/Chinese printings are separate Cardmarket products with
    # their own URL, not a language filter on the same product page.
    assert supports_language_filter(Language.JAPANESE) is False
    assert supports_language_filter(Language.KOREAN) is False
    assert supports_language_filter(Language.CHINESE) is False


def test_build_filtered_url_with_no_filters_returns_base_url_unchanged() -> None:
    url = "https://www.cardmarket.com/de/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    assert build_filtered_url(url) == url


def test_build_filtered_url_language_only() -> None:
    url = build_filtered_url("https://cardmarket.com/x", language=Language.GERMAN)
    assert url == "https://cardmarket.com/x?language=3"


def test_build_filtered_url_condition_only() -> None:
    url = build_filtered_url("https://cardmarket.com/x", min_condition=Condition.GOOD)
    assert url == "https://cardmarket.com/x?minCondition=4"


def test_build_filtered_url_language_and_condition_combined() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x", language=Language.ENGLISH, min_condition=Condition.NEAR_MINT
    )
    assert url == "https://cardmarket.com/x?language=1&minCondition=2"


def test_build_filtered_url_unsupported_language_is_silently_ignored() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x", language=Language.JAPANESE, min_condition=Condition.GOOD
    )
    assert url == "https://cardmarket.com/x?minCondition=4"


def test_build_filtered_url_appends_to_an_already_queried_base_url() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x?utm_source=pokemontcgio", language=Language.GERMAN
    )
    assert url == "https://cardmarket.com/x?utm_source=pokemontcgio&language=3"


# --- build_filtered_url: signed / first_edition / altered -------------------- #
# Cardmarket's own extra[isSigned]/extra[isFirstEd]/extra[isAltered] filters
# (ids confirmed live from the filter form: 0=Egal, Y=Ja, N=Nein). Unlike
# language/condition, callers pass these as a definite True/False almost
# always -- a real card either is or isn't signed.


def test_build_filtered_url_signed_true_and_false() -> None:
    assert build_filtered_url("https://cardmarket.com/x", signed=True) == (
        "https://cardmarket.com/x?extra%5BisSigned%5D=Y"
    )
    assert build_filtered_url("https://cardmarket.com/x", signed=False) == (
        "https://cardmarket.com/x?extra%5BisSigned%5D=N"
    )


def test_build_filtered_url_first_edition_and_altered() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x", first_edition=True, altered=False
    )
    assert url == "https://cardmarket.com/x?extra%5BisFirstEd%5D=Y&extra%5BisAltered%5D=N"


def test_build_filtered_url_extras_unset_by_default() -> None:
    # None (unset) means "don't add this filter at all" -- distinct from
    # False ("Nein"), which does add it.
    assert build_filtered_url("https://cardmarket.com/x") == "https://cardmarket.com/x"


def test_build_filtered_url_combines_everything() -> None:
    url = build_filtered_url(
        "https://cardmarket.com/x",
        language=Language.GERMAN,
        min_condition=Condition.NEAR_MINT,
        signed=True,
        first_edition=False,
        altered=False,
    )
    assert url == (
        "https://cardmarket.com/x?language=3&minCondition=2"
        "&extra%5BisSigned%5D=Y&extra%5BisFirstEd%5D=N&extra%5BisAltered%5D=N"
    )


# --- resolve_cardmarket_url ------------------------------------------------ #
# pokemontcg.io's cardmarket_url is a tracking shortlink whose redirect target
# is fixed on their end -- query filters appended to the shortlink itself are
# silently dropped. Resolving to the real cardmarket.com URL first is what
# lets build_filtered_url's parameters actually take effect.


def _session_redirecting_to(final_url: str) -> MagicMock:
    response = MagicMock()
    response.url = final_url
    session = MagicMock()
    session.get.return_value = response
    return session


def test_resolve_cardmarket_url_follows_the_redirect() -> None:
    session = _session_redirecting_to(
        "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    )

    result = resolve_cardmarket_url(
        "https://prices.pokemontcg.io/cardmarket/skg-h32", session=session
    )

    assert result == "https://www.cardmarket.com/en/Pokemon/Products/Singles/Skyridge/Xatu-V1-SKH32"
    session.get.assert_called_once_with(
        "https://prices.pokemontcg.io/cardmarket/skg-h32", allow_redirects=True, timeout=10
    )


def test_resolve_cardmarket_url_falls_back_to_original_on_request_error() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")

    result = resolve_cardmarket_url("https://prices.pokemontcg.io/cardmarket/skg-h32", session=session)

    assert result == "https://prices.pokemontcg.io/cardmarket/skg-h32"


