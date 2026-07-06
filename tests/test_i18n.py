"""Tests for the English-only UI translation layer."""

from __future__ import annotations

from app import i18n


def test_translates_known_strings() -> None:
    i18n._EN["Karten"] = "Cards"

    assert i18n.tr("Karten") == "Cards"


def test_falls_back_to_the_german_source_string_when_untranslated() -> None:
    assert i18n.tr("Ein ganz neuer, unübersetzter Text") == "Ein ganz neuer, unübersetzter Text"
