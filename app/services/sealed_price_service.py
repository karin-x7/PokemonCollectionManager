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

Unlike sealed products, single *cards* genuinely can have Japanese/
Korean/Chinese prints as an entirely separate Cardmarket product with an
unrelated set name (see ``price_service.py``), where falling back across
languages would silently substitute a financially unrelated product's
price. That risk doesn't apply here in the same way -- a sealed product's
Japanese/Korean/Chinese offers live on the very same page as everything
else -- but the "any language" fallback is still skipped for these three:
if the (now correctly pre-filtered) page turns up no offers in the
requested language, it means there are currently no sellers for that
specific print language, not "close enough" -- e.g. a Japanese-exclusive
box has no reason to track Korean pricing just because Korean happens to
have sellers right now.
"""

from __future__ import annotations

from collections.abc import Callable

from app.database.repositories.sealed_price_repository import SealedPriceRepository
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.i18n import tr
from app.logging_config import get_logger
from app.models.enums import PriceQuality
from app.models.sealed_price import SealedPriceRecord
from app.models.sealed_product import SealedProduct
from app.pricing.browser_price_reader import (
    BrowserPriceReaderError,
    build_sealed_filtered_url,
    read_sealed_offers_for_card,
    sealed_supports_language_filter,
    supports_language_filter,
)
from app.pricing.models import SealedOffer
from app.services.exceptions import SealedProductNotFoundError
from app.utils.time import utc_now_iso

logger = get_logger(__name__)
_SOURCE = "cardmarket"

_CURRENCY = "EUR"


def _cheapest(offers: list[SealedOffer]) -> SealedOffer | None:
    return min(offers, key=lambda offer: offer.price) if offers else None


class SealedPriceService:
    """Determines and persists a sealed product's current Cardmarket price."""

    def __init__(
        self,
        repository: SealedProductRepository,
        price_repository: SealedPriceRepository,
        offer_reader: Callable[[str, str], list[SealedOffer]] = read_sealed_offers_for_card,
    ) -> None:
        self._repo = repository
        self._prices = price_repository
        self._offer_reader = offer_reader

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
        url = product.cardmarket_url
        if sealed_supports_language_filter(product.language):
            # Re-derive the filter fresh here rather than trusting that the
            # stored URL already carries it: products added/edited before
            # this filter existed for Japanese/Korean/Chinese (or before the
            # feature existed at all) have a stored URL with no filter at
            # all, and would otherwise keep reading the full, unfiltered
            # offer table forever. build_sealed_filtered_url is idempotent,
            # so this is a no-op if the stored URL is already correct.
            url = build_sealed_filtered_url(url, product.language)
        try:
            offers = self._offer_reader(url, product.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        same_language = _cheapest([o for o in offers if o.language is product.language])
        if same_language is not None:
            return (
                same_language.price,
                PriceQuality.EXACT,
                tr("Exakter Treffer: {language}.").format(language=product.language.label),
            )

        if not supports_language_filter(product.language):
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
