"""SQL access for the ``sealed_price_history`` table.

Mirrors ``price_repository.py``, ``card_id`` swapped for
``sealed_product_id``. Pure data access: the ``services`` layer decides what
price/quality to record and when.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from app.database.connection import Database
from app.models.enums import PriceQuality
from app.models.sealed_price import SealedPriceRecord
from app.utils.time import utc_now_iso


def _row_to_record(row: sqlite3.Row) -> SealedPriceRecord:
    return SealedPriceRecord(
        id=row["id"],
        sealed_product_id=row["sealed_product_id"],
        price=row["price"],
        currency=row["currency"],
        price_quality=PriceQuality.from_value(row["price_quality"]),
        rationale=row["rationale"],
        source=row["source"],
        recorded_at=row["recorded_at"],
    )


class SealedPriceRepository:
    """Access to a sealed product's price history: append, or clear it all."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def add_record(self, record: SealedPriceRecord) -> SealedPriceRecord:
        """Insert a new price history entry. ``record.id`` is ignored."""
        recorded_at = record.recorded_at or utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO sealed_price_history (
                    sealed_product_id, price, currency, price_quality,
                    rationale, source, recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.sealed_product_id,
                    record.price,
                    record.currency,
                    record.price_quality.value,
                    record.rationale,
                    record.source,
                    recorded_at,
                ),
            )
        return replace(record, id=cursor.lastrowid, recorded_at=recorded_at)

    def list_for_product(self, sealed_product_id: int) -> list[SealedPriceRecord]:
        """Return a sealed product's price history, oldest first."""
        rows = self._conn.execute(
            "SELECT * FROM sealed_price_history WHERE sealed_product_id = ? ORDER BY id ASC",
            (sealed_product_id,),
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def delete_for_product(self, sealed_product_id: int) -> None:
        """Delete every price history entry for a sealed product. Irreversible."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM sealed_price_history WHERE sealed_product_id = ?",
                (sealed_product_id,),
            )
