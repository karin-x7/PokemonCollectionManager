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

from app.pricing import sealed_image_capture
from app.pricing.sealed_image_capture import (
    _find_product_image_control,
    capture_sealed_product_image,
)


class _FakeRect:
    def __init__(self, left: int, top: int, width: int, height: int) -> None:
        self.left = left
        self.top = top
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
    monkeypatch.setattr(sealed_image_capture, "_capture_and_crop", lambda *a, **k: None)

    result = capture_sealed_product_image(window, "Base Set Booster Box", dest_dir=tmp_path)

    assert result is not None
    assert result.startswith(str(tmp_path))
    assert result.endswith(".png")


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
