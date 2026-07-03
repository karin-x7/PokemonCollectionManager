"""SQL access for the ``collections`` table.

Pure data access: no name validation, no duplicate handling beyond surfacing
the raw :class:`sqlite3.IntegrityError` — the ``services`` layer decides what
those errors mean for the user.
"""

from __future__ import annotations

import sqlite3

from app.database.connection import Database
from app.models.collection import Collection
from app.utils.time import utc_now_iso


def _row_to_collection(row: sqlite3.Row) -> Collection:
    return Collection(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        position=row["position"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CollectionRepository:
    """CRUD access for collections, ordered by their sidebar position."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def list_all(self) -> list[Collection]:
        """Return all collections ordered by position, then id."""
        rows = self._conn.execute(
            "SELECT * FROM collections ORDER BY position ASC, id ASC"
        ).fetchall()
        return [_row_to_collection(row) for row in rows]

    def get(self, collection_id: int) -> Collection | None:
        """Return a single collection by id, or ``None`` if it doesn't exist."""
        row = self._conn.execute(
            "SELECT * FROM collections WHERE id = ?", (collection_id,)
        ).fetchone()
        return _row_to_collection(row) if row is not None else None

    def _next_position(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next FROM collections"
        ).fetchone()
        return int(row["next"])

    def create(self, name: str, description: str = "") -> Collection:
        """Insert a new collection at the end of the sidebar order.

        Raises:
            sqlite3.IntegrityError: If ``name`` already exists (UNIQUE
                constraint) — translated to a friendly error by the service.
        """
        now = utc_now_iso()
        position = self._next_position()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO collections (name, description, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, description, position, now, now),
            )
        return Collection(
            id=cursor.lastrowid,
            name=name,
            description=description,
            position=position,
            created_at=now,
            updated_at=now,
        )

    def rename(self, collection_id: int, new_name: str) -> None:
        """Rename a collection.

        Raises:
            sqlite3.IntegrityError: If ``new_name`` already exists.
        """
        with self._conn:
            self._conn.execute(
                "UPDATE collections SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, utc_now_iso(), collection_id),
            )

    def delete(self, collection_id: int) -> None:
        """Delete a collection. Cascades to its cards via the foreign key."""
        with self._conn:
            self._conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    def reorder(self, ordered_ids: list[int]) -> None:
        """Persist a new sidebar order given as a list of collection ids."""
        with self._conn:
            self._conn.executemany(
                "UPDATE collections SET position = ?, updated_at = ? WHERE id = ?",
                [(index, utc_now_iso(), cid) for index, cid in enumerate(ordered_ids)],
            )
