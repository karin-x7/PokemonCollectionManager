"""Best-effort screenshot capture of a sealed product's photo from Cardmarket.

Sealed products have no pokemontcg.io-style image API the way cards do (see
``app.catalog.card_image_cache``), and a plain HTTP fetch of a Cardmarket
page is blocked (live-confirmed: HTTP 403) -- the same reason
``browser_price_reader.py`` reads pages via a real, already-open Chrome
window instead of scraping. This module reuses that same already-open
window (see its ``on_window_ready`` hook) rather than opening a second one:
it finds the product photo's own ``Image``-type UI Automation control (a
live spike confirmed Cardmarket product pages expose the main photo this
way, with its accessible name matching the product's own name -- distinct
from small icon/logo images elsewhere on the page, which report their own,
unrelated names), then crops exactly that control's on-screen rectangle out
of a ``PrintWindow`` capture of the whole window.

Deliberately best-effort throughout: every failure mode (no Image control
found, a crop/IO error, GDI failure) returns ``None`` and logs a warning
instead of raising -- a missing photo must never block adding a product,
mirroring ``ensure_card_image()``'s "never raises" contract.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from app import config
from app.logging_config import get_logger

logger = get_logger(__name__)

#: A live-reported, live-screenshotted bug: the captured photo was a solid
#: black rectangle -- the product's ``Image`` control was found and its
#: geometry read correctly, but the underlying Chrome tab hadn't actually
#: *painted* the image's pixels yet at the exact moment ``PrintWindow`` ran
#: (the surrounding text can finish rendering well before a lazy-loaded
#: ``<img>`` does). One retry after a short extra wait gives the image a
#: second chance to have actually painted; a still-blank second attempt is
#: treated the same as "no image found" (``None``) rather than permanently
#: saving a useless black file the user would otherwise never notice.
_BLANK_RETRY_DELAY = 1.0


def _find_product_image_control(window: object, product_name: str):
    """The best-matching ``Image``-type control on ``window``, or ``None``.

    Prefers a control whose accessible name contains (or is contained by,
    case-insensitively) ``product_name`` -- the live-confirmed pattern for
    Cardmarket's own product photo. Falls back to the single largest
    ``Image`` control on the page (icons/flags are consistently much
    smaller than an actual product photo) if no name match is found, or if
    ``product_name`` is blank.

    Live-reported (with the actual price found correctly, but no photo
    saved): Cardmarket's product page renders the photo inside an image
    *carousel*, live-confirmed to contain several ``<img>`` elements sharing
    the exact same accessible name -- e.g. the current slide, an adjacent
    slide positioned off to the side (at a negative on-screen x-coordinate,
    still full-sized) for the slide transition, and a zero-sized responsive
    duplicate. Naively returning the *first* name match (as this used to)
    could just as easily grab one of those off-screen/zero-sized siblings
    as the one actually visible -- and since the same carousel markup is
    the same every time, this wasn't a flaky, retry-fixable timing issue but
    a deterministic wrong-control pick, always failing for that product.
    Now: name-matches are filtered to those actually visible within the
    window's own bounds first, then (mirroring the no-match fallback below)
    the largest of *those* is used, so an off-screen sibling with an
    identical name can no longer be picked over the real, visible photo.
    """
    try:
        images = window.descendants(control_type="Image")
    except Exception:  # noqa: BLE001 — UI tree can vanish mid-read
        return None
    if not images:
        return None

    try:
        window_rect = window.rectangle()
    except Exception:  # noqa: BLE001 — window may vanish mid-read
        window_rect = None

    def _area(control) -> int:
        try:
            rect = control.rectangle()
        except Exception:  # noqa: BLE001 — control may vanish mid-read
            return 0
        return max(0, rect.width()) * max(0, rect.height())

    def _is_onscreen(control) -> bool:
        if window_rect is None:
            return True
        try:
            rect = control.rectangle()
        except Exception:  # noqa: BLE001 — control may vanish mid-read
            return False
        return (
            rect.width() > 0
            and rect.height() > 0
            and rect.left >= window_rect.left
            and rect.top >= window_rect.top
            and rect.right <= window_rect.right
            and rect.bottom <= window_rect.bottom
        )

    onscreen_images = [control for control in images if _is_onscreen(control)]

    normalized_name = product_name.casefold().strip()
    if normalized_name:
        name_matches = []
        for control in onscreen_images:
            try:
                control_name = (control.window_text() or control.element_info.name or "").casefold()
            except Exception:  # noqa: BLE001 — control may vanish mid-read
                continue
            if control_name and (
                control_name in normalized_name or normalized_name in control_name
            ):
                name_matches.append(control)
        if name_matches:
            return max(name_matches, key=_area)

    # No on-screen name match (or a blank name to begin with): fall back to
    # the largest on-screen control, or -- if the on-screen filter somehow
    # excluded everything -- the largest overall, rather than finding
    # nothing at all.
    return max(onscreen_images, key=_area, default=None) or max(images, key=_area, default=None)


def capture_sealed_product_image(
    window: object, product_name: str, dest_dir: Path | None = None
) -> str | None:
    """Capture the product photo shown in ``window`` to a new temp file.

    Returns the saved file's path, or ``None`` (logging a warning) if no
    plausible image control was found or the capture failed for any
    reason -- never raises.

    Retries once, after a short extra wait, if the first capture comes back
    solid black (see :func:`_is_suspiciously_blank`) -- a real, live-
    screenshotted bug: the image control was found and its geometry read
    correctly, but the underlying tab hadn't actually painted the image's
    pixels yet at the exact moment ``PrintWindow`` ran (a lazy-loaded
    ``<img>`` can lag well behind the surrounding text). A still-blank
    second attempt is treated the same as "no image found" -- a permanently
    saved black file would otherwise sit there unnoticed.
    """
    control = _find_product_image_control(window, product_name)
    if control is None:
        logger.warning("No product image control found for %r.", product_name)
        return None

    try:
        window_rect = window.rectangle()
        image_rect = control.rectangle()
    except Exception as exc:  # noqa: BLE001 — control may vanish mid-read
        logger.warning("Could not read image control geometry for %r: %s", product_name, exc)
        return None

    for attempt in (1, 2):
        try:
            cropped = _capture_and_crop(window.handle, window_rect, image_rect)
        except Exception as exc:  # noqa: BLE001 — GDI/Qt failures, never fatal
            logger.warning("Product image capture failed for %r: %s", product_name, exc)
            return None
        if not _is_suspiciously_blank(cropped):
            break
        if attempt == 1:
            logger.info(
                "Captured image for %r looked blank -- retrying once after a short wait.",
                product_name,
            )
            time.sleep(_BLANK_RETRY_DELAY)
        else:
            logger.warning("Captured image for %r was still blank after a retry.", product_name)
            return None

    directory = dest_dir if dest_dir is not None else config.SEALED_PHOTOS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"tmp_{uuid.uuid4().hex}.png"
    if not cropped.save(str(dest)):
        logger.warning("Could not save captured image for %r.", product_name)
        return None
    return str(dest)


#: Live-reported (with screenshots): a captured "photo" that was actually a
#: clean vertical two-tone split -- solid black on one side, a slightly
#: lighter near-black on the other -- with no real image content at all. The
#: original 3x3 sample grid only ever checked for "all samples identical",
#: which this passed: two of its columns happened to fall one on each side
#: of the split, so the 9 samples weren't *all* the same colour even though
#: the capture was still just two flat rectangles, not a photo. A denser
#: grid plus a minimum-distinct-colours bar (instead of "more than one")
#: catches this: a real card photo is colour-rich enough that even a modest
#: sample count almost always yields well above this bar, while a capture
#: that's only ever a handful of flat regions -- one uniform colour, two,
#: or a handful from a partially-painted/composited window -- won't.
_MIN_DISTINCT_SAMPLE_COLOURS = 5


def _is_suspiciously_blank(image) -> bool:
    """Whether ``image`` looks like a failed capture -- (near-)uniformly a

    handful of flat colour regions, e.g. the solid black ``PrintWindow``
    sometimes yields for content that hadn't painted yet, or a partially
    composited window split into a couple of flat blocks. Sampled at a grid
    of points rather than every pixel (cheap, and a genuine photo covering
    the whole crop essentially never happens to match at only a few of
    them)."""
    if image.isNull() or image.width() == 0 or image.height() == 0:
        return True
    xs = (0.1, 0.3, 0.5, 0.7, 0.9)
    ys = (0.1, 0.3, 0.5, 0.7, 0.9)
    samples = {
        image.pixel(int(x * (image.width() - 1)), int(y * (image.height() - 1)))
        for x in xs
        for y in ys
    }
    return len(samples) < _MIN_DISTINCT_SAMPLE_COLOURS


def _capture_and_crop(hwnd: int, window_rect, image_rect):
    """Screenshot the whole ``hwnd`` via PrintWindow, return just the
    ``image_rect`` crop as a ``QImage`` (not yet saved to disk)."""
    # Imported lazily: pywin32/PySide6 GDI plumbing is only needed for this
    # one best-effort operation, mirroring the lazy win32gui import in
    # browser_price_reader.py.
    import win32gui
    import win32ui
    from ctypes import windll

    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage

    width = window_rect.width()
    height = window_rect.height()

    window_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(window_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    try:
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)
        # PW_RENDERFULLCONTENT=2 -- the flag that reliably captures modern
        # (GPU-composited) window content; the plain PrintWindow(...,0)
        # often yields a blank/black image for such windows.
        windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)

        info = bitmap.GetInfo()
        bits = bitmap.GetBitmapBits(True)
        image = QImage(bits, info["bmWidth"], info["bmHeight"], QImage.Format.Format_RGB32)

        crop = QRect(
            image_rect.left - window_rect.left,
            image_rect.top - window_rect.top,
            image_rect.width(),
            image_rect.height(),
        )
        return image.copy(crop)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, window_dc)
