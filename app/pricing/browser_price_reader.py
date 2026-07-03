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
from pathlib import Path
from urllib.parse import urlencode

import requests

from app.logging_config import get_logger
from app.models.enums import Condition, Language
from app.pricing.models import CardmarketOffer

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 30.0
_POLL_INTERVAL = 0.5
#: Extra time to let the page finish rendering once the window/title appears.
_SETTLE_DELAY = 2.0

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
_LANGUAGE_BY_LABEL = {language.label.casefold(): language for language in Language}

#: Cardmarket's own numeric ids for its ``language``/``minCondition`` product-page
#: query filters, confirmed live by reading the filter form's own input elements
#: (not documented anywhere public). Note these are *not* contiguous — e.g.
#: Dutch is 12 — and only cover the western languages Cardmarket exposes as a
#: filter on a single product page. Japanese/Korean/Chinese printings are
#: separate Cardmarket products with their own URL entirely, not a language
#: filter on the same page, so they have no id here.
_CARDMARKET_LANGUAGE_IDS: dict[Language, int] = {
    Language.ENGLISH: 1,
    Language.FRENCH: 2,
    Language.GERMAN: 3,
    Language.SPANISH: 4,
    Language.ITALIAN: 5,
    Language.PORTUGUESE: 8,
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

#: A German-formatted price like "1.234,56 €" or "13,90 €".
_PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*€")
#: A bare quantity token (small integer) immediately following a price.
_QUANTITY_RE = re.compile(r"^\d{1,3}$")


class BrowserPriceReaderError(Exception):
    """Raised when a card's Cardmarket offers couldn't be read."""


def resolve_cardmarket_url(url: str, session: requests.Session | None = None) -> str:
    """Follow redirects to the actual cardmarket.com product page.

    ``card.cardmarket_url`` (sourced from pokemontcg.io's own API) is a
    tracking shortlink (``prices.pokemontcg.io/cardmarket/<id>``), not a
    direct link — a live smoke test caught that this shortlink's redirect
    target is a **fixed** string on pokemontcg.io's end. Any ``language``/
    ``minCondition`` query parameters appended to the shortlink are silently
    dropped during the redirect, landing on the fully unfiltered page every
    time regardless of what filter was requested. Resolving the redirect
    first and filtering the *real* URL avoids this.

    Falls back to the original ``url`` (unresolved) if the request fails —
    the browser will still open *something* rather than nothing.
    """
    http = session or requests.Session()
    try:
        response = http.get(url, allow_redirects=True, timeout=10)
    except requests.RequestException as exc:
        logger.warning("Could not resolve redirect for %s: %s -- using it as-is.", url, exc)
        return url
    return response.url


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

    ``signed``/``first_edition``/``altered`` map to Cardmarket's own
    ``extra[isSigned]``/``extra[isFirstEd]``/``extra[isAltered]`` filters
    (ids confirmed live from the filter form's own inputs — "Egal"/Ja/Nein
    are ``0``/``Y``/``N``). Unlike ``language``/``min_condition`` these are
    almost always passed as a definite ``True``/``False`` rather than left
    ``None``: a real card either is or isn't signed, so leaving this unset
    would silently match against a page mixing signed and unsigned offers,
    breaking an "exact" match's accuracy. There's no Cardmarket filter for
    Reverse Holo at all (not exposed on the product page), so it has no
    parameter here.
    """
    params: dict[str, int | str] = {}
    if language is not None and language in _CARDMARKET_LANGUAGE_IDS:
        params["language"] = _CARDMARKET_LANGUAGE_IDS[language]
    if min_condition is not None:
        params["minCondition"] = _CARDMARKET_CONDITION_IDS[min_condition]
    if signed is not None:
        params["extra[isSigned]"] = "Y" if signed else "N"
    if first_edition is not None:
        params["extra[isFirstEd]"] = "Y" if first_edition else "N"
    if altered is not None:
        params["extra[isAltered]"] = "Y" if altered else "N"
    if not params:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


def _parse_price(token: str) -> float | None:
    match = _PRICE_RE.search(token)
    if not match:
        return None
    return float(match.group(1).replace(".", "").replace(",", "."))


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


def _open_in_chrome(url: str) -> None:
    """Launch ``url`` in Google Chrome specifically, in a new tab.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed where expected.
    """
    chrome_path = _find_chrome_executable()
    if chrome_path is None:
        raise BrowserPriceReaderError(
            "Google Chrome wurde nicht gefunden. Bitte installiere Chrome "
            r"(erwarteter Pfad: ...\Google\Chrome\Application\chrome.exe)."
        )
    subprocess.Popen([chrome_path, url])  # noqa: S603 — fixed executable, one URL argument


def _open_and_capture_visible_text(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[str]:
    """Open ``url`` in Chrome, capture its visible on-screen text, close the tab.

    Matching is scoped to whatever window is currently in the *foreground*
    (``GetForegroundWindow``) **and** whose title mentions both Chrome and
    Cardmarket, polled repeatedly until both match — not "any open window
    with a matching title". ``match_hint`` (the card's name) is used only
    for the error message if no matching window ever appears, *not* for the
    matching itself: a real card ("Charizard VMAX" filtered by German)
    showed a live "Cardmarket-Tab nicht gefunden" failure because Cardmarket
    renders the page in the requested language, including the card's
    *localised* name in the title ("Glurak VMAX | Cardmarket") — nothing
    close to the English catalogue name this project stores. "Cardmarket"
    itself is the one thing present in the title regardless of locale. A
    live smoke test earlier also caught the broader ``Desktop(...).windows()``
    scan matching a stale, already-open tab with a coincidentally similar
    title (e.g. a leftover Cardmarket tab from an earlier lookup, or even
    this project's own
    debugging browser session) instead of the tab this call just opened,
    silently returning a real but wrong price. Since opening a URL normally
    focuses the new tab, the foreground window at match time should be
    exactly it; requiring a known browser in the title is a second,
    cheap safety net against matching some unrelated foreground app.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, or no matching
            foreground window appears within ``timeout``.
    """
    # Imported lazily: pywinauto/pywin32 are Windows-only, and importing them
    # directly at module load would break this module (and anything
    # importing it, e.g. for tests) on non-Windows platforms.
    import win32gui
    from pywinauto import Desktop

    _open_in_chrome(url)

    desktop = Desktop(backend="uia")
    deadline = time.monotonic() + timeout
    window = None
    while time.monotonic() < deadline:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            try:
                title = win32gui.GetWindowText(hwnd)
            except Exception:  # noqa: BLE001 — window may have closed mid-poll
                title = ""
            lowered_title = title.casefold()
            if "cardmarket" in lowered_title and "chrome" in lowered_title:
                try:
                    candidate = desktop.window(handle=hwnd)
                    candidate.window_text()  # sanity check it's wrappable
                except Exception:  # noqa: BLE001 — window may have closed mid-poll
                    pass
                else:
                    window = candidate
                    break
        time.sleep(_POLL_INTERVAL)

    if window is None:
        raise BrowserPriceReaderError(
            f"Cardmarket-Tab für „{match_hint}“ wurde nicht rechtzeitig gefunden."
        )

    try:
        time.sleep(_SETTLE_DELAY)
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
    finally:
        try:
            window.set_focus()
            window.type_keys("^w")
        except Exception:  # noqa: BLE001 — best-effort tab cleanup
            logger.warning("Could not close the Cardmarket tab for %r automatically.", match_hint)


def read_offers_for_card(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[CardmarketOffer]:
    """Open ``url`` in Chrome, read its offers, close the tab.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, no matching
            foreground window appears within ``timeout``, or the window's
            content can't be parsed into any offers.
    """
    lines = _open_and_capture_visible_text(url, match_hint, timeout)
    offers = _parse_offer_lines(lines)
    if not offers:
        raise BrowserPriceReaderError(
            f"Keine Angebote auf der Cardmarket-Seite für „{match_hint}“ erkannt."
        )
    return offers


