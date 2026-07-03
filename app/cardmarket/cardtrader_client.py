"""HTTP client for the CardTrader API (read-only).

Used from Step 4 onwards for the Pokémon expansion (set) list, which powers
fuzzy set-name resolution in :class:`app.services.catalog_search_service.
CatalogSearchService`. Marketplace/pricing endpoints (individual offers)
remain Step 6 scope.

Authenticated via the JWT in ``config/secrets.json`` (``cardtrader.
jwt_token``), read strictly (no buy/sell endpoints are used).
"""

from __future__ import annotations

import requests

from app.cardmarket.models import CardTraderExpansion
from app.logging_config import get_logger
from app.secrets import get_secret

logger = get_logger(__name__)

_BASE_URL = "https://api.cardtrader.com/api/v2"
_DEFAULT_TIMEOUT = 20.0

#: Verified live against the CardTrader API (GET /games) — stable game id.
POKEMON_GAME_ID = 5


class CardTraderClientError(Exception):
    """Raised when the CardTrader API cannot be reached or errors out."""


class CardTraderClient:
    """Thin read-only wrapper around the CardTrader ``/expansions`` endpoint."""

    def __init__(
        self,
        jwt_token: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self._jwt_token = jwt_token if jwt_token is not None else get_secret(
            "cardtrader", "jwt_token"
        )
        self._timeout = timeout
        self._session = session or requests.Session()
        self._expansions_cache: list[CardTraderExpansion] | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._jwt_token}"} if self._jwt_token else {}

    def list_pokemon_expansions(self) -> list[CardTraderExpansion]:
        """Return all Pokémon expansions (sets), cached after the first call.

        The CardTrader ``/expansions`` endpoint ignores the ``game_id`` query
        parameter server-side and always returns every game's expansions, so
        filtering happens client-side.

        Raises:
            CardTraderClientError: On a network error or non-2xx response.
        """
        if self._expansions_cache is not None:
            return self._expansions_cache

        try:
            response = self._session.get(
                f"{_BASE_URL}/expansions",
                headers=self._headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("CardTrader /expansions request failed: %s", exc)
            raise CardTraderClientError(
                "CardTrader (Set-Liste) ist gerade nicht erreichbar."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise CardTraderClientError(
                "Antwort von CardTrader (Set-Liste) war ungültig."
            ) from exc

        expansions = [
            CardTraderExpansion(
                id=raw["id"],
                game_id=raw["game_id"],
                code=raw.get("code", ""),
                name=raw.get("name", ""),
            )
            for raw in payload
            if raw.get("game_id") == POKEMON_GAME_ID
        ]
        self._expansions_cache = expansions
        return expansions
