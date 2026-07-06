"""Tests for the tcgdex.dev localized-designation lookup.

Names/labels only -- this module must never be used for pricing (see its
own module docstring for why). Uses a fake session keyed by URL so each
test can script the exact sequence of English/target-locale/set lookups
tcgdex.dev is queried with, without any real network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.catalog.tcgdex_designation_lookup import (
    TcgdexDesignationLookupError,
    find_localized_designation,
)
from app.models.enums import Language


class FakeSession:
    """Returns a queued JSON payload (or 404) for each exact URL, in order

    of first match -- payloads are keyed by the path suffix after the base
    URL so tests read naturally."""

    def __init__(self, responses: dict[str, dict | None]) -> None:
        self._responses = responses
        self.requested_paths: list[str] = []

    def get(self, url: str, timeout: float):
        path = url.split("api.tcgdex.net/v2", 1)[1]
        self.requested_paths.append(path)
        response = MagicMock()
        if path not in self._responses or self._responses[path] is None:
            response.status_code = 404
            return response
        response.status_code = 200
        response.json.return_value = self._responses[path]
        response.raise_for_status.return_value = None
        return response


_ENGLISH_HO_OH = {
    "id": "neo3-7",
    "name": "Ho-oh",
    "localId": "7",
    "dexId": [250],
    "set": {"id": "neo3", "name": "Neo Revelation"},
}
_ENGLISH_SET = {"id": "neo3", "name": "Neo Revelation", "releaseDate": "2001-09-21"}

_JA_CANDIDATES = [
    {"id": "SVLS-003", "name": "Hououou-modern"},
    {"id": "neo3-011", "name": "ho-oh"},
    {"id": "PCG4-020", "name": "ho-oh ex"},
]
_JA_NEO3_DETAIL = {
    "id": "neo3-011",
    "name": "ho-oh",
    "localId": "011",
    "set": {"id": "neo3", "name": "めざめる伝説"},
}
_JA_NEO3_SET = {"id": "neo3", "name": "めざめる伝説", "releaseDate": "2000-11-23"}
_JA_SVLS_DETAIL = {
    "id": "SVLS-003",
    "name": "Hououou-modern",
    "localId": "003",
    "set": {"id": "SVLS", "name": "Modern Starter"},
}
_JA_SVLS_SET = {"id": "SVLS", "name": "Modern Starter", "releaseDate": "2024-08-30"}
_JA_PCG4_DETAIL = {
    "id": "PCG4-020",
    "name": "ho-oh ex",
    "localId": "020",
    "set": {"id": "PCG4", "name": "Gold Sky Silver Sea"},
}
_JA_PCG4_SET = {"id": "PCG4", "name": "Gold Sky Silver Sea", "releaseDate": "2005-04-08"}


def _real_ho_oh_session() -> FakeSession:
    return FakeSession(
        {
            "/en/cards/neo3-7": _ENGLISH_HO_OH,
            "/en/sets/neo3": _ENGLISH_SET,
            "/ja/cards?dexId=250&category=Pokemon": _JA_CANDIDATES,
            "/ja/cards/neo3-011": _JA_NEO3_DETAIL,
            "/ja/sets/neo3": _JA_NEO3_SET,
            "/ja/cards/SVLS-003": _JA_SVLS_DETAIL,
            "/ja/sets/SVLS": _JA_SVLS_SET,
            "/ja/cards/PCG4-020": _JA_PCG4_DETAIL,
            "/ja/sets/PCG4": _JA_PCG4_SET,
        }
    )


def test_picks_the_candidate_released_closest_before_the_english_set() -> None:
    """Real case this was built for: Neo Revelation (2001-09-21, EN) sourced

    from Awakening Legends (2000-11-23, JA) -- not the much later Modern
    Starter or Gold Sky Silver Sea reprints of the same species.
    """
    session = _real_ho_oh_session()

    result = find_localized_designation("neo3-7", Language.JAPANESE, session=session)

    assert result is not None
    assert result.set_id == "neo3"
    assert result.set_name == "めざめる伝説"
    assert result.local_id == "011"


def test_implausibly_distant_candidate_is_rejected_instead_of_guessed() -> None:
    """Real false positive this was built for: Umbreon VMAX (Evolving

    Skies, EN released 2021) has no genuine Japanese Sword & Shield-era
    entry in tcgdex at all -- its only same-species "ja" candidate was a
    2005 reprint, 16 years off. Must return ``None``, not that guess.
    """
    english_umbreon = {
        "id": "swsh7-215",
        "name": "Umbreon VMAX",
        "localId": "215",
        "dexId": [197],
        "set": {"id": "swsh7", "name": "Evolving Skies"},
    }
    english_set = {"id": "swsh7", "name": "Evolving Skies", "releaseDate": "2021-08-27"}
    ja_candidates = [{"id": "PCG6-069", "name": "Umbreon (Delta Species)"}]
    ja_detail = {
        "id": "PCG6-069",
        "name": "Umbreon (Delta Species)",
        "localId": "069",
        "set": {"id": "PCG6", "name": "Holon Research Tower"},
    }
    ja_set = {"id": "PCG6", "name": "Holon Research Tower", "releaseDate": "2005-10-28"}
    session = FakeSession(
        {
            "/en/cards/swsh7-215": english_umbreon,
            "/en/sets/swsh7": english_set,
            "/ja/cards?dexId=197&category=Pokemon": ja_candidates,
            "/ja/cards/PCG6-069": ja_detail,
            "/ja/sets/PCG6": ja_set,
        }
    )

    result = find_localized_designation("swsh7-215", Language.JAPANESE, session=session)

    assert result is None


def test_unsupported_language_returns_none_without_any_request() -> None:
    session = FakeSession({})

    result = find_localized_designation("neo3-7", Language.ENGLISH, session=session)

    assert result is None
    assert session.requested_paths == []


def test_missing_english_card_returns_none() -> None:
    session = FakeSession({"/en/cards/unknown-1": None})

    assert find_localized_designation("unknown-1", Language.JAPANESE, session=session) is None


def test_english_card_without_dex_id_returns_none() -> None:
    session = FakeSession(
        {"/en/cards/trainer-1": {"id": "trainer-1", "name": "Poke Ball", "dexId": []}}
    )

    assert find_localized_designation("trainer-1", Language.JAPANESE, session=session) is None


def test_no_candidates_in_target_locale_returns_none() -> None:
    session = FakeSession(
        {
            "/en/cards/neo3-7": _ENGLISH_HO_OH,
            "/en/sets/neo3": _ENGLISH_SET,
            "/ja/cards?dexId=250&category=Pokemon": [],
        }
    )

    assert find_localized_designation("neo3-7", Language.JAPANESE, session=session) is None


def test_korean_returns_none_when_tcgdex_has_no_coverage() -> None:
    """Confirmed live: tcgdex's Korean/Chinese coverage is essentially

    empty for even common species -- this must degrade to "no suggestion",
    not an error."""
    session = FakeSession(
        {
            "/en/cards/neo3-7": _ENGLISH_HO_OH,
            "/en/sets/neo3": _ENGLISH_SET,
            "/ko/cards?dexId=250&category=Pokemon": [],
        }
    )

    assert find_localized_designation("neo3-7", Language.KOREAN, session=session) is None


def test_network_error_raises_lookup_error() -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")

    with pytest.raises(TcgdexDesignationLookupError):
        find_localized_designation("neo3-7", Language.JAPANESE, session=session)
