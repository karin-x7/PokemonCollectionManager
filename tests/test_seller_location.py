"""Tests for the global seller-location preference (Germany-only toggle)."""

from __future__ import annotations

from app.database.connection import Database
from app.database.repositories.settings_repository import SettingsRepository
from app.pricing.cardmarket_parsing import SELLER_COUNTRY_GERMANY_ID
from app.pricing.seller_location import (
    is_germany_only_enabled,
    resolve_seller_country_id,
    set_germany_only_enabled,
)


def test_is_germany_only_enabled_defaults_to_false(temp_db: Database) -> None:
    settings = SettingsRepository(temp_db)
    assert is_germany_only_enabled(settings) is False


def test_set_germany_only_enabled_persists_true(temp_db: Database) -> None:
    settings = SettingsRepository(temp_db)
    set_germany_only_enabled(settings, True)
    assert is_germany_only_enabled(settings) is True


def test_set_germany_only_enabled_can_be_turned_back_off(temp_db: Database) -> None:
    settings = SettingsRepository(temp_db)
    set_germany_only_enabled(settings, True)
    set_germany_only_enabled(settings, False)
    assert is_germany_only_enabled(settings) is False


def test_resolve_seller_country_id_is_none_when_disabled(temp_db: Database) -> None:
    settings = SettingsRepository(temp_db)
    assert resolve_seller_country_id(settings) is None


def test_resolve_seller_country_id_is_germany_when_enabled(temp_db: Database) -> None:
    settings = SettingsRepository(temp_db)
    set_germany_only_enabled(settings, True)
    assert resolve_seller_country_id(settings) == SELLER_COUNTRY_GERMANY_ID


def test_resolve_seller_country_id_is_none_without_a_settings_repository() -> None:
    assert resolve_seller_country_id(None) is None
