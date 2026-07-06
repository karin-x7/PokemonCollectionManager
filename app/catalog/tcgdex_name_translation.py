"""Live fallback: translate a foreign-language card name to English via tcgdex.dev.

``app.catalog.name_translation``'s static, PokeAPI-generated table only
covers Pokémon *species* names ("Glurak" -> "Charizard") -- PokeAPI has no
concept of Trainer/Item/Supporter/Stadium cards at all, so a German
Trainer-card name like "Lillys Entschlossenheit" ("Lillie's Determination")
never resolves through it. This module covers exactly that gap with a live
lookup instead of a precomputed table (there is no practical way to
pre-generate a table for every Trainer card in every language, and building
one would need constant upkeep as new sets release).

Live-confirmed (see PROJECT_PROGRESS.md): tcgdex.dev shares one set-id/
local-id numbering scheme across the Western release languages (English,
German, French, Spanish, Italian, Portuguese) -- unlike Japanese/Korean/
Traditional Chinese, which get fully independent numbering (see
``tcgdex_designation_lookup.py``, built around that difference for the
reverse direction: English -> foreign designation). That means a card's
*own* tcgdex id (e.g. ``"me01-184"``) refers to the exact same physical card
under every Western locale, including ``en`` -- so once a foreign-language
name search finds the right id, its English name is a second, direct lookup
away, no species/Pokédex-number matching required at all.

Only meant as a fallback once the normal tolerant search (and the
Pokémon-species table) already came back empty -- an extra couple of live
requests for an otherwise-dead-end search is an acceptable cost. The five
locale searches below run *concurrently*, not one after another: tried
sequentially, a query that matches no locale at all (or a currently slow
tcgdex) would stack up to five timeouts back to back -- live-observed to
compound badly with pokemontcg.io's own occasional slowness elsewhere in
the same search (a user report: a search taking "very long" once this
fallback was added). A short, dedicated timeout (see
:data:`_DEFAULT_TIMEOUT`) keeps a single slow/degraded locale from
dominating even the parallel case.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests

from app.logging_config import get_logger
from app.utils.text_normalize import normalize_for_search

logger = get_logger(__name__)

_BASE_URL = "https://api.tcgdex.net/v2"
#: Short on purpose: tcgdex responds in well under a second normally (see
#: PROJECT_PROGRESS.md's live timings) -- this is a fallback tier, not worth
#: waiting as long as the primary pokemontcg.io search does for a slow/
#: degraded response.
_DEFAULT_TIMEOUT = 6.0

#: Western release languages, searched concurrently -- excludes ``en`` (the
#: query is already assumed non-English at this point) and the
#: independently-numbered ja/ko/zh-tw locales (already covered, in the other
#: direction, by ``tcgdex_designation_lookup.py``).
_WESTERN_LOCALES = ("de", "fr", "es", "it", "pt")


def translate_foreign_card_name(
    query: str, session: requests.Session | None = None
) -> str | None:
    """Best-effort: the English name of whatever card ``query`` names in
    some other Western language.

    ``None`` if no plausible match was found in any covered locale, or on a
    network failure -- never raises, mirrors ``app.catalog.name_translation.
    translate_to_english``'s "no translation available" contract.
    """
    target = normalize_for_search(query)
    if not target:
        return None

    http = session or requests.Session()
    pool = ThreadPoolExecutor(max_workers=len(_WESTERN_LOCALES))
    try:
        futures = {
            pool.submit(_search_locale, http, locale, query): locale
            for locale in _WESTERN_LOCALES
        }
        for future in as_completed(futures):
            candidates = future.result()
            if not candidates:
                continue
            for candidate in _ranked(candidates, target):
                english_name = _english_name(http, candidate.get("id", ""))
                if english_name:
                    return english_name
        return None
    finally:
        # Don't wait for still-running locale searches once an answer (or
        # "no answer") is already decided -- only futures that haven't
        # started yet are actually cancellable, but that's still the common
        # case (an early match usually beats several of the five to the
        # punch).
        pool.shutdown(wait=False, cancel_futures=True)


def _search_locale(http: requests.Session, locale: str, query: str) -> list[dict]:
    try:
        response = http.get(
            f"{_BASE_URL}/{locale}/cards?name={quote(query)}", timeout=_DEFAULT_TIMEOUT
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("tcgdex name search failed (locale=%s, query=%r): %s", locale, query, exc)
        return []
    data = response.json()
    return data if isinstance(data, list) else []


def _ranked(candidates: list[dict], target: str) -> list[dict]:
    """Exact (normalised) name matches first, then loose substring matches --

    mirrors the rest of the catalogue search's own normalise-and-compare
    tolerance."""
    exact = [c for c in candidates if normalize_for_search(c.get("name", "")) == target]
    loose = [c for c in candidates if target in normalize_for_search(c.get("name", ""))]
    ordered = exact + [c for c in loose if c not in exact]
    return ordered


def _english_name(http: requests.Session, card_id: str) -> str | None:
    if not card_id:
        return None
    try:
        response = http.get(f"{_BASE_URL}/en/cards/{card_id}", timeout=_DEFAULT_TIMEOUT)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("tcgdex English lookup failed (id=%s): %s", card_id, exc)
        return None
    return response.json().get("name") or None
