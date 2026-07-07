"""Platform dispatch for the Cardmarket browser-reading backend.

Every supported OS gets its own module here (``_windows.py``, ``_macos.py``,
eventually ``_linux.py``), each exposing the exact same six functions --
window automation is fundamentally OS-specific (Windows UI Automation vs.
macOS's Accessibility API vs. Linux's AT-SPI have nothing in common at the
API level), but the *behaviour* every caller relies on is identical across
all three: open a Cardmarket URL in Chrome, read whatever text is visible,
close the tab again.

Picking the right module happens once, here, at import time -- callers
(``app.pricing.browser_price_reader``, and everything importing from it)
never branch on ``sys.platform`` themselves.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from app.pricing.browser._windows import (
        read_offers_for_card,
        read_product_info,
        read_sealed_offers_for_card,
        read_sealed_product_info,
        resolve_cardmarket_search_result,
        search_cardmarket,
    )
elif sys.platform == "darwin":
    from app.pricing.browser._macos import (
        read_offers_for_card,
        read_product_info,
        read_sealed_offers_for_card,
        read_sealed_product_info,
        resolve_cardmarket_search_result,
        search_cardmarket,
    )
else:
    # Linux (and anything else) has no backend yet -- see PROJECT_PROGRESS.md.
    # Deferred to first actual use (not import time) so the rest of the app
    # -- everything not touching live Cardmarket price lookups -- still
    # works fully on an unsupported platform (manual price entry, CSV/Excel
    # import/export, statistics, wantlist, ...).
    from app.pricing.browser._unsupported import (
        read_offers_for_card,
        read_product_info,
        read_sealed_offers_for_card,
        read_sealed_product_info,
        resolve_cardmarket_search_result,
        search_cardmarket,
    )

__all__ = [
    "read_offers_for_card",
    "read_product_info",
    "read_sealed_offers_for_card",
    "read_sealed_product_info",
    "resolve_cardmarket_search_result",
    "search_cardmarket",
]
