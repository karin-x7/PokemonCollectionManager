"""SQL access for the ``price_history`` table.

Pure data access: the ``services`` layer decides what price/quality to
record and when.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from app.database.connection import Database
from app.models.enums import PriceQuality
from app.models.price import PriceRecord
from app.utils.time import utc_now_iso


def _row_to_record(row: sqlite3.Row) -> PriceRecord:
    return PriceRecord(
        id=row["id"],
        card_id=row["card_id"],
        price=row["price"],
        currency=row["currency"],
        price_quality=PriceQuality.from_value(row["price_quality"]),
        rationale=row["rationale"],
        source=row["source"],
        recorded_at=row["recorded_at"],
    )


class PriceRepository:
    """Access to a card's price history: append new records, or clear them all."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def add_record(self, record: PriceRecord) -> PriceRecord:
        """Insert a new price history entry. ``record.id`` is ignored."""
        recorded_at = record.recorded_at or utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO price_history (
                    card_id, price, currency, price_quality, rationale,
                    source, recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.card_id,
                    record.price,
                    record.currency,
                    record.price_quality.value,
                    record.rationale,
                    record.source,
                    recorded_at,
                ),
            )
        return replace(record, id=cursor.lastrowid, recorded_at=recorded_at)

    def list_for_card(self, card_id: int) -> list[PriceRecord]:
        """Return a card's price history, oldest first."""
        rows = self._conn.execute(
            "SELECT * FROM price_history WHERE card_id = ? ORDER BY id ASC",
            (card_id,),
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def list_all(self) -> list[PriceRecord]:
        """Every card's price history, across the whole collection, oldest first.

        Used to build the combined "collection value over time" chart (see
        ``app.services.statistics_service.value_over_time``) -- fetching
        everything in one query instead of one ``list_for_card`` call per
        card.
        """
        rows = self._conn.execute(
            "SELECT * FROM price_history ORDER BY recorded_at ASC, id ASC"
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def delete_for_card(self, card_id: int) -> None:
        """Delete every price history entry for a card. Irreversible."""
        with self._conn:
            self._conn.execute("DELETE FROM price_history WHERE card_id = ?", (card_id,))
