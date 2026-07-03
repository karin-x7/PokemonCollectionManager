"""SQL access for the ``cards`` table.

Pure data access: no validation — the ``services`` layer decides what a
missing card or an invalid quantity means for the user.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from app.database.connection import Database
from app.models.card import Card
from app.models.enums import Condition, Language, PriceQuality, Variant
from app.utils.time import utc_now_iso


def _row_to_card(row: sqlite3.Row) -> Card:
    return Card(
        id=row["id"],
        collection_id=row["collection_id"],
        name=row["name"],
        set_name=row["set_name"],
        set_code=row["set_code"],
        card_number=row["card_number"],
        variant=Variant.from_value(row["variant"]),
        language=Language.from_code(row["language"]),
        condition=Condition.from_code(row["condition"]),
        quantity=row["quantity"],
        notes=row["notes"],
        photo_path=row["photo_path"],
        external_card_id=row["external_card_id"],
        cardmarket_url=row["cardmarket_url"],
        current_price=row["current_price"],
        price_currency=row["price_currency"],
        price_quality=PriceQuality.from_value(row["price_quality"]),
        price_rationale=row["price_rationale"],
        price_updated_at=row["price_updated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CardRepository:
    """CRUD access for cards belonging to a collection."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def list_by_collection(self, collection_id: int) -> list[Card]:
        """Return all cards in a collection, most recently added first."""
        rows = self._conn.execute(
            "SELECT * FROM cards WHERE collection_id = ? ORDER BY id DESC",
            (collection_id,),
        ).fetchall()
        return [_row_to_card(row) for row in rows]

    def get(self, card_id: int) -> Card | None:
        """Return a single card by id, or ``None`` if it doesn't exist."""
        row = self._conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        return _row_to_card(row) if row is not None else None

    def create(self, card: Card) -> Card:
        """Insert a new card. ``card.id`` is ignored.

        Returns the persisted card with its assigned ``id`` and timestamps.
        """
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO cards (
                    collection_id, name, set_name, set_code, card_number,
                    variant, language, condition, quantity, notes,
                    photo_path, external_card_id, cardmarket_url,
                    current_price, price_currency, price_quality,
                    price_rationale, price_updated_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.collection_id,
                    card.name,
                    card.set_name,
                    card.set_code,
                    card.card_number,
                    card.variant.value,
                    card.language.code,
                    card.condition.code,
                    card.quantity,
                    card.notes,
                    card.photo_path,
                    card.external_card_id,
                    card.cardmarket_url,
                    card.current_price,
                    card.price_currency,
                    card.price_quality.value,
                    card.price_rationale,
                    card.price_updated_at,
                    now,
                    now,
                ),
            )
        return replace(card, id=cursor.lastrowid, created_at=now, updated_at=now)

    def update_details(
        self,
        card_id: int,
        variant: Variant,
        language: Language,
        condition: Condition,
        quantity: int,
        notes: str,
    ) -> None:
        """Update the owned-copy attributes editable after creation."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE cards
                SET variant = ?, language = ?, condition = ?, quantity = ?,
                    notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    variant.value,
                    language.code,
                    condition.code,
                    quantity,
                    notes,
                    utc_now_iso(),
                    card_id,
                ),
            )

    def update_price(
        self,
        card_id: int,
        price: float | None,
        currency: str,
        quality: PriceQuality,
        rationale: str,
        updated_at: str,
    ) -> None:
        """Persist the latest price determination for a card."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE cards
                SET current_price = ?, price_currency = ?, price_quality = ?,
                    price_rationale = ?, price_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (price, currency, quality.value, rationale, updated_at, utc_now_iso(), card_id),
            )

    def update_cardmarket_url(self, card_id: int, cardmarket_url: str) -> None:
        """Backfill a card's Cardmarket URL (self-healing for cards added
        before that field existed)."""
        with self._conn:
            self._conn.execute(
                "UPDATE cards SET cardmarket_url = ?, updated_at = ? WHERE id = ?",
                (cardmarket_url, utc_now_iso(), card_id),
            )

    def delete(self, card_id: int) -> None:
        """Delete a card."""
        with self._conn:
            self._conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
