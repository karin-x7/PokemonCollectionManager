"""HTTP client for the pokemontcg.io card catalogue API.

Read-only. An API key is optional (raises the public rate limit) and is
read from ``config/secrets.json`` (``pokemontcg_io.api_key``) if not passed
explicitly.

Only trailing wildcards (``term*``) are used for partial matches: the API
was measured live to be slow-to-unresponsive with leading wildcards
(``*term*``), while a prefix match stays within a few seconds. This matches
the common case of a user typing the start of a name/set anyway.
"""

from __future__ import annotations

import time

import requests

from app.catalog.models import CatalogCard, CatalogSet
from app.logging_config import get_logger
from app.secrets import get_secret

logger = get_logger(__name__)

#: pokemontcg.io drops the "EX " era prefix from its own set names for the
#: entire EX Series (e.g. its ``"ex2"`` is just "Sandstorm", not "EX
#: Sandstorm") -- live-confirmed against the API's own /sets response for
#: all 16 ("Ruby & Sapphire" through "Power Keepers"), cross-checked against
#: Bulbapedia's official expansion list (user-supplied). Cardmarket, by
#: contrast, uses the full "EX ..." name -- correcting it here keeps a
#: catalogue-matched card's displayed set name consistent with a manually
#: entered one from the same set (see also ``resolve_set_code``, whose
#: matching relies on exactly this same "EX " prefix difference).
_EX_SERIES_SET_NAMES: dict[str, str] = {
    "ex1": "EX Ruby & Sapphire",
    "ex2": "EX Sandstorm",
    "ex3": "EX Dragon",
    "ex4": "EX Team Magma vs Team Aqua",
    "ex5": "EX Hidden Legends",
    "ex6": "EX FireRed & LeafGreen",
    "ex7": "EX Team Rocket Returns",
    "ex8": "EX Deoxys",
    "ex9": "EX Emerald",
    "ex10": "EX Unseen Forces",
    "ex11": "EX Delta Species",
    "ex12": "EX Legend Maker",
    "ex13": "EX Holon Phantoms",
    "ex14": "EX Crystal Guardians",
    "ex15": "EX Dragon Frontiers",
    "ex16": "EX Power Keepers",
}


def _corrected_set_name(set_id: str, set_name: str) -> str:
    """``set_name``, or the corrected "EX ..." form for a known EX Series id."""
    return _EX_SERIES_SET_NAMES.get(set_id, set_name)


#: Sets where Cardmarket splits a single pokemontcg.io card record into
#: multiple, mutually exclusive marketplace products -- confirmed live for
#: Base Set ("base1"): its Charizard has separate "Normal" (Unlimited) and
#: "Shadowless" Cardmarket products (Charizard-V1-BS4 / Charizard-V2-BS4),
#: but pokemontcg.io only tracks one card record with one cardmarket link,
#: which always resolves to the Shadowless product -- and since Shadowless
#: only ever exists in English, that link is flat-out wrong for any other
#: printed language. There's no way to tell from pokemontcg.io's own data
#: (or anything else already on a ``Card``) which physical variant the user
#: actually owns, so auto-filling it here would silently risk linking (and
#: therefore pricing) the wrong print. Left blank instead, the same way
#: Japanese/Korean/Chinese prints already rely on the user filling in
#: "Eigener Cardmarket-Link" themselves with the exact product they have.
_AMBIGUOUS_VARIANT_SET_CODES = frozenset({"base1"})


def has_ambiguous_cardmarket_variants(set_code: str) -> bool:
    """Whether ``set_code`` is one where pokemontcg.io's single cardmarket

    link can't be trusted (see ``_AMBIGUOUS_VARIANT_SET_CODES`` above) --
    used by ``price_service.py`` to give a specific, actionable message
    instead of a generic "no link known" one.
    """
    return set_code in _AMBIGUOUS_VARIANT_SET_CODES


_BASE_URL = "https://api.pokemontcg.io/v2"
_DEFAULT_TIMEOUT = 20.0
#: A live smoke test caught pokemontcg.io itself taking >30s to respond
#: during a brief slow period -- past this client's own timeout, but
#: recovering moments later. One retry gives a second chance without
#: turning a momentary hiccup into "the catalogue is unreachable".
_MAX_ATTEMPTS = 2
_DEFAULT_RETRY_DELAY = 1.0


class PokemonTcgClientError(Exception):
    """Raised when the pokemontcg.io API cannot be reached or errors out."""


def _prefix_clause(field: str, term: str) -> str:
    """Build a ``field:term*`` prefix-match clause.

    A quoted phrase combined with a trailing wildcard (``"multi word"*``) is
    rejected by the API with a 400 — measured live. So a multi-word term
    becomes an exact quoted phrase instead (no wildcard); only single-word
    terms get the trailing-wildcard prefix match.
    """
    escaped = term.strip().replace('"', '\\"')
    if " " in escaped:
        return f'{field}:"{escaped}"'
    return f"{field}:{escaped}*"


def _exact_clause(field: str, term: str) -> str:
    """Build a ``field:term`` exact-match clause, quoting multi-word terms."""
    escaped = term.strip().replace('"', '\\"')
    return f'{field}:"{escaped}"' if " " in escaped else f"{field}:{escaped}"


def build_query(
    name: str | None = None,
    set_id: str | None = None,
    number: str | None = None,
) -> str:
    """Build a pokemontcg.io ``q`` query string from optional field filters.

    ``name`` becomes a trailing-wildcard prefix match (or an exact phrase for
    multi-word terms — see :func:`_prefix_clause`). ``set_id`` and ``number``
    are matched exactly.

    ``set_id`` (not ``set.name``) is deliberate: pokemontcg.io's ``set.name``
    field is tokenised, so both a wildcard prefix (``set.name:base*``) and a
    quoted phrase (``set.name:"base"``) match *every* set whose name merely
    contains the word "base" — including the unrelated "Base Set 2" reprint
    when the user meant the original "Base" set — measured live. ``set.id``
    (e.g. ``"base1"``) is an opaque, single-token identifier and matches
    exactly one set.
    """
    clauses: list[str] = []
    if name and name.strip():
        clauses.append(_prefix_clause("name", name))
    if set_id and set_id.strip():
        clauses.append(_exact_clause("set.id", set_id))
    if number and number.strip():
        clauses.append(_exact_clause("number", number))
    return " ".join(clauses)


class PokemonTcgClient:
    """Thin read-only wrapper around the pokemontcg.io ``/cards`` endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
        retry_delay: float = _DEFAULT_RETRY_DELAY,
    ) -> None:
        self._api_key = api_key if api_key is not None else get_secret(
            "pokemontcg_io", "api_key"
        )
        self._timeout = timeout
        self._session = session or requests.Session()
        self._retry_delay = retry_delay
        self._sets_cache: list[CatalogSet] | None = None

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._api_key} if self._api_key else {}

    def list_sets(self) -> list[CatalogSet]:
        """Return all known sets/expansions, cached after the first call.

        Used to resolve a free-text set name/partial term to the exact
        ``set.id`` :meth:`search` filters on (see :func:`build_query`).

        Raises:
            PokemonTcgClientError: On a network error or non-2xx response.
        """
        if self._sets_cache is not None:
            return self._sets_cache
        payload = self._get("/sets", params={"pageSize": 250})
        self._sets_cache = [
            CatalogSet(
                id=raw.get("id", ""),
                name=_corrected_set_name(raw.get("id", ""), raw.get("name", "")),
            )
            for raw in payload.get("data", [])
        ]
        return self._sets_cache

    def resolve_set_code(self, set_name: str) -> str:
        """Best-effort ``set.id`` for a free-text set name.

        Backs the "Karte manuell eintragen" flow: there, the set name comes
        from Cardmarket's own page title/breadcrumb rather than a confirmed
        catalogue match, and can differ slightly from pokemontcg.io's own
        naming. Tries an exact (casefolded) name match first (this already
        covers the whole EX Series thanks to :data:`_EX_SERIES_SET_NAMES`
        correcting pokemontcg.io's own dropped "EX " prefix -- see its own
        docs), then a "given name ends with <catalogue name>" match as a
        general fallback for any other, not-yet-catalogued prefix
        difference. Blank if nothing matches or ``set_name`` is blank.

        Raises:
            PokemonTcgClientError: On a network error or non-2xx response
                (same as :meth:`list_sets`) -- callers should treat this as
                best-effort and not block card creation on it.
        """
        if not set_name:
            return ""
        normalized = set_name.casefold().strip()
        sets = self.list_sets()
        for catalog_set in sets:
            if catalog_set.name.casefold() == normalized:
                return catalog_set.id
        for catalog_set in sets:
            if normalized.endswith(f" {catalog_set.name.casefold()}"):
                return catalog_set.id
        return ""

    def search(
        self,
        name: str | None = None,
        set_id: str | None = None,
        number: str | None = None,
        page_size: int = 25,
    ) -> list[CatalogCard]:
        """Search the catalogue by any combination of name/set/number.

        Raises:
            PokemonTcgClientError: On a network error or non-2xx response.
        """
        query = build_query(name=name, set_id=set_id, number=number)
        if not query:
            return []
        payload = self._get("/cards", params={"q": query, "pageSize": page_size})
        return [self._parse_card(raw) for raw in payload.get("data", [])]

    def get_card_by_id(self, external_id: str) -> CatalogCard | None:
        """Look up a single card by its catalogue id (e.g. ``"base1-4"``).

        Used to backfill :attr:`CatalogCard.cardmarket_url` for a card added
        before that field existed. Returns ``None`` if the id doesn't exist.

        Raises:
            PokemonTcgClientError: On a network error or non-2xx response
                other than 404.
        """
        response = self._get_with_retry(f"/cards/{external_id}")
        if response.status_code == 404:
            return None
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("pokemontcg.io request failed (/cards/%s): %s", external_id, exc)
            raise PokemonTcgClientError(
                "Der Kartenkatalog (pokemontcg.io) ist gerade nicht erreichbar."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise PokemonTcgClientError(
                "Antwort des Kartenkatalogs (pokemontcg.io) war ungültig."
            ) from exc

        data = payload.get("data")
        return self._parse_card(data) if data else None

    def _get(self, path: str, params: dict) -> dict:
        response = self._get_with_retry(path, params)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("pokemontcg.io request failed (%s, params=%r): %s", path, params, exc)
            raise PokemonTcgClientError(
                "Der Kartenkatalog (pokemontcg.io) ist gerade nicht erreichbar."
            ) from exc
        try:
            return response.json()
        except ValueError as exc:
            raise PokemonTcgClientError(
                "Antwort des Kartenkatalogs (pokemontcg.io) war ungültig."
            ) from exc

    def _get_with_retry(self, path: str, params: dict | None = None) -> requests.Response:
        """GET, retrying once on a timeout/connection error before giving up.

        Does not itself raise on a non-2xx status (e.g. 404) -- callers
        decide how to interpret that (:meth:`get_card_by_id` treats 404 as
        "not found", not an error; :meth:`_get` always treats it as one).
        """
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._session.get(
                    f"{_BASE_URL}{path}",
                    params=params,
                    headers=self._headers(),
                    timeout=self._timeout,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                logger.warning(
                    "pokemontcg.io request timed out (%s, params=%r), attempt %d/%d: %s",
                    path, params, attempt, _MAX_ATTEMPTS, exc,
                )
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(self._retry_delay)
            except requests.RequestException as exc:
                logger.error("pokemontcg.io request failed (%s, params=%r): %s", path, params, exc)
                raise PokemonTcgClientError(
                    "Der Kartenkatalog (pokemontcg.io) ist gerade nicht erreichbar."
                ) from exc

        raise PokemonTcgClientError(
            "Der Kartenkatalog (pokemontcg.io) ist gerade nicht erreichbar."
        ) from last_exc

    @staticmethod
    def _parse_card(raw: dict) -> CatalogCard:
        set_info = raw.get("set") or {}
        images = raw.get("images") or {}
        cardmarket = raw.get("cardmarket") or {}
        set_code = set_info.get("id", "")
        # cardmarket_url is passed through as-is even for sets with known
        # variant ambiguity (see has_ambiguous_cardmarket_variants) -- this
        # client is a faithful passthrough of whatever pokemontcg.io says,
        # nothing more. Deciding whether that link can be trusted is the
        # consumer's job: CatalogSearchService resolves and splits it into
        # variant-specific entries for the interactive add-a-new-card flow,
        # and PriceService refuses to trust an unresolved, still-ambiguous
        # one for a card that's already been added.
        return CatalogCard(
            external_id=raw.get("id", ""),
            name=raw.get("name", ""),
            set_name=_corrected_set_name(set_code, set_info.get("name", "")),
            set_code=set_code,
            card_number=raw.get("number", ""),
            rarity=raw.get("rarity") or "",
            image_small_url=images.get("small"),
            image_large_url=images.get("large"),
            cardmarket_url=cardmarket.get("url"),
        )
