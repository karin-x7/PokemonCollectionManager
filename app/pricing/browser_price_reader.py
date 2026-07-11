"""Re-export façade over the cross-platform Cardmarket price-reading stack.

This module used to contain everything -- URL building, on-screen-text
parsing, and the Windows-only UI Automation window reading -- in one file.
It's now split into:

- :mod:`app.pricing.cardmarket_parsing` -- pure, OS-agnostic URL-building
  and text-parsing logic, shared verbatim by every platform.
- :mod:`app.pricing.browser` -- picks the right platform backend
  (``_windows``, ``_macos``, ``_linux``) at import time based on
  ``sys.platform``, each exposing the same function names.

This module just re-exports both under their original names, so every
existing caller (``app.services.*``, ``app.ui.workers.*``, and this
module's own test suite before it was split) keeps working against the
stable ``app.pricing.browser_price_reader`` import path without needing to
know any of the above happened.
"""

from __future__ import annotations

from app.pricing.browser import (
    open_cardmarket_link,
    open_cardmarket_search,
    read_offers_for_card,
    read_product_info,
    read_sealed_offers_for_card,
    read_sealed_product_info,
    resolve_cardmarket_search_result,
    search_cardmarket,
)
from app.pricing.cardmarket_parsing import (
    BrowserPriceReaderError,
    build_filtered_url,
    build_sealed_filtered_url,
    find_alternate_version_url,
    is_market_divergent_language,
    is_unresolved_pokemontcg_shortlink,
    resolve_cardmarket_url,
    sealed_supports_language_filter,
    supports_language_filter,
    with_canonical_locale,
)

__all__ = [
    "BrowserPriceReaderError",
    "build_filtered_url",
    "build_sealed_filtered_url",
    "find_alternate_version_url",
    "is_market_divergent_language",
    "is_unresolved_pokemontcg_shortlink",
    "open_cardmarket_link",
    "open_cardmarket_search",
    "read_offers_for_card",
    "read_product_info",
    "read_sealed_offers_for_card",
    "read_sealed_product_info",
    "resolve_cardmarket_search_result",
    "resolve_cardmarket_url",
    "search_cardmarket",
    "sealed_supports_language_filter",
    "supports_language_filter",
    "with_canonical_locale",
]
