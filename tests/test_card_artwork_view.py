"""Tests for CardArtworkView's photo/placeholder/Reverse-Holo-overlay state."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QPixmap

from app.ui.app import build_application
from app.ui.widgets.card_artwork_view import CardArtworkView


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.fixture
def sample_image_path(tmp_path) -> str:
    pixmap = QPixmap(20, 20)
    pixmap.fill(QColor("red"))
    path = tmp_path / "sample.png"
    pixmap.save(str(path))
    return str(path)


def test_show_empty_clears_state(qapp) -> None:
    view = CardArtworkView()
    view.show_empty()

    assert view._pixmap is None
    assert view._reverse_holo is False


def test_show_photo_with_none_path_has_no_pixmap(qapp) -> None:
    view = CardArtworkView()
    view.show_photo(None, reverse_holo=True)

    assert view._pixmap is None
    # reverse_holo flag itself is stored even without a pixmap to draw it on,
    # since there's nothing to visually distinguish either way.
    assert view._reverse_holo is True


def test_show_photo_with_missing_file_has_no_pixmap(qapp) -> None:
    view = CardArtworkView()
    view.show_photo("/does/not/exist.png", reverse_holo=False)

    assert view._pixmap is None


def test_show_photo_loads_pixmap_and_sets_reverse_holo_flag(qapp, sample_image_path) -> None:
    view = CardArtworkView()
    view.show_photo(sample_image_path, reverse_holo=True)

    assert view._pixmap is not None
    assert not view._pixmap.isNull()
    assert view._reverse_holo is True


def test_show_photo_without_reverse_holo(qapp, sample_image_path) -> None:
    view = CardArtworkView()
    view.show_photo(sample_image_path, reverse_holo=False)

    assert view._pixmap is not None
    assert view._reverse_holo is False


def test_paint_event_does_not_crash_in_any_state(qapp, sample_image_path) -> None:
    view = CardArtworkView()
    view.resize(200, 180)

    view.show_empty()
    assert not view.grab().isNull()

    view.show_photo(sample_image_path, reverse_holo=False)
    assert not view.grab().isNull()

    view.show_photo(sample_image_path, reverse_holo=True)
    assert not view.grab().isNull()
