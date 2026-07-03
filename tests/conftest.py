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
