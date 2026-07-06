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

import uuid
from pathlib import Path

from app import config
from app.logging_config import get_logger

logger = get_logger(__name__)


def _find_product_image_control(window: object, product_name: str):
    """The best-matching ``Image``-type control on ``window``, or ``None``.

    Prefers a control whose accessible name contains (or is contained by,
    case-insensitively) ``product_name`` -- the live-confirmed pattern for
    Cardmarket's own product photo. Falls back to the single largest
    ``Image`` control on the page (icons/flags are consistently much
    smaller than an actual product photo) if no name match is found, or if
    ``product_name`` is blank.
    """
    try:
        images = window.descendants(control_type="Image")
    except Exception:  # noqa: BLE001 — UI tree can vanish mid-read
        return None
    if not images:
        return None

    normalized_name = product_name.casefold().strip()

    def _area(control) -> int:
        try:
            rect = control.rectangle()
        except Exception:  # noqa: BLE001 — control may vanish mid-read
            return 0
        return max(0, rect.width()) * max(0, rect.height())

    if normalized_name:
        for control in images:
            try:
                control_name = (control.window_text() or control.element_info.name or "").casefold()
            except Exception:  # noqa: BLE001 — control may vanish mid-read
                continue
            if control_name and (
                control_name in normalized_name or normalized_name in control_name
            ):
                return control

    return max(images, key=_area, default=None)


def capture_sealed_product_image(
    window: object, product_name: str, dest_dir: Path | None = None
) -> str | None:
    """Capture the product photo shown in ``window`` to a new temp file.

    Returns the saved file's path, or ``None`` (logging a warning) if no
    plausible image control was found or the capture failed for any
    reason -- never raises.
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

    directory = dest_dir if dest_dir is not None else config.SEALED_PHOTOS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"tmp_{uuid.uuid4().hex}.png"

    try:
        _capture_and_crop(window.handle, window_rect, image_rect, dest)
    except Exception as exc:  # noqa: BLE001 — GDI/Qt failures, never fatal
        logger.warning("Product image capture failed for %r: %s", product_name, exc)
        return None
    return str(dest)


def _capture_and_crop(hwnd: int, window_rect, image_rect, dest: Path) -> None:
    """Screenshot the whole ``hwnd`` via PrintWindow, save just ``image_rect``."""
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
        cropped = image.copy(crop)
        if not cropped.save(str(dest)):
            raise OSError(f"QImage.save() returned False for {dest}")
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, window_dc)
