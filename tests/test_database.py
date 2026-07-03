"""Tests for schema creation, migrations and connection behaviour."""

from __future__ import annotations

from pathlib import Path

from app.database.connection import Database

_EXPECTED_TABLES = {"collections", "cards", "price_history", "settings", "schema_migrations"}


def _table_names(db: Database) -> set[str]:
    rows = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_initialize_creates_database_file(tmp_path: Path) -> None:
    db_path = tmp_path / "created.db"
    assert not db_path.exists()

    db = Database(db_path)
    db.initialize()
    try:
        assert db_path.exists()
    finally:
        db.close()


def test_initialize_creates_all_tables(temp_db: Database) -> None:
    assert _EXPECTED_TABLES.issubset(_table_names(temp_db))


def test_schema_version_is_recorded(temp_db: Database) -> None:
    version = temp_db.connection.execute(
        "SELECT MAX(version) AS v FROM schema_migrations"
    ).fetchone()["v"]
    assert version == 3


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "idem.db"

    first = Database(db_path)
    applied_first = first.initialize()
    first.close()

    second = Database(db_path)
    applied_second = second.initialize()
    try:
        assert applied_first == 3
        assert applied_second == 0  # nothing pending on a second run
    finally:
        second.close()


def test_foreign_keys_enforced(temp_db: Database) -> None:
    result = temp_db.connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert result == 1
