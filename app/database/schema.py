"""Database schema definitions expressed as ordered migrations.

Each migration is a ``(version, description, statements)`` triple. New schema
changes are appended as additional migrations with a higher version number and
are *never* edited retroactively, which keeps every machine reproducibly in
sync from an empty database.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Migration:
    """A single, ordered schema change."""

    version: int
    description: str
    statements: tuple[str, ...]


# --- Version 1: initial schema -------------------------------------------- #

_V1_COLLECTIONS = """
CREATE TABLE IF NOT EXISTS collections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""

_V1_CARDS = """
CREATE TABLE IF NOT EXISTS cards (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id     INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    name              TEXT    NOT NULL,
    set_name          TEXT    NOT NULL DEFAULT '',
    set_code          TEXT    NOT NULL DEFAULT '',
    card_number       TEXT    NOT NULL DEFAULT '',
    variant           TEXT    NOT NULL DEFAULT 'Normal',
    language          TEXT    NOT NULL DEFAULT 'EN',
    condition         TEXT    NOT NULL DEFAULT 'NM',
    quantity          INTEGER NOT NULL DEFAULT 1,
    notes             TEXT    NOT NULL DEFAULT '',
    photo_path        TEXT,
    external_card_id  TEXT,
    cardmarket_url    TEXT,
    current_price     REAL,
    price_currency    TEXT    NOT NULL DEFAULT 'EUR',
    price_quality     TEXT    NOT NULL DEFAULT 'no_price',
    price_rationale   TEXT,
    price_updated_at  TEXT,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL
);
"""

_V1_PRICE_HISTORY = """
CREATE TABLE IF NOT EXISTS price_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id       INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    price         REAL    NOT NULL,
    currency      TEXT    NOT NULL DEFAULT 'EUR',
    price_quality TEXT    NOT NULL DEFAULT 'no_price',
    rationale     TEXT    NOT NULL DEFAULT '',
    source        TEXT    NOT NULL DEFAULT '',
    recorded_at   TEXT    NOT NULL
);
"""

_V1_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_V1_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_cards_collection ON cards(collection_id);",
    "CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);",
    "CREATE INDEX IF NOT EXISTS idx_cards_set ON cards(set_code);",
    "CREATE INDEX IF NOT EXISTS idx_price_history_card ON price_history(card_id);",
)


#: The ordered list of all migrations. Append-only.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="Initial schema: collections, cards, price_history, settings.",
        statements=(
            _V1_COLLECTIONS,
            _V1_CARDS,
            _V1_PRICE_HISTORY,
            _V1_SETTINGS,
            *_V1_INDEXES,
        ),
    ),
)
