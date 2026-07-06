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

import time
from collections.abc import Callable

from app.catalog.pokemontcg_client import (
    PokemonTcgClient,
    PokemonTcgClientError,
    has_ambiguous_cardmarket_variants,
)
from app.catalog.tcgdex_designation_lookup import (
    LocalizedDesignation,
    TcgdexDesignationLookupError,
    find_localized_designation,
)
from app.database.repositories.card_repository import CardRepository
from app.database.repositories.price_repository import PriceRepository
from app.logging_config import get_logger
from app.models.card import Card
from app.models.enums import Language, PriceQuality
from app.models.price import PriceRecord
from app.pricing.browser_price_reader import (
    BrowserPriceReaderError,
    build_filtered_url,
    find_alternate_version_url,
    is_unresolved_pokemontcg_shortlink,
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
#: A deliberately *noticeable* pause before opening the one alternate-
#: version tab (see ``_try_alternate_version``) -- this project previously
#: triggered a temporary Cardmarket account lockout by opening up to 6
#: candidate tabs back-to-back with no delay at all (see PROJECT_PROGRESS.md,
#: "Verworfener Versuch"). Never make this instant, and never try more than
#: one alternate.
_VERSION_SWITCH_DELAY_SECONDS = 3.0

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
        designation_lookup: Callable[
            [str, Language], LocalizedDesignation | None
        ] = find_localized_designation,
        version_switch_delay: float = _VERSION_SWITCH_DELAY_SECONDS,
    ) -> None:
        self._cards = card_repository
        self._prices = price_repository
        self._pokemontcg = pokemontcg_client
        self._offer_reader = offer_reader
        self._resolve_url = url_resolver
        self._designation_lookup = designation_lookup
        self._version_switch_delay = version_switch_delay

    def update_price_for_card(self, card_id: int) -> Card:
        """Look up and persist the current Cardmarket price for a card.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        card = self._cards.get(card_id)
        if card is None:
            raise CardNotFoundError(card_id)

        if card.manual_cardmarket_url:
            # A user-supplied override always wins -- typically set for a
            # Japanese/Korean/Chinese print (see the check below) once the
            # user has looked up the correct, language-specific Cardmarket
            # product themselves.
            real_url = card.manual_cardmarket_url
        elif not supports_language_filter(card.language):
            # Cardmarket lists Japanese/Korean/Chinese prints as entirely
            # separate products (often under the *Japanese* set's own name,
            # e.g. Neo Revelation's Ho-Oh is "Awakening Legends" there), not
            # as a language filter on the same product page. pokemontcg.io's
            # own cardmarket_url always points at the Western product --
            # silently falling through the ladder below against that URL
            # would misprice this card from unrelated Western copies. Bail
            # out with a clear rationale instead of guessing.
            return self._record(
                card,
                None,
                PriceQuality.NO_PRICE,
                f"Automatische Preisermittlung für {card.language.label} wird "
                "nicht unterstützt (Cardmarket führt diesen Druck als "
                "eigenständiges Produkt). Trage unter „Eigener Cardmarket-"
                "Link“ den korrekten Link ein, um die Preisermittlung für "
                "diese Karte zu aktivieren."
                + self._designation_hint(card),
            )
        else:
            if card.cardmarket_url and not (
                has_ambiguous_cardmarket_variants(card.set_code)
                and is_unresolved_pokemontcg_shortlink(card.cardmarket_url)
            ):
                # Already has a specific link -- whether it's an ordinary
                # set's own link or one of Base Set's two variant-specific
                # links (see CatalogSearchService, which resolves those
                # before the card is ever added), it's known-good and used
                # as-is. The exclusion only matters for a Base Set-style
                # card whose stored link is still pokemontcg.io's own
                # unresolved, variant-ambiguous shortlink (e.g. a card added
                # before this variant-splitting existed) -- that one is
                # deliberately *not* trusted here, same as if it had no
                # link at all.
                cardmarket_url = card.cardmarket_url
            elif has_ambiguous_cardmarket_variants(card.set_code):
                # Base Set-style sets split into multiple Cardmarket
                # products pokemontcg.io can't tell apart on its own --
                # checked before ever falling back to backfilling a link,
                # since a freshly backfilled one would just be
                # pokemontcg.io's single, arbitrary link again. Same remedy
                # as the Japanese/Korean/Chinese branch above: the user
                # fills in the exact link themselves (or -- the easier way
                # -- picks the specific variant from the catalogue search
                # results dialog to begin with, which already resolves this
                # correctly).
                return self._record(
                    card,
                    None,
                    PriceQuality.NO_PRICE,
                    f"{card.set_name} führt mehrere Druckvarianten (z. B. Normal/"
                    "Shadowless) als getrennte Cardmarket-Produkte, die "
                    "pokemontcg.io nicht auseinanderhält. Trage unter „Eigener "
                    "Cardmarket-Link“ den korrekten Link für die Version ein, "
                    "die du besitzt.",
                )
            else:
                cardmarket_url = self._backfill_cardmarket_url(card)
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
        # Extras are a hard requirement, not a loosenable ladder step: a
        # signed (or reverse holo) card must never be priced against
        # unsigned/non-reverse offers, so every tier below filters by these,
        # even the "fully unfiltered" last one -- that one is only
        # unfiltered with respect to language/condition.
        extras = {
            "signed": card.is_signed,
            "first_edition": card.is_first_edition,
            "altered": card.is_altered,
            "reverse_holo": card.is_reverse_holo,
        }

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
            **extras,
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
        same_language_url = build_filtered_url(
            base_url, language=card.language if language_filtered else None, **extras
        )
        try:
            offers = self._offer_reader(same_language_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        result = _exact_or_nearest_condition(card, offers, language_filtered)
        if result is not None:
            return result

        # Step 2.5: some vintage sets (e.g. Base Set) list a card's language
        # as an entirely separate Cardmarket *product* under a sibling
        # "-V<n>-" URL, not just a filter on this one page. Reaching here
        # with zero offers at all in this language (not just no exact/near
        # match, but the broadest same-language read above coming back
        # completely empty) is the signature of being on the wrong product
        # entirely, not just "no stock right now" -- worth one, and only
        # one, alternate-version tab before falling back to any-language.
        if language_filtered and not offers:
            alt_result = self._try_alternate_version(card, base_url, extras)
            if alt_result is not None:
                return alt_result

        # Step 3: same condition or better (server-filtered), any language.
        condition_url = build_filtered_url(base_url, min_condition=card.condition, **extras)
        try:
            offers = self._offer_reader(condition_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        result = _same_condition_other_language(card, offers)
        if result is not None:
            return result

        # Step 4: nothing matched language or condition — average over
        # every offer on the page (still scoped to the extras, but neither
        # language nor condition).
        extras_only_url = build_filtered_url(base_url, **extras)
        try:
            offers = self._offer_reader(extras_only_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)
        return _average(offers)

    def _try_alternate_version(
        self, card: Card, base_url: str, extras: dict[str, bool]
    ) -> _PriceResult | None:
        """One, and only one, sibling-version Cardmarket tab -- see the

        ``_VERSION_SWITCH_DELAY_SECONDS`` module docstring for why this
        must never become a candidate loop. A read failure here is silently
        treated as "no offers on the alternate either", not an error --
        this is an extra, best-effort attempt, and the ladder must still
        fall through to the ordinary any-language steps if it doesn't pan
        out. On success, the corrected URL is persisted back to the card
        (mirroring the existing shortlink-resolution self-correction) so
        every future lookup goes straight to the right product.
        """
        alternate_url = find_alternate_version_url(base_url)
        if alternate_url is None:
            return None

        time.sleep(self._version_switch_delay)

        at_or_better_url = build_filtered_url(
            alternate_url, language=card.language, min_condition=card.condition, **extras
        )
        try:
            offers = self._offer_reader(at_or_better_url, card.name)
        except BrowserPriceReaderError:
            offers = []
        result = _exact_or_nearest_condition(card, offers, language_already_filtered=True)

        if result is None:
            same_language_url = build_filtered_url(alternate_url, language=card.language, **extras)
            try:
                offers = self._offer_reader(same_language_url, card.name)
            except BrowserPriceReaderError:
                offers = []
            result = _exact_or_nearest_condition(card, offers, language_already_filtered=True)

        if result is not None:
            self._cards.update_cardmarket_url(card.id, alternate_url)
            logger.info(
                "Card id=%s: switched to alternate Cardmarket version %s (was %s)",
                card.id, alternate_url, base_url,
            )
        return result

    def _designation_hint(self, card: Card) -> str:
        """Best-effort suggestion of the Japanese/Korean/Chinese Cardmarket

        product to search for, via tcgdex.dev's *names* (never prices --
        see ``app.catalog.tcgdex_designation_lookup``'s own docstring for
        why). Empty string if no external id, no coverage, or the lookup
        itself fails -- this is a nice-to-have addition to the rationale
        above, not something that should ever break the price update.
        """
        if not card.external_card_id:
            return ""
        try:
            designation = self._designation_lookup(card.external_card_id, card.language)
        except TcgdexDesignationLookupError as exc:
            logger.warning("tcgdex designation lookup failed for card id=%s: %s", card.id, exc)
            return ""
        if designation is None:
            return ""
        return (
            f" Mögliche Bezeichnung auf Cardmarket (via tcgdex.dev): "
            f"„{designation.card_name}“, Set „{designation.set_name}“, "
            f"Nr. {designation.local_id}."
        )

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
