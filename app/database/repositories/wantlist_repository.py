"""SQL access for the ``wantlist_items`` table.

Pure data access: no validation -- the ``services`` layer decides what a
missing item means for the user. Mirrors ``sealed_product_repository.py``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from app.database.connection import Database
from app.models.enums import Condition, Language, PriceQuality
from app.models.wantlist import WantlistItem, WantlistItemDetailsValues
from app.utils.time import utc_now_iso


def _row_to_item(row: sqlite3.Row) -> WantlistItem:
    return WantlistItem(
        id=row["id"],
        name=row["name"],
        set_name=row["set_name"],
        card_number=row["card_number"],
        language=Language.from_code(row["language"]),
        condition=Condition.from_code(row["condition"]),
        target_price=row["target_price"],
        notes=row["notes"],
        cardmarket_url=row["cardmarket_url"],
        current_price=row["current_price"],
        price_currency=row["price_currency"],
        price_quality=PriceQuality.from_value(row["price_quality"]),
        price_rationale=row["price_rationale"],
        price_updated_at=row["price_updated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class WantlistRepository:
    """CRUD access for wantlist items (a global list, not collection-scoped)."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def get(self, item_id: int) -> WantlistItem | None:
        """Return a single wantlist item by id, or ``None`` if it doesn't exist."""
        row = self._conn.execute(
            "SELECT * FROM wantlist_items WHERE id = ?", (item_id,)
        ).fetchone()
        return _row_to_item(row) if row is not None else None

    def list_all(self) -> list[WantlistItem]:
        """Return every wantlist item, most recently added first."""
        rows = self._conn.execute("SELECT * FROM wantlist_items ORDER BY id DESC").fetchall()
        return [_row_to_item(row) for row in rows]

    def create(self, item: WantlistItem) -> WantlistItem:
        """Insert a new wantlist item. ``item.id`` is ignored.

        Returns the persisted item with its assigned ``id`` and timestamps.
        """
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO wantlist_items (
                    name, set_name, card_number, language, condition, target_price,
                    notes, cardmarket_url, current_price, price_currency, price_quality,
                    price_rationale, price_updated_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.name,
                    item.set_name,
                    item.card_number,
                    item.language.code,
                    item.condition.code,
                    item.target_price,
                    item.notes,
                    item.cardmarket_url,
                    item.current_price,
                    item.price_currency,
                    item.price_quality.value,
                    item.price_rationale,
                    item.price_updated_at,
                    now,
                    now,
                ),
            )
        return replace(item, id=cursor.lastrowid, created_at=now, updated_at=now)

    def update_details(self, item_id: int, values: WantlistItemDetailsValues) -> None:
        """Update the user-editable attributes (target price/language/condition/

        notes/Cardmarket link)."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE wantlist_items
                SET language = ?, condition = ?, target_price = ?, notes = ?,
                    cardmarket_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values.language.code,
                    values.condition.code,
                    values.target_price,
                    values.notes,
                    values.cardmarket_url or None,
                    utc_now_iso(),
                    item_id,
                ),
            )

    def update_price(
        self,
        item_id: int,
        price: float | None,
        currency: str,
        quality: PriceQuality,
        rationale: str,
        updated_at: str,
    ) -> None:
        """Persist the latest price determination for a wantlist item."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE wantlist_items
                SET current_price = ?, price_currency = ?, price_quality = ?,
                    price_rationale = ?, price_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (price, currency, quality.value, rationale, updated_at, utc_now_iso(), item_id),
            )

    def delete(self, item_id: int) -> None:
        """Delete a wantlist item."""
        with self._conn:
            self._conn.execute("DELETE FROM wantlist_items WHERE id = ?", (item_id,))
