"""Tolerant, multi-field catalogue search.

Resolves a free-text query into pokemontcg.io catalogue matches
(name/set/number/images). Set-name resolution uses pokemontcg.io's own
``/sets`` list (not CardTrader's) — see :func:`_extract_set` for why: the two
sources don't share a naming vocabulary, and filtering ``set.name`` itself
turned out to be unreliable (see ``app.catalog.pokemontcg_client.
build_query``). Never hard-fails just because the set could not be resolved
or a structured filter came back empty — it keeps loosening the query
instead.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import replace

from app.catalog.models import CatalogCard, CatalogSet
from app.catalog.name_translation import translate_to_english
from app.catalog.pokemontcg_client import (
    PokemonTcgClient,
    PokemonTcgClientError,
    has_ambiguous_cardmarket_variants,
)
from app.catalog.tcgdex_name_translation import translate_foreign_card_name
from app.pricing.browser_price_reader import find_alternate_version_url, resolve_cardmarket_url
from app.services.exceptions import CatalogSearchError
from app.utils.text_normalize import normalize_for_search

#: A token that looks like a card number/collector number: "4", "H32",
#: "SWSH001", "4/102" — an optional short letter prefix, digits, and an
#: optional "/rest" suffix.
_NUMBER_RE = re.compile(r"^[A-Za-z]{0,4}\d+(/\w+)?$")

#: Print-finish/variant words a user might add alongside a card name (e.g.
#: "xatu skyridge holo") that describe *how the physical card was printed*,
#: not part of pokemontcg.io's own name field -- a live bug report found
#: "xatu skyridge holo" returning zero results (while "xatu skyridge"
#: worked fine) because pokemontcg.io's own search treats a multi-word name
#: as an *exact* phrase, and "Xatu" the catalogue name obviously never
#: contains the word "holo". These are stripped from the name query
#: entirely rather than turned into a real filter: pokemontcg.io's own
#: rarity data was independently found unreliable for this project's
#: purposes (see PROJECT_PROGRESS.md), so there's nothing trustworthy to
#: filter by -- the fix is just to stop this noise from breaking the name
#: match, not to also start filtering by finish.
#: Multi-word phrases are listed as tuples and checked first (as a
#: contiguous slice) so "reverse holo" isn't left as a dangling "reverse".
_VARIANT_PHRASES: tuple[tuple[str, ...], ...] = (
    ("reverse", "holo"),
    ("non", "holo"),
    ("1st", "edition"),
)
_VARIANT_WORDS = frozenset(
    {"holo", "nonholo", "reverseholo", "foil", "shadowless", "unlimited", "promo"}
)


def _strip_variant_words(tokens: list[str]) -> list[str]:
    """Remove known print-finish/variant words/phrases from ``tokens``,

    leaving only the words that are actually part of the card's name."""
    remaining = list(tokens)
    for phrase in _VARIANT_PHRASES:
        length = len(phrase)
        for start in range(len(remaining) - length + 1):
            if tuple(t.casefold() for t in remaining[start : start + length]) == phrase:
                remaining = remaining[:start] + remaining[start + length :]
                break
    return [t for t in remaining if t.casefold() not in _VARIANT_WORDS]

_SET_NAME_FUZZY_CUTOFF = 0.72
#: Minimum length for a candidate to count as a confident *prefix* match
#: (e.g. "base" -> "Base Set") — below this, too many short/generic words
#: would spuriously prefix-match unrelated set names.
_SET_NAME_PREFIX_MIN_LENGTH = 4
_DEFAULT_MAX_RESULTS = 25


#: Prefix lengths tried (longest first) once the exact name search finds
#: nothing -- bounded to a handful of extra requests per search, never an
#: unbounded/per-card loop.
_SHRINKING_PREFIX_LENGTHS = (6, 4, 3)


def _translate_name_with_suffix(name: str) -> str | None:
    """Translate a foreign species name even when followed by a card-type

    suffix pokemontcg.io never translates (e.g. "Blitza VMAX" -> "Jolteon
    VMAX", not just "Blitza" alone). ``translate_to_english`` only ever
    matches a *whole* query against a single foreign species name -- a live
    bug report found "Blitza VMAX" returning nothing at all, even though
    "Blitza" alone translates fine, because normalising the combined query
    collapses it to "blitzavmax", which isn't a key in the translation
    table at all (only the bare species name is). Tried longest-to-shortest
    so a genuinely multi-word foreign name (were one ever added) still gets
    first refusal over assuming the last word is an untranslatable suffix.
    """
    tokens = name.split()
    for split_point in range(len(tokens), 0, -1):
        candidate = " ".join(tokens[:split_point])
        translated = translate_to_english(candidate)
        if translated and translated.casefold() != candidate.casefold():
            suffix = " ".join(tokens[split_point:])
            return f"{translated} {suffix}".strip()
    return None


def _shrinking_name_candidates(name: str) -> list[str]:
    """Progressively shorter, space-free prefixes of ``name``, plus each of

    its individual words.

    Spaces are dropped first: pokemontcg.io treats a multi-word ``name``
    as an *exact* quoted phrase, not a prefix match (see
    ``pokemontcg_client._prefix_clause``), so a still-multi-word shortened
    query wouldn't loosen anything. Collapsing "ho oh" to "hooh" first
    turns it back into a single-word trailing-wildcard prefix match, which
    is exactly the workaround a user typing "hooh" directly relies on.

    Individual words are also tried on their own: a live bug report found
    "poke pad"/"pokepad" returning nothing at all for "Poké Pad" -- unlike
    "ho-oh", pokemontcg.io's own search never folds the "é" for *any*
    accent-free prefix of the collapsed *whole* name ("pokepad", "poke",
    ...), but a plain, accent-free "pad*" prefix query still finds it,
    because pokemontcg.io's wildcard prefix match checks every word in a
    multi-word name field, not just the first. Longest word first (most
    specific, least noise from unrelated same-prefix cards).
    """
    collapsed = name.replace(" ", "")
    lengths = sorted({len(collapsed), *_SHRINKING_PREFIX_LENGTHS}, reverse=True)
    # Never repeat the exact query the caller already tried (the full,
    # un-collapsed name) -- only worth trying again once its length or
    # spacing actually differs.
    seen: set[str] = {name}
    candidates: list[str] = []
    for length in lengths:
        if length < 3 or length > len(collapsed):
            continue
        prefix = collapsed[:length]
        if prefix not in seen:
            seen.add(prefix)
            candidates.append(prefix)
    for word in sorted(set(name.split()), key=len, reverse=True):
        casefolded = word.casefold()
        if len(casefolded) >= 3 and casefolded not in seen:
            seen.add(casefolded)
            candidates.append(casefolded)
    return candidates


def _extract_number(tokens: list[str]) -> tuple[str | None, list[str]]:
    """Pull the first number-like token out of ``tokens``, if any."""
    for index, token in enumerate(tokens):
        if _NUMBER_RE.match(token):
            return token, tokens[:index] + tokens[index + 1 :]
    return None, tokens


def _set_name_score(candidate: str, name: str) -> float:
    """Score how well ``candidate`` (already casefolded) identifies ``name``.

    A partial *prefix* of an official set name (e.g. "base" for "Base Set")
    counts as a confident match — "tolerant search over ... partial terms" is
    the whole point — so it scores as high as an exact match, but only once
    the candidate covers at least half of the name's length. Without that
    ratio requirement, a card name that happens to literally prefix some
    unrelated, longer set name would wrongly be treated as a confident set
    reference. Otherwise fall back to a plain fuzzy ratio (typo tolerance,
    e.g. "skyrige" -> "Skyridge").
    """
    if (
        len(candidate) >= _SET_NAME_PREFIX_MIN_LENGTH
        and name.startswith(candidate)
        and len(candidate) / len(name) >= 0.5
    ):
        return 1.0
    return difflib.SequenceMatcher(None, candidate, name).ratio()


def _extract_set(
    tokens: list[str], sets: list[CatalogSet]
) -> tuple[CatalogSet | None, list[str]]:
    """Resolve the best-matching contiguous slice of ``tokens`` against known
    sets (by prefix or fuzzy typo match — see :func:`_set_name_score`).

    Matched against pokemontcg.io's own ``/sets`` list rather than
    CardTrader's expansions: the two sources name the same set differently
    (CardTrader calls the 1999 base set "Base Set"; pokemontcg.io calls it
    just "Base" and reserves "Base Set 2" for the 2000 reprint) — resolving
    against CardTrader's vocabulary and then filtering pokemontcg.io by that
    name risked mixing up exactly this kind of reprint. Resolving against
    pokemontcg.io's own list guarantees the resolved name (and its ``id``,
    used for the actual filter) refers to a set pokemontcg.io itself knows by
    that name.

    Every contiguous slice is scored against every set name and the
    *globally* best-scoring slice wins (ties keep the first-found one). Slices
    are tried longest-first so that on a tie between a full name and one of
    its own prefix words (e.g. "team rocket" scoring 1.0 the same as just
    "team" against "Team Rocket"), the longer, more complete match wins.
    """
    if not tokens or not sets:
        return None, tokens

    total = len(tokens)
    best: tuple[float, int, int, CatalogSet] | None = None
    for length in range(total, 0, -1):
        for start in range(0, total - length + 1):
            candidate = " ".join(tokens[start : start + length]).casefold()
            for catalog_set in sets:
                score = _set_name_score(candidate, catalog_set.name.casefold())
                if score >= _SET_NAME_FUZZY_CUTOFF and (best is None or score > best[0]):
                    best = (score, start, length, catalog_set)

    if best is None:
        return None, tokens
    _, start, length, resolved_set = best
    remaining = tokens[:start] + tokens[start + length :]
    return resolved_set, remaining


def _expand_ambiguous_variants(results: list[CatalogCard]) -> list[CatalogCard]:
    """Splits a Base Set-style match into its two Cardmarket-specific

    variants (see ``has_ambiguous_cardmarket_variants``) -- every other
    match passes through unchanged. This is the one place in the app that
    can safely resolve pokemontcg.io's single, ambiguous link into two
    concrete, correctly-linked choices: the user is about to explicitly
    pick one row from the search results dialog anyway, so presenting
    "Charizard — Base" and "Charizard — Base (Shadowless)" as two distinct,
    already-correctly-linked options is a natural fit right here (as
    opposed to a card that's already been added, where there's no "pick a
    row" moment left to hang the disambiguation on -- see PriceService).
    """
    expanded: list[CatalogCard] = []
    for card in results:
        expanded.extend(_split_ambiguous_variant(card))
    return expanded


def _split_ambiguous_variant(card: CatalogCard) -> list[CatalogCard]:
    if not card.cardmarket_url or not has_ambiguous_cardmarket_variants(card.set_code):
        return [card]
    try:
        real_url = resolve_cardmarket_url(card.cardmarket_url)
    except Exception:  # noqa: BLE001 — best-effort: fall back to the single,
        # unresolved entry rather than failing the whole search over this.
        return [card]
    alternate_url = find_alternate_version_url(real_url)
    if alternate_url is None:
        return [card]
    # pokemontcg.io's own link for Base Set always resolves to the higher-
    # numbered ("-V2-") Shadowless product (live-confirmed against
    # api.pokemontcg.io); the lower-numbered sibling
    # find_alternate_version_url prefers is the Normal/Unlimited one, which
    # exists in every language, not just English -- listed first since it's
    # the far more common case.
    normal = replace(card, cardmarket_url=alternate_url)
    shadowless = replace(
        card, set_name=f"{card.set_name} (Shadowless)", cardmarket_url=real_url
    )
    return [normal, shadowless]


class CatalogSearchService:
    """Resolves a free-text query into ranked catalogue matches."""

    def __init__(
        self,
        pokemontcg_client: PokemonTcgClient,
        max_results: int = _DEFAULT_MAX_RESULTS,
    ) -> None:
        self._pokemontcg = pokemontcg_client
        self._max_results = max_results

    def search(self, query: str) -> list[CatalogCard]:
        """Tolerant search over name/set/number/partial terms.

        Raises:
            CatalogSearchError: If the catalogue backend cannot be reached.
        """
        cleaned = (query or "").strip()
        if not cleaned:
            return []

        tokens = cleaned.split()
        number, tokens = _extract_number(tokens)
        tokens = _strip_variant_words(tokens)
        catalog_set, tokens = _extract_set(tokens, self._safe_list_sets())
        set_id = catalog_set.id if catalog_set else None
        name = " ".join(tokens).strip() or None

        results = self._safe_search(name=name, set_id=set_id, number=number)
        if not results and number:
            results = self._safe_search(name=name, set_id=set_id)
        if not results and set_id:
            results = self._safe_search(name=name)

        if not results and name:
            results = self._search_name_tolerantly(name, set_id, number)

        results = results[: self._max_results]
        return _expand_ambiguous_variants(results)

    def _search_name_tolerantly(
        self, name: str, set_id: str | None, number: str | None
    ) -> list[CatalogCard]:
        """Three extra loosening tiers once an exact name search found nothing.

        First, if ``name`` is a known foreign-language *species* name (e.g.
        "Turtok"), retry with its English equivalent (e.g. "Blastoise") --
        pokemontcg.io only knows English names at all. Second, a live
        tcgdex.dev lookup (see ``app.catalog.tcgdex_name_translation``)
        covers foreign-language *Trainer/Item/Stadium* card names (e.g.
        "Lillys Entschlossenheit" -> "Lillie's Determination") -- the
        species table above has no equivalent for these since PokeAPI (its
        source) knows nothing about them. Tried *before* the shrinking-
        prefix tier below on purpose: a genuinely foreign-language name can
        never match any English prefix there anyway, so running that tier
        first would only add several pointless (and, if pokemontcg.io is
        having a slow day, potentially very slow) round-trips before ever
        reaching the one tier that could actually resolve it -- live-
        reported by a user as the search taking "very long" while this tier
        still sat last. Last, regardless of language, a shrinking-prefix
        search (see :func:`_shrinking_name_candidates`) filtered
        client-side by a loose, accent/punctuation-insensitive match
        against the original name -- pokemontcg.io's own search doesn't
        fold accents or hyphens (a live smoke test found "poképad" worked
        but "pokepad"/"poke pad" didn't).
        """
        translated = _translate_name_with_suffix(name)
        if translated and translated.casefold() != name.casefold():
            results = self._safe_search(name=translated, set_id=set_id, number=number)
            if results:
                return results

        foreign_card_name = translate_foreign_card_name(name)
        if foreign_card_name and foreign_card_name.casefold() != name.casefold():
            results = self._safe_search(name=foreign_card_name, set_id=set_id, number=number)
            if results:
                return results

        target = normalize_for_search(name)
        for candidate in _shrinking_name_candidates(name):
            results = self._safe_search(name=candidate, set_id=set_id, number=number)
            matches = [r for r in results if target in normalize_for_search(r.name)]
            if matches:
                return matches
        return []

    def _safe_list_sets(self) -> list[CatalogSet]:
        """Best-effort set list — resolution is an aid, not a requirement, so
        a lookup failure degrades to name-only search rather than failing the
        whole query."""
        try:
            return self._pokemontcg.list_sets()
        except PokemonTcgClientError:
            return []

    def _safe_search(
        self,
        name: str | None = None,
        set_id: str | None = None,
        number: str | None = None,
    ) -> list[CatalogCard]:
        try:
            return self._pokemontcg.search(name=name, set_id=set_id, number=number)
        except PokemonTcgClientError as exc:
            raise CatalogSearchError(str(exc)) from exc
