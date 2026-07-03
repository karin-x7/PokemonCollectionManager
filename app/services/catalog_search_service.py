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

from app.catalog.models import CatalogCard, CatalogSet
from app.catalog.pokemontcg_client import PokemonTcgClient, PokemonTcgClientError
from app.services.exceptions import CatalogSearchError

#: A token that looks like a card number/collector number: "4", "H32",
#: "SWSH001", "4/102" — an optional short letter prefix, digits, and an
#: optional "/rest" suffix.
_NUMBER_RE = re.compile(r"^[A-Za-z]{0,4}\d+(/\w+)?$")

_SET_NAME_FUZZY_CUTOFF = 0.72
#: Minimum length for a candidate to count as a confident *prefix* match
#: (e.g. "base" -> "Base Set") — below this, too many short/generic words
#: would spuriously prefix-match unrelated set names.
_SET_NAME_PREFIX_MIN_LENGTH = 4
_DEFAULT_MAX_RESULTS = 25


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
        catalog_set, tokens = _extract_set(tokens, self._safe_list_sets())
        set_id = catalog_set.id if catalog_set else None
        name = " ".join(tokens).strip() or None

        results = self._safe_search(name=name, set_id=set_id, number=number)
        if not results and number:
            results = self._safe_search(name=name, set_id=set_id)
        if not results and set_id:
            results = self._safe_search(name=name)

        return results[: self._max_results]

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
