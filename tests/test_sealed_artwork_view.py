"""Tests for SealedArtworkView's photo/placeholder state.

Mirrors ``test_card_artwork_view.py``, minus the Reverse Holo overlay (which
doesn't exist for sealed products).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QPixmap

from app.ui.app import build_application
from app.ui.widgets.sealed_artwork_view import SealedArtworkView


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
    view = SealedArtworkView()
    view.show_empty()

    assert view._pixmap is None


def test_show_photo_with_none_path_has_no_pixmap(qapp) -> None:
    view = SealedArtworkView()
    view.show_photo(None)

    assert view._pixmap is None


def test_show_photo_with_missing_file_has_no_pixmap(qapp) -> None:
    view = SealedArtworkView()
    view.show_photo("/does/not/exist.png")

    assert view._pixmap is None


def test_show_photo_loads_pixmap(qapp, sample_image_path) -> None:
    view = SealedArtworkView()
    view.show_photo(sample_image_path)

    assert view._pixmap is not None
    assert not view._pixmap.isNull()


def test_paint_event_does_not_crash_in_any_state(qapp, sample_image_path) -> None:
    view = SealedArtworkView()
    view.resize(200, 200)

    view.show_empty()
    assert not view.grab().isNull()

    view.show_photo(sample_image_path)
    assert not view.grab().isNull()
