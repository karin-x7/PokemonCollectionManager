"""Tests for name_translation.translate_to_english.

Uses a small, fake translation table (monkeypatched) instead of the real,
~1025-entry bundled JSON -- deterministic, no dependency on that file's
exact contents, no network.
"""

from __future__ import annotations

from app.catalog import name_translation


def _fake_table() -> dict[str, str]:
    return {
        "turtok": "Blastoise",
        "hooh": "Ho-Oh",
    }


def test_translates_a_known_foreign_name(monkeypatch) -> None:
    monkeypatch.setattr(name_translation, "_translations", _fake_table)

    assert name_translation.translate_to_english("Turtok") == "Blastoise"


def test_translation_lookup_is_normalised(monkeypatch) -> None:
    monkeypatch.setattr(name_translation, "_translations", _fake_table)

    assert name_translation.translate_to_english("TURTOK") == "Blastoise"
    assert name_translation.translate_to_english("  turtok  ".strip()) == "Blastoise"


def test_hyphenated_name_matches_unhyphenated_query(monkeypatch) -> None:
    monkeypatch.setattr(name_translation, "_translations", _fake_table)

    assert name_translation.translate_to_english("hooh") == "Ho-Oh"
    assert name_translation.translate_to_english("ho oh") == "Ho-Oh"


def test_unknown_name_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(name_translation, "_translations", _fake_table)

    assert name_translation.translate_to_english("Blastoise") is None
    assert name_translation.translate_to_english("Nonexistentmon") is None


def test_missing_translations_file_yields_empty_table(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(name_translation, "_TRANSLATIONS_PATH", tmp_path / "missing.json")
    name_translation._translations.cache_clear()

    try:
        assert name_translation.translate_to_english("turtok") is None
    finally:
        name_translation._translations.cache_clear()
