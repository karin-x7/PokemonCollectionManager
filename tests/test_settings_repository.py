"""Tests for SettingsRepository: get/set access to the generic settings table."""

from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.settings_repository import SettingsRepository


def test_get_returns_default_when_unset(temp_db: Database) -> None:
    repo = SettingsRepository(temp_db)

    assert repo.get("ui_language") is None
    assert repo.get("ui_language", "de") == "de"


def test_set_then_get_round_trips(temp_db: Database) -> None:
    repo = SettingsRepository(temp_db)

    repo.set("ui_language", "en")

    assert repo.get("ui_language") == "en"


def test_set_overwrites_an_existing_value(temp_db: Database) -> None:
    repo = SettingsRepository(temp_db)
    repo.set("ui_language", "en")

    repo.set("ui_language", "de")

    assert repo.get("ui_language") == "de"
