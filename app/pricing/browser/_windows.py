"""Windows backend: reads Cardmarket seller offers off a normally-opened
Chrome tab via Windows UI Automation.

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

Every function here has the exact same name/signature as its counterpart in
``app.pricing.browser._macos``/``._linux`` -- ``app.pricing.browser_price_
reader`` picks whichever module actually matches ``sys.platform`` and
re-exports these six names, so callers never need to know which platform
backend is actually running.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote

from app import config
from app.i18n import tr
from app.logging_config import get_logger
from app.pricing.cardmarket_parsing import (
    BrowserPriceReaderError,
    _find_breadcrumb_set_name,
    _has_cookie_banner,
    _parse_offer_lines,
    _parse_product_info,
    _parse_search_result_line,
    _parse_sealed_offer_lines,
    _parse_sealed_product_info,
    _PRODUCT_TITLE_RE,
    _SEALED_TITLE_RE,
    has_cookie_decline_button_text,
    with_canonical_locale,
)
from app.pricing.models import CardmarketOffer, CardmarketSearchResult, ProductInfo, SealedOffer, SealedProductInfo

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

#: Chrome is maximized (see ``_maximize_window`` below), not kept at some
#: small/fixed size: two smaller sizes (700x850, then 1280x720) both proved
#: too cramped to actually read prices/offers comfortably (live-reported).
#: Full-size is fine precisely *because* the app is kept in the foreground
#: throughout (see ``_restore_foreground``) -- Chrome is expected to be
#: sitting behind it the whole time, not something the user has to work
#: around by squinting at a small window.


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

    A plain ``SetForegroundWindow`` call is well known to be silently
    *ignored* by Windows when the calling process doesn't already own the
    foreground -- a deliberate anti-focus-stealing restriction, not a bug --
    live-reported: this function ran without error every time, yet Chrome
    kept staying in front regardless. The standard Win32 workaround is used
    instead: briefly attaching this thread's input state to whichever
    thread currently owns the foreground window (Chrome's, at this point),
    which grants this thread the same foreground-switching privilege that
    one already has, only for the duration of the call.
    """
    if hwnd is None:
        return
    try:
        import win32api
        import win32gui
        import win32process

        current_fg = win32gui.GetForegroundWindow()
        this_thread = win32api.GetCurrentThreadId()
        fg_thread = (
            win32process.GetWindowThreadProcessId(current_fg)[0] if current_fg else 0
        )
        attached = bool(fg_thread) and fg_thread != this_thread
        if attached:
            win32process.AttachThreadInput(fg_thread, this_thread, True)
        try:
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                win32process.AttachThreadInput(fg_thread, this_thread, False)
    except Exception:  # noqa: BLE001 — never let a focus nicety break a lookup
        pass


def _open_in_chrome(url: str, cold_start: bool) -> None:
    """Launch ``url`` in Google Chrome specifically, in a new tab.

    ``cold_start`` (Chrome wasn't already running) additionally requests a
    maximized start -- ignored by Chrome for a tab opened in an
    already-running instance, which is the common case (see
    ``_maximize_window``, called unconditionally after the window is
    matched, for the case this flag doesn't cover).

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed where expected.
    """
    import subprocess

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
        args.append("--start-maximized")
    args.append(url)
    subprocess.Popen(args)  # noqa: S603 — fixed executable, fixed/one URL argument


def _dismiss_cookie_banner(window) -> None:
    """Best-effort: click Cardmarket's own "decline non-essential cookies"

    button if its consent banner is currently showing, otherwise do
    nothing. Silently swallows any error -- this must never block or fail
    the actual price lookup it's called from."""
    try:
        for control in window.descendants(control_type="Button"):
            text = control.window_text() or ""
            if has_cookie_decline_button_text(text):
                control.click_input()
                logger.info("Dismissed Cardmarket's cookie-consent banner.")
                return
    except Exception:  # noqa: BLE001 — best-effort, never blocks the read
        pass


#: Where the resized window is placed -- arbitrary but fixed, so it lands in
def _maximize_window(hwnd: int) -> None:
    """Best-effort: maximize the Chrome window at ``hwnd`` regardless of how
    it was opened -- without stealing foreground focus.

    ``--start-maximized`` (see ``_open_in_chrome``) only actually takes
    effect when Chrome's browser process itself is freshly started --
    Chrome commonly keeps running in the background with no visible window
    at all (Windows' "continue running background apps" setting, on by
    default for many installs), so ``_open_in_chrome``'s own ``cold_start``
    check (no visible window to snapshot) mistakes this for a genuine cold
    start and still passes the flag, but the launch is actually just
    forwarded via IPC to that already-running process, which opens a new
    window at its own default (often small/normal, not maximized) size --
    the flag is silently ignored in that path. Maximizing here
    unconditionally is the only way to reliably get a full-size window
    regardless of which of the two ever actually happened.

    Deliberately ``SetWindowPlacement``, not ``ShowWindow(hwnd,
    SW_MAXIMIZE)`` or pywinauto's own ``window.maximize()`` (which calls
    that internally): a live-reported regression with the *previous*
    version of this function (which called pywinauto's ``restore()``, and
    separately, briefly, an equivalent ``ShowWindow(..., SW_RESTORE)``)
    found Chrome visibly stealing the foreground again, badly enough to
    break price detection outright -- Win32 documents ``ShowWindow`` as
    *always* activating the window as part of showing it, for essentially
    every one of its ``nCmdShow`` values, including ``SW_MAXIMIZE``.
    ``SetWindowPlacement`` sets a window's maximized/minimized/normal state
    and position directly, with no window-activation side effect at all.
    """
    try:
        import win32con
        import win32gui

        flags, _show_cmd, min_pos, max_pos, normal_rect = win32gui.GetWindowPlacement(hwnd)
        win32gui.SetWindowPlacement(
            hwnd, (flags, win32con.SW_SHOWMAXIMIZED, min_pos, max_pos, normal_rect)
        )
    except Exception:  # noqa: BLE001 — cosmetic only, never blocks the read
        logger.warning("Could not maximize the Cardmarket Chrome window.")


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

    _maximize_window(hwnd)

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
    :func:`~app.pricing.cardmarket_parsing.with_canonical_locale`) -- the
    *stored* URL a user might click themselves is never touched, only this
    one read.

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


def read_sealed_offers_for_card(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[SealedOffer]:
    """Open ``url`` in Chrome, read its sealed-product offers, close the tab.

    Reads via a canonical-locale copy of ``url`` (see
    :func:`~app.pricing.cardmarket_parsing.with_canonical_locale`) -- the
    *stored* URL a user might click themselves is never touched, only this
    one read.

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
