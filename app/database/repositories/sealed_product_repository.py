"""SQL access for the ``sealed_products`` table.

Pure data access: no validation — the ``services`` layer decides what a
missing product or an invalid quantity means for the user. Mirrors
``card_repository.py``, minus everything sealed products don't have
(card number, condition, catalogue linkage).
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from app.database.connection import Database
from app.models.enums import Language, PriceQuality
from app.models.sealed_product import SealedProduct, SealedProductDetailsValues, SealedProductFilter
from app.utils.text_normalize import normalize_for_search
from app.utils.time import utc_now_iso


def _row_to_product(row: sqlite3.Row) -> SealedProduct:
    return SealedProduct(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        language=Language.from_code(row["language"]),
        quantity=row["quantity"],
        notes=row["notes"],
        cardmarket_url=row["cardmarket_url"],
        photo_path=row["photo_path"],
        current_price=row["current_price"],
        price_currency=row["price_currency"],
        price_quality=PriceQuality.from_value(row["price_quality"]),
        price_rationale=row["price_rationale"],
        price_updated_at=row["price_updated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SealedProductRepository:
    """CRUD access for sealed products (a global list, not collection-scoped)."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    def _conn(self) -> sqlite3.Connection:
        return self._db.connection

    def get(self, product_id: int) -> SealedProduct | None:
        """Return a single sealed product by id, or ``None`` if it doesn't exist."""
        row = self._conn.execute(
            "SELECT * FROM sealed_products WHERE id = ?", (product_id,)
        ).fetchone()
        return _row_to_product(row) if row is not None else None

    def search(self, product_filter: SealedProductFilter) -> list[SealedProduct]:
        """Return sealed products matching every set criterion in ``product_filter``.

        Unset fields (``None``/empty text) are simply not filtered on.
        """
        clauses: list[str] = []
        params: list[object] = []

        text = product_filter.search_text.strip()
        if text:
            like = f"%{normalize_for_search(text)}%"
            clauses.append(
                "(normalize_text(name) LIKE ? OR normalize_text(category) LIKE ? "
                "OR normalize_text(notes) LIKE ?)"
            )
            params.extend([like, like, like])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM sealed_products {where} ORDER BY id DESC", params
        ).fetchall()
        return [_row_to_product(row) for row in rows]

    def create(self, product: SealedProduct) -> SealedProduct:
        """Insert a new sealed product. ``product.id`` is ignored.

        Returns the persisted product with its assigned ``id`` and timestamps.
        """
        now = utc_now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO sealed_products (
                    name, category, language, quantity, notes,
                    cardmarket_url, photo_path, current_price, price_currency, price_quality,
                    price_rationale, price_updated_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.name,
                    product.category,
                    product.language.code,
                    product.quantity,
                    product.notes,
                    product.cardmarket_url,
                    product.photo_path,
                    product.current_price,
                    product.price_currency,
                    product.price_quality.value,
                    product.price_rationale,
                    product.price_updated_at,
                    now,
                    now,
                ),
            )
        return replace(product, id=cursor.lastrowid, created_at=now, updated_at=now)

    def update_details(self, product_id: int, values: SealedProductDetailsValues) -> None:
        """Update the owned-copy attributes editable after creation."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE sealed_products
                SET language = ?, quantity = ?, notes = ?, cardmarket_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values.language.code,
                    values.quantity,
                    values.notes,
                    values.cardmarket_url or None,
                    utc_now_iso(),
                    product_id,
                ),
            )

    def update_price(
        self,
        product_id: int,
        price: float | None,
        currency: str,
        quality: PriceQuality,
        rationale: str,
        updated_at: str,
    ) -> None:
        """Persist the latest price determination for a sealed product."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE sealed_products
                SET current_price = ?, price_currency = ?, price_quality = ?,
                    price_rationale = ?, price_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (price, currency, quality.value, rationale, updated_at, utc_now_iso(), product_id),
            )

    def update_photo_path(self, product_id: int, photo_path: str) -> None:
        """Backfill a sealed product's photo path once its screenshot capture

        (which needs the product's real, post-insert id for its filename)
        has finished moving the temp file into place."""
        with self._conn:
            self._conn.execute(
                "UPDATE sealed_products SET photo_path = ?, updated_at = ? WHERE id = ?",
                (photo_path, utc_now_iso(), product_id),
            )

    def delete(self, product_id: int) -> None:
        """Delete a sealed product."""
        with self._conn:
            self._conn.execute("DELETE FROM sealed_products WHERE id = ?", (product_id,))
