"""Cross-language Pokémon species name lookup for search.

pokemontcg.io only knows English names, so searching "Turtok" (the German
name for Blastoise) finds nothing there, and a locally-owned card is always
stored under its English name too (see ``CardService.add_card_from_catalog``)
-- searching a foreign name for it fails the same way. This module answers
"what's the English name for this foreign-language name?" from a static
table generated once from the real PokeAPI (see PROJECT_PROGRESS.md) and
committed as ``pokemon_name_translations.json`` -- the app itself never
calls PokeAPI at runtime.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.utils.text_normalize import normalize_for_search

_TRANSLATIONS_PATH = Path(__file__).resolve().parent / "pokemon_name_translations.json"


@lru_cache(maxsize=1)
def _translations() -> dict[str, str]:
    """The bundled {normalised foreign name: canonical English name} table.

    Loaded once and cached; an empty dict (not an error) if the file is
    somehow missing, so a search without it just skips this lookup instead
    of crashing.
    """
    try:
        with _TRANSLATIONS_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def translate_to_english(term: str) -> str | None:
    """Return the English species name for a foreign-language ``term``.

    ``None`` if ``term`` isn't a known foreign name (e.g. it's already
    English, or unrecognised) -- callers should treat that as "no
    translation available", not an error.
    """
    return _translations().get(normalize_for_search(term))


def translate_name_with_suffix(name: str) -> str | None:
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

    ``None`` if no prefix of ``name`` translates -- callers should treat
    that the same as "no translation available" from ``translate_to_english``.
    """
    tokens = name.split()
    for split_point in range(len(tokens), 0, -1):
        candidate = " ".join(tokens[:split_point])
        translated = translate_to_english(candidate)
        if translated and translated.casefold() != candidate.casefold():
            suffix = " ".join(tokens[split_point:])
            return f"{translated} {suffix}".strip()
    return None
