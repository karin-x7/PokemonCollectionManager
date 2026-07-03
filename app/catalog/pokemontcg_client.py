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

import requests

from app.catalog.models import CatalogCard, CatalogSet
from app.logging_config import get_logger
from app.secrets import get_secret

logger = get_logger(__name__)

_BASE_URL = "https://api.pokemontcg.io/v2"
_DEFAULT_TIMEOUT = 20.0


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
    ) -> None:
        self._api_key = api_key if api_key is not None else get_secret(
            "pokemontcg_io", "api_key"
        )
        self._timeout = timeout
        self._session = session or requests.Session()
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
            CatalogSet(id=raw.get("id", ""), name=raw.get("name", ""))
            for raw in payload.get("data", [])
        ]
        return self._sets_cache

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
        try:
            response = self._session.get(
                f"{_BASE_URL}/cards/{external_id}",
                headers=self._headers(),
                timeout=self._timeout,
            )
            if response.status_code == 404:
                return None
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
        try:
            response = self._session.get(
                f"{_BASE_URL}{path}",
                params=params,
                headers=self._headers(),
                timeout=self._timeout,
            )
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

    @staticmethod
    def _parse_card(raw: dict) -> CatalogCard:
        set_info = raw.get("set") or {}
        images = raw.get("images") or {}
        cardmarket = raw.get("cardmarket") or {}
        return CatalogCard(
            external_id=raw.get("id", ""),
            name=raw.get("name", ""),
            set_name=set_info.get("name", ""),
            set_code=set_info.get("id", ""),
            card_number=raw.get("number", ""),
            rarity=raw.get("rarity") or "",
            image_small_url=images.get("small"),
            image_large_url=images.get("large"),
            cardmarket_url=cardmarket.get("url"),
        )
