"""Tests for the QPainter-drawn condition badge icon cache."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.models.enums import Condition
from app.ui.app import build_application
from app.ui.condition_icon_provider import get_condition_icon


@pytest.fixture(scope="module")
def qapp():
    return build_application([])


@pytest.mark.parametrize("condition", list(Condition))
def test_every_condition_has_a_non_null_icon(qapp, condition: Condition) -> None:
    icon = get_condition_icon(condition)
    assert not icon.isNull()


def test_icon_is_cached_across_calls(qapp) -> None:
    assert get_condition_icon(Condition.NEAR_MINT) is get_condition_icon(Condition.NEAR_MINT)
