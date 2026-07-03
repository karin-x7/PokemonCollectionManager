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


def test_build_query_multi_word_name_becomes_exact_phrase_without_wildcard() -> None:
    # A quoted phrase combined with a trailing wildcard is rejected by the
    # API with a 400 (measured live), so multi-word terms drop the wildcard.
    assert build_query(name="team rocket") == 'name:"team rocket"'


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


def test_search_parses_cardmarket_url_when_present() -> None:
    session = _session_returning(
        {"data": [_raw_card(cardmarket={"url": "https://prices.pokemontcg.io/cardmarket/skg-h32"})]}
    )
    client = PokemonTcgClient(session=session)

    results = client.search(name="xatu")

    assert results[0].cardmarket_url == "https://prices.pokemontcg.io/cardmarket/skg-h32"


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
    client = PokemonTcgClient(session=session)

    with pytest.raises(PokemonTcgClientError):
        client.search(name="xatu")


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


def test_list_sets_caches_after_first_call() -> None:
    session = _session_returning({"data": [{"id": "base1", "name": "Base"}]})
    client = PokemonTcgClient(session=session)

    client.list_sets()
    client.list_sets()

    assert session.get.call_count == 1


def test_list_sets_raises_client_error_on_request_exception() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    client = PokemonTcgClient(session=session)

    with pytest.raises(PokemonTcgClientError):
        client.list_sets()


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
    client = PokemonTcgClient(session=session)

    with pytest.raises(PokemonTcgClientError):
        client.get_card_by_id("ecard3-H32")


def test_get_card_by_id_raises_client_error_on_http_error_status() -> None:
    session = _session_returning({}, status_code=500)
    client = PokemonTcgClient(session=session)

    with pytest.raises(PokemonTcgClientError):
        client.get_card_by_id("ecard3-H32")
