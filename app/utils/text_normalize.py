"""Loose, accent/punctuation-insensitive text matching.

SQLite's ``LIKE`` is only case-insensitive for ASCII, and pokemontcg.io's own
search doesn't fold accents either -- a live smoke test found "poképad"
worked but "pokepad"/"poke pad" didn't, and "ho-oh" worked but "hooh"/
"ho oh" didn't. :func:`normalize_for_search` strips accents and punctuation
from both the stored name and the user's query so either spelling matches.
"""

from __future__ import annotations

import unicodedata

#: Kept characters after normalisation: letters and digits only. Hyphens,
#: spaces, apostrophes etc. are dropped entirely so "Ho-Oh"/"ho oh"/"hooh"
#: all normalise to the same string.
_ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")


def normalize_for_search(text: str) -> str:
    """Fold ``text`` to a loose, comparable form: no accents, no punctuation,
    no case, no spacing.

    ``"Poképad"`` and ``"poke pad"``/``"pokepad"`` both become
    ``"pokepad"``; ``"Ho-Oh"`` and ``"ho oh"``/``"hooh"`` both become
    ``"hooh"``.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return "".join(ch for ch in without_accents if ch in _ALLOWED)
