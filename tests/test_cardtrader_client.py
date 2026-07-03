"""Tests for the CardTrader expansions client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.cardmarket.cardtrader_client import CardTraderClient, CardTraderClientError
from app.cardmarket.models import CardTraderExpansion

_MIXED_GAMES_PAYLOAD = [
    {"id": 1, "game_id": 1, "code": "gnt", "name": "Game Night"},
    {"id": 1492, "game_id": 5, "code": "skg", "name": "Skyridge"},
    {"id": 1500, "game_id": 5, "code": "base1", "name": "Base"},
]


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


def test_list_pokemon_expansions_filters_out_other_games() -> None:
    session = _session_returning(_MIXED_GAMES_PAYLOAD)
    client = CardTraderClient(jwt_token="token", session=session)

    expansions = client.list_pokemon_expansions()

    assert expansions == [
        CardTraderExpansion(id=1492, game_id=5, code="skg", name="Skyridge"),
        CardTraderExpansion(id=1500, game_id=5, code="base1", name="Base"),
    ]


def test_list_pokemon_expansions_sends_bearer_token() -> None:
    session = _session_returning(_MIXED_GAMES_PAYLOAD)
    client = CardTraderClient(jwt_token="token", session=session)

    client.list_pokemon_expansions()

    _, kwargs = session.get.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer token"}


def test_list_pokemon_expansions_caches_after_first_call() -> None:
    session = _session_returning(_MIXED_GAMES_PAYLOAD)
    client = CardTraderClient(jwt_token="token", session=session)

    client.list_pokemon_expansions()
    client.list_pokemon_expansions()

    assert session.get.call_count == 1


def test_list_pokemon_expansions_raises_client_error_on_request_exception() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    client = CardTraderClient(jwt_token="token", session=session)

    with pytest.raises(CardTraderClientError):
        client.list_pokemon_expansions()


def test_list_pokemon_expansions_raises_client_error_on_http_error_status() -> None:
    session = _session_returning([], status_code=500)
    client = CardTraderClient(jwt_token="token", session=session)

    with pytest.raises(CardTraderClientError):
        client.list_pokemon_expansions()
