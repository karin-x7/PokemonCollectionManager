"""Looks up a card's localized (Japanese/Korean/Chinese) designation via tcgdex.dev.

Names/labels only -- **never prices** (tcgdex's bundled Cardmarket data
turned out unreliable, see PROJECT_PROGRESS.md; this project only ever
prices a card via the real Cardmarket automation or a user-supplied link).

Solves a narrower problem than full price automation: Cardmarket lists
Japanese/Korean/Chinese prints as entirely separate products, often under
the *Japanese* set's own name (e.g. Neo Revelation's Ho-Oh is "Awakening
Legends" there) -- this at least tells the user what to search Cardmarket
for, instead of them having to research it by hand (e.g. via Bulbapedia).

Matching approach (confirmed live against the real Ho-Oh case, see
PROJECT_PROGRESS.md): tcgdex assigns each *locale* its own independent set-id
sequence, so the same id string (e.g. ``"neo3"``) can mean a completely
different set in two locales -- ids cannot be reused across locales. Instead:

1. Look up the card's own (English) tcgdex entry via its existing
   ``external_card_id`` -- same id pokemontcg.io already uses -- to get its
   national Pokédex number (``dexId``) and English set release date.
2. Search the target locale for every card sharing that ``dexId``
   (typically a handful of candidates, one per era that species was ever
   printed in that language).
3. Pick whichever candidate's *set* released closest before the English
   set's release date -- a foreign release always precedes its English
   localisation, never follows it long-term, and the closest preceding one
   is virtually always the correct source set.

Correctly identified "Awakening Legends" (released 2000-11-23) as the
source of Neo Revelation's (released 2001-09-21) Ho-Oh this way, matching
the user's own independently-confirmed Cardmarket link.

Known coverage gap: Korean and Chinese returned zero candidates for a very
common species in a live test -- this will realistically only help Japanese
cards today, though the same code path applies if tcgdex's ko/zh coverage
improves later.

A second live test caught a false positive from the same coverage gap:
Umbreon VMAX (Evolving Skies, EN 2021) has no real Japanese Sword & Shield-
era entry in tcgdex at all, yet the "closest preceding release" step still
picked its only same-species "ja" candidate -- a 2005 reprint, 16 years off.
A plausibility check (:data:`_MAX_PLAUSIBLE_LOCALIZATION_GAP_DAYS`) now
rejects any match further apart than a real localisation gap could ever be,
returning ``None`` ("no confident suggestion") instead of a guess that could
send the user looking for the wrong product entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import requests

from app.logging_config import get_logger
from app.models.enums import Language

logger = get_logger(__name__)

_BASE_URL = "https://api.tcgdex.net/v2"
_DEFAULT_TIMEOUT = 10.0
#: A live test caught a false-positive suggestion: Umbreon VMAX (Evolving
#: Skies, EN released 2021-08-27) matched tcgdex's only same-``dexId`` "ja"
#: candidate, a 2005 Delta Species reprint -- 16 years off, because tcgdex
#: simply has no real Japanese Sword & Shield-era entry for that card at
#: all. Genuine JP-to-EN localisation gaps run at most ~2 years even for
#: vintage sets (confirmed live: Neo Revelation's real ~10-month gap) --
#: anything further apart is treated as "no confident match" instead of a
#: guess that could send the user looking for the wrong product entirely.
_MAX_PLAUSIBLE_LOCALIZATION_GAP_DAYS = 730

#: tcgdex's own locale codes for the languages this project supports beyond
#: the Cardmarket-filterable Western ones (see ``browser_price_reader.
#: supports_language_filter``) -- confirmed live against the real API.
TCGDEX_LOCALES: dict[Language, str] = {
    Language.JAPANESE: "ja",
    Language.KOREAN: "ko",
    Language.CHINESE: "zh-tw",
}


class TcgdexDesignationLookupError(Exception):
    """Raised on a network error or non-2xx/404 response."""


@dataclass(frozen=True, slots=True)
class LocalizedDesignation:
    """The localized name/set tcgdex reports for a card, used to search

    Cardmarket by hand -- never persisted or used for pricing.
    """

    card_name: str
    set_name: str
    set_id: str
    local_id: str


def _get_json(session: requests.Session, path: str) -> dict | None:
    """GET a tcgdex path, returning ``None`` for a 404, raising on any other

    failure."""
    try:
        response = session.get(f"{_BASE_URL}{path}", timeout=_DEFAULT_TIMEOUT)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("tcgdex request failed (%s): %s", path, exc)
        raise TcgdexDesignationLookupError("tcgdex.dev ist gerade nicht erreichbar.") from exc
    return response.json()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def find_localized_designation(
    external_card_id: str,
    language: Language,
    session: requests.Session | None = None,
) -> LocalizedDesignation | None:
    """Best-effort lookup of ``external_card_id``'s designation in ``language``.

    Returns ``None`` if the language isn't covered (see :data:`TCGDEX_LOCALES`),
    the English card or its national Pokédex number can't be found, or no
    candidate exists in the target locale -- all real, expected outcomes
    given tcgdex's coverage gaps, not failures.

    Raises:
        TcgdexDesignationLookupError: On a network error or non-2xx response.
    """
    locale = TCGDEX_LOCALES.get(language)
    if locale is None:
        return None

    http = session or requests.Session()

    english = _get_json(http, f"/en/cards/{external_card_id}")
    if english is None:
        return None
    dex_ids = english.get("dexId") or []
    if not dex_ids:
        return None
    english_set = english.get("set") or {}
    english_release = _parse_date(_get_release_date(http, "en", english_set.get("id")))

    candidates = _get_json(
        http, f"/{locale}/cards?dexId={dex_ids[0]}&category=Pokemon"
    )
    if not candidates:
        return None

    best: tuple[date | None, dict] | None = None
    for candidate in candidates:
        detail = _get_json(http, f"/{locale}/cards/{candidate['id']}")
        if detail is None:
            continue
        set_info = detail.get("set") or {}
        release = _parse_date(_get_release_date(http, locale, set_info.get("id")))
        if best is None or _is_better_match(release, best[0], english_release):
            best = (release, detail)

    if best is None:
        return None
    best_release, detail = best
    if (
        english_release is None
        or best_release is None
        or abs((best_release - english_release).days) > _MAX_PLAUSIBLE_LOCALIZATION_GAP_DAYS
    ):
        logger.info(
            "tcgdex designation candidate for %s rejected as implausible "
            "(english=%s, candidate=%s)",
            external_card_id,
            english_release,
            best_release,
        )
        return None
    set_info = detail.get("set") or {}
    return LocalizedDesignation(
        card_name=detail.get("name", ""),
        set_name=set_info.get("name", ""),
        set_id=set_info.get("id", ""),
        local_id=detail.get("localId", ""),
    )


def _get_release_date(http: requests.Session, locale: str, set_id: str | None) -> str | None:
    if not set_id:
        return None
    set_detail = _get_json(http, f"/{locale}/sets/{set_id}")
    return set_detail.get("releaseDate") if set_detail else None


def _is_better_match(
    candidate: date | None, current_best: date | None, anchor: date | None
) -> bool:
    """Whichever candidate set released closest *before* ``anchor`` wins --

    a foreign release always precedes its English localisation. Falls back
    to "closest overall" if nothing released before ``anchor`` (or ``anchor``
    itself is unknown)."""
    if anchor is None:
        return current_best is None
    if candidate is None:
        return False
    candidate_before = candidate <= anchor
    best_before = current_best is not None and current_best <= anchor
    if candidate_before and not best_before:
        return True
    if not candidate_before and best_before:
        return False
    if current_best is None:
        return True
    if candidate_before:  # both before anchor -- the later (closer) one wins
        return candidate > current_best
    return abs((candidate - anchor).days) < abs((current_best - anchor).days)
