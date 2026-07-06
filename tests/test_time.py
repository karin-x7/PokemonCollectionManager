"""Tests for the shared timestamp formatting helper."""

from __future__ import annotations

from app.utils.time import format_display_datetime


def test_format_display_datetime_spaces_date_and_time_apart() -> None:
    assert format_display_datetime("2026-07-04T20:05:27+00:00") == "04.07.2026   20:05"


def test_format_display_datetime_ignores_seconds() -> None:
    assert format_display_datetime("2026-01-01T00:00:59+00:00") == "01.01.2026   00:00"
