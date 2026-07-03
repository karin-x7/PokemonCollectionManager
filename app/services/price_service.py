"""Business logic for determining and recording a card's Cardmarket price.

Applies the tolerant matching ladder from :class:`~app.models.enums.
PriceQuality`: an exact language+condition match is preferred, falling back
step by step to a looser estimate, and finally to "no price found" — never a
hard failure. This is the only layer the GUI is allowed to call into for
price updates.

Each ladder step reads a separately Cardmarket-filtered page (via
``language``/``minCondition`` query parameters — see
:func:`~app.pricing.browser_price_reader.build_filtered_url`) rather than
fetching the whole, unfiltered offer list once and matching client-side. This
was a deliberate fix after a live smoke test caught the original single-fetch
design misattributing a price from a stale, unrelated background browser tab
(see PROJECT_PROGRESS.md, Schritt 7 follow-up): letting Cardmarket's own
filters narrow the page means there is far less unrelated content for the
window-reading step to misread, and it needs no reliable per-offer language
detection for the two most common ladder steps (EXACT / ESTIMATED_FROM_
CONDITION) since the server already guarantees the language match.
"""

from __future__ import annotations

from collections.abc import Callable

from app.catalog.pokemontcg_client import PokemonTcgClient, PokemonTcgClientError
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.price_repository import PriceRepository
from app.logging_config import get_logger
from app.models.card import Card
from app.models.enums import PriceQuality
from app.models.price import PriceRecord
from app.pricing.browser_price_reader import (
    BrowserPriceReaderError,
    build_filtered_url,
    read_offers_for_card,
    resolve_cardmarket_url,
    supports_language_filter,
)
from app.pricing.models import CardmarketOffer
from app.services.exceptions import CardNotFoundError
from app.utils.time import utc_now_iso

logger = get_logger(__name__)

_SOURCE = "cardmarket"
_CURRENCY = "EUR"

_PriceResult = tuple[float | None, PriceQuality, str]


def _exact_or_nearest_condition(
    card: Card, offers: list[CardmarketOffer], language_already_filtered: bool
) -> _PriceResult | None:
    """Try EXACT, then ESTIMATED_FROM_CONDITION, against same-language offers.

    ``offers`` must already be scoped to ``card.language`` — either because
    Cardmarket's own ``language`` filter guarantees it, or (when the card's
    language has no Cardmarket filter id, e.g. Japanese) because it was
    filtered client-side beforehand. Returns ``None`` if neither tier finds
    anything, so the caller can fall through to the next ladder step.
    """
    if not language_already_filtered:
        offers = [o for o in offers if o.language is card.language]
    if not offers:
        return None

    exact = [o for o in offers if o.condition is card.condition]
    if exact:
        cheapest = min(exact, key=lambda o: o.price)
        return (
            cheapest.price,
            PriceQuality.EXACT,
            f"Exakter Treffer: {card.language.label}, {card.condition.label}.",
        )

    with_condition = [o for o in offers if o.condition is not None]
    if with_condition:
        nearest = min(
            with_condition, key=lambda o: (o.condition.distance_to(card.condition), o.price)
        )
        return (
            nearest.price,
            PriceQuality.ESTIMATED_FROM_CONDITION,
            f"Geschätzt aus {card.language.label}, Zustand {nearest.condition.label} "
            f"statt {card.condition.label}.",
        )
    return None


def _same_condition_other_language(card: Card, offers: list[CardmarketOffer]) -> _PriceResult | None:
    """Try ESTIMATED_FROM_LANGUAGE: same condition, cheapest regardless of language."""
    same_condition = [o for o in offers if o.condition is card.condition]
    if not same_condition:
        return None
    cheapest = min(same_condition, key=lambda o: o.price)
    language_label = (
        cheapest.language.label if cheapest.language is not None else "unbekannter Sprache"
    )
    return (
        cheapest.price,
        PriceQuality.ESTIMATED_FROM_LANGUAGE,
        f"Geschätzt aus {language_label} statt {card.language.label}, "
        f"gleicher Zustand ({card.condition.label}).",
    )


def _average(offers: list[CardmarketOffer]) -> _PriceResult:
    """AVERAGE: mean price over every offer found, ignoring condition/language."""
    if not offers:
        return None, PriceQuality.NO_PRICE, "Keine Angebote auf Cardmarket gefunden."
    average = sum(o.price for o in offers) / len(offers)
    return (
        round(average, 2),
        PriceQuality.AVERAGE,
        "Durchschnitt über alle gefundenen Angebote, unabhängig von Zustand und Sprache.",
    )


class PriceService:
    """Determines and persists a card's current Cardmarket price."""

    def __init__(
        self,
        card_repository: CardRepository,
        price_repository: PriceRepository,
        pokemontcg_client: PokemonTcgClient,
        offer_reader: Callable[[str, str], list[CardmarketOffer]] = read_offers_for_card,
        url_resolver: Callable[[str], str] = resolve_cardmarket_url,
    ) -> None:
        self._cards = card_repository
        self._prices = price_repository
        self._pokemontcg = pokemontcg_client
        self._offer_reader = offer_reader
        self._resolve_url = url_resolver

    def update_price_for_card(self, card_id: int) -> Card:
        """Look up and persist the current Cardmarket price for a card.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        card = self._cards.get(card_id)
        if card is None:
            raise CardNotFoundError(card_id)

        cardmarket_url = card.cardmarket_url or self._backfill_cardmarket_url(card)
        if cardmarket_url is None:
            return self._record(
                card,
                None,
                PriceQuality.NO_PRICE,
                "Keine Cardmarket-Zuordnung für diese Karte bekannt.",
            )

        # cardmarket_url (from pokemontcg.io) is a tracking shortlink whose
        # redirect target is fixed on their end -- any ?language=/
        # minCondition= filter appended to it gets silently dropped during
        # the redirect. Resolving to the real cardmarket.com URL first is
        # what lets the per-tier filters below actually take effect.
        real_url = self._resolve_url(cardmarket_url)
        if real_url != cardmarket_url:
            self._cards.update_cardmarket_url(card.id, real_url)

        price, quality, rationale = self._determine_price(card, real_url)
        return self._record(card, price, quality, rationale)

    def _determine_price(self, card: Card, base_url: str) -> tuple[float | None, PriceQuality, str]:
        """Walk the matching ladder, one Cardmarket-filtered page per step.

        A read that raises :class:`BrowserPriceReaderError` (tab/window
        problem, nothing parseable at all) aborts immediately with
        ``NO_PRICE`` and that error's own message — it means the browser
        step itself failed, not that this particular tier had no matching
        offers, so retrying with a different filter wouldn't help. An empty
        (but successfully read) offer list, by contrast, just means "try the
        next, looser tier".
        """
        # Step 1: same language *and* at-or-better condition, both
        # server-filtered together where Cardmarket supports it. A live
        # smoke test found that filtering by language alone could still
        # return every condition Cardmarket has in stock -- for a card with
        # many cheap, worse-than-requested offers, those buried the
        # relevant (at-or-better) ones further down the page than this
        # reader actually captures. Combining both filters keeps the result
        # small enough that this can't happen.
        language_filtered = supports_language_filter(card.language)
        at_or_better_url = build_filtered_url(
            base_url,
            language=card.language if language_filtered else None,
            min_condition=card.condition,
        )
        try:
            offers = self._offer_reader(at_or_better_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        result = _exact_or_nearest_condition(card, offers, language_filtered)
        if result is not None:
            return result

        # Step 2: nothing at or better exists in this language -- widen to
        # every condition to find the nearest *worse* one instead. Only
        # reached when step 1 found literally no stock at all in this
        # language at the requested condition or better, so it's rare in
        # practice; the pagination risk step 1 avoids is accepted here.
        same_language_url = (
            build_filtered_url(base_url, language=card.language)
            if language_filtered
            else base_url
        )
        try:
            offers = self._offer_reader(same_language_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        result = _exact_or_nearest_condition(card, offers, language_filtered)
        if result is not None:
            return result

        # Step 3: same condition or better (server-filtered), any language.
        condition_url = build_filtered_url(base_url, min_condition=card.condition)
        try:
            offers = self._offer_reader(condition_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        result = _same_condition_other_language(card, offers)
        if result is not None:
            return result

        # Step 4: nothing matched language or condition — average over
        # every offer on the fully unfiltered page.
        try:
            offers = self._offer_reader(base_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)
        return _average(offers)

    def _backfill_cardmarket_url(self, card: Card) -> str | None:
        """Fetch a missing ``cardmarket_url`` for a card added before Step 7."""
        if not card.external_card_id:
            return None
        try:
            catalog_card = self._pokemontcg.get_card_by_id(card.external_card_id)
        except PokemonTcgClientError as exc:
            logger.warning("Could not backfill cardmarket_url for card id=%s: %s", card.id, exc)
            return None
        if catalog_card is None or not catalog_card.cardmarket_url:
            return None
        self._cards.update_cardmarket_url(card.id, catalog_card.cardmarket_url)
        return catalog_card.cardmarket_url

    def _record(
        self, card: Card, price: float | None, quality: PriceQuality, rationale: str
    ) -> Card:
        now = utc_now_iso()
        self._cards.update_price(card.id, price, _CURRENCY, quality, rationale, now)
        if price is not None:
            self._prices.add_record(
                PriceRecord(
                    id=None,
                    card_id=card.id,
                    price=price,
                    currency=_CURRENCY,
                    price_quality=quality,
                    rationale=rationale,
                    source=_SOURCE,
                )
            )
        logger.info("Price updated: card id=%s quality=%s price=%s", card.id, quality.value, price)
        return self._cards.get(card.id)
