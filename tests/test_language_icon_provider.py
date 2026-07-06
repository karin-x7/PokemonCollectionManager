"""Tests for the QPainter-drawn language flag icon cache."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import Language
from app.ui.app import build_application
from app.ui.language_icon_provider import get_language_icon


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.mark.parametrize("language", list(Language))
def test_every_language_has_a_non_null_icon(qapp, language: Language) -> None:
    icon = get_language_icon(language)
    assert not icon.isNull()


def test_icon_is_cached_across_calls(qapp) -> None:
    assert get_language_icon(Language.GERMAN) is get_language_icon(Language.GERMAN)
