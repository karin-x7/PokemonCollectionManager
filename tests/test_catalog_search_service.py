"""Tests for CatalogSearchService's tolerant multi-field search."""

from __future__ import annotations

import pytest

from app.catalog.models import CatalogCard, CatalogSet
from app.catalog.pokemontcg_client import PokemonTcgClientError
from app.services.catalog_search_service import CatalogSearchService
from app.services.exceptions import CatalogSearchError

_SETS = [
    CatalogSet(id="skg", name="Skyridge"),
    CatalogSet(id="base1", name="Base"),
    CatalogSet(id="teamrocket", name="Team Rocket"),
]

_XATU = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)


class FakePokemonTcgClient:
    """Records every call made to it and returns pre-programmed results."""

    def __init__(
        self,
        responses: list[list[CatalogCard]] | None = None,
        sets: list[CatalogSet] | None = _SETS,
    ) -> None:
        self.calls: list[dict] = []
        self._responses = list(responses) if responses is not None else None
        self._default_result = [_XATU]
        self._search_error: Exception | None = None
        self._sets = sets
        self._sets_error: Exception | None = None

    def raise_on_next_calls(self, error: Exception) -> None:
        self._search_error = error

    def raise_on_list_sets(self, error: Exception) -> None:
        self._sets_error = error

    def list_sets(self) -> list[CatalogSet]:
        if self._sets_error is not None:
            raise self._sets_error
        return self._sets

    def search(self, name=None, set_id=None, number=None, page_size=25):
        self.calls.append({"name": name, "set_id": set_id, "number": number})
        if self._search_error is not None:
            raise self._search_error
        if self._responses is not None:
            return self._responses.pop(0) if self._responses else []
        return self._default_result


def test_empty_query_returns_no_results_and_makes_no_calls() -> None:
    pokemontcg = FakePokemonTcgClient()
    service = CatalogSearchService(pokemontcg)

    assert service.search("   ") == []
    assert pokemontcg.calls == []


def test_extracts_number_token_from_query() -> None:
    pokemontcg = FakePokemonTcgClient(sets=[])
    service = CatalogSearchService(pokemontcg)

    service.search("xatu H32")

    assert pokemontcg.calls == [{"name": "xatu", "set_id": None, "number": "H32"}]


def test_resolves_fuzzy_set_name_against_pokemontcg_sets() -> None:
    pokemontcg = FakePokemonTcgClient()
    service = CatalogSearchService(pokemontcg)

    # "skyrige" is a typo for "Skyridge".
    service.search("xatu skyrige")

    assert pokemontcg.calls == [{"name": "xatu", "set_id": "skg", "number": None}]


def test_resolves_multi_word_set_name() -> None:
    pokemontcg = FakePokemonTcgClient()
    service = CatalogSearchService(pokemontcg)

    service.search("dark raichu team rocket")

    assert pokemontcg.calls == [{"name": "dark raichu", "set_id": "teamrocket", "number": None}]


def test_resolves_partial_set_name_prefix() -> None:
    # "base" is a partial term for the official pokemontcg.io set name
    # "Base" — this is the "tolerant search over ... partial terms" case.
    pokemontcg = FakePokemonTcgClient()
    service = CatalogSearchService(pokemontcg)

    service.search("charizard base")

    assert pokemontcg.calls == [{"name": "charizard", "set_id": "base1", "number": None}]


def test_reprint_sets_are_resolved_by_id_not_name_to_avoid_ambiguity() -> None:
    # "Base" and "Base Set 2" are two different, real pokemontcg.io sets
    # (original 1999 printing vs. the 2000 reprint). Filtering by the exact
    # set.id (not a set.name substring/prefix match) is what keeps a query
    # for "base" from also matching the "Base Set 2" reprint.
    sets_with_reprint = _SETS + [CatalogSet(id="base4", name="Base Set 2")]
    pokemontcg = FakePokemonTcgClient(sets=sets_with_reprint)
    service = CatalogSearchService(pokemontcg)

    service.search("charizard base 4")

    assert pokemontcg.calls == [{"name": "charizard", "set_id": "base1", "number": "4"}]


def test_loosens_query_when_structured_search_finds_nothing() -> None:
    # First call (name+set+number) empty, second (name+set) empty, third
    # (name only) finally returns a result.
    pokemontcg = FakePokemonTcgClient(responses=[[], [], [_XATU]])
    service = CatalogSearchService(pokemontcg)

    results = service.search("xatu skyrige H32")

    assert results == [_XATU]
    assert pokemontcg.calls == [
        {"name": "xatu", "set_id": "skg", "number": "H32"},
        {"name": "xatu", "set_id": "skg", "number": None},
        {"name": "xatu", "set_id": None, "number": None},
    ]


def test_set_resolution_outage_degrades_to_name_only_search() -> None:
    pokemontcg = FakePokemonTcgClient()
    pokemontcg.raise_on_list_sets(PokemonTcgClientError("down"))
    service = CatalogSearchService(pokemontcg)

    service.search("xatu skyridge")

    assert pokemontcg.calls == [{"name": "xatu skyridge", "set_id": None, "number": None}]


def test_pokemontcg_search_error_is_translated_to_catalog_search_error() -> None:
    pokemontcg = FakePokemonTcgClient()
    pokemontcg.raise_on_next_calls(PokemonTcgClientError("down"))
    service = CatalogSearchService(pokemontcg)

    with pytest.raises(CatalogSearchError):
        service.search("xatu")


def test_results_capped_at_max_results() -> None:
    many = [_XATU] * 30
    pokemontcg = FakePokemonTcgClient(responses=[many], sets=[])
    service = CatalogSearchService(pokemontcg, max_results=25)

    assert len(service.search("xatu")) == 25
