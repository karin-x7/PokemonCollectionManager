"""SQLite connection management.

Wraps a single :class:`sqlite3.Connection` with sensible pragmas (foreign
keys on, WAL journalling) and takes care of creating the database file and
running migrations. The class is a context manager so callers can guarantee
the connection is closed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType

from app import config
from app.database.migrations import run_migrations
from app.logging_config import get_logger

logger = get_logger(__name__)


class Database:
    """Owns the SQLite connection for the application.

    Example:
        >>> with Database() as db:
        ...     db.initialize()
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._path = Path(db_path) if db_path is not None else Path(config.DB_PATH)
        self._conn: sqlite3.Connection | None = None

    @property
    def path(self) -> Path:
        """Filesystem path of the database file."""
        return self._path

    @property
    def connection(self) -> sqlite3.Connection:
        """The live connection, opening it on first access."""
        if self._conn is None:
            self.connect()
        assert self._conn is not None  # for type checkers
        return self._conn

    def connect(self) -> sqlite3.Connection:
        """Open the connection, creating the parent directory if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        self._conn = conn
        logger.info("Connected to database at %s", self._path)
        return conn

    def initialize(self) -> int:
        """Ensure the connection is open and the schema is migrated.

        Returns:
            The number of migrations applied.
        """
        applied = run_migrations(self.connection)
        logger.info("Database initialised (%d migration(s) applied).", applied)
        return applied

    def close(self) -> None:
        """Close the connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("Database connection closed.")

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
