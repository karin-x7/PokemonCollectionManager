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


def test_strips_holo_from_the_name_query() -> None:
    """Real bug: "xatu skyridge holo" found nothing at all, while "xatu

    skyridge" worked -- pokemontcg.io's own name field never contains the
    word "holo", so a name search including it as an exact phrase always
    failed. "holo" describes the print finish, not the card's name, and is
    now stripped before the query is ever sent.
    """
    pokemontcg = FakePokemonTcgClient()
    service = CatalogSearchService(pokemontcg)

    service.search("xatu skyridge holo")

    assert pokemontcg.calls == [{"name": "xatu", "set_id": "skg", "number": None}]


def test_strips_reverse_holo_phrase_from_the_name_query() -> None:
    pokemontcg = FakePokemonTcgClient(sets=[])
    service = CatalogSearchService(pokemontcg)

    service.search("xatu reverse holo")

    assert pokemontcg.calls == [{"name": "xatu", "set_id": None, "number": None}]


def test_strips_1st_edition_phrase_from_the_name_query() -> None:
    pokemontcg = FakePokemonTcgClient(sets=[])
    service = CatalogSearchService(pokemontcg)

    service.search("charizard 1st edition")

    assert pokemontcg.calls == [{"name": "charizard", "set_id": None, "number": None}]


def test_variant_words_do_not_strip_ex_gx_vmax_from_the_card_name() -> None:
    """These describe the card's actual subtype/identity (a distinct,

    differently-named card), not a print finish -- must never be stripped.
    """
    pokemontcg = FakePokemonTcgClient(sets=[])
    service = CatalogSearchService(pokemontcg)

    service.search("umbreon vmax")

    assert pokemontcg.calls == [{"name": "umbreon vmax", "set_id": None, "number": None}]


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


def test_foreign_language_name_is_translated_when_direct_search_finds_nothing(
    monkeypatch,
) -> None:
    blastoise = CatalogCard(
        external_id="base1-2",
        name="Blastoise",
        set_name="Base",
        set_code="base1",
        card_number="2",
        rarity="Rare Holo",
        image_small_url=None,
        image_large_url=None,
    )
    # First call (the raw "turtok" name search) finds nothing; the second
    # (after translation to "Blastoise") succeeds.
    pokemontcg = FakePokemonTcgClient(responses=[[], [blastoise]], sets=[])
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english",
        lambda term: "Blastoise" if term.casefold() == "turtok" else None,
    )
    service = CatalogSearchService(pokemontcg)

    results = service.search("turtok")

    assert results == [blastoise]
    assert pokemontcg.calls == [
        {"name": "turtok", "set_id": None, "number": None},
        {"name": "Blastoise", "set_id": None, "number": None},
    ]


def test_foreign_language_name_with_card_type_suffix_is_translated(monkeypatch) -> None:
    """Real bug: "Blitza VMAX" (German Jolteon VMAX) returned nothing at

    all -- translating the *whole* two-word query collapses to
    "blitzavmax", which was never a key in the translation table (only the
    bare species name "blitza" is). The suffix ("VMAX") must be split off,
    the species name translated on its own, then the suffix reattached.
    """
    jolteon_vmax = CatalogCard(
        external_id="swsh1-40",
        name="Jolteon VMAX",
        set_name="Sword & Shield",
        set_code="swsh1",
        card_number="40",
        rarity="Rare Holo VMAX",
        image_small_url=None,
        image_large_url=None,
    )
    pokemontcg = FakePokemonTcgClient(responses=[[], [jolteon_vmax]], sets=[])
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english",
        lambda term: "Jolteon" if term.casefold() == "blitza" else None,
    )
    service = CatalogSearchService(pokemontcg)

    results = service.search("Blitza VMAX")

    assert results == [jolteon_vmax]
    assert pokemontcg.calls == [
        {"name": "Blitza VMAX", "set_id": None, "number": None},
        {"name": "Jolteon VMAX", "set_id": None, "number": None},
    ]


def test_shrinking_prefix_search_finds_a_hyphenated_name(monkeypatch) -> None:
    ho_oh = CatalogCard(
        external_id="skg-h1",
        name="Ho-Oh",
        set_name="Skyridge",
        set_code="skg",
        card_number="H1",
        rarity="Rare Holo",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", lambda term: None
    )
    # Direct "hooh" search finds nothing; the shrunk "hoo" prefix does.
    pokemontcg = FakePokemonTcgClient(responses=[[], [ho_oh]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("hooh")

    assert results == [ho_oh]
    assert pokemontcg.calls[-1] == {"name": "hoo", "set_id": None, "number": None}


def test_shrinking_prefix_search_filters_out_unrelated_names(monkeypatch) -> None:
    ho_oh = CatalogCard(
        external_id="skg-h1",
        name="Ho-Oh",
        set_name="Skyridge",
        set_code="skg",
        card_number="H1",
        rarity="Rare Holo",
        image_small_url=None,
        image_large_url=None,
    )
    hoothoot = CatalogCard(
        external_id="skg-h2",
        name="Hoothoot",
        set_name="Skyridge",
        set_code="skg",
        card_number="H2",
        rarity="Common",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", lambda term: None
    )
    # The short "hoo" prefix legitimately also matches "Hoothoot" server-side
    # -- the client-side normalised filter must drop it since "hooh" isn't
    # contained in "hoothoot".
    pokemontcg = FakePokemonTcgClient(responses=[[], [ho_oh, hoothoot]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("hooh")

    assert results == [ho_oh]


def test_shrinking_prefix_search_tries_individual_words_not_just_the_full_prefix(
    monkeypatch,
) -> None:
    # Real, live-confirmed bug: pokemontcg.io's own search never folds
    # accents for *any* accent-free prefix of the whole collapsed name
    # ("pokepad", "poke", ...), so "poke pad"/"pokepad" found nothing at
    # all for "Poké Pad" -- but a plain "pad*" prefix query (this card's
    # own second word, which has no accent) does find it, since
    # pokemontcg.io's wildcard prefix match checks every word in a
    # multi-word name field, not just the first.
    poke_pad = CatalogCard(
        external_id="me3-113",
        name="Poké Pad",
        set_name="Perfect Order",
        set_code="me3",
        card_number="POR113",
        rarity="Uncommon",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", lambda term: None
    )
    # Calls in order: exact "poke pad", then "pokepad"/"pokepa"/"poke"/"pok"
    # (all still accent-free prefixes of the collapsed full name, all find
    # nothing), then finally "pad" alone, which does.
    pokemontcg = FakePokemonTcgClient(responses=[[], [], [], [], [], [poke_pad]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("poke pad")

    assert results == [poke_pad]
    assert pokemontcg.calls[-1] == {"name": "pad", "set_id": None, "number": None}


def test_foreign_trainer_card_name_is_translated_via_tcgdex_when_all_else_fails(
    monkeypatch,
) -> None:
    """Trainer/Item/Stadium card names have no PokeAPI equivalent at all (no

    species, no Pokédex number) -- ``translate_to_english`` never knows them,
    so this live tcgdex.dev tier is the only one that can resolve them.
    Tried right after the species-translation tier, *before* the shrinking-
    prefix loop: a genuinely foreign name could never match an English
    prefix there anyway, so only 2 pokemontcg.io calls are needed here (the
    initial exact search, then the tcgdex-translated retry) -- not the
    shrinking-prefix loop's several extra ones.
    """
    lillies_determination = CatalogCard(
        external_id="me1-184",
        name="Lillie's Determination",
        set_name="Mega Evolution",
        set_code="me1",
        card_number="184",
        rarity="Uncommon",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name",
        lambda term: "Lillie's Determination" if term == "Entschlossenheit" else None,
    )
    pokemontcg = FakePokemonTcgClient(responses=[[], [lillies_determination]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("Entschlossenheit")

    assert results == [lillies_determination]
    assert pokemontcg.calls == [
        {"name": "Entschlossenheit", "set_id": None, "number": None},
        {"name": "Lillie's Determination", "set_id": None, "number": None},
    ]


def test_shrinking_prefix_tier_is_skipped_once_tcgdex_translation_already_succeeded(
    monkeypatch,
) -> None:
    lillies_determination = CatalogCard(
        external_id="me1-184",
        name="Lillie's Determination",
        set_name="Mega Evolution",
        set_code="me1",
        card_number="184",
        rarity="Uncommon",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name",
        lambda term: "Lillie's Determination",
    )
    pokemontcg = FakePokemonTcgClient(responses=[[], [lillies_determination]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("Entschlossenheit")

    assert results == [lillies_determination]
    # Only 2 calls -- if the shrinking-prefix loop had also run, there would
    # be several more before this one.
    assert pokemontcg.calls == [
        {"name": "Entschlossenheit", "set_id": None, "number": None},
        {"name": "Lillie's Determination", "set_id": None, "number": None},
    ]


def test_tcgdex_translation_tier_is_skipped_once_species_translation_already_succeeded(
    monkeypatch,
) -> None:
    blastoise = CatalogCard(
        external_id="base1-2",
        name="Blastoise",
        set_name="Base",
        set_code="base1",
        card_number="2",
        rarity="Rare Holo",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english",
        lambda term: "Blastoise" if term.casefold() == "turtok" else None,
    )

    def _fail_if_called(term):
        raise AssertionError(
            "tcgdex tier must not run once the species-translation tier already succeeded"
        )

    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", _fail_if_called
    )
    pokemontcg = FakePokemonTcgClient(responses=[[], [blastoise]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("turtok")

    assert results == [blastoise]


def test_no_tcgdex_translation_found_leaves_results_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", lambda term: None
    )
    pokemontcg = FakePokemonTcgClient(responses=[[], [], [], [], []], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("Entschlossenheit")

    assert results == []


def test_symbol_synonym_resolves_a_delta_species_card(monkeypatch) -> None:
    # Real, live-confirmed case: pokemontcg.io stores this card's name as
    # "Rayquaza δ" -- the literal symbol, never the plain word "Delta".
    rayquaza_delta = CatalogCard(
        external_id="ex12-97",
        name="Rayquaza δ",
        set_name="Dragon Frontiers",
        set_code="ex12",
        card_number="97",
        rarity="Rare Holo",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english", lambda term: None
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", lambda term: None
    )
    # Direct "Rayquaza Delta" search finds nothing; substituting the symbol
    # ("Rayquaza δ") does.
    pokemontcg = FakePokemonTcgClient(responses=[[], [rayquaza_delta]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("Rayquaza Delta")

    assert results == [rayquaza_delta]
    assert pokemontcg.calls == [
        {"name": "Rayquaza Delta", "set_id": None, "number": None},
        {"name": "Rayquaza δ", "set_id": None, "number": None},
    ]


def test_translated_candidate_gets_shrinking_prefix_loosening_too(monkeypatch) -> None:
    """Real, live-confirmed cascade gap: "Nachtara GX" (German Umbreon-GX)

    translates fine to "Umbreon GX", but pokemontcg.io stores the name with
    a hyphen ("Umbreon-GX") -- the direct translated-candidate search still
    fails on its own. Before this fix, only the original, untranslated
    "Nachtara GX" ever got the shrinking-prefix loosening applied to it,
    which can never match an English-only catalogue no matter how much it's
    shortened. The translated candidate must get the same loosening.
    """
    umbreon_gx = CatalogCard(
        external_id="skg-h32",
        name="Umbreon-GX",
        set_name="Hidden Fates",
        set_code="sm115",
        card_number="SV65",
        rarity="Rare Secret",
        image_small_url=None,
        image_large_url=None,
    )
    monkeypatch.setattr(
        "app.catalog.name_translation.translate_to_english",
        lambda term: "Umbreon" if term.casefold() == "nachtara" else None,
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.translate_foreign_card_name", lambda term: None
    )
    # First call (raw "Nachtara GX") empty, second (translated "Umbreon GX")
    # also empty, third (its own shrunk "UmbreonGX" prefix) finally succeeds.
    pokemontcg = FakePokemonTcgClient(responses=[[], [], [umbreon_gx]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("Nachtara GX")

    assert results == [umbreon_gx]
    assert pokemontcg.calls == [
        {"name": "Nachtara GX", "set_id": None, "number": None},
        {"name": "Umbreon GX", "set_id": None, "number": None},
        {"name": "UmbreonGX", "set_id": None, "number": None},
    ]


# --- Base Set Normal/Shadowless variant splitting --------------------------- #

_CHARIZARD_BASE1 = CatalogCard(
    external_id="base1-4",
    name="Charizard",
    set_name="Base",
    set_code="base1",
    card_number="4",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
    cardmarket_url="https://prices.pokemontcg.io/cardmarket/base1-4",
)
_RESOLVED_SHADOWLESS_URL = (
    "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard-V2-BS4"
)
_RESOLVED_NORMAL_URL = (
    "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard-V1-BS4"
)


def test_base_set_result_is_split_into_normal_and_shadowless_variants(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.catalog_search_service.resolve_cardmarket_url",
        lambda url: _RESOLVED_SHADOWLESS_URL,
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.find_alternate_version_url",
        lambda url: _RESOLVED_NORMAL_URL,
    )
    pokemontcg = FakePokemonTcgClient(responses=[[_CHARIZARD_BASE1]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("charizard base1")

    assert len(results) == 2
    normal, shadowless = results
    assert normal.set_name == "Base"
    assert normal.cardmarket_url == _RESOLVED_NORMAL_URL
    assert shadowless.set_name == "Base (Shadowless)"
    assert shadowless.cardmarket_url == _RESOLVED_SHADOWLESS_URL
    # Everything else about the card (name, number, rarity, ...) is unchanged.
    assert normal.name == shadowless.name == "Charizard"
    assert normal.card_number == shadowless.card_number == "4"


def test_non_ambiguous_result_is_not_split(monkeypatch) -> None:
    resolve_calls = []
    monkeypatch.setattr(
        "app.services.catalog_search_service.resolve_cardmarket_url",
        lambda url: resolve_calls.append(url) or url,
    )
    pokemontcg = FakePokemonTcgClient(responses=[[_XATU]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("xatu")

    assert results == [_XATU]
    assert resolve_calls == []


def test_ambiguous_result_without_a_cardmarket_url_is_not_split() -> None:
    card = CatalogCard(
        external_id="base1-99",
        name="Some Common",
        set_name="Base",
        set_code="base1",
        card_number="99",
        rarity="Common",
        image_small_url=None,
        image_large_url=None,
        cardmarket_url=None,
    )
    pokemontcg = FakePokemonTcgClient(responses=[[card]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("some common base1")

    assert results == [card]


def test_resolve_failure_falls_back_to_a_single_unmodified_entry(monkeypatch) -> None:
    def _raise(url):
        raise ConnectionError("network down")

    monkeypatch.setattr("app.services.catalog_search_service.resolve_cardmarket_url", _raise)
    pokemontcg = FakePokemonTcgClient(responses=[[_CHARIZARD_BASE1]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("charizard base1")

    assert results == [_CHARIZARD_BASE1]


def test_no_alternate_version_found_falls_back_to_a_single_entry(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.catalog_search_service.resolve_cardmarket_url",
        lambda url: _RESOLVED_SHADOWLESS_URL,
    )
    monkeypatch.setattr(
        "app.services.catalog_search_service.find_alternate_version_url", lambda url: None
    )
    pokemontcg = FakePokemonTcgClient(responses=[[_CHARIZARD_BASE1]], sets=[])
    service = CatalogSearchService(pokemontcg)

    results = service.search("charizard base1")

    assert len(results) == 1
    assert results[0].cardmarket_url == _CHARIZARD_BASE1.cardmarket_url
