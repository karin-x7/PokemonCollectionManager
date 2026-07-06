"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.database.connection import Database


@pytest.fixture
def temp_db(tmp_path: Path) -> Iterator[Database]:
    """An initialised database backed by a throwaway file per test."""
    db = Database(tmp_path / "test.db")
    db.initialize()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _no_real_database_backups(tmp_path: Path, monkeypatch) -> None:
    """Redirects Database.initialize()'s automatic backup to a throwaway

    directory for every test. Mirrors ``_no_real_set_icon_downloads``
    below: ``backup_database`` defaults to the real ``config.BACKUPS_DIR``,
    which would otherwise fill the real app data directory with test
    artifacts (e.g. ``test_migrations_are_idempotent``'s own throwaway
    database, live-confirmed to leak a real backup file this way) every
    time the test suite runs.
    """
    from app import config

    monkeypatch.setattr(config, "BACKUPS_DIR", tmp_path / "test_backups")


@pytest.fixture(autouse=True)
def _no_real_set_icon_downloads(monkeypatch) -> None:
    """Prevents any test from hitting the real network/disk for set icons.

    ``app.ui.set_icon_provider.get_set_icon`` downloads-and-caches lazily the
    first time a given set is rendered -- real UI widget tests construct
    real ``Card``/``CatalogCard`` objects with a real ``set_code`` and render
    them through the actual widgets, which would otherwise trigger a genuine
    network call (slow, flaky, and -- since it defaults to the real app data
    directory -- pollutes it) on every test run.
    """
    import app.ui.set_icon_provider as set_icon_provider

    monkeypatch.setattr(set_icon_provider, "ensure_set_icon", lambda *_a, **_kw: None)
    set_icon_provider._icons.clear()
