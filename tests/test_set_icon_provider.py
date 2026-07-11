"""Tests for the set-icon in-memory cache's own scaling logic.

``get_set_icon`` itself is globally monkeypatched to skip network/disk (see
conftest.py's autouse ``_no_real_set_icon_downloads``) in every other test --
these exercise ``_load_scaled_icon`` directly against real, on-disk test
images instead.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage, QPixmap

from app.ui.app import build_application
from app.ui.set_icon_provider import _ICON_SIZE, _load_scaled_icon


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


def _save_solid_image(path, width: int, height: int) -> None:
    image = QImage(width, height, QImage.Format.Format_RGBA8888)
    image.fill(QColor(255, 165, 0, 255))
    assert image.save(str(path))


def test_scaled_icon_canvas_matches_the_fixed_icon_size(qapp, tmp_path) -> None:
    # Real, live-reported bug: pokemontcg.io serves some set icons at huge,
    # non-square native resolutions (884x452px, live-confirmed) -- wrapped
    # directly into a QIcon with no resizing, Qt's default item-view icon
    # rendering reserved a decoration slot sized to that, showing as a
    # mismatched box around the actual small, aspect-fit glyph.
    path = tmp_path / "huge_icon.png"
    _save_solid_image(path, 884, 452)

    icon = _load_scaled_icon(str(path))

    assert icon is not None
    pixmap = icon.pixmap(_ICON_SIZE, _ICON_SIZE)
    assert pixmap.width() == _ICON_SIZE
    assert pixmap.height() == _ICON_SIZE


def test_scaled_icon_preserves_aspect_ratio_centred_on_transparent_canvas(
    qapp, tmp_path
) -> None:
    # A wide (2:1) source must not be stretched to fill the square canvas --
    # it should be letterboxed (transparent above/below), centred.
    path = tmp_path / "wide_icon.png"
    _save_solid_image(path, 40, 20)

    icon = _load_scaled_icon(str(path))

    image = icon.pixmap(_ICON_SIZE, _ICON_SIZE).toImage()
    assert image.pixelColor(0, 0).alpha() == 0  # corner: transparent letterbox
    assert image.pixelColor(_ICON_SIZE // 2, _ICON_SIZE // 2).alpha() > 0  # centre: the icon


def test_scaled_icon_returns_none_for_a_null_source(tmp_path) -> None:
    missing = tmp_path / "does-not-exist.png"

    assert _load_scaled_icon(str(missing)) is None
