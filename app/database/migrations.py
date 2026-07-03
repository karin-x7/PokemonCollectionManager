"""Forward-only migration runner.

Applied versions are tracked in the ``schema_migrations`` table. On startup
the runner applies every migration whose version is greater than the current
maximum, each inside its own transaction, so an interrupted upgrade never
leaves the database half-migrated.
"""

from __future__ import annotations

import sqlite3

from app.database.schema import MIGRATIONS, Migration
from app.logging_config import get_logger
from app.utils.time import utc_now_iso

logger = get_logger(__name__)

_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at  TEXT NOT NULL
);
"""


def _current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version (0 if none)."""
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
    return int(row["v"]) if row is not None else 0


def _apply(conn: sqlite3.Connection, migration: Migration) -> None:
    """Apply a single migration atomically and record it."""
    logger.info("Applying migration %d: %s", migration.version, migration.description)
    with conn:  # commits on success, rolls back on exception
        for statement in migration.statements:
            conn.executescript(statement)
        conn.execute(
            "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
            (migration.version, migration.description, utc_now_iso()),
        )


def run_migrations(conn: sqlite3.Connection) -> int:
    """Bring the database schema up to the latest version.

    Args:
        conn: An open SQLite connection.

    Returns:
        The number of migrations applied during this call.
    """
    conn.executescript(_TRACKING_TABLE)
    current = _current_version(conn)
    pending = [m for m in MIGRATIONS if m.version > current]

    if not pending:
        logger.debug("Schema up to date at version %d.", current)
        return 0

    for migration in sorted(pending, key=lambda m: m.version):
        _apply(conn, migration)

    logger.info("Applied %d migration(s); schema now at version %d.",
                len(pending), _current_version(conn))
    return len(pending)
