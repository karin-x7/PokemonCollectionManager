"""Cardmarket-adjacent market data integrations (via CardTrader).

The expansion/set client (:mod:`app.cardmarket.cardtrader_client`) was built
in Step 4 but catalogue search ended up using pokemontcg.io's own ``/sets``
list instead (see :mod:`app.services.catalog_search_service`) — CardTrader
and pokemontcg.io name the same sets differently (e.g. CardTrader's "Base
Set" vs. pokemontcg.io's "Base" for the 1999 base set), so resolving against
CardTrader and then filtering pokemontcg.io by that name risked matching the
wrong reprint. The client remains for Step 6 (marketplace offers/pricing,
where CardTrader is the primary, granular price source).
"""

from __future__ import annotations

from app.cardmarket.cardtrader_client import CardTraderClient, CardTraderClientError
from app.cardmarket.models import CardTraderExpansion

__all__ = ["CardTraderClient", "CardTraderClientError", "CardTraderExpansion"]
