"""Tests for the sealed product image capture's pure-Python matching logic.

The actual PrintWindow/GDI crop (``_capture_and_crop``) needs a real window
handle and is exercised only by a live, manual smoke test (this project's
convention for anything that touches real OS/Chrome state) -- these tests
cover ``_find_product_image_control``'s matching/fallback behaviour and
``capture_sealed_product_image``'s best-effort error handling using fake
UI-Automation-shaped objects, with ``_capture_and_crop`` monkeypatched.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QImage

from app.pricing import sealed_image_capture
from app.pricing.sealed_image_capture import (
    _find_product_image_control,
    _is_suspiciously_blank,
    capture_sealed_product_image,
)


def _solid_image(color: str = "black", size: int = 10) -> QImage:
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    return image


def _varied_image(size: int = 10) -> QImage:
    """A non-blank stand-in for a real photo -- a distinct colour at every
    pixel (a simple gradient), so every one of ``_is_suspiciously_blank``'s
    sample points lands on a different colour, same as a genuine photo's
    rich colour variety."""
    image = QImage(size, size, QImage.Format.Format_RGB32)
    for y in range(size):
        for x in range(size):
            image.setPixelColor(x, y, QColor(x * 20 % 256, y * 20 % 256, (x + y) * 10 % 256))
    return image


class _FakeRect:
    def __init__(self, left: int, top: int, width: int, height: int) -> None:
        self.left = left
        self.top = top
        self.right = left + width
        self.bottom = top + height
        self._width = width
        self._height = height

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class _FakeElementInfo:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeControl:
    def __init__(self, name: str, rect: _FakeRect) -> None:
        self._name = name
        self._rect = rect
        self.element_info = _FakeElementInfo(name)

    def window_text(self) -> str:
        return self._name

    def rectangle(self) -> _FakeRect:
        return self._rect


class _FakeWindow:
    def __init__(self, images: list[_FakeControl], handle: int = 123) -> None:
        self._images = images
        self.handle = handle

    def descendants(self, control_type: str | None = None) -> list[_FakeControl]:
        return self._images if control_type == "Image" else []

    def rectangle(self) -> _FakeRect:
        return _FakeRect(0, 0, 1000, 1000)


def test_find_product_image_control_returns_none_without_any_image() -> None:
    window = _FakeWindow([])

    assert _find_product_image_control(window, "Base Set Booster Box") is None


def test_find_product_image_control_matches_by_name() -> None:
    icon = _FakeControl("flag-en", _FakeRect(0, 0, 20, 20))
    photo = _FakeControl("Base Set Booster Box", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([icon, photo])

    found = _find_product_image_control(window, "Base Set Booster Box")

    assert found is photo


def test_find_product_image_control_falls_back_to_largest_when_no_name_matches() -> None:
    small = _FakeControl("unrelated-icon", _FakeRect(0, 0, 20, 20))
    large = _FakeControl("also-unrelated", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([small, large])

    found = _find_product_image_control(window, "Base Set Booster Box")

    assert found is large


def test_find_product_image_control_skips_offscreen_carousel_sibling() -> None:
    # Live-reported bug: Cardmarket's photo carousel has several <img>
    # elements sharing the exact same accessible name -- an adjacent slide
    # sitting off to the side (negative on-screen x, for the slide
    # transition) is full-sized and would previously have been returned
    # just because it was encountered first, deterministically capturing a
    # blank/wrong crop every single time for that product.
    offscreen_sibling = _FakeControl("Blitza", _FakeRect(-171, 472, 242, 343))
    visible_photo = _FakeControl("Blitza", _FakeRect(92, 472, 242, 343))
    window = _FakeWindow([offscreen_sibling, visible_photo])

    found = _find_product_image_control(window, "Blitza")

    assert found is visible_photo


def test_find_product_image_control_skips_zero_sized_duplicate() -> None:
    zero_sized = _FakeControl("Blitza", _FakeRect(0, 0, 0, 0))
    visible_photo = _FakeControl("Blitza", _FakeRect(92, 472, 242, 343))
    window = _FakeWindow([zero_sized, visible_photo])

    found = _find_product_image_control(window, "Blitza")

    assert found is visible_photo


def test_find_product_image_control_falls_back_to_largest_with_blank_name() -> None:
    small = _FakeControl("a", _FakeRect(0, 0, 20, 20))
    large = _FakeControl("b", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([small, large])

    found = _find_product_image_control(window, "")

    assert found is large


def test_capture_returns_none_when_no_image_control_found() -> None:
    window = _FakeWindow([])

    result = capture_sealed_product_image(window, "Base Set Booster Box")

    assert result is None


def test_capture_returns_saved_path_on_success(monkeypatch, tmp_path) -> None:
    photo = _FakeControl("Base Set Booster Box", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([photo])
    monkeypatch.setattr(
        sealed_image_capture, "_capture_and_crop", lambda *a, **k: _varied_image()
    )

    result = capture_sealed_product_image(window, "Base Set Booster Box", dest_dir=tmp_path)

    assert result is not None
    assert result.startswith(str(tmp_path))
    assert result.endswith(".png")


def test_is_suspiciously_blank_detects_a_solid_colour_image() -> None:
    assert _is_suspiciously_blank(_solid_image("black")) is True
    assert _is_suspiciously_blank(_solid_image("white")) is True


def test_is_suspiciously_blank_false_for_a_varied_image() -> None:
    assert _is_suspiciously_blank(_varied_image()) is False


def test_is_suspiciously_blank_true_for_a_null_image() -> None:
    assert _is_suspiciously_blank(QImage()) is True


def test_is_suspiciously_blank_detects_a_two_tone_split_image() -> None:
    # Live-reported (with screenshots): a captured "photo" was actually a
    # clean vertical two-tone split -- solid black on one side, a slightly
    # lighter near-black on the other -- with no real image content. The
    # original 3x3 sample grid missed this: two of its three x-positions
    # happened to fall on the same side of the split, so the 9 samples
    # weren't literally *all* identical even though the image was still
    # just two flat rectangles, not a photo.
    size = 20
    image = QImage(size, size, QImage.Format.Format_RGB32)
    for y in range(size):
        for x in range(size):
            image.setPixelColor(x, y, QColor("black") if x < size * 0.55 else QColor(20, 22, 27))

    assert _is_suspiciously_blank(image) is True


def test_capture_retries_once_after_a_blank_first_attempt(monkeypatch, tmp_path) -> None:
    # Real, live-screenshotted bug: the first capture came back solid black
    # (the image hadn't painted yet) -- a retry should give it another
    # chance rather than saving the useless black file.
    photo = _FakeControl("Base Set Booster Box", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([photo])
    attempts = [_solid_image("black"), _varied_image()]
    monkeypatch.setattr(
        sealed_image_capture, "_capture_and_crop", lambda *a, **k: attempts.pop(0)
    )
    monkeypatch.setattr(sealed_image_capture.time, "sleep", lambda seconds: None)

    result = capture_sealed_product_image(window, "Base Set Booster Box", dest_dir=tmp_path)

    assert result is not None
    assert attempts == []  # both queued attempts were consumed


def test_capture_returns_none_when_still_blank_after_retry(monkeypatch, tmp_path) -> None:
    photo = _FakeControl("Base Set Booster Box", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([photo])
    monkeypatch.setattr(
        sealed_image_capture, "_capture_and_crop", lambda *a, **k: _solid_image("black")
    )
    monkeypatch.setattr(sealed_image_capture.time, "sleep", lambda seconds: None)

    result = capture_sealed_product_image(window, "Base Set Booster Box", dest_dir=tmp_path)

    assert result is None


def test_capture_returns_none_when_crop_raises(monkeypatch, tmp_path) -> None:
    photo = _FakeControl("Base Set Booster Box", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([photo])

    def _raise(*args, **kwargs):
        raise OSError("GDI failure")

    monkeypatch.setattr(sealed_image_capture, "_capture_and_crop", _raise)

    result = capture_sealed_product_image(window, "Base Set Booster Box", dest_dir=tmp_path)

    assert result is None


def test_capture_returns_none_when_geometry_read_fails(tmp_path) -> None:
    class _BrokenControl(_FakeControl):
        def rectangle(self):
            raise RuntimeError("control vanished")

    photo = _BrokenControl("Base Set Booster Box", _FakeRect(0, 0, 400, 400))
    window = _FakeWindow([photo])

    result = capture_sealed_product_image(window, "Base Set Booster Box", dest_dir=tmp_path)

    assert result is None
