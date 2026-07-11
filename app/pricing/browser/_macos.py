"""macOS backend: reads Cardmarket seller offers off a normally-opened
Chrome tab via the Accessibility API (the same mechanism VoiceOver uses).

Mirrors ``app.pricing.browser._windows`` function-for-function -- see that
module's own docstring for the overall design (Chrome specifically, why
this isn't scraping, the six-function contract every platform backend
exposes). This file is the macOS equivalent of every Windows-only piece
there (``pywinauto``/``win32gui``) rebuilt on top of PyObjC:

- ``ApplicationServices`` (``AXUIElement*`` functions) -- reads/interacts
  with Chrome's already-rendered window content, the macOS equivalent of
  UI Automation. Requires the user to grant this app Accessibility access
  (System Settings > Privacy & Security > Accessibility) the first time --
  there is no way around that prompt, and no way for this code to grant it
  on the user's behalf.
- ``AppKit`` (``NSWorkspace``/``NSRunningApplication``) -- finds/activates
  Chrome and this app, the macOS equivalent of ``win32gui.SetForegroundWindow``.
- ``Quartz`` -- posts the Cmd+W keystroke that closes the opened tab, the
  macOS equivalent of ``window.type_keys("^w")``.

IMPORTANT, read before touching this file: none of this has been run on an
actual Mac. It was written to be structurally correct against Apple's
public Accessibility API and PyObjC's usual bridging conventions, mirroring
the already-working Windows backend as closely as the two platforms'
completely different APIs allow -- but it *will* need real, live debugging
on real macOS hardware before it can be trusted, the same way the Windows
backend only reached its current, several-times-corrected state through
repeated live testing (see PROJECT_PROGRESS.md for that history). Treat
every AX-tree assumption below (what role a cookie-consent button has,
whether background tabs are excluded from the tree automatically the way
they are on Windows, ...) as a hypothesis to verify, not a known fact.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Callable
from urllib.parse import quote

from app.i18n import tr
from app.logging_config import get_logger
from app.pricing.cardmarket_parsing import (
    BrowserPriceReaderError,
    _has_cookie_banner,
    _parse_offer_lines,
    _parse_product_info,
    _parse_search_result_line,
    _parse_sealed_offer_lines,
    _parse_sealed_product_info,
    has_cookie_decline_button_text,
    with_canonical_locale,
)
from app.pricing.models import CardmarketOffer, CardmarketSearchResult, ProductInfo, SealedOffer, SealedProductInfo

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 30.0
_POLL_INTERVAL = 0.5
_SETTLE_DELAY = 2.0
_MIN_EXPECTED_LINES = 30

#: Chrome's own bundle identifier -- stable across versions/install
#: locations, used both to find Chrome (via ``NSWorkspace``) and to find its
#: already-running process (via ``NSRunningApplication``).
_CHROME_BUNDLE_ID = "com.google.Chrome"

#: Accessibility attribute/action names -- passed as raw strings rather than
#: imported constants (e.g. ``kAXWindowsAttribute``). Deliberate: these are
#: exactly the string values Apple's own headers define them as, and are
#: far less likely to break across PyObjC versions than relying on every
#: one of these particular names having been bridged/exported identically.
_AX_WINDOWS = "AXWindows"
_AX_TITLE = "AXTitle"
_AX_CHILDREN = "AXChildren"
_AX_VALUE = "AXValue"
_AX_DESCRIPTION = "AXDescription"
_AX_ROLE = "AXRole"
_AX_POSITION = "AXPosition"
_AX_SIZE = "AXSize"
_AX_PRESS = "AXPress"
_AX_ROLE_BUTTON = "AXButton"
_AX_ROLE_LINK = "AXLink"

#: ``AXValueType`` enum values (Apple's ``ApplicationServices/HIServices``
#: header) -- used to wrap a ``CGPoint``/``CGSize`` for
#: ``AXUIElementSetAttributeValue``. Passed as raw ints for the same reason
#: as the attribute names above.
_AX_VALUE_CGPOINT_TYPE = 1
_AX_VALUE_CGSIZE_TYPE = 2

#: A tree walk has to stop somewhere -- a real Chrome page's AX tree is deep
#: but finite; this is a generous ceiling against a pathological/cyclic tree
#: rather than a value expected to actually be hit in practice.
_MAX_AX_TREE_DEPTH = 80

#: ``NSApplicationActivateIgnoringOtherApps`` (``AppKit/NSRunningApplication``)
#: -- passed as a raw int for the same reason as the AX constants above.
_ACTIVATE_IGNORING_OTHER_APPS = 1 << 1

#: ``kCGHIDEventTap`` (``CGEventTapLocation`` enum) and
#: ``kCGEventFlagMaskCommand`` (``CGEventFlags`` enum), from
#: ``Quartz/CoreGraphics`` -- used to post the Cmd+W keystroke. Raw values
#: for the same reason as the AX constants above.
_CG_HID_EVENT_TAP = 0
_CG_EVENT_FLAG_MASK_COMMAND = 1 << 20
#: ``kVK_ANSI_W`` (``Carbon/HIToolbox`` virtual keycode) -- the physical "W"
#: key, independent of keyboard layout for the letter position (not the
#: character), which is what a keyboard-shortcut keycode always refers to.
_KEYCODE_W = 13


def _find_chrome_app_url():
    """The installed Google Chrome.app's URL, or ``None`` if not installed."""
    from AppKit import NSWorkspace

    return NSWorkspace.sharedWorkspace().URLForApplicationWithBundleIdentifier_(_CHROME_BUNDLE_ID)


def _chrome_pid() -> int | None:
    """The process id of Chrome's currently-running instance, if any."""
    from AppKit import NSWorkspace

    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.bundleIdentifier() == _CHROME_BUNDLE_ID:
            return app.processIdentifier()
    return None


def _require_accessibility_permission() -> None:
    """Raises a clear error if this app hasn't been granted Accessibility
    access yet -- every function below that reads/manipulates a Chrome
    window depends on it, and a missing grant otherwise fails as a much
    less obvious "window not found" error instead.
    """
    from ApplicationServices import AXIsProcessTrusted

    if not AXIsProcessTrusted():
        raise BrowserPriceReaderError(
            tr(
                "Diese App benötigt die Bedienungshilfen-Berechtigung, um "
                "Cardmarket-Preise zu lesen. Bitte unter Systemeinstellungen "
                "> Datenschutz & Sicherheit > Bedienungshilfen aktivieren "
                "und die App neu starten."
            )
        )


def _open_in_chrome(url: str) -> None:
    """Launch ``url`` in Google Chrome specifically, in a new tab.

    Unlike the Windows backend, there's no separate cold-start window-size
    request here -- ``_maximize_window`` (called unconditionally once the
    window is matched, see ``_open_and_capture_visible_text``) already
    covers both the cold- and warm-start case identically, so there's
    nothing this launch step needs to do differently between them.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed where expected.
    """
    import subprocess

    if _find_chrome_app_url() is None:
        raise BrowserPriceReaderError(
            tr(
                "Google Chrome wurde nicht gefunden. Bitte installiere "
                "Chrome aus dem App Store oder von google.com/chrome."
            )
        )
    # "open -a <app> <url>" is macOS's own, standard way to open a URL with
    # a specific app -- equivalent to a user dragging the link onto Chrome's
    # dock icon, not a Chrome-specific automation trick.
    subprocess.Popen(["open", "-a", "Google Chrome", url])  # noqa: S603, S607


def open_cardmarket_link(url: str) -> None:
    """Open ``url`` in Chrome and leave it open, in its normal foreground size.

    Backs the "Open Cardmarket link" context-menu action -- see
    ``app.pricing.browser._windows.open_cardmarket_link``'s own docstring
    for why this is deliberately simpler than every other function here (no
    window-matching, resizing, or closing at all).

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed where expected.
    """
    import subprocess

    if _find_chrome_app_url() is None:
        raise BrowserPriceReaderError(
            tr(
                "Google Chrome wurde nicht gefunden. Bitte installiere "
                "Chrome aus dem App Store oder von google.com/chrome."
            )
        )
    subprocess.Popen(["open", "-a", "Google Chrome", url])  # noqa: S603, S607


def open_cardmarket_search(name: str) -> None:
    """Open Cardmarket's own site search for ``name`` in Chrome, in its

    normal foreground size, and leave it open -- see
    ``app.pricing.browser._windows.open_cardmarket_search``'s own docstring
    for the full rationale (same "leave it open" contract as
    :func:`open_cardmarket_link`).

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed where expected.
    """
    from urllib.parse import quote

    url = f"https://www.cardmarket.com/en/Pokemon/Products/Search?searchString={quote(name)}"
    open_cardmarket_link(url)


def _ax_attr(element, attribute: str):
    """``AXUIElementCopyAttributeValue``, collapsed to just the value (or
    ``None`` on any error) -- every call site here only ever wants the
    value, never the raw ``AXError`` code, and repeating the
    error-code-checking boilerplate at every call site would bury the
    actual logic.
    """
    from ApplicationServices import AXUIElementCopyAttributeValue

    try:
        error, value = AXUIElementCopyAttributeValue(element, attribute, None)
    except Exception:  # noqa: BLE001 — a stale/vanished element can raise
        return None
    return value if error == 0 else None


def _chrome_window_titles(pid: int | None) -> list[str]:
    """Every one of Chrome's window titles right now, in whatever order the
    Accessibility API reports them.

    A list, not a dict keyed by window handle like the Windows backend's
    ``_chrome_window_titles`` -- an ``AXUIElement`` reference has no stable,
    hashable identity across separate Accessibility calls the way a Win32
    ``HWND`` integer does, so matching (see ``_find_new_cardmarket_window``)
    instead compares *how many times* a given title appears now vs. before,
    which needs only a plain list.
    """
    if pid is None:
        return []
    from ApplicationServices import AXUIElementCreateApplication

    app_ref = AXUIElementCreateApplication(pid)
    windows = _ax_attr(app_ref, _AX_WINDOWS) or []
    return [_ax_attr(window, _AX_TITLE) or "" for window in windows]


def _find_new_cardmarket_window(pid: int, titles_before: list[str]):
    """The first current Chrome window whose title mentions "Cardmarket" but
    wasn't already present (same text, same count) before this lookup
    started.

    Mirrors the Windows backend's title-diff matching (see its own
    ``_open_and_capture_visible_text`` docstring for why this must exclude
    a stale, already-open tab from an earlier lookup rather than matching
    any window that merely mentions Cardmarket) -- adapted to compare
    per-title *counts* rather than per-handle identity, since ``AXUIElement``
    has no stable handle equivalent (see ``_chrome_window_titles``).
    """
    from ApplicationServices import AXUIElementCreateApplication

    app_ref = AXUIElementCreateApplication(pid)
    windows = _ax_attr(app_ref, _AX_WINDOWS) or []
    before_counts = Counter(titles_before)
    seen_counts: Counter = Counter()
    for window in windows:
        title = _ax_attr(window, _AX_TITLE) or ""
        seen_counts[title] += 1
        if "cardmarket" not in title.casefold():
            continue
        if seen_counts[title] > before_counts.get(title, 0):
            return window
    return None


def _activate_own_app() -> None:
    """Best-effort: brings this app back to the foreground.

    Mirrors ``app.pricing.browser._windows._restore_foreground``, but
    without that function's ``AttachThreadInput`` workaround -- macOS has no
    equivalent restriction blocking a background process from activating
    itself (unlike Win32's ``SetForegroundWindow``, which silently no-ops
    for a caller that isn't already foreground); a plain
    ``activateWithOptions_`` call is expected to just work. Unverified live,
    like everything else in this module.
    """
    try:
        from AppKit import NSRunningApplication

        NSRunningApplication.currentApplication().activateWithOptions_(
            _ACTIVATE_IGNORING_OTHER_APPS
        )
    except Exception:  # noqa: BLE001 — never let a focus nicety break a lookup
        pass


def _activate_chrome(pid: int) -> None:
    """Best-effort: brings Chrome to the foreground -- needed just before
    posting the Cmd+W keystroke (see ``_close_active_tab``), since a
    synthetic keyboard event is delivered to whichever app currently has
    keyboard focus, the same requirement ``window.set_focus()`` serves on
    Windows before sending Ctrl+W there.
    """
    try:
        from AppKit import NSRunningApplication

        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is not None:
            app.activateWithOptions_(_ACTIVATE_IGNORING_OTHER_APPS)
    except Exception:  # noqa: BLE001 — never let a focus nicety break a lookup
        pass


def _maximize_window(window) -> None:
    """Best-effort: resize ``window`` to fill the main screen's visible
    area (below the menu bar, above the Dock) -- without stealing
    foreground focus.

    Deliberately sets position+size directly rather than toggling the
    window's zoom state (the green-button/"AXZoomWindow" action) or its
    native fullscreen state (the ``AXFullScreen`` attribute): a toggle is
    only correct if you already know the current state, whereas setting an
    explicit position/size is idempotent regardless of it -- mirrors the
    Windows backend's own ``_maximize_window``, which had exactly this
    "must not depend on unknown prior state" requirement after its first,
    toggle-shaped attempt (``window.restore()``) caused a live regression
    there. Native fullscreen is also avoided on principle: it moves a
    window to its own macOS Space instead of maximizing in place, which
    would defeat "stays behind the app" entirely.
    """
    try:
        from ApplicationServices import AXUIElementSetAttributeValue, AXValueCreate
        from AppKit import NSScreen

        screen = NSScreen.mainScreen()
        if screen is None:
            return
        visible = screen.visibleFrame()
        full_height = screen.frame().size.height
        # AX/Quartz screen coordinates have their origin at the top-left;
        # NSScreen's have it at the bottom-left -- convert the y coordinate.
        position = _AXValuePoint(visible.origin.x, full_height - visible.origin.y - visible.size.height)
        size = _AXValueSize(visible.size.width, visible.size.height)
        AXUIElementSetAttributeValue(
            window, _AX_POSITION, AXValueCreate(_AX_VALUE_CGPOINT_TYPE, position)
        )
        AXUIElementSetAttributeValue(
            window, _AX_SIZE, AXValueCreate(_AX_VALUE_CGSIZE_TYPE, size)
        )
    except Exception:  # noqa: BLE001 — cosmetic only, never blocks the read
        logger.warning("Could not maximize the Cardmarket Chrome window.")


def _AXValuePoint(x: float, y: float):
    """A ``CGPoint`` struct suitable for ``AXValueCreate`` -- a tiny helper
    only to keep ``_maximize_window`` readable; PyObjC's ``Quartz.CGPoint``
    is a plain ``(x, y)``-shaped struct wrapper."""
    from Quartz import CGPoint

    return CGPoint(x, y)


def _AXValueSize(width: float, height: float):
    """A ``CGSize`` struct suitable for ``AXValueCreate`` -- see
    ``_AXValuePoint``."""
    from Quartz import CGSize

    return CGSize(width, height)


def _close_active_tab(pid: int) -> None:
    """Best-effort: sends Cmd+W to close the currently-active tab.

    Requires Chrome to be the frontmost app for the keystroke to land on it
    (see ``_activate_chrome``) -- mirrors the Windows backend's
    ``window.set_focus()`` + ``type_keys("^w")`` pair, just posted as a raw
    synthetic key event instead of through pywinauto.
    """
    from Quartz import CGEventCreateKeyboardEvent, CGEventPost, CGEventSetFlags

    _activate_chrome(pid)
    for key_down in (True, False):
        event = CGEventCreateKeyboardEvent(None, _KEYCODE_W, key_down)
        CGEventSetFlags(event, _CG_EVENT_FLAG_MASK_COMMAND)
        CGEventPost(_CG_HID_EVENT_TAP, event)


#: Cardmarket's own cookie-consent banner button -- dismissed the same way
#: on every platform, see ``has_cookie_decline_button_text``'s own docstring
#: in cardmarket_parsing.py.
def _dismiss_cookie_banner(window) -> None:
    """Best-effort: click Cardmarket's own "decline non-essential cookies"

    button if its consent banner is currently showing, otherwise do
    nothing. Silently swallows any error -- this must never block or fail
    the actual price lookup it's called from."""
    try:
        from ApplicationServices import AXUIElementPerformAction

        buttons: list = []
        _collect_by_role(window, _AX_ROLE_BUTTON, buttons)
        for button in buttons:
            text = _ax_attr(button, _AX_TITLE) or ""
            if has_cookie_decline_button_text(text):
                AXUIElementPerformAction(button, _AX_PRESS)
                logger.info("Dismissed Cardmarket's cookie-consent banner.")
                return
    except Exception:  # noqa: BLE001 — best-effort, never blocks the read
        pass


def _collect_by_role(element, role: str, results: list, depth: int = 0) -> None:
    """Every descendant of ``element`` (inclusive) whose ``AXRole`` matches
    ``role``, appended to ``results`` in tree order."""
    if depth > _MAX_AX_TREE_DEPTH:
        return
    try:
        if _ax_attr(element, _AX_ROLE) == role:
            results.append(element)
        for child in _ax_attr(element, _AX_CHILDREN) or ():
            _collect_by_role(child, role, results, depth + 1)
    except Exception:  # noqa: BLE001 — a control may vanish mid-walk
        return


def _read_visible_text(window) -> list[str]:
    """Every text-bearing element under ``window``, in tree order --
    the macOS/Accessibility equivalent of the Windows backend's
    ``_read_visible_text``.

    Assumes (unverified live) that Chrome, like on Windows, only exposes
    the *active* tab's content through the Accessibility tree at all --
    i.e. that there is no separate "is this control actually visible right
    now" check needed the way the Windows backend's own
    ``descendant.is_visible()`` check has to filter background tabs'
    controls out of a tree that otherwise contains all of them regardless
    of which tab is active. If that assumption turns out wrong on real
    hardware, this is the first place to add an equivalent filter.
    """
    lines: list[str] = []
    _walk_ax_text(window, lines)
    return lines


def _walk_ax_text(element, lines: list[str], depth: int = 0) -> None:
    if depth > _MAX_AX_TREE_DEPTH:
        return
    try:
        for attribute in (_AX_VALUE, _AX_TITLE, _AX_DESCRIPTION):
            value = _ax_attr(element, attribute)
            if isinstance(value, str) and value:
                lines.append(value)
                break  # one text value per element, mirrors window_text()
        for child in _ax_attr(element, _AX_CHILDREN) or ():
            _walk_ax_text(child, lines, depth + 1)
    except Exception:  # noqa: BLE001 — a control may vanish mid-walk
        return


def _open_and_capture_visible_text(
    url: str,
    match_hint: str,
    timeout: float = _DEFAULT_TIMEOUT,
    on_window_ready: Callable[[object], None] | None = None,
) -> list[str]:
    """Open ``url`` in Chrome, capture its visible on-screen text, close the tab.

    Structurally identical to the Windows backend's own function of the
    same name -- see its docstring for the full rationale (title-diff
    window matching, the settle-delay retry for a still-rendering page,
    ``on_window_ready`` for the sealed-product/manual-entry image capture).
    The only platform-specific pieces are how a "window" is found/resized/
    closed; the parsing of whatever text comes back is 100% shared (see
    ``app.pricing.cardmarket_parsing``).

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, or no matching window appears
            within ``timeout``.
    """
    _require_accessibility_permission()

    titles_before = _chrome_window_titles(_chrome_pid())
    _open_in_chrome(url)

    deadline = time.monotonic() + timeout
    window = None
    while time.monotonic() < deadline:
        pid = _chrome_pid()
        if pid is not None:
            window = _find_new_cardmarket_window(pid, titles_before)
        if window is not None:
            break
        time.sleep(_POLL_INTERVAL)

    _activate_own_app()

    if window is None:
        raise BrowserPriceReaderError(
            tr("Cardmarket-Tab für „{hint}“ wurde nicht rechtzeitig gefunden.").format(
                hint=match_hint
            )
        )

    _maximize_window(window)

    try:
        time.sleep(_SETTLE_DELAY)
        _dismiss_cookie_banner(window)
        lines = _read_visible_text(window)
        if len(lines) < _MIN_EXPECTED_LINES or _has_cookie_banner(lines):
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
            pid = _chrome_pid()
            if pid is not None:
                _close_active_tab(pid)
        except Exception:  # noqa: BLE001 — best-effort tab cleanup
            logger.warning("Could not close the Cardmarket tab for %r automatically.", match_hint)
        finally:
            _activate_own_app()


def read_product_info(
    url: str, timeout: float = _DEFAULT_TIMEOUT, capture_image: bool = False
) -> ProductInfo:
    """Open ``url`` in Chrome, parse its title into name/set/number, close the tab.

    ``capture_image`` is accepted for interface parity with the Windows
    backend but always yields ``ProductInfo.photo_path=None`` on macOS for
    now -- the Windows version's screenshot capture
    (``app.pricing.sealed_image_capture``) is built on ``PrintWindow``,
    which has no direct macOS equivalent (that would be Quartz's
    ``CGWindowListCreateImage``, needing its own Screen Recording
    permission on top of Accessibility) -- deferred rather than guessed at
    without a way to verify it. This never affects whether the lookup
    itself succeeds, the same as a failed capture on Windows.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, no matching window appears within
            ``timeout``, or the page's title doesn't match the expected
            Cardmarket product-page pattern.
    """
    lines = _open_and_capture_visible_text(url, tr("Karte manuell eintragen"), timeout)
    info = _parse_product_info(lines)
    if info is None:
        raise BrowserPriceReaderError(
            tr(
                "Die Seite wurde nicht als Cardmarket-Produktseite erkannt. Bitte "
                "prüfe den Link."
            )
        )
    return info


def read_offers_for_card(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[CardmarketOffer]:
    """Open ``url`` in Chrome, read its offers, close the tab.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, no matching window appears within
            ``timeout``, or the window's content can't be parsed into any
            offers.
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

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, or no matching window appears
            within ``timeout``.
    """
    results: list[CardmarketSearchResult] = []

    def _collect(window: object) -> None:
        links: list = []
        _collect_by_role(window, _AX_ROLE_LINK, links)
        for link in links:
            text = _ax_attr(link, _AX_TITLE) or _ax_attr(link, _AX_VALUE) or ""
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

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, no matching window appears within
            ``timeout``, the matching link can't be found on a fresh
            search, or the resulting page's own URL can't be read.
    """
    real_url: str | None = None

    def _click_through(window: object) -> None:
        nonlocal real_url
        from ApplicationServices import AXUIElementPerformAction

        links: list = []
        _collect_by_role(window, _AX_ROLE_LINK, links)
        for link in links:
            text = _ax_attr(link, _AX_TITLE) or _ax_attr(link, _AX_VALUE) or ""
            if text != chosen.raw_text:
                continue
            AXUIElementPerformAction(link, _AX_PRESS)
            time.sleep(_SETTLE_DELAY)
            found_lines: list[str] = []
            _walk_ax_text(window, found_lines)
            for line in found_lines:
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

    ``capture_image`` is accepted for interface parity but always yields
    ``SealedProductInfo.photo_path=None`` for now -- see
    ``read_product_info``'s own docstring for why.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, no matching window appears within
            ``timeout``, or the page's title doesn't match the expected
            Cardmarket product-page pattern.
    """
    lines = _open_and_capture_visible_text(url, tr("Sealed-Produkt eintragen"), timeout)
    info = _parse_sealed_product_info(lines)
    if info is None:
        raise BrowserPriceReaderError(
            tr(
                "Die Seite wurde nicht als Cardmarket-Produktseite erkannt. Bitte "
                "prüfe den Link."
            )
        )
    return info


def read_sealed_offers_for_card(
    url: str, match_hint: str, timeout: float = _DEFAULT_TIMEOUT
) -> list[SealedOffer]:
    """Open ``url`` in Chrome, read its sealed-product offers, close the tab.

    Raises:
        BrowserPriceReaderError: If Chrome isn't installed, Accessibility
            access hasn't been granted, no matching window appears within
            ``timeout``, or the window's content can't be parsed into any
            offers.
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
