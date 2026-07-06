"""SQL access for the generic ``settings`` key/value table.

Pure data access: no validation of keys/values -- callers (e.g. the UI
language preference) decide what a given key means.
"""

from __future__ import annotations

import sqlite3

from app.database.connection import Database
from app.utils.time import utc_now_iso


class SettingsRepository:
    """Get/set access to persisted app-wide settings."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return the stored value for ``key``, or ``default`` if unset."""
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row is not None else default

    def set(self, key: str, value: str) -> None:
        """Insert or update the value stored for ``key``."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, utc_now_iso()),
            )
