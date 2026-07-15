"""Cardmarket price lookup + persistence for sealed products.

Mirrors ``price_service.py``, drastically simplified: sealed products have
no condition ladder (Cardmarket only ever sells them sealed -- "Opened
products cannot be sold", confirmed live on a real product page) and no
pokemontcg.io shortlink to resolve (``cardmarket_url`` is always the user's
own pasted link already, never a tracking shortlink) -- the only tier is
"same language" vs. "any language". The stored ``cardmarket_url`` already
carries Cardmarket's own ``?language=`` filter where supported (rewritten by
``SealedProductService`` at add/edit time, via the sealed-specific
``sealed_supports_language_filter``/``build_sealed_filtered_url`` -- this
now covers Japanese/Korean/Traditional Chinese too, not just the six
western languages, see their docstrings for the live confirmation), so this
reads whatever that URL returns and matches language locally in Python as a
second, redundant safety net -- harmless if the page was already filtered,
still correct if it wasn't (e.g. an older product added before that fix).

The "any language" fallback is still always skipped for Japanese/Korean/
Chinese specifically (see ``app.pricing.cardmarket_parsing.
is_market_divergent_language``), regardless of whether the page could be
filtered: these print languages can have wildly different market prices
for what Cardmarket otherwise treats as the same product, unlike German vs.
English. If the (already language-filtered) page turns up no offers in the
requested language, that means there are currently no sellers for that
specific print language, not "close enough" -- e.g. a Japanese-exclusive
box has no reason to track Korean pricing just because Korean happens to
have sellers right now.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.i18n import tr
from app.logging_config import get_logger
from app.models.enums import PriceQuality
from app.models.sealed_price import SealedPriceRecord
from app.models.sealed_product import SealedProduct
from app.pricing.browser_price_reader import (
    BrowserPriceReaderError,
    build_sealed_filtered_url,
    is_market_divergent_language,
    read_sealed_offers_for_card,
    sealed_supports_language_filter,
)
from app.pricing.models import SealedOffer
from app.pricing.seller_location import resolve_seller_country_id
from app.services.exceptions import SealedProductNotFoundError
from app.utils.time import utc_now_iso

logger = get_logger(__name__)
_SOURCE = "cardmarket"

_CURRENCY = "EUR"

#: A deliberately *noticeable* pause before every single Cardmarket tab this
#: class opens -- see ``price_service._REQUEST_DELAY_SECONDS``'s own
#: docstring for the full history: this project has one confirmed incident
#: of a temporary Cardmarket account lockout from opening several tabs
#: back-to-back with no delay at all. Every read in this class goes through
#: :meth:`SealedPriceService._read_offers`, which always sleeps first.
_REQUEST_DELAY_SECONDS = 3.0


def _cheapest(offers: list[SealedOffer]) -> SealedOffer | None:
    return min(offers, key=lambda offer: offer.price) if offers else None


class SealedPriceService:
    """Determines and persists a sealed product's current Cardmarket price."""

    def __init__(
        self,
        repository: SealedProductRepository,
        price_repository: SealedPriceRepository,
        offer_reader: Callable[[str, str], list[SealedOffer]] = read_sealed_offers_for_card,
        settings_repository: SettingsRepository | None = None,
        request_delay: float = _REQUEST_DELAY_SECONDS,
    ) -> None:
        self._repo = repository
        self._prices = price_repository
        self._offer_reader = offer_reader
        # None (the default -- e.g. most tests) resolves to "no seller-
        # location filter", same as the setting being off; see
        # app.pricing.seller_location.
        self._settings = settings_repository
        self._request_delay = request_delay

    def _read_offers(self, url: str, match_hint: str) -> list[SealedOffer]:
        """Every ``offer_reader`` call in this class's ladder goes through

        here -- see ``_REQUEST_DELAY_SECONDS``'s own docstring for why the
        pause before each one is mandatory. Exceptions are intentionally
        left to propagate -- callers each already decide for themselves
        whether a raise here means "abort" or "try the next tier".
        """
        time.sleep(self._request_delay)
        return self._offer_reader(url, match_hint)

    def resolve_display_url(self, product_id: int) -> str | None:
        """The Cardmarket URL to show a human for ``product_id``, if any is known.

        Mirrors ``PriceService.resolve_display_url``, drastically simplified
        (see this module's own docstring): no shortlink resolution, no
        backfill -- ``cardmarket_url`` is always the user's own pasted link
        already. Backs the "Open Cardmarket link" context-menu action.

        Raises:
            SealedProductNotFoundError: If the product does not exist.
        """
        product = self._repo.get(product_id)
        if product is None:
            raise SealedProductNotFoundError(product_id)
        if product.cardmarket_url is None:
            return None
        if sealed_supports_language_filter(product.language):
            return build_sealed_filtered_url(product.cardmarket_url, product.language)
        return product.cardmarket_url

    def update_price_for_product(self, product_id: int) -> SealedProduct:
        """Look up and persist ``product_id``'s current Cardmarket price.

        Raises:
            SealedProductNotFoundError: If the product does not exist.
        """
        product = self._repo.get(product_id)
        if product is None:
            raise SealedProductNotFoundError(product_id)

        if product.cardmarket_url is None:
            return self._record(
                product,
                None,
                PriceQuality.NO_PRICE,
                tr("Keine Cardmarket-Zuordnung für dieses Produkt bekannt."),
            )

        price, quality, rationale = self._determine_price(product)
        return self._record(product, price, quality, rationale)

    def _determine_price(
        self, product: SealedProduct
    ) -> tuple[float | None, PriceQuality, str]:
        """Mirrors price_service.py's own seller-location wrapping (see its

        ``determine_price`` docstring for the full rationale), scaled down
        to sealed products' two-tier ladder ("exact" = same language,
        "buffer" = any other language, skipped for Japanese/Korean/Chinese):
        preferred-country exact, then all-country exact, then the buffer
        tier unfiltered by seller location -- each phase only runs once the
        previous one came back empty-handed. Off (the default), this
        collapses to a single, unfiltered-by-country pass, exactly as
        before.

        Deliberately *not* a country-filtered buffer phase too (an earlier
        version had one) -- see ``price_service.PriceService.
        determine_price``'s own docstring for why: needlessly more
        Cardmarket tabs for one lookup, for no real benefit once the
        cheaper exact-match checks above have already tried the preferred
        country.
        """
        seller_country_id = resolve_seller_country_id(self._settings)
        if seller_country_id is None:
            return self._run_ladder(product, seller_country=None)

        exact = self._check_same_language(product, seller_country_id)
        if exact is not None:
            return self._with_seller_location_note(exact, filtered=True)

        exact = self._check_same_language(product, None)
        if exact is not None:
            return self._with_seller_location_note(exact, filtered=False)

        result = self._run_ladder(product, seller_country=None, skip_exact=True)
        return self._with_seller_location_note(result, filtered=False)

    @staticmethod
    def _with_seller_location_note(
        result: tuple[float | None, PriceQuality, str], filtered: bool
    ) -> tuple[float | None, PriceQuality, str]:
        """Mirrors ``PriceService._with_seller_location_note`` -- see its own

        docstring. Only called when the "Only sellers from Germany" setting
        is actually on (see ``_determine_price``).
        """
        price, quality, rationale = result
        note = tr("Verkäuferstandort: Deutschland.") if filtered else tr("Verkäuferstandort: alle Länder.")
        combined = f"{rationale} {note}" if rationale else note
        return price, quality, combined

    def _filtered_url(self, product: SealedProduct, seller_country: int | None) -> str:
        # Re-derive the filter fresh here rather than trusting that the
        # stored URL already carries it: products added/edited before this
        # filter existed for Japanese/Korean/Chinese (or before the feature
        # existed at all) have a stored URL with no filter at all, and would
        # otherwise keep reading the full, unfiltered offer table forever.
        # build_sealed_filtered_url is idempotent, so this is a no-op if the
        # stored URL is already correct.
        return build_sealed_filtered_url(
            product.cardmarket_url, product.language, seller_country=seller_country
        )

    def _check_same_language(
        self, product: SealedProduct, seller_country: int | None
    ) -> tuple[float | None, PriceQuality, str] | None:
        """Tier-1-only check (same language as ``product``) -- the "exact match"

        half of the seller-location ladder, mirroring
        ``PriceService._check_exact_native``. ``None`` if no same-language
        offer was found, so the caller can fall through to the next phase --
        including when the read raises ``BrowserPriceReaderError``: a
        sellerCountry-filtered page legitimately having zero offers is the
        expected, common case for a narrow single-country filter, not a
        browser/read failure (see ``PriceService._check_exact_native``'s own
        docstring for the same reasoning in full).
        """
        try:
            offers = self._read_offers(self._filtered_url(product, seller_country), product.name)
        except BrowserPriceReaderError:
            return None
        same_language = _cheapest([o for o in offers if o.language is product.language])
        if same_language is None:
            return None
        return (
            same_language.price,
            PriceQuality.EXACT,
            # No "Exact match:" prefix -- PriceQuality.EXACT's own label
            # already says that; see price_service.py's matching fix for
            # the live-reported UI duplication this avoids.
            f"{product.language.label}.",
        )

    def _run_ladder(
        self, product: SealedProduct, seller_country: int | None, skip_exact: bool = False
    ) -> tuple[float | None, PriceQuality, str]:
        """The original, unwrapped matching ladder -- see :meth:`_determine_price`'s

        own docstring for how the seller-location preference (if any) wraps
        multiple calls to this around it. ``skip_exact`` is set by that
        wrapping once the same-language tier has already been tried (in
        both country states) and failed -- re-checking it here would be
        harmless (it would just fail again) but pointless.
        """
        try:
            offers = self._read_offers(self._filtered_url(product, seller_country), product.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        if not skip_exact:
            same_language = _cheapest([o for o in offers if o.language is product.language])
            if same_language is not None:
                return same_language.price, PriceQuality.EXACT, f"{product.language.label}."

        if is_market_divergent_language(product.language):
            # Japanese/Korean/Chinese: unlike German vs. English (same
            # product, plausibly similar value), these print languages can
            # have wildly different market prices for what Cardmarket
            # otherwise treats as offers on the same product page (the
            # stored URL is already filtered to this exact language via
            # sealed_supports_language_filter/build_sealed_filtered_url --
            # see sealed_product_service.py). No offers turning up here
            # means there are currently no sellers for this specific print
            # language, not "close enough" -- so this still refuses to
            # guess from a different language's price rather than silently
            # reporting one as an "estimate".
            return (
                None,
                PriceQuality.NO_PRICE,
                tr(
                    "Auf dieser Seite gibt es aktuell keine Angebote in "
                    "{expected} -- für Japanisch/Koreanisch/Chinesisch wird "
                    "aus einer anderen Sprache kein Schätzpreis übernommen, "
                    "da die Preise stark abweichen können."
                ).format(expected=product.language.label),
            )

        cheapest_any = _cheapest(offers)
        if cheapest_any is not None:
            language_label = (
                cheapest_any.language.label
                if cheapest_any.language is not None
                else tr("unbekannter Sprache")
            )
            return (
                cheapest_any.price,
                PriceQuality.ESTIMATED_FROM_LANGUAGE,
                tr("Geschätzt aus {found}, gewünscht war {expected}.").format(
                    found=language_label, expected=product.language.label
                ),
            )
        return None, PriceQuality.NO_PRICE, tr("Keine Angebote auf Cardmarket gefunden.")

    def _record(
        self,
        product: SealedProduct,
        price: float | None,
        quality: PriceQuality,
        rationale: str,
    ) -> SealedProduct:
        updated_at = utc_now_iso()
        self._repo.update_price(product.id, price, _CURRENCY, quality, rationale, updated_at)
        if price is not None:
            self._prices.add_record(
                SealedPriceRecord(
                    id=None,
                    sealed_product_id=product.id,
                    price=price,
                    currency=_CURRENCY,
                    price_quality=quality,
                    rationale=rationale,
                    source=_SOURCE,
                    recorded_at=updated_at,
                )
            )
        logger.info(
            "Sealed product price updated: id=%s quality=%s price=%s",
            product.id, quality.value, price,
        )
        return self._repo.get(product.id)
