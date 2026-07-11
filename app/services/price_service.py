"""Business logic for determining and recording a card's Cardmarket price.

Applies the tolerant matching ladder from :class:`~app.models.enums.
PriceQuality`, in this fixed priority order (user-specified, live-reported
after the previous, uncapped "nearest condition" logic once matched a Poor
Cardmarket offer to a Near Mint card):

1. Same language, exact condition -> ``EXACT``.
2. Same language, condition +-1 step (never more) -> ``ESTIMATED_FROM_CONDITION``.
3. English, exact condition -> ``ESTIMATED_FROM_LANGUAGE`` (skipped entirely
   if the card's own language already *is* English -- tier 1/2 already
   covered that -- or if it's one of the market-divergent languages, see
   ``app.pricing.cardmarket_parsing.is_market_divergent_language``: a
   Japanese/Korean/Chinese card is never priced from an English offer,
   since unlike German vs. English these can have wildly different market
   values for what Cardmarket otherwise treats as the same product).
4. English, condition +-1 step -> ``ESTIMATED_FROM_LANGUAGE`` (same skip).
5. ``NO_PRICE`` -- deliberately no further "average over everything, ignore
   language/condition entirely" fallback; a guess with no distance limit at
   all is worse than admitting no price was found.

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
from app.i18n import tr
from app.logging_config import get_logger
from app.models.card import Card
from app.models.enums import Language, PriceQuality
from app.models.price import PriceRecord
from app.pricing.browser_price_reader import (
    BrowserPriceReaderError,
    build_filtered_url,
    find_alternate_version_url,
    is_market_divergent_language,
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

#: The hard cap on how far an estimated condition may deviate from the
#: card's own -- user-specified: a wildly different condition (e.g. Poor
#: standing in for Near Mint) is worse than no estimate at all. Distances
#: are measured via ``Condition.distance_to``, already used for "nearest"
#: selection before this cap existed.
_MAX_CONDITION_DISTANCE = 1


def _price_for_language(
    card: Card,
    offers: list[CardmarketOffer],
    target_language: Language,
    is_native_language: bool,
) -> _PriceResult | None:
    """Try exact condition, then condition +-1 (never more), against
    ``offers`` scoped to ``target_language``.

    Shared by both halves of the ladder: ``is_native_language=True`` scores
    the card's *own* language (tiers 1/2, quality EXACT/
    ESTIMATED_FROM_CONDITION), ``is_native_language=False`` scores the
    English fallback (tiers 3/4, always ESTIMATED_FROM_LANGUAGE since the
    print language itself already differs from the card's own). Always
    filters ``offers`` by ``target_language`` itself -- regardless of
    whether the page was already server-filtered by Cardmarket's own
    ``language`` parameter (see ``build_filtered_url``) or not (e.g. a
    language with no Cardmarket filter id at all, such as Japanese) -- so
    callers never need to track that separately. Returns ``None`` if
    nothing within the +-1 cap exists, so the caller can fall through to
    the next ladder tier.
    """
    scoped = [o for o in offers if o.language is target_language]
    if not scoped:
        return None

    exact = [o for o in scoped if o.condition is card.condition]
    if exact:
        cheapest = min(exact, key=lambda o: o.price)
        if is_native_language:
            return (
                cheapest.price,
                PriceQuality.EXACT,
                # No "Exact match:" prefix here -- PriceQuality.EXACT's own
                # label already says that; a live-reported UI change started
                # showing the label and this rationale together, which
                # duplicated the phrase ("Exact match — Exact match: English,
                # Near Mint."). Just the specific language/condition it
                # matched against.
                f"{target_language.label}, {card.condition.label}.",
            )
        return (
            cheapest.price,
            PriceQuality.ESTIMATED_FROM_LANGUAGE,
            # No "Geschätzt aus"/"Estimated from" prefix -- same reasoning as
            # the EXACT tier above: PriceQuality.ESTIMATED_FROM_LANGUAGE's own
            # label already says "Estimated from a different language", so
            # repeating it here just made this text longer than it needed to
            # be (live-reported: it visually overflowed the detail panel).
            tr("{found_language} statt {expected_language}, gleicher Zustand ({condition}).").format(
                found_language=target_language.label,
                expected_language=card.language.label,
                condition=card.condition.label,
            ),
        )

    with_condition = [o for o in scoped if o.condition is not None]
    if with_condition:
        nearest = min(
            with_condition, key=lambda o: (o.condition.distance_to(card.condition), o.price)
        )
        if nearest.condition.distance_to(card.condition) > _MAX_CONDITION_DISTANCE:
            return None
        if is_native_language:
            return (
                nearest.price,
                PriceQuality.ESTIMATED_FROM_CONDITION,
                # No "Geschätzt aus"/"Estimated from" prefix -- same reasoning
                # as the EXACT tier above: PriceQuality.ESTIMATED_FROM_
                # CONDITION's own label already says "Estimated from a
                # different condition".
                tr("{language}, {found_condition} statt {expected_condition}.").format(
                    language=target_language.label,
                    found_condition=nearest.condition.label,
                    expected_condition=card.condition.label,
                ),
            )
        return (
            nearest.price,
            PriceQuality.ESTIMATED_FROM_LANGUAGE,
            tr(
                "{found_language}, {found_condition} statt {expected_language}, "
                "{expected_condition}."
            ).format(
                found_language=target_language.label,
                found_condition=nearest.condition.label,
                expected_language=card.language.label,
                expected_condition=card.condition.label,
            ),
        )
    return None


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
            # card whose pokemontcg.io-sourced link points at the wrong
            # product entirely (see ``has_ambiguous_cardmarket_variants``
            # below for the one other place that happens), once the user has
            # looked up the correct Cardmarket product themselves.
            real_url = card.manual_cardmarket_url
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
                    tr(
                        "{set_name} führt mehrere Druckvarianten (z. B. "
                        "Normal/Shadowless) als getrennte Cardmarket-Produkte, "
                        "die pokemontcg.io nicht auseinanderhält. Trage unter "
                        "„Eigener Cardmarket-Link“ den korrekten Link für die "
                        "Version ein, die du besitzt."
                    ).format(set_name=card.set_name),
                )
            else:
                cardmarket_url = self._backfill_cardmarket_url(card)
                if cardmarket_url is None:
                    return self._record(
                        card,
                        None,
                        PriceQuality.NO_PRICE,
                        tr("Keine Cardmarket-Zuordnung für diese Karte bekannt."),
                    )

            # cardmarket_url (from pokemontcg.io) is a tracking shortlink whose
            # redirect target is fixed on their end -- any ?language=/
            # minCondition= filter appended to it gets silently dropped during
            # the redirect. Resolving to the real cardmarket.com URL first is
            # what lets the per-tier filters below actually take effect.
            real_url = self._resolve_url(cardmarket_url)
            if real_url != cardmarket_url:
                self._cards.update_cardmarket_url(card.id, real_url)

        price, quality, rationale = self.determine_price(card, real_url)
        return self._record(card, price, quality, rationale)

    def resolve_display_url(self, card_id: int) -> str | None:
        """The best Cardmarket URL to show a human for ``card_id``, if any is known.

        Backs the "Open Cardmarket link" context-menu action, which just
        opens the page for the user to look at themselves -- deliberately
        much simpler than ``update_price_for_card``'s own URL resolution:
        the safety checks there (bailing out for an ambiguous Base
        Set-style variant, or a Japanese/Korean/Chinese print with no
        filter) exist to stop an *automated* lookup from silently
        mispricing a card against the wrong product. None of that risk
        applies to a human looking at a possibly-imprecise page and
        judging for themselves, so this always returns whatever link is
        known, filtered by language/condition where Cardmarket supports it.

        Raises:
            CardNotFoundError: If the card does not exist.
        """
        card = self._cards.get(card_id)
        if card is None:
            raise CardNotFoundError(card_id)

        if card.manual_cardmarket_url:
            real_url = card.manual_cardmarket_url
        else:
            cardmarket_url = card.cardmarket_url or self._backfill_cardmarket_url(card)
            if cardmarket_url is None:
                return None
            real_url = self._resolve_url(cardmarket_url)
            if real_url != cardmarket_url:
                self._cards.update_cardmarket_url(card.id, real_url)

        if supports_language_filter(card.language):
            real_url = build_filtered_url(
                real_url, language=card.language, min_condition=card.condition
            )
        return real_url

    def determine_price(self, card: Card, base_url: str) -> tuple[float | None, PriceQuality, str]:
        """Walk the matching ladder, one Cardmarket-filtered page per step.

        Public (not just an internal step of ``update_price_for_card``):
        :class:`~app.services.wantlist_service.WantlistService` reuses this
        exact ladder for a not-yet-owned card too, via an ephemeral ``Card``
        built from the wantlist entry's own fields -- duplicating this
        logic would risk drifting out of sync with the various live-tuned
        edge cases described below.

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

        # Tier 1+2: same language, exact condition then +-1 (never more).
        # Two reads, not one: at-or-better is server-filtered together with
        # language where Cardmarket supports it -- a live smoke test found
        # that filtering by language alone could still return every
        # condition Cardmarket has in stock, and for a card with many cheap,
        # worse-than-requested offers, those buried the relevant ones
        # further down the page than this reader actually captures. Only
        # falls through to the broader, condition-unfiltered read below if
        # tier 1 (which structurally can't see anything *worse* than the
        # card's own condition, only same-or-better) doesn't find a hit
        # within the +-1 cap either.
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

        result = _price_for_language(card, offers, card.language, is_native_language=True)
        if result is not None:
            return result

        same_language_url = build_filtered_url(
            base_url, language=card.language if language_filtered else None, **extras
        )
        try:
            offers = self._offer_reader(same_language_url, card.name)
        except BrowserPriceReaderError as exc:
            return None, PriceQuality.NO_PRICE, str(exc)

        result = _price_for_language(card, offers, card.language, is_native_language=True)
        if result is not None:
            return result

        # Some vintage sets (e.g. Base Set) list a card's language as an
        # entirely separate Cardmarket *product* under a sibling "-V<n>-"
        # URL, not just a filter on this one page. Reaching here with zero
        # offers at all in this language (not just no exact/near match, but
        # the broadest same-language read above coming back completely
        # empty) is the signature of being on the wrong product entirely,
        # not just "no stock right now" -- worth one, and only one,
        # alternate-version tab before falling through to the English tier.
        if language_filtered and not offers:
            alt_result = self._try_alternate_version(card, base_url, extras)
            if alt_result is not None:
                return alt_result

        # Tier 3+4: English fallback, exact condition then +-1 -- skipped
        # entirely if the card's own language already *is* English (tier 1+2
        # above already covered that), or if it's one of the market-divergent
        # languages (see is_market_divergent_language's own docs): a
        # Japanese/Korean/Chinese card must never be silently priced from an
        # English offer, even within the usual condition-tolerance cap --
        # unlike German vs. English, these can have wildly different market
        # values for what Cardmarket otherwise treats as the same product.
        if card.language is not Language.ENGLISH and not is_market_divergent_language(
            card.language
        ):
            english_at_or_better_url = build_filtered_url(
                base_url, language=Language.ENGLISH, min_condition=card.condition, **extras
            )
            try:
                offers = self._offer_reader(english_at_or_better_url, card.name)
            except BrowserPriceReaderError as exc:
                return None, PriceQuality.NO_PRICE, str(exc)

            result = _price_for_language(card, offers, Language.ENGLISH, is_native_language=False)
            if result is not None:
                return result

            english_any_condition_url = build_filtered_url(
                base_url, language=Language.ENGLISH, **extras
            )
            try:
                offers = self._offer_reader(english_any_condition_url, card.name)
            except BrowserPriceReaderError as exc:
                return None, PriceQuality.NO_PRICE, str(exc)

            result = _price_for_language(card, offers, Language.ENGLISH, is_native_language=False)
            if result is not None:
                return result

        if is_market_divergent_language(card.language):
            return (
                None,
                PriceQuality.NO_PRICE,
                tr(
                    "Keine {language}-Angebote auf Cardmarket gefunden. Ein "
                    "Preis aus einer anderen Sprache wird nicht geschätzt, da "
                    "sich Marktpreise für {language} stark unterscheiden "
                    "können."
                ).format(language=card.language.label)
                + self._designation_hint(card),
            )

        # Nothing within the +-1 cap in either the card's own language or
        # English -- deliberately NO_PRICE here, not a guess averaged over
        # everything regardless of condition/language (see module docstring).
        return None, PriceQuality.NO_PRICE, tr("Keine Angebote auf Cardmarket gefunden.")

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
        result = _price_for_language(card, offers, card.language, is_native_language=True)

        if result is None:
            same_language_url = build_filtered_url(alternate_url, language=card.language, **extras)
            try:
                offers = self._offer_reader(same_language_url, card.name)
            except BrowserPriceReaderError:
                offers = []
            result = _price_for_language(card, offers, card.language, is_native_language=True)

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
        return " " + tr(
            "Mögliche Bezeichnung auf Cardmarket (via tcgdex.dev): "
            "„{card_name}“, Set „{set_name}“, Nr. {local_id}."
        ).format(
            card_name=designation.card_name,
            set_name=designation.set_name,
            local_id=designation.local_id,
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
