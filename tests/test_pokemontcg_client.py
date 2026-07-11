"""Tests for the pokemontcg.io catalogue client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.catalog.models import CatalogCard, CatalogSet
from app.catalog.pokemontcg_client import PokemonTcgClient, PokemonTcgClientError, build_query

# -- build_query (pure, no network) ---------------------------------------- #


def test_build_query_name_only() -> None:
    assert build_query(name="xatu") == "name:xatu*"


def test_build_query_name_and_set() -> None:
    assert build_query(name="xatu", set_id="skg") == "name:xatu* set.id:skg"


def test_build_query_all_fields() -> None:
    assert (
        build_query(name="xatu", set_id="skg", number="H32")
        == "name:xatu* set.id:skg number:H32"
    )


def test_build_query_multi_word_name_becomes_and_combined_prefix_clauses() -> None:
    # Live-confirmed: pokemontcg.io's own stored `name` field literally uses
    # a hyphen for GX/EX-type suffixes ("Umbreon-GX"), not a space -- one
    # quoted exact phrase with a space unreliably matches that hyphenated
    # token. Independent per-word prefix wildcards, AND-combined, sidestep
    # this (and as a bonus also find combo-name cards a single phrase never
    # would, e.g. "Umbreon & Darkrai-GX").
    assert build_query(name="team rocket") == "name:team* name:rocket*"


def test_build_query_escapes_inner_quotes() -> None:
    assert build_query(name='foo"bar') == 'name:foo\\"bar*'


def test_build_query_empty_when_no_fields() -> None:
    assert build_query() == ""


def test_build_query_ignores_blank_fields() -> None:
    assert build_query(name="  ", set_id=None, number="") == ""


# -- PokemonTcgClient.search / list_sets (mocked HTTP) ---------------------- #


def _raw_card(**overrides) -> dict:
    base = {
        "id": "skg-h32",
        "name": "Xatu",
        "number": "H32",
        "rarity": "Rare Holo",
        "set": {"id": "skg", "name": "Skyridge"},
        "images": {"small": "small.png", "large": "large.png"},
    }
    base.update(overrides)
    return base


def _session_returning(payload, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.raise_for_status.side_effect = (
        None if status_code < 400 else requests.HTTPError(response=response)
    )
    session = MagicMock()
    session.get.return_value = response
    return session


def test_search_parses_results_into_catalog_cards() -> None:
    session = _session_returning({"data": [_raw_card()]})
    client = PokemonTcgClient(api_key=None, session=session)

    results = client.search(name="xatu", set_id="skg")

    assert results == [
        CatalogCard(
            external_id="skg-h32",
            name="Xatu",
            set_name="Skyridge",
            set_code="skg",
            card_number="H32",
            rarity="Rare Holo",
            image_small_url="small.png",
            image_large_url="large.png",
        )
    ]


def test_search_corrects_ex_series_set_name() -> None:
    # Real, live-confirmed bug: a card from this set searched/added via the
    # catalogue showed set_name "Sandstorm" (pokemontcg.io's own, prefix-
    # dropped name), while a card added manually via a Cardmarket link for
    # the very same set showed "EX Sandstorm" -- making them look like two
    # different sets in the Karten table. See _EX_SERIES_SET_NAMES's docs.
    session = _session_returning(
        {"data": [_raw_card(set={"id": "ex2", "name": "Sandstorm"})]}
    )
    client = PokemonTcgClient(session=session)

    results = client.search(name="cacturne")

    assert results[0].set_name == "EX Sandstorm"
    assert results[0].set_code == "ex2"


def test_search_parses_cardmarket_url_when_present() -> None:
    session = _session_returning(
        {"data": [_raw_card(cardmarket={"url": "https://prices.pokemontcg.io/cardmarket/skg-h32"})]}
    )
    client = PokemonTcgClient(session=session)

    results = client.search(name="xatu")

    assert results[0].cardmarket_url == "https://prices.pokemontcg.io/cardmarket/skg-h32"


def test_search_passes_through_cardmarket_url_even_for_base_set() -> None:
    # The client itself is a faithful passthrough of whatever pokemontcg.io
    # says, even for a set with known Cardmarket variant ambiguity (see
    # has_ambiguous_cardmarket_variants) -- deciding whether that link can be
    # trusted is the consumer's job (CatalogSearchService/PriceService), not
    # this low-level client's.
    session = _session_returning(
        {
            "data": [
                _raw_card(
                    set={"id": "base1", "name": "Base"},
                    cardmarket={"url": "https://prices.pokemontcg.io/cardmarket/base1-4"},
                )
            ]
        }
    )
    client = PokemonTcgClient(session=session)

    results = client.search(name="charizard", set_id="base1")

    assert results[0].cardmarket_url == "https://prices.pokemontcg.io/cardmarket/base1-4"


def test_has_ambiguous_cardmarket_variants() -> None:
    from app.catalog.pokemontcg_client import has_ambiguous_cardmarket_variants

    assert has_ambiguous_cardmarket_variants("base1") is True
    assert has_ambiguous_cardmarket_variants("skg") is False


def test_search_sends_api_key_header_when_configured() -> None:
    session = _session_returning({"data": []})
    client = PokemonTcgClient(api_key="secret-key", session=session)

    client.search(name="xatu")

    _, kwargs = session.get.call_args
    assert kwargs["headers"] == {"X-Api-Key": "secret-key"}


def test_search_without_api_key_sends_no_header() -> None:
    session = _session_returning({"data": []})
    client = PokemonTcgClient(api_key=None, session=session)

    client.search(name="xatu")

    _, kwargs = session.get.call_args
    assert kwargs["headers"] == {}


def test_search_returns_empty_list_without_any_filters() -> None:
    session = MagicMock()
    client = PokemonTcgClient(session=session)

    assert client.search() == []
    session.get.assert_not_called()


def test_search_raises_client_error_on_request_exception() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    client = PokemonTcgClient(session=session, retry_delay=0)

    with pytest.raises(PokemonTcgClientError):
        client.search(name="xatu")


def test_search_retries_once_on_timeout_and_succeeds() -> None:
    """Real incident: pokemontcg.io itself measured live taking >30s to

    respond during a brief slow period, past this client's own timeout --
    a single retry should give a second chance instead of failing outright.
    """
    success_response = MagicMock()
    success_response.json.return_value = {"data": []}
    success_response.raise_for_status.return_value = None
    session = MagicMock()
    session.get.side_effect = [requests.Timeout("slow"), success_response]
    client = PokemonTcgClient(session=session, retry_delay=0)

    results = client.search(name="xatu")

    assert results == []
    assert session.get.call_count == 2


def test_search_raises_after_exhausting_retries_on_persistent_timeout() -> None:
    session = MagicMock()
    session.get.side_effect = requests.Timeout("slow")
    client = PokemonTcgClient(session=session, retry_delay=0)

    with pytest.raises(PokemonTcgClientError):
        client.search(name="xatu")

    assert session.get.call_count == 2


def test_search_raises_client_error_on_http_error_status() -> None:
    session = _session_returning({}, status_code=500)
    client = PokemonTcgClient(session=session)

    with pytest.raises(PokemonTcgClientError):
        client.search(name="xatu")


def test_list_sets_parses_results_into_catalog_sets() -> None:
    session = _session_returning(
        {"data": [{"id": "base1", "name": "Base"}, {"id": "base4", "name": "Base Set 2"}]}
    )
    client = PokemonTcgClient(session=session)

    assert client.list_sets() == [
        CatalogSet(id="base1", name="Base"),
        CatalogSet(id="base4", name="Base Set 2"),
    ]


def test_list_sets_corrects_ex_series_names() -> None:
    # pokemontcg.io's own /sets response drops the "EX " era prefix for the
    # whole EX Series (live-confirmed for all 16, "ex1" through "ex16") --
    # see _EX_SERIES_SET_NAMES's own docs.
    session = _session_returning({"data": [{"id": "ex2", "name": "Sandstorm"}]})
    client = PokemonTcgClient(session=session)

    assert client.list_sets() == [CatalogSet(id="ex2", name="EX Sandstorm")]


def test_list_sets_caches_after_first_call() -> None:
    session = _session_returning({"data": [{"id": "base1", "name": "Base"}]})
    client = PokemonTcgClient(session=session)

    client.list_sets()
    client.list_sets()

    assert session.get.call_count == 1


def test_list_sets_raises_client_error_on_request_exception() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    client = PokemonTcgClient(session=session, retry_delay=0)

    with pytest.raises(PokemonTcgClientError):
        client.list_sets()


# -- PokemonTcgClient.resolve_set_code (mocked HTTP) ------------------------ #


def _sets_client() -> PokemonTcgClient:
    session = _session_returning(
        {
            "data": [
                {"id": "ex2", "name": "Sandstorm"},
                {"id": "base1", "name": "Base"},
                {"id": "neo1", "name": "Genesis"},
            ]
        }
    )
    return PokemonTcgClient(session=session)


def test_resolve_set_code_exact_match() -> None:
    assert _sets_client().resolve_set_code("Base") == "base1"


def test_resolve_set_code_matches_case_insensitively() -> None:
    assert _sets_client().resolve_set_code("BASE") == "base1"


def test_resolve_set_code_ex_series_name_matches_directly_via_correction() -> None:
    # Real, live-confirmed case: Cardmarket's own page title calls this set
    # "EX Sandstorm", but pokemontcg.io's raw API response just says
    # "Sandstorm" (id "ex2") -- _corrected_set_name (applied inside
    # list_sets, see its own docs/_EX_SERIES_SET_NAMES) already restores the
    # "EX " prefix pokemontcg.io drops for its whole EX Series, so this is
    # now an *exact* match, not the "ends with" fallback below.
    assert _sets_client().resolve_set_code("EX Sandstorm") == "ex2"


def test_resolve_set_code_drops_a_leading_era_prefix_as_a_fallback() -> None:
    # A set not covered by the explicit EX Series correction table still
    # falls back to a "given name ends with <catalogue name>" match, e.g. a
    # dropped "Neo " era prefix.
    assert _sets_client().resolve_set_code("Neo Genesis") == "neo1"


def test_resolve_set_code_blank_when_nothing_matches() -> None:
    assert _sets_client().resolve_set_code("Totally Unknown Set") == ""


def test_resolve_set_code_blank_for_blank_input() -> None:
    assert _sets_client().resolve_set_code("") == ""


# -- PokemonTcgClient.get_card_by_id (mocked HTTP) -------------------------- #


def test_get_card_by_id_returns_parsed_card() -> None:
    session = _session_returning({"data": _raw_card(id="ecard3-H32")})
    client = PokemonTcgClient(session=session)

    card = client.get_card_by_id("ecard3-H32")

    assert card is not None
    assert card.external_id == "ecard3-H32"


def test_get_card_by_id_returns_none_on_404() -> None:
    session = _session_returning({}, status_code=404)
    client = PokemonTcgClient(session=session)

    assert client.get_card_by_id("does-not-exist") is None
    session.get.return_value.raise_for_status.assert_not_called()


def test_get_card_by_id_raises_client_error_on_request_exception() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    client = PokemonTcgClient(session=session, retry_delay=0)

    with pytest.raises(PokemonTcgClientError):
        client.get_card_by_id("ecard3-H32")


def test_get_card_by_id_raises_client_error_on_http_error_status() -> None:
    session = _session_returning({}, status_code=500)
    client = PokemonTcgClient(session=session)

    with pytest.raises(PokemonTcgClientError):
        client.get_card_by_id("ecard3-H32")
