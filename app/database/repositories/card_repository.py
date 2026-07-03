"""SQL access for the ``cards`` table.

Pure data access: no validation — the ``services`` layer decides what a
missing card or an invalid quantity means for the user.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from app.database.connection import Database
from app.models.card import Card, CardDetailsValues, CardFilter
from app.models.enums import Condition, Language, PriceQuality
from app.utils.time import utc_now_iso


def _row_to_card(row: sqlite3.Row) -> Card:
    return Card(
        id=row["id"],
        collection_id=row["collection_id"],
        name=row["name"],
        set_name=row["set_name"],
        set_code=row["set_code"],
        card_number=row["card_number"],
        language=Language.from_code(row["language"]),
        condition=Condition.from_code(row["condition"]),
        is_reverse_holo=bool(row["is_reverse_holo"]),
        is_signed=bool(row["is_signed"]),
        is_first_edition=bool(row["is_first_edition"]),
        is_altered=bool(row["is_altered"]),
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

    def search(self, card_filter: CardFilter) -> list[Card]:
        """Return cards matching every set criterion in ``card_filter``.

        Unset fields (``None``/empty text) are simply not filtered on.
        ``collection_id=None`` searches across every collection.
        """
        clauses: list[str] = []
        params: list[object] = []

        if card_filter.collection_id is not None:
            clauses.append("collection_id = ?")
            params.append(card_filter.collection_id)
        text = card_filter.search_text.strip()
        if text:
            clauses.append("(name LIKE ? OR set_name LIKE ? OR card_number LIKE ? OR notes LIKE ?)")
            like = f"%{text}%"
            params.extend([like, like, like, like])
        if card_filter.set_name:
            clauses.append("set_name = ?")
            params.append(card_filter.set_name)
        if card_filter.language is not None:
            clauses.append("language = ?")
            params.append(card_filter.language.code)
        if card_filter.condition is not None:
            clauses.append("condition = ?")
            params.append(card_filter.condition.code)
        if card_filter.min_price is not None:
            clauses.append("current_price >= ?")
            params.append(card_filter.min_price)
        if card_filter.max_price is not None:
            clauses.append("current_price <= ?")
            params.append(card_filter.max_price)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM cards {where} ORDER BY id DESC", params
        ).fetchall()
        return [_row_to_card(row) for row in rows]

    def distinct_set_names(self, collection_id: int | None) -> list[str]:
        """Return the distinct, non-empty set names in scope, alphabetically.

        ``collection_id=None`` looks across every collection — used to
        populate the Set filter dropdown for whichever scope is active.
        """
        if collection_id is not None:
            rows = self._conn.execute(
                "SELECT DISTINCT set_name FROM cards WHERE collection_id = ? "
                "AND set_name != '' ORDER BY set_name COLLATE NOCASE",
                (collection_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT DISTINCT set_name FROM cards WHERE set_name != '' "
                "ORDER BY set_name COLLATE NOCASE"
            ).fetchall()
        return [row["set_name"] for row in rows]

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
                    language, condition,
                    is_reverse_holo, is_signed, is_first_edition, is_altered,
                    quantity, notes,
                    photo_path, external_card_id, cardmarket_url,
                    current_price, price_currency, price_quality,
                    price_rationale, price_updated_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.collection_id,
                    card.name,
                    card.set_name,
                    card.set_code,
                    card.card_number,
                    card.language.code,
                    card.condition.code,
                    int(card.is_reverse_holo),
                    int(card.is_signed),
                    int(card.is_first_edition),
                    int(card.is_altered),
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

    def update_details(self, card_id: int, values: CardDetailsValues) -> None:
        """Update the owned-copy attributes editable after creation."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE cards
                SET language = ?, condition = ?,
                    is_reverse_holo = ?, is_signed = ?, is_first_edition = ?,
                    is_altered = ?, quantity = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values.language.code,
                    values.condition.code,
                    int(values.is_reverse_holo),
                    int(values.is_signed),
                    int(values.is_first_edition),
                    int(values.is_altered),
                    values.quantity,
                    values.notes,
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
