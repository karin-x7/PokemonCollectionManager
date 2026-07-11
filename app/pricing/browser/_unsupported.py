"""Placeholder backend for platforms with no native reader yet (Linux).

Same six-function contract as ``_windows``/``_macos``, but every function
just raises -- there is nothing to fall back to (no HTTP scraping: see
``app.pricing.browser_price_reader``'s own module docstring for why), so
this is picked up automatically by ``app.pricing.browser`` on any platform
that isn't Windows or macOS, and swapped for a real ``_linux`` module once
that backend exists (task: Cross-Platform-Port Phase 2).
"""

from __future__ import annotations

import sys

from app.i18n import tr
from app.pricing.cardmarket_parsing import BrowserPriceReaderError
from app.pricing.models import CardmarketOffer, CardmarketSearchResult, ProductInfo, SealedOffer, SealedProductInfo


def _unsupported() -> BrowserPriceReaderError:
    return BrowserPriceReaderError(
        tr(
            "Cardmarket-Preisabruf wird auf dieser Plattform ({platform}) noch "
            "nicht unterstützt."
        ).format(platform=sys.platform)
    )


def read_product_info(
    url: str, timeout: float = 30.0, capture_image: bool = False
) -> ProductInfo:
    raise _unsupported()


def read_offers_for_card(
    url: str, match_hint: str, timeout: float = 30.0
) -> list[CardmarketOffer]:
    raise _unsupported()


def search_cardmarket(name: str, timeout: float = 30.0) -> list[CardmarketSearchResult]:
    raise _unsupported()


def resolve_cardmarket_search_result(
    name: str, chosen: CardmarketSearchResult, timeout: float = 30.0
) -> str:
    raise _unsupported()


def read_sealed_product_info(
    url: str, timeout: float = 30.0, capture_image: bool = False
) -> SealedProductInfo:
    raise _unsupported()


def read_sealed_offers_for_card(
    url: str, match_hint: str, timeout: float = 30.0
) -> list[SealedOffer]:
    raise _unsupported()


def open_cardmarket_link(url: str) -> None:
    raise _unsupported()


def open_cardmarket_search(name: str) -> None:
    raise _unsupported()
