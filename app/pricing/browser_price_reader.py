"""Reads Cardmarket seller offers off a normally-opened Chrome tab.

This deliberately does **not** automate or drive a browser: it opens the URL
by launching Google Chrome directly with the URL as an argument (Chrome's own
normal behaviour — a new tab in the existing window, indistinguishable from a
user clicking a link) and then reads the already-rendered window's on-screen
text via Windows UI Automation, the same mechanism screen readers use.
Nothing here talks to the page over the network or a remote-debugging
protocol; it only observes what is already visible on screen, then closes the
one tab it opened. There is no batch/loop over multiple cards — this reads
exactly one card per call, triggered by one user action.

Chrome specifically (not "whatever the OS default browser is") is a
deliberate choice: a live smoke test on a machine whose default browser was
Firefox repeatedly picked up stale, unrelated background tabs because the
window-matching had to search broadly across every open window. Targeting
one known browser lets the window search also require its title to mention
Chrome, narrowing the search considerably.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import requests

from app import config
from app.i18n import tr
from app.logging_config import get_logger
from app.models.enums import Condition, Language, SealedCategory
from app.pricing.models import (
    CardmarketOffer,
    CardmarketSearchResult,
    ProductInfo,
    SealedOffer,
    SealedProductInfo,
)

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 30.0
_POLL_INTERVAL = 0.5
#: Extra time to let the page finish rendering once the window/title appears.
_SETTLE_DELAY = 2.0
#: A live incident caught the window title (set by JS as soon as navigation
#: starts) appearing well before the page's actual content (the offer
#: table) had rendered -- the capture ran right after only the browser's
#: own chrome (toolbar, tab strip) was there, netting ~20 sparse lines
#: instead of the usual several dozen. If a first capture looks that thin,
#: it's given one more settle delay and re-read before giving up on it.
_MIN_EXPECTED_LINES = 30

#: Common install locations, checked if the registry lookup (see
#: ``_find_chrome_executable``) doesn't turn up a usable path.
_CHROME_FALLBACK_PATHS = (
    r"Google\Chrome\Application\chrome.exe",
)

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
#: (not documented anywhere public). Note these are *not* contiguous — e.g.
#: Dutch is 12 — and only cover the western languages Cardmarket exposes as a
#: filter on a single *card's* page. Japanese/Korean/Chinese prints of a
#: single card are separate Cardmarket products with their own URL entirely
#: (often under the Japanese set's own name, e.g. Neo Revelation's Ho-Oh is
#: "Awakening Legends" there), not a language filter on the same page, so
#: they have no id here -- see ``price_service.py``'s own handling of this.
_CARDMARKET_LANGUAGE_IDS: dict[Language, int] = {
    Language.ENGLISH: 1,
    Language.FRENCH: 2,
    Language.GERMAN: 3,
    Language.SPANISH: 4,
    Language.ITALIAN: 5,
    Language.PORTUGUESE: 8,
}

#: Unlike single cards, a *sealed* product's Cardmarket page genuinely does
#: expose Japanese/Korean/Traditional Chinese as a language filter on the
#: same page -- live-confirmed against a real, Asian-exclusive-only set
#: ("Abyss Eye Booster Box", no Western release at all): its own filter
#: sidebar lists exactly these three languages, and clicking each one's
#: checkbox in a real browser session produced ``?language=7`` (Japanese),
#: ``?language=10`` (Korean), ``?language=11`` (Traditional Chinese)
#: respectively. Deliberately a separate table from
#: ``_CARDMARKET_LANGUAGE_IDS`` above, not merged into it: cards genuinely
#: need Japanese/Korean/Chinese treated as "no filter, different product"
#: (see ``price_service.py``), and silently changing that shared table
#: would defeat its own "bail out, don't guess" protection there.
_SEALED_CARDMARKET_LANGUAGE_IDS: dict[Language, int] = {
    **_CARDMARKET_LANGUAGE_IDS,
    Language.JAPANESE: 7,
    Language.KOREAN: 10,
    Language.CHINESE: 11,
}
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


class BrowserPriceReaderError(Exception):
    """Raised when a card's Cardmarket offers couldn't be read."""


#: A live incident found pokemontcg.io itself (the same host that serves
#: the ``prices.pokemontcg.io`` shortlink resolved here) briefly taking
#: >30s to respond -- past this function's own timeout, with no retry at
#: all, it silently fell back to opening the *unresolved* shortlink in
#: Chrome, whose own redirect page doesn't render as a real Cardmarket
#: product page. One retry gives a second chance before giving up.
_RESOLVE_MAX_ATTEMPTS = 2
_RESOLVE_TIMEOUT = 10
_RESOLVE_RETRY_DELAY = 1.0


#: Host of pokemontcg.io's own tracking shortlink -- see ``resolve_cardmarket_
#: url``'s docstring below.
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


#: Cardmarket product-slug version suffix -- some vintage sets list a
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
#: See PROJECT_PROGRESS.md ("Verworfener Versuch") for why any fix here
#: must stay to a single alternate, never a candidate loop.
_VERSION_SUFFIX_RE = re.compile(r"-V(\d+)")


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


def build_filtered_url(
    base_url: str,
    *,
    language: Language | None = None,
    min_condition: Condition | None = None,
    signed: bool | None = None,
    first_edition: bool | None = None,
    altered: bool | None = None,
    reverse_holo: bool | None = None,
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
    nested under ``extra[...]``. An earlier round of research had
    ``isSigned``/``isFirstEd``/``isAltered`` wrapped as ``extra[isSigned]``
    etc.; live-confirmed wrong (2026-07-06) by comparing against the exact
    URLs Cardmarket's own filter sidebar produces when the checkboxes are
    clicked directly (``?language=1&minCondition=2&isReverseHolo=N&isSigned=
    N&isFirstEd=N&isAltered=N``, no ``extra[...]`` anywhere) -- the
    unrecognised ``extra[...]`` keys were most likely silently dropped
    (or worse, broke the whole filter's server-side binding) rather than
    raising, which is why the wrong shape went unnoticed. Unlike
    ``language``/``min_condition`` these four are almost always passed as a
    definite ``True``/``False`` rather than left ``None``: a real card
    either is or isn't signed, so leaving this unset would silently match
    against a page mixing signed and unsigned offers, breaking an "exact"
    match's accuracy.
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


def build_sealed_filtered_url(base_url: str, language: Language) -> str:
    """Set Cardmarket's own ``?language=N`` filter for a sealed product.

    Sealed products have no condition ladder or extras (signed, 1st edition,
    reverse holo, ...) to filter by at all, so unlike :func:`build_filtered_url`
    this only ever narrows by language. A ``language`` with no known id (see
    :func:`sealed_supports_language_filter`) is silently ignored, same
    convention as :func:`build_filtered_url`.

    Idempotent: any pre-existing ``language`` query parameter is replaced
    rather than duplicated. This matters because, unlike single cards, a
    sealed product's stored ``cardmarket_url`` may already carry this same
    filter from when it was added/edited -- price lookups re-derive the
    filter fresh from whatever URL is stored (see ``SealedPriceService``),
    so calling this twice on an already-filtered URL must not stack a
    second ``&language=`` onto it.
    """
    if not sealed_supports_language_filter(language):
        return base_url
    parts = urlsplit(base_url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "language"]
    query.append(("language", str(_SEALED_CARDMARKET_LANGUAGE_IDS[language])))
    return urlunsplit(parts._replace(query=urlencode(query)))


#: Matches "https://www.cardmarket.com/<locale>/<rest>" -- the two-letter
#: path segment right after the domain is Cardmarket's own UI-locale
#: selector (not to be confused with the *print-language* ``?language=N``
#: query filter from ``build_filtered_url``, which is a wholly separate,
#: locale-independent concept).
_CARDMARKET_LOCALE_RE = re.compile(r"^(https?://(?:www\.)?cardmarket\.com)/[a-z]{2}(/.*)$")


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


def _find_chrome_executable() -> str | None:
    """Locate chrome.exe via the registry, falling back to common install paths.

    The registry's ``App Paths`` entry is how Windows itself records where an
    installed application lives, independent of which browser (if any) is
    set as the OS default — this is what lets the lookup work regardless of
    the user's default-browser setting.
    """
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
        ) as key:
            path, _ = winreg.QueryValueEx(key, "")
            if path and Path(path).exists():
                return path
    except OSError:
        pass

    for program_files in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if not program_files:
            continue
        for relative in _CHROME_FALLBACK_PATHS:
            candidate = Path(program_files) / relative
            if candidate.exists():
                return str(candidate)
    return None


#: Chrome's own top-level window class -- used to enumerate its windows
#: without pulling in any other browser/app that happens to mention
#: "chrome" or "cardmarket" in a window title.
_CHROME_WINDOW_CLASS = "Chrome_WidgetWin_1"

#: Smallest window Chrome is launched at when it isn't already running --
#: only takes effect on that cold start (an already-running Chrome ignores
#: --window-size for a new tab opened in its existing window). Narrow
#: enough to stay unobtrusive behind the app (user request), but not so
#: narrow that Cardmarket's own responsive layout collapses into a
#: simplified view that might drop the offer table this reads.
_COLD_START_WINDOW_SIZE = "700,850"


def _chrome_window_titles() -> dict[int, str]:
    """Maps every visible top-level Chrome window handle to its current title.

    Used to detect *which* window just opened the tab this call is waiting
    for, without needing that window to be in the foreground (see
    ``_open_and_capture_visible_text``).
    """
    import win32gui

    titles: dict[int, str] = {}

    def _collect(hwnd: int, _: object) -> None:
        try:
            if (
                win32gui.GetClassName(hwnd) == _CHROME_WINDOW_CLASS
                and win32gui.IsWindowVisible(hwnd)
            ):
                titles[hwnd] = win32gui.GetWindowText(hwnd)
        except Exception:  # noqa: BLE001 — a window can vanish mid-enumeration
            pass

    win32gui.EnumWindows(_collect, None)
    return titles


def _restore_foreground(hwnd: int | None) -> None:
    """Best-effort: brings ``hwnd`` (this app's own window) back to the
    foreground.

    Chrome briefly needs the actual OS foreground for two things this
    module still does: a cold start creating its window, and focusing the
    opened tab to send it the "close tab" shortcut. Both cases hand focus
    back to the app right after, instead of leaving Chrome's window on top
    (user request: the app should stay in front, Chrome opens behind it).
    """
    if hwnd is None:
        return
    try:
        import win32gui

        win32gui.SetForegroundWindow(hwnd)
    except Exception:  # noqa: BLE001 — never let a focus nicety break a lookup
        pass


def _open_in_chrome(url: str, cold_start: bool) -> None:
    """Launch ``url`` in Google Chrome specifically, in a new tab.

    ``cold_start`` (Chrome wasn't already running) additionally requests
    the smallest usable window size -- ignored by Chrome for a tab opened
    in an already-running instance, which is the common case.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed where expected.
    """
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        raise BrowserPriceReaderError(
            tr(
                "Google Chrome wurde nicht gefunden. Bitte installiere Chrome "
                r"(erwarteter Pfad: ...\Google\Chrome\Application\chrome.exe)."
            )
        )
    args = [chrome_path]
    if cold_start:
        args.append(f"--window-size={_COLD_START_WINDOW_SIZE}")
    args.append(url)
    subprocess.Popen(args)  # noqa: S603 — fixed executable, fixed/one URL argument


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


def _dismiss_cookie_banner(window) -> None:
    """Best-effort: click Cardmarket's own "decline non-essential cookies"

    button if its consent banner is currently showing, otherwise do
    nothing. Silently swallows any error -- this must never block or fail
    the actual price lookup it's called from."""
    try:
        for control in window.descendants(control_type="Button"):
            text = (control.window_text() or "").strip().casefold()
            if text in _COOKIE_DECLINE_BUTTON_TEXTS:
                control.click_input()
                logger.info("Dismissed Cardmarket's cookie-consent banner.")
                return
    except Exception:  # noqa: BLE001 — best-effort, never blocks the read
        pass


def _has_cookie_banner(lines: list[str]) -> bool:
    """Whether ``lines`` still shows Cardmarket's own cookie-consent banner

    text -- a live-confirmed intermittent case where the banner's own text
    is momentarily present at the same time the button controls needed to
    dismiss it aren't reliably clickable yet (the page is still settling),
    so this is treated the same as "too few lines" below: a signal to wait
    and re-read, not a final result."""
    return any("cardmarket uses cookies" in line.casefold() for line in lines)


def _open_and_capture_visible_text(
    url: str,
    match_hint: str,
    timeout: float = _DEFAULT_TIMEOUT,
    on_window_ready: Callable[[object], None] | None = None,
) -> list[str]:
    """Open ``url`` in Chrome, capture its visible on-screen text, close the tab.

    ``on_window_ready``, if given, is called with the already-rendered
    ``pywinauto`` window right after the text read succeeds, before the tab
    is closed -- e.g. for :mod:`app.pricing.sealed_image_capture` to grab a
    screenshot crop of the product photo from the same tab, without opening
    Chrome a second time (real risk: some sites treat repeated automated
    opens as suspicious activity). Best-effort: any exception it raises is
    caught and logged, never allowed to break the actual text read this
    function exists for.

    Chrome is deliberately kept out of the foreground throughout (user
    request: the app should stay the visible/active window, Chrome loads
    behind it) -- so matching can no longer rely on ``GetForegroundWindow``
    the way an earlier version of this function did. Instead, every
    visible Chrome window's title is snapshotted *before* opening the URL;
    afterwards, each currently open Chrome window is checked against that
    snapshot, and the match is whichever one now mentions "Cardmarket" in
    its title but didn't already (either a brand-new window -- Chrome
    wasn't running yet -- or an existing window whose active tab just
    changed to this one). That "changed since the snapshot" condition is
    exactly what a plain, undated title search lacks: a live smoke test
    once caught a broad "any window mentioning Cardmarket" search matching
    a stale, already-open tab from an earlier lookup instead of the tab
    this call just opened, silently returning a real but wrong price.
    ``match_hint`` (the card's name) is used only for the error message if
    no matching window ever appears, *not* for the matching itself: a real
    card ("Charizard VMAX" filtered by German) showed a live "Cardmarket-Tab
    nicht gefunden" failure because Cardmarket renders the page in the
    requested language, including the card's *localised* name in the title
    ("Glurak VMAX | Cardmarket") -- nothing close to the English catalogue
    name this project stores.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, or no matching
            window appears within ``timeout``.
    """
    # Imported lazily: pywinauto/pywin32 are Windows-only, and importing them
    # directly at module load would break this module (and anything
    # importing it, e.g. for tests) on non-Windows platforms.
    import win32gui
    from pywinauto import Desktop

    own_hwnd = win32gui.GetForegroundWindow()
    titles_before = _chrome_window_titles()
    _open_in_chrome(url, cold_start=not titles_before)

    desktop = Desktop(backend="uia")
    deadline = time.monotonic() + timeout
    window = None
    while time.monotonic() < deadline:
        for hwnd, title in _chrome_window_titles().items():
            if "cardmarket" not in title.casefold():
                continue
            if titles_before.get(hwnd) == title:
                continue  # unchanged since the snapshot -- a stale tab, not ours
            try:
                candidate = desktop.window(handle=hwnd)
                candidate.window_text()  # sanity check it's wrappable
            except Exception:  # noqa: BLE001 — window may have closed mid-poll
                continue
            window = candidate
            break
        if window is not None:
            break
        time.sleep(_POLL_INTERVAL)

    _restore_foreground(own_hwnd)

    if window is None:
        raise BrowserPriceReaderError(
            tr("Cardmarket-Tab für „{hint}“ wurde nicht rechtzeitig gefunden.").format(
                hint=match_hint
            )
        )

    try:
        time.sleep(_SETTLE_DELAY)
        _dismiss_cookie_banner(window)
        lines = _read_visible_text(window)
        if len(lines) < _MIN_EXPECTED_LINES or _has_cookie_banner(lines):
            # The window title (set by JS as soon as navigation starts) can
            # appear well before the page's real content has rendered --
            # give it one more moment rather than reading only the
            # browser's own chrome (toolbar/tab strip) and reporting no
            # offers on a page that actually has plenty. A still-visible
            # cookie banner gets the same treatment: on a brand-new profile
            # (or right after switching locale for the first time) its own
            # button controls are sometimes not reliably clickable on the
            # very first pass yet, live-confirmed intermittent.
            logger.info(
                "Only %d lines captured for %r (or cookie banner still "
                "showing) -- giving the page one more moment to render "
                "before reading again.",
                len(lines), match_hint,
            )
            time.sleep(_SETTLE_DELAY)
            _dismiss_cookie_banner(window)
            lines = _read_visible_text(window)
        if on_window_ready is not None:
            try:
                on_window_ready(window)
            except Exception:  # noqa: BLE001 — best-effort, e.g. image capture
                logger.warning(
                    "on_window_ready callback failed for %r -- continuing without it.",
                    match_hint,
                )
        return lines
    finally:
        try:
            window.set_focus()
            window.type_keys("^w")
        except Exception:  # noqa: BLE001 — best-effort tab cleanup
            logger.warning("Could not close the Cardmarket tab for %r automatically.", match_hint)
        finally:
            # window.set_focus() just above necessarily brought Chrome
            # forward again (needed for the "^w" keystroke to land on it) --
            # hand focus back to the app now that Chrome is done being
            # interacted with.
            _restore_foreground(own_hwnd)


def _read_visible_text(window) -> list[str]:
    """Every visible control's text under ``window``, in tree order."""
    lines: list[str] = []
    for descendant in window.descendants():
        try:
            # A tabbed browser keeps every open tab's content in the same
            # top-level window's accessibility tree, even tabs that are
            # not the active one — only the active tab's controls report
            # as visible. Without this check, text from unrelated
            # background tabs (other pages, other Cardmarket lookups)
            # leaks into the parsed offers.
            if not descendant.is_visible():
                continue
            text = descendant.window_text()
        except Exception:  # noqa: BLE001 — a control may vanish mid-walk
            continue
        if text:
            lines.append(text)
    return lines


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
                name=match.group("name").strip(),
                set_name=match.group("set_name").strip(),
                card_number=match.group("number").strip(),
            )
    for line in lines:
        match = _SEALED_TITLE_RE.match(line)
        if match:
            name = match.group("name").strip()
            return ProductInfo(
                name=name, set_name=_find_breadcrumb_set_name(lines, name), card_number=""
            )
    return None


def read_product_info(
    url: str, timeout: float = _DEFAULT_TIMEOUT, capture_image: bool = False
) -> ProductInfo:
    """Open ``url`` in Chrome, parse its title into name/set/number, close the tab.

    Backs the "Karte manuell eintragen" flow: the user pastes a Cardmarket
    product link directly (e.g. for a vintage multi-version product or a
    JP/KO/ZH print the catalogue search can't reliably find) instead of
    picking a possibly-wrong catalogue match. There is no card name yet to
    use as a match hint here — that's the whole point of this function — so
    the generic flow name is used instead; it only ever surfaces in the
    "tab not found in time" error message.

    If ``capture_image`` is set, a best-effort screenshot crop of the card's
    photo is taken from the same already-open tab (see
    :mod:`app.pricing.sealed_image_capture`, reused as-is -- catalogue-less
    manual entry has exactly the same "no pokemontcg.io image available"
    problem sealed products do) and returned as ``ProductInfo.photo_path``
    (a temp file, or ``None`` if the capture wasn't attempted or failed --
    this never affects whether the lookup as a whole succeeds).

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, no matching
            foreground window appears within ``timeout``, or the page's
            title doesn't match the expected Cardmarket product-page
            pattern (e.g. the link wasn't a real product page).
    """
    captured_photo_path: str | None = None

    def _capture(window: object) -> None:
        nonlocal captured_photo_path
        if not capture_image:
            return
        from app.pricing.sealed_image_capture import capture_sealed_product_image

        # The name isn't parsed yet at this point (that happens below, from
        # `lines`, once this whole read finishes) -- but the window's own
        # title already contains it in the same "<Name> (<Number>) - <Set>
        # | Cardmarket" form _PRODUCT_TITLE_RE matches (or the bare "<Name>
        # | Cardmarket" form for unnumbered promos, see
        # _parse_product_info's own docs), so it's read directly off the
        # window instead of waiting for `info`.
        title_match = _PRODUCT_TITLE_RE.match(window.window_text())
        if title_match is None:
            title_match = _SEALED_TITLE_RE.match(window.window_text())
        name_hint = title_match.group("name").strip() if title_match else ""
        captured_photo_path = capture_sealed_product_image(
            window, name_hint, dest_dir=config.PHOTOS_DIR
        )

    lines = _open_and_capture_visible_text(
        url, tr("Karte manuell eintragen"), timeout, on_window_ready=_capture
    )
    info = _parse_product_info(lines)
    if info is None:
        raise BrowserPriceReaderError(
            tr(
                "Die Seite wurde nicht als Cardmarket-Produktseite erkannt. Bitte "
                "prüfe den Link."
            )
        )
    if captured_photo_path is not None:
        info = replace(info, photo_path=captured_photo_path)
    return info


def read_offers_for_card(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[CardmarketOffer]:
    """Open ``url`` in Chrome, read its offers, close the tab.

    Reads via a canonical-locale copy of ``url`` (see
    :func:`with_canonical_locale`) -- the *stored* URL a user might click
    themselves is never touched, only this one read.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, no matching
            foreground window appears within ``timeout``, or the window's
            content can't be parsed into any offers.
    """
    lines = _open_and_capture_visible_text(with_canonical_locale(url), match_hint, timeout)
    offers = _parse_offer_lines(lines)
    if not offers:
        raise BrowserPriceReaderError(
            tr("Keine Angebote auf der Cardmarket-Seite für „{hint}“ erkannt.").format(
                hint=match_hint
            )
        )
    return offers


#: A search-result page's own hyperlinks flatten every descendant text node
#: into one accessible name, live-confirmed as "<Name> <Set> \xa0<Name>
#: (<Code>) From <Price>" -- the name appears twice (once from the product
#: image's alt text, once from the title text below it), which is exactly
#: what the backreference below relies on to find the right split point
#: even when the set name itself contains spaces.
_SEARCH_RESULT_RE = re.compile(
    r"^(?P<name>.+?) (?P<set_name>.+?) \xa0(?P=name) \((?P<code>[^)]+)\) From (?P<price>.+)$"
)


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


def search_cardmarket(name: str, timeout: float = _DEFAULT_TIMEOUT) -> list[CardmarketSearchResult]:
    """Search Cardmarket's own site search for ``name``, returning every

    matching product as a selectable candidate.

    Backs the "Cardmarket-Link suchen" flow: when a card has no known
    Cardmarket link at all (neither pokemontcg.io's own cross-reference nor
    a user-supplied one -- a real, live-confirmed gap for a newly released
    set), this searches Cardmarket directly, the same way a human would, so
    the user can pick the right product from a list instead of researching
    the correct link by hand. No URL is included yet (see
    :class:`~app.pricing.models.CardmarketSearchResult`'s own docs for why)
    -- once the user picks one, :func:`resolve_cardmarket_search_result`
    recovers its real URL.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed or no matching
            foreground window appears within ``timeout``.
    """
    results: list[CardmarketSearchResult] = []

    def _collect(window: object) -> None:
        for link in window.descendants(control_type="Hyperlink"):
            try:
                text = link.window_text()
            except Exception:  # noqa: BLE001 — a control may vanish mid-walk
                continue
            parsed = _parse_search_result_line(text)
            if parsed is not None:
                results.append(parsed)

    url = f"https://www.cardmarket.com/en/Pokemon/Products/Search?searchString={quote(name)}"
    _open_and_capture_visible_text(url, name, timeout, on_window_ready=_collect)
    return results


def resolve_cardmarket_search_result(
    name: str, chosen: CardmarketSearchResult, timeout: float = _DEFAULT_TIMEOUT
) -> str:
    """Click through to ``chosen``'s real Cardmarket product page, returning its URL.

    Re-runs the same search :func:`search_cardmarket` did (that page is
    already closed by the time the user has picked a candidate), finds the
    hyperlink matching ``chosen.raw_text`` exactly, and invokes it --
    Cardmarket exposes no href at all via UI Automation, only visible text
    (see :class:`~app.pricing.models.CardmarketSearchResult`'s own docs),
    so reading the resulting page's own address bar (already part of what
    :func:`_read_visible_text` captures) is the only reliable way to
    recover the real URL. Uses the UI Automation *Invoke* pattern rather
    than a simulated click -- live-confirmed to work reliably regardless of
    the link's on-screen position, unlike a coordinate-based click.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, no matching
            foreground window appears within ``timeout``, the matching link
            can't be found on a fresh search, or the resulting page's own
            URL can't be read.
    """
    real_url: str | None = None

    def _click_through(window: object) -> None:
        nonlocal real_url
        for link in window.descendants(control_type="Hyperlink"):
            try:
                text = link.window_text()
            except Exception:  # noqa: BLE001 — a control may vanish mid-walk
                continue
            if text != chosen.raw_text:
                continue
            link.invoke()
            time.sleep(_SETTLE_DELAY)
            for descendant in window.descendants():
                try:
                    line = descendant.window_text()
                except Exception:  # noqa: BLE001
                    continue
                if line.startswith("cardmarket.com/"):
                    real_url = f"https://www.{line}"
                    return
            return

    url = f"https://www.cardmarket.com/en/Pokemon/Products/Search?searchString={quote(name)}"
    _open_and_capture_visible_text(url, name, timeout, on_window_ready=_click_through)
    if real_url is None:
        raise BrowserPriceReaderError(
            tr(
                "Der gewählte Cardmarket-Treffer konnte nicht wiedergefunden "
                "werden. Bitte erneut versuchen."
            )
        )
    return real_url


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


def read_sealed_product_info(
    url: str, timeout: float = _DEFAULT_TIMEOUT, capture_image: bool = False
) -> SealedProductInfo:
    """Open ``url`` in Chrome, parse its title/breadcrumb into name/category.

    Backs the sealed-product "manuell eintragen" flow -- there is no
    pokemontcg.io-style catalogue for sealed products at all, so this is the
    only way to add one.

    If ``capture_image`` is set, a best-effort screenshot crop of the
    product's photo is taken from the same already-open tab (see
    :mod:`app.pricing.sealed_image_capture`) and returned as
    ``SealedProductInfo.photo_path`` (a temp file, or ``None`` if the
    capture wasn't attempted or failed -- this never affects whether the
    lookup as a whole succeeds).

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, no matching
            foreground window appears within ``timeout``, or the page's
            title doesn't match the expected Cardmarket product-page
            pattern (e.g. the link wasn't a real product page).
    """
    captured_photo_path: str | None = None

    def _capture(window: object) -> None:
        nonlocal captured_photo_path
        if not capture_image:
            return
        # Imported lazily: this module deliberately has no other dependency
        # on `sealed_image_capture` (a Windows-only, best-effort concern),
        # mirroring the lazy pywinauto/win32gui imports above.
        from app.pricing.sealed_image_capture import capture_sealed_product_image

        # The product name isn't parsed yet at this point (that happens
        # below, from `lines`, once this whole read finishes) -- but the
        # window's own title already contains it in the same
        # "<Name> | Cardmarket" form _SEALED_TITLE_RE matches, so it's
        # read directly off the window instead of waiting for `info`.
        title_match = _SEALED_TITLE_RE.match(window.window_text())
        name_hint = title_match.group("name").strip() if title_match else ""
        captured_photo_path = capture_sealed_product_image(window, name_hint)

    lines = _open_and_capture_visible_text(
        url, tr("Sealed-Produkt eintragen"), timeout, on_window_ready=_capture
    )
    info = _parse_sealed_product_info(lines)
    if info is None:
        raise BrowserPriceReaderError(
            tr(
                "Die Seite wurde nicht als Cardmarket-Produktseite erkannt. Bitte "
                "prüfe den Link."
            )
        )
    if captured_photo_path is not None:
        info = replace(info, photo_path=captured_photo_path)
    return info


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


def read_sealed_offers_for_card(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[SealedOffer]:
    """Open ``url`` in Chrome, read its sealed-product offers, close the tab.

    Reads via a canonical-locale copy of ``url`` (see
    :func:`with_canonical_locale`) -- the *stored* URL a user might click
    themselves is never touched, only this one read. This is the primary
    fix for the "zero offers parsed" bug (see the module-level warning log
    below): the ``_GERMAN_LANGUAGE_LABELS`` table is kept only as a
    secondary safety net for URLs read before this existed.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, no matching
            foreground window appears within ``timeout``, or the window's
            content can't be parsed into any offers.
    """
    lines = _open_and_capture_visible_text(with_canonical_locale(url), match_hint, timeout)
    offers = _parse_sealed_offer_lines(lines)
    if not offers:
        logger.warning(
            "No offers parsed for %r -- %d lines captured: %r",
            match_hint, len(lines), lines,
        )
        raise BrowserPriceReaderError(
            tr("Keine Angebote auf der Cardmarket-Seite für „{hint}“ erkannt.").format(
                hint=match_hint
            )
        )
    return offers


