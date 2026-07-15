"""Cardmarket URL-building and on-screen-text-parsing logic.

Deliberately has **no** operating-system dependency at all (no window
automation, no ``subprocess``) -- every platform's browser-reading backend
(``app.pricing.browser._windows``, ``._macos``, ``._linux``) shares this
exact same module for building filtered Cardmarket URLs and turning a flat
list of on-screen text tokens into parsed offers/product info. Splitting
this out (rather than duplicating it three times, once per platform) means
a parsing fix only ever needs to happen once, and stays fully unit-testable
without any real browser/window involved, regardless of which platform's
backend is actually in use.
"""

from __future__ import annotations

import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from app.catalog.name_translation import translate_name_with_suffix
from app.i18n import tr
from app.logging_config import get_logger
from app.models.enums import Condition, Language, SealedCategory
from app.pricing.models import CardmarketOffer, CardmarketSearchResult, ProductInfo, SealedOffer, SealedProductInfo

logger = get_logger(__name__)


class BrowserPriceReaderError(Exception):
    """Raised when a card's Cardmarket offers couldn't be read."""


_CONDITION_CODES = {
    "MT": Condition.MINT,
    "NM": Condition.NEAR_MINT,
    "EX": Condition.EXCELLENT,
    "GD": Condition.GOOD,
    "LP": Condition.LIGHT_PLAYED,
    "PL": Condition.PLAYED,
    "PO": Condition.POOR,
}
#: Cardmarket renders its offer table in whatever locale the product URL's
#: own path prefix selects (e.g. ".../de/..." for German) -- a user pasting
#: a link from their own, German-language Cardmarket session (the normal
#: case, not something this app controls) gets a page whose "Sprache"
#: column shows the German word for each print language ("Deutsch",
#: "Englisch", ...), not the English one. Cards don't notice this (their
#: offer rows are anchored on the condition badge, e.g. "NM", which Cardmarket
#: renders identically in every locale) but sealed products have no
#: condition ladder and are anchored on the language word instead -- without
#: this table, a German-locale sealed-product page silently parsed to zero
#: offers every time (real, live-confirmed bug: "Preis von Cardmarket
#: abrufen" always returned "kein Preis gefunden" for a /de/ URL).
_GERMAN_LANGUAGE_LABELS: dict[str, Language] = {
    "englisch": Language.ENGLISH,
    "deutsch": Language.GERMAN,
    "französisch": Language.FRENCH,
    "italienisch": Language.ITALIAN,
    "spanisch": Language.SPANISH,
    "portugiesisch": Language.PORTUGUESE,
    "japanisch": Language.JAPANESE,
    "koreanisch": Language.KOREAN,
    "chinesisch": Language.CHINESE,
}
_LANGUAGE_BY_LABEL = {
    **{language.label.casefold(): language for language in Language},
    **_GERMAN_LANGUAGE_LABELS,
}

#: Cardmarket's own numeric ids for its ``language``/``minCondition`` product-page
#: query filters, confirmed live by reading the filter form's own input elements
#: (not documented anywhere public). Note these are *not* contiguous -- e.g.
#: Dutch is 12. Previously assumed Japanese/Korean/Chinese had no filter id at
#: all here (single cards in those languages were treated as an entirely
#: separate Cardmarket product, e.g. Neo Revelation's Ho-Oh being "Awakening
#: Legends") -- live-reported (with a screenshot) that this was wrong for the
#: general case: ``?language=7&minCondition=3`` on an ordinary single card's
#: own product page (Ho-Oh EX, "Rage of the Broken Heavens") correctly
#: narrowed straight to its Japanese/Excellent-or-better offers, same ids as
#: the sealed-product table below already used. The "separate product"
#: scenario is real but narrower than assumed: it's specific to certain
#: vintage/reprint sets whose pokemontcg.io-sourced URL points at the wrong
#: product entirely, not a general property of these three languages -- see
#: :func:`~app.services.price_service.PriceService._try_alternate_version`
#: and the manual-Cardmarket-link override for how that narrower case is
#: still handled.
_CARDMARKET_LANGUAGE_IDS: dict[Language, int] = {
    Language.ENGLISH: 1,
    Language.FRENCH: 2,
    Language.GERMAN: 3,
    Language.SPANISH: 4,
    Language.ITALIAN: 5,
    Language.PORTUGUESE: 8,
    Language.JAPANESE: 7,
    Language.KOREAN: 10,
    Language.CHINESE: 11,
}

#: Sealed products and single cards turned out to share the exact same
#: language-filter ids (see the correction above) -- kept as its own name
#: rather than replacing every call site, since ``sealed_supports_language_
#: filter``/``build_sealed_filtered_url`` are still meaningfully distinct
#: *functions* (sealed products have no condition ladder or extras filter at
#: all, for instance), just no longer a distinct *language set*.
_SEALED_CARDMARKET_LANGUAGE_IDS: dict[Language, int] = _CARDMARKET_LANGUAGE_IDS

#: Japanese/Korean/Chinese prints of the *same* card can have wildly
#: different market prices from Western-language copies -- unlike, say,
#: German vs. English (the same product, plausibly similar value). This is
#: unrelated to whether Cardmarket exposes a URL filter for these languages
#: (see the correction above, it does): it's a deliberate refusal to ever
#: silently estimate one of these three languages' price *from* a different
#: language's offers, even when the ordinary condition-tolerance ladder
#: would otherwise allow it. Named/checked separately from
#: :func:`supports_language_filter` so the two concerns -- "can this URL be
#: filtered by language" vs. "is cross-language price estimation safe for
#: this language" -- can't accidentally get tangled again.
_MARKET_DIVERGENT_LANGUAGES = frozenset({Language.JAPANESE, Language.KOREAN, Language.CHINESE})
#: Cardmarket's own numeric id for Germany in its ``sellerCountry`` filter --
#: live-confirmed by the user (``?sellerCountry=7`` on a real product page
#: correctly narrowed to German sellers only). Not contiguous with anything
#: else on this page (in particular, *not* 1, despite Germany being
#: Cardmarket's home market) -- like the language ids above, not derivable
#: from the filter UI's own (alphabetical) display order, so no other
#: country id is assumed here without the same kind of live confirmation.
SELLER_COUNTRY_GERMANY_ID = 7

#: ``minCondition`` matches this condition *or better*; ids run Mint(1)..Poor(7),
#: identical order to our own :class:`Condition` enum.
_CARDMARKET_CONDITION_IDS: dict[Condition, int] = {
    Condition.MINT: 1,
    Condition.NEAR_MINT: 2,
    Condition.EXCELLENT: 3,
    Condition.GOOD: 4,
    Condition.LIGHT_PLAYED: 5,
    Condition.PLAYED: 6,
    Condition.POOR: 7,
}

#: A price in either German ("1.234,56 €") or English ("1,234.56 €") number
#: formatting -- which one Cardmarket renders in depends on the resolved
#: URL's locale prefix (``/de/`` vs. ``/en/``, itself determined by
#: whatever the pokemontcg.io shortlink's redirect/session cookies default
#: to, not something this project controls), so both must be recognised.
#: This intentionally only requires *some* separator before the final two
#: decimal digits -- see :func:`_parse_price` for how the actual decimal
#: separator is determined from it.
_PRICE_RE = re.compile(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€")
#: A bare quantity token (small integer) immediately following a price.
_QUANTITY_RE = re.compile(r"^\d{1,3}$")

#: Cardmarket's own product-page title, live-confirmed as
#: "<Name> (<Number>) - <Set> | Cardmarket" (the OS window title tacks on
#: " - Google Chrome"; the plain tab title doesn't -- this matches either
#: since it only anchors on the "| Cardmarket" suffix). "<Number>" is blank
#: for products with no printed number (e.g. some promos).
_PRODUCT_TITLE_RE = re.compile(r"^(?P<name>.+?) \((?P<number>[^)]*)\) - (?P<set_name>.+?) \| Cardmarket")

#: Sealed products' own product-page title has no "(<Number>) - <Set>" part
#: at all, live-confirmed as just "<Name> | Cardmarket" (e.g. "Base Set
#: Booster Box | Cardmarket") -- a different format from single cards, since
#: they have no card number and aren't grouped under a specific set/language
#: the way single-card products are.
_SEALED_TITLE_RE = re.compile(r"^(?P<name>.+?) \| Cardmarket")

#: Cardmarket's product-slug version suffix -- some vintage sets list a
#: language as an entirely separate *product* under a sibling version
#: number, not a filter on one shared page (real, live-confirmed case:
#: Base Set's Venusaur is "-V2-BS15", English-only, vs. "-V1-BS15",
#: multi-language -- pokemontcg.io links the wrong one for a non-English
#: card). Live-checked against the real database: the suffix isn't always
#: followed by another "-" -- e.g. ".../Umbreon-VMAX-V1?utm_source=..." ends
#: right at the "?" -- so this only requires the leading "-V" and digits,
#: not a specific trailing character, and the digit span is replaced
#: in-place (not via a template substitution) so whatever follows
#: (another "-", a "?query", or nothing) is left completely untouched.
_VERSION_SUFFIX_RE = re.compile(r"-V(\d+)")

#: Matches "https://www.cardmarket.com/<locale>/<rest>" -- the two-letter
#: path segment right after the domain is Cardmarket's own UI-locale
#: selector (not to be confused with the *print-language* ``?language=N``
#: query filter from :func:`build_filtered_url`, which is a wholly separate,
#: locale-independent concept).
_CARDMARKET_LOCALE_RE = re.compile(r"^(https?://(?:www\.)?cardmarket\.com)/[a-z]{2}(/.*)$")

#: A search-result page's own hyperlinks flatten every descendant text node
#: into one accessible name, live-confirmed as "<Name> <Set> \xa0<Name>
#: (<Code>) From <Price>" -- the name appears twice (once from the product
#: image's alt text, once from the title text below it), which is exactly
#: what the backreference below relies on to find the right split point
#: even when the set name itself contains spaces.
_SEARCH_RESULT_RE = re.compile(
    r"^(?P<name>.+?) (?P<set_name>.+?) \xa0(?P=name) \((?P<code>[^)]+)\) From (?P<price>.+)$"
)

#: A live incident found pokemontcg.io itself (the same host that serves
#: the ``prices.pokemontcg.io`` shortlink resolved here) briefly taking
#: >30s to respond -- past this function's own timeout, with no retry at
#: all, it silently fell back to opening the *unresolved* shortlink in
#: Chrome, whose own redirect page doesn't render as a real Cardmarket
#: product page. One retry gives a second chance before giving up.
_RESOLVE_MAX_ATTEMPTS = 2
_RESOLVE_TIMEOUT = 10
_RESOLVE_RETRY_DELAY = 1.0

#: Host of pokemontcg.io's own tracking shortlink -- see
#: :func:`resolve_cardmarket_url`'s docstring below.
_POKEMONTCG_SHORTLINK_PREFIX = "https://prices.pokemontcg.io/"


def is_unresolved_pokemontcg_shortlink(url: str) -> bool:
    """Whether ``url`` is still pokemontcg.io's own tracking shortlink,

    not yet resolved to a real cardmarket.com product page -- used by
    ``price_service.py`` to tell an already-resolved, card-specific link
    (e.g. one of Base Set's two variant-specific links, picked via the
    catalogue search results dialog) apart from a still-untouched, possibly
    variant-ambiguous one that happens to already be stored on the card
    (e.g. from before that variant-splitting existed).
    """
    return url.startswith(_POKEMONTCG_SHORTLINK_PREFIX)


def resolve_cardmarket_url(
    url: str, session: requests.Session | None = None, retry_delay: float = _RESOLVE_RETRY_DELAY
) -> str:
    """Follow redirects to the actual cardmarket.com product page.

    ``card.cardmarket_url`` (sourced from pokemontcg.io's own API) is a
    tracking shortlink (``prices.pokemontcg.io/cardmarket/<id>``), not a
    direct link — a live smoke test caught that this shortlink's redirect
    target is a **fixed** string on pokemontcg.io's end. Any ``language``/
    ``minCondition`` query parameters appended to the shortlink are silently
    dropped during the redirect, landing on the fully unfiltered page every
    time regardless of what filter was requested. Resolving the redirect
    first and filtering the *real* URL avoids this.

    Retries once on a timeout/connection error (see above) before falling
    back to the original ``url`` (unresolved) -- the browser will still open
    *something* rather than nothing, but a resolved URL is much better.
    """
    http = session or requests.Session()
    for attempt in range(1, _RESOLVE_MAX_ATTEMPTS + 1):
        try:
            response = http.get(url, allow_redirects=True, timeout=_RESOLVE_TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as exc:
            logger.warning(
                "Could not resolve redirect for %s, attempt %d/%d: %s",
                url, attempt, _RESOLVE_MAX_ATTEMPTS, exc,
            )
            if attempt < _RESOLVE_MAX_ATTEMPTS:
                time.sleep(retry_delay)
                continue
            return url
        except requests.RequestException as exc:
            logger.warning("Could not resolve redirect for %s: %s -- using it as-is.", url, exc)
            return url
        else:
            return response.url
    return url


def find_alternate_version_url(url: str) -> str | None:
    """The single most plausible sibling version of ``url``, if it has a

    recognisable "-V<n>" product-slug suffix at all -- ``None`` for a
    modern card's URL (no such suffix), which never has this problem.
    Prefers the *lower* version number first (the confirmed real case,
    Base Set, has the multi-language product at the lower number) and
    falls back to the next higher one only if there's no lower number left.
    """
    match = _VERSION_SUFFIX_RE.search(url)
    if match is None:
        return None
    current = int(match.group(1))
    candidate = current - 1 if current > 1 else current + 1
    start, end = match.span(1)
    return f"{url[:start]}{candidate}{url[end:]}"


def supports_language_filter(language: Language) -> bool:
    """Whether Cardmarket exposes ``language`` as a filter on this product page."""
    return language in _CARDMARKET_LANGUAGE_IDS


def is_market_divergent_language(language: Language) -> bool:
    """Whether ``language`` must never be silently estimated from a

    different language's offers -- see :data:`_MARKET_DIVERGENT_LANGUAGES`'s
    own docs for why this is a separate concern from
    :func:`supports_language_filter`.
    """
    return language in _MARKET_DIVERGENT_LANGUAGES


def build_filtered_url(
    base_url: str,
    *,
    language: Language | None = None,
    min_condition: Condition | None = None,
    signed: bool | None = None,
    first_edition: bool | None = None,
    altered: bool | None = None,
    reverse_holo: bool | None = None,
    seller_country: int | None = None,
) -> str:
    """Append Cardmarket's own query filters for language/condition/extras.

    All of these are applied by Cardmarket itself, server-side, so the
    returned page already contains only matching offers, sorted by price —
    this lets the reader work from a short, already-narrowed list instead of
    scanning (and potentially misreading) the full, unfiltered offer table.
    ``min_condition`` means "this condition or better", matching Cardmarket's
    own semantics. A ``language`` with no known Cardmarket id (see
    :func:`supports_language_filter`) is silently ignored — callers should
    check first if an unfiltered fallback matters.

    ``signed``/``first_edition``/``altered``/``reverse_holo`` map to
    Cardmarket's own ``isSigned``/``isFirstEd``/``isAltered``/
    ``isReverseHolo`` filters — all four *bare* top-level parameters, not
    nested under ``extra[...]``. Unlike ``language``/``min_condition`` these
    four are almost always passed as a definite ``True``/``False`` rather
    than left ``None``: a real card either is or isn't signed, so leaving
    this unset would silently match against a page mixing signed and
    unsigned offers, breaking an "exact" match's accuracy.

    ``seller_country`` maps to Cardmarket's own ``sellerCountry`` filter (see
    :data:`SELLER_COUNTRY_GERMANY_ID`) -- ``None`` (the default) omits it
    entirely, i.e. no seller-location narrowing at all.
    """
    params: dict[str, int | str] = {}
    if language is not None and language in _CARDMARKET_LANGUAGE_IDS:
        params["language"] = _CARDMARKET_LANGUAGE_IDS[language]
    if min_condition is not None:
        params["minCondition"] = _CARDMARKET_CONDITION_IDS[min_condition]
    if signed is not None:
        params["isSigned"] = "Y" if signed else "N"
    if first_edition is not None:
        params["isFirstEd"] = "Y" if first_edition else "N"
    if altered is not None:
        params["isAltered"] = "Y" if altered else "N"
    if reverse_holo is not None:
        params["isReverseHolo"] = "Y" if reverse_holo else "N"
    if seller_country is not None:
        params["sellerCountry"] = seller_country
    if not params:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


def sealed_supports_language_filter(language: Language) -> bool:
    """Whether Cardmarket exposes ``language`` as a filter on a *sealed*

    product's page -- a strictly larger set than :func:`supports_language_filter`,
    which only covers single cards (see :data:`_SEALED_CARDMARKET_LANGUAGE_IDS`'s
    own docs for why the two are intentionally different).
    """
    return language in _SEALED_CARDMARKET_LANGUAGE_IDS


def build_sealed_filtered_url(
    base_url: str, language: Language, *, seller_country: int | None = None
) -> str:
    """Set Cardmarket's own ``?language=N``/``?sellerCountry=N`` filters for a sealed product.

    Sealed products have no condition ladder or extras (signed, 1st edition,
    reverse holo, ...) to filter by at all, so unlike :func:`build_filtered_url`
    this only ever narrows by language and seller country. A ``language`` with
    no known id (see :func:`sealed_supports_language_filter`) is silently
    ignored, same convention as :func:`build_filtered_url`; ``seller_country``
    left ``None`` (the default) omits that filter entirely.

    Idempotent: any pre-existing ``language``/``sellerCountry`` query
    parameter is replaced rather than duplicated. This matters because,
    unlike single cards, a sealed product's stored ``cardmarket_url`` may
    already carry this same filter from when it was added/edited -- price
    lookups re-derive the filter fresh from whatever URL is stored (see
    ``SealedPriceService``), so calling this twice on an already-filtered URL
    must not stack a second ``&language=``/``&sellerCountry=`` onto it.
    """
    parts = urlsplit(base_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query)
        if key not in ("language", "sellerCountry")
    ]
    if sealed_supports_language_filter(language):
        query.append(("language", str(_SEALED_CARDMARKET_LANGUAGE_IDS[language])))
    if seller_country is not None:
        query.append(("sellerCountry", str(seller_country)))
    return urlunsplit(parts._replace(query=urlencode(query)))


def with_canonical_locale(url: str, locale: str = "en") -> str:
    """Rewrite ``url``'s own UI-locale path segment to ``locale``, leaving

    everything else (path, query string) untouched. ``None`` if ``url``
    doesn't look like a Cardmarket product URL, returned unchanged instead.

    Used only when *reading offers* for a price lookup, never when reading
    a product's own name/category: Cardmarket renders the offer table's
    boilerplate text (the language word per offer, "you must be logged
    in..." etc.) in whatever locale the URL's own path segment selects --
    a user browsing (and pasting links from) Cardmarket in French, Spanish,
    Italian, etc. would hit the exact same class of "zero offers parsed"
    bug this project's own German users already did, one locale at a time,
    if the reader tried to keep a translated word list per locale instead.
    Canonicalising to one fixed locale before the actual scrape sidesteps
    that entirely, while leaving the *stored* URL (what a user might click
    themselves) in whatever locale they originally pasted -- this only
    rewrites a temporary, in-memory copy used for the one read.
    """
    match = _CARDMARKET_LOCALE_RE.match(url)
    if match is None:
        return url
    return f"{match.group(1)}/{locale}{match.group(2)}"


def _parse_price(token: str) -> float | None:
    """Parse a matched price, working out which separator is the decimal

    point regardless of locale: it's whichever of ``,``/``.`` appears
    *last* -- German ("1.234,56") ends in a comma, English ("1,234.56")
    ends in a period -- any earlier occurrences are thousands separators
    and simply dropped.
    """
    match = _PRICE_RE.search(token)
    if not match:
        return None
    raw = match.group(1)
    decimal_pos = max(raw.rfind(","), raw.rfind("."))
    integer_part = raw[:decimal_pos].replace(",", "").replace(".", "")
    decimal_part = raw[decimal_pos + 1 :]
    return float(f"{integer_part}.{decimal_part}")


def _first_match(span: list[str], table: dict, normalize):
    """Return the first value in ``table`` whose key matches a token in
    ``span`` (after applying ``normalize``), or ``None``."""
    for token in span:
        value = table.get(normalize(token))
        if value is not None:
            return value
    return None


def _parse_offer_lines(lines: list[str]) -> list[CardmarketOffer]:
    """Group a flat, ordered list of on-screen text tokens into offers.

    Cardmarket's offer table renders, per row, roughly: a seller rating
    number, seller name, a condition badge as plain text
    (``MT``/``NM``/``EX``/``GD``/``LP``/``PL``/``PO``), a language flag icon
    (whose accessible name, e.g. ``"Italian"``, appears as its own text
    token), an optional comment, a price, and a quantity — but the exact
    order/spacing can vary, so this scans for a price as the end of each row
    and looks for a condition/language token anywhere in the tokens since
    the previous row ended, rather than assuming fixed positions.

    A row without a recognisable condition badge is treated as page noise
    (e.g. the "7-day average price" summary figures) and dropped — every
    genuine offer row has one.
    """
    offers: list[CardmarketOffer] = []
    row_start = 0
    index = 0
    while index < len(lines):
        price = _parse_price(lines[index])
        if price is None:
            index += 1
            continue

        span = lines[row_start:index]
        condition = _first_match(span, _CONDITION_CODES, str.upper)
        language = _first_match(span, _LANGUAGE_BY_LABEL, str.casefold)
        seller = next((tok for tok in span if tok and not tok.isdigit() and tok != "K"), "")

        # Skip the quantity token that follows the price, if present.
        next_index = index + 1
        if next_index < len(lines) and _QUANTITY_RE.match(lines[next_index]):
            next_index += 1

        if condition is not None:
            offers.append(
                CardmarketOffer(seller=seller, condition=condition, language=language, price=price)
            )
        row_start = next_index
        index = next_index

    return offers


#: Cardmarket's own cookie-consent banner text, in every locale this project
#: has actually seen it in -- live-confirmed on a brand-new Chrome profile's
#: very first visit (not specific to locale-switching: any real user of a
#: public build of this app would hit the exact same banner on their own
#: first-ever price lookup). Declining non-essential cookies, not accepting
#: all, per this project's own privacy stance.
_COOKIE_DECLINE_BUTTON_TEXTS = {
    "only required cookies",
    "nur erforderliche cookies",
}


def has_cookie_decline_button_text(text: str) -> bool:
    """Whether ``text`` is one of Cardmarket's own "decline non-essential

    cookies" button labels -- shared so every platform backend's own
    cookie-banner-dismiss logic recognises the same set of labels."""
    return text.strip().casefold() in _COOKIE_DECLINE_BUTTON_TEXTS


def _has_cookie_banner(lines: list[str]) -> bool:
    """Whether ``lines`` still shows Cardmarket's own cookie-consent banner

    text -- a live-confirmed intermittent case where the banner's own text
    is momentarily present at the same time the button controls needed to
    dismiss it aren't reliably clickable yet (the page is still settling),
    so this is treated the same as "too few lines" below: a signal to wait
    and re-read, not a final result."""
    return any("cardmarket uses cookies" in line.casefold() for line in lines)


def _has_bot_check(lines: list[str]) -> bool:
    """Whether ``lines`` shows Cardmarket's own Cloudflare bot-check

    interstitial ("Checking your Browser…") instead of the real page.

    Live-reported: this interstitial's own chrome (tab strip, "Ray ID",
    Cloudflare branding, etc.) easily clears the same line-count threshold
    ``_has_cookie_banner`` and the "too few lines" check use for "still
    loading" -- so it was previously accepted as a normal, fully-rendered
    page with zero offers on it, and the tab closed immediately afterwards,
    long before Cloudflare's own automatic JS verification (typically a few
    seconds) had a chance to finish and redirect to the actual product
    page. Matched on "Cloudflare"/"Ray ID" specifically since those are
    Cloudflare's own branding, not translated regardless of the page's UI
    language -- unlike the surrounding "Checking your Browser…" text, which
    is.
    """
    joined = " ".join(lines).casefold()
    return "cloudflare" in joined and "ray id" in joined


def _find_breadcrumb_set_name(lines: list[str], name: str) -> str:
    """The set/category name for a card whose title has no "(Number) - Set"

    clause at all (see :func:`_parse_product_info`), inferred from
    Cardmarket's own breadcrumb navigation rather than the title.

    Live-confirmed structure (a real "Shining Mew" page, an unnumbered
    promo): the breadcrumb renders each level as a "/<Label>" line followed
    by a plain "<Label>" line -- except the current page's own entry, which
    only ever gets the bare "/<Name>" line (no plain-label duplicate, since
    it isn't a clickable link). That means the plain label line immediately
    *before* "/<Name>" is reliably the enclosing set/category, regardless
    of the page's own UI locale (Cardmarket's own breadcrumb labels for
    sets/categories are consistently in English, live-confirmed unchanged
    even on a ``/de/`` locale page) -- unlike relying on some
    locale-specific literal breadcrumb suffix text. Blank if the pattern
    isn't found (e.g. a differently-structured page).
    """
    target = f"/{name}"
    for index, line in enumerate(lines):
        if line == target and index > 0:
            candidate = lines[index - 1]
            if candidate and not candidate.startswith("/"):
                return candidate.strip()
    return ""


def _detect_dominant_language(lines: list[str]) -> Language | None:
    """Best-effort guess at the product's language: the most common one among
    its own already-visible offer rows (see :func:`_parse_offer_lines`,
    reusing the exact same parsing this project already trusts for price
    lookups), or ``None`` if no offers could be parsed at all (e.g. currently
    out of stock, or the offer table hadn't finished rendering).

    Only ever a starting point for the add-card dialog's language dropdown
    (see ``ProductInfo.detected_language``'s own docs) -- a product page can
    genuinely list several languages side by side, so "most common" is a
    reasonable single guess, not a guarantee of the exact card the user is
    about to add.
    """
    offers = _parse_offer_lines(lines)
    languages = [offer.language for offer in offers if offer.language is not None]
    if not languages:
        return None
    return max(set(languages), key=languages.count)


def _english_card_name(name: str) -> str:
    """``name`` translated to English if it's a recognised foreign species
    name (with or without a card-type suffix, e.g. "Blitza V" -> "Jolteon
    V"), otherwise ``name`` unchanged.

    A manually-entered card's name/set/number are parsed straight off
    Cardmarket's own product-page title -- live-reported: on a non-English
    Cardmarket locale (e.g. cardmarket.com/de/...), that title is in the
    page's own language ("Despotar V"), not English ("Tyranitar V"), even
    though every other card in the collection is stored under its English
    name (see ``CardService.add_card_from_catalog``). Applied here, not
    left to the UI dialog, so it's consistent regardless of what opens
    that dialog.
    """
    translated = translate_name_with_suffix(name)
    return translated if translated is not None else name


def _parse_product_info(lines: list[str]) -> ProductInfo | None:
    """Find and parse Cardmarket's own product-page title among ``lines``.

    Falls back to the same bare "<Name> | Cardmarket" pattern sealed
    products use (:data:`_SEALED_TITLE_RE`) if no line matches the full
    "<Name> (<Number>) - <Set>" pattern -- live-confirmed against a real
    unnumbered promo ("Shining Mew" from Cardmarket's own "Unnumbered
    Promos" category): with no printed number, Cardmarket drops the whole
    "(Number) - Set" clause from the title instead of leaving it empty, so
    the primary pattern never matches at all and the lookup would otherwise
    fail outright for every such promo. ``card_number`` is left blank in
    that case (see ``ProductInfo``'s own docstring), but ``set_name`` is
    still recovered from the breadcrumb (see
    :func:`_find_breadcrumb_set_name`) rather than left blank too -- both
    remain editable in the add-card dialog regardless.
    """
    for line in lines:
        match = _PRODUCT_TITLE_RE.match(line)
        if match:
            return ProductInfo(
                name=_english_card_name(match.group("name").strip()),
                set_name=match.group("set_name").strip(),
                card_number=match.group("number").strip(),
                detected_language=_detect_dominant_language(lines),
            )
    for line in lines:
        match = _SEALED_TITLE_RE.match(line)
        if match:
            name = match.group("name").strip()
            return ProductInfo(
                name=_english_card_name(name),
                set_name=_find_breadcrumb_set_name(lines, name),
                card_number="",
                detected_language=_detect_dominant_language(lines),
            )
    return None


def _parse_search_result_line(text: str) -> CardmarketSearchResult | None:
    match = _SEARCH_RESULT_RE.match(text)
    if match is None:
        return None
    return CardmarketSearchResult(
        name=match.group("name").strip(),
        set_name=match.group("set_name").strip(),
        card_number=match.group("code").strip(),
        price_hint=match.group("price").strip(),
        raw_text=text,
    )


def _parse_sealed_product_info(lines: list[str]) -> SealedProductInfo | None:
    """Find and parse a sealed product's title/breadcrumb among ``lines``.

    The title gives the name; the category comes from the breadcrumb's own
    trailing text, which Cardmarket renders as "<Name> <Category>" in one
    accessible text node right after the name's own breadcrumb entry (e.g.
    "Base Set Booster Box Booster Boxes" for a "Booster Box" category) --
    found by looking for a line that starts with "<name> " and taking
    whatever follows as the category. Blank if no such line is found.
    """
    name = None
    for line in lines:
        match = _SEALED_TITLE_RE.match(line)
        if match:
            name = match.group("name").strip()
            break
    if name is None:
        return None
    category = ""
    prefix = f"{name} "
    for line in lines:
        # Skip the title line(s) themselves -- "<name> | Cardmarket[ - Google
        # Chrome]" also starts with "<name> ", but that's not a breadcrumb.
        if "Cardmarket" in line:
            continue
        if line.startswith(prefix) and len(line) > len(prefix):
            category = line[len(prefix) :].strip()
            break
    # Normalised to one of the fixed SealedCategory labels where recognised
    # (e.g. Cardmarket's own "Booster Boxes" -> "Booster Box"), so products
    # added this way sort/group consistently with manually-typed ones. Falls
    # back to the raw breadcrumb text for a category that doesn't match any
    # known bucket, rather than discarding it -- the add-dialog still shows
    # this as an overridable dropdown either way.
    guessed = SealedCategory.guess_from_text(category)
    if guessed is not SealedCategory.OTHER:
        category = guessed.label
    return SealedProductInfo(name=name, category=category)


def _parse_sealed_offer_lines(lines: list[str]) -> list[SealedOffer]:
    """Group a flat, ordered list of on-screen text tokens into sealed offers.

    Mirrors :func:`_parse_offer_lines`, but a genuine offer row is
    recognised by a matched **language** token instead of a condition badge
    -- sealed products have no condition ladder on Cardmarket at all (see
    :class:`~app.pricing.models.SealedOffer`), so a condition-based check
    would silently discard every real offer.
    """
    offers: list[SealedOffer] = []
    row_start = 0
    index = 0
    while index < len(lines):
        price = _parse_price(lines[index])
        if price is None:
            index += 1
            continue

        span = lines[row_start:index]
        language = _first_match(span, _LANGUAGE_BY_LABEL, str.casefold)
        seller = next((tok for tok in span if tok and not tok.isdigit() and tok != "K"), "")

        next_index = index + 1
        if next_index < len(lines) and _QUANTITY_RE.match(lines[next_index]):
            next_index += 1

        if language is not None:
            offers.append(SealedOffer(seller=seller, language=language, price=price))
        row_start = next_index
        index = next_index

    return offers
