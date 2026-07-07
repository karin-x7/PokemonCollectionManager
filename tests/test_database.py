"""Tests for schema creation, migrations and connection behaviour."""

from __future__ import annotations

from pathlib import Path

from app.database.connection import Database

_EXPECTED_TABLES = {
    "collections",
    "cards",
    "price_history",
    "settings",
    "sealed_products",
    "sealed_price_history",
    "wantlist_items",
    "schema_migrations",
}


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
    assert version == 9


def test_migration_8_backfills_ex_series_set_names(tmp_path: Path) -> None:
    # Migration 8 corrects pre-existing cards' set_name for the EX Series,
    # whose pokemontcg.io set names drop the leading "EX " era prefix (see
    # the migration's own description and app.catalog.pokemontcg_client's
    # _EX_SERIES_SET_NAMES) -- applied here by running migrations 1-7,
    # inserting a "dirty" pre-fix row, then applying migration 8 alone, to
    # verify the hand-written UPDATE statements actually rewrite existing
    # data rather than just relying on the forward-looking client-side fix.
    import sqlite3

    from app.database.migrations import _TRACKING_TABLE, _apply
    from app.database.schema import MIGRATIONS

    db_path = tmp_path / "backfill.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_TRACKING_TABLE)
        for migration in MIGRATIONS[:7]:
            _apply(conn, migration)

        conn.execute(
            "INSERT INTO collections (name, created_at, updated_at) "
            "VALUES ('Binder', '2026-01-01', '2026-01-01')"
        )
        collection_id = conn.execute("SELECT id FROM collections").fetchone()["id"]
        conn.execute(
            "INSERT INTO cards "
            "(collection_id, name, set_name, set_code, created_at, updated_at) "
            "VALUES (?, 'Cacturne', 'Sandstorm', 'ex2', '2026-01-01', '2026-01-01')",
            (collection_id,),
        )
        conn.commit()

        _apply(conn, MIGRATIONS[7])

        set_name = conn.execute("SELECT set_name FROM cards").fetchone()["set_name"]
        assert set_name == "EX Sandstorm"
    finally:
        conn.close()


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "idem.db"

    first = Database(db_path)
    applied_first = first.initialize()
    first.close()

    second = Database(db_path)
    applied_second = second.initialize()
    try:
        assert applied_first == 9
        assert applied_second == 0  # nothing pending on a second run
    finally:
        second.close()


def test_foreign_keys_enforced(temp_db: Database) -> None:
    result = temp_db.connection.execute("PRAGMA foreign_keys").fetchone()[0]
    assert result == 1


def test_sealed_products_has_no_collection_id_column(temp_db: Database) -> None:
    columns = {
        row["name"]
        for row in temp_db.connection.execute("PRAGMA table_info(sealed_products)").fetchall()
    }
    assert "collection_id" not in columns
    assert "name" in columns


def test_sealed_products_has_photo_path_column(temp_db: Database) -> None:
    columns = {
        row["name"]
        for row in temp_db.connection.execute("PRAGMA table_info(sealed_products)").fetchall()
    }
    assert "photo_path" in columns


def test_sealed_price_history_has_expected_columns(temp_db: Database) -> None:
    columns = {
        row["name"]
        for row in temp_db.connection.execute(
            "PRAGMA table_info(sealed_price_history)"
        ).fetchall()
    }
    assert columns == {
        "id",
        "sealed_product_id",
        "price",
        "currency",
        "price_quality",
        "rationale",
        "source",
        "recorded_at",
    }
