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


# --- Version 2: card "extras" (Reverse Holo / Signed / 1st Edition /
# Altered) as independent yes/no flags instead of folded into `variant` ---- #

_V2_ADD_COLUMNS = (
    "ALTER TABLE cards ADD COLUMN is_reverse_holo INTEGER NOT NULL DEFAULT 0;",
    "ALTER TABLE cards ADD COLUMN is_signed INTEGER NOT NULL DEFAULT 0;",
    "ALTER TABLE cards ADD COLUMN is_first_edition INTEGER NOT NULL DEFAULT 0;",
    "ALTER TABLE cards ADD COLUMN is_altered INTEGER NOT NULL DEFAULT 0;",
)

# Carry forward what the old, combined `variant` values meant so existing
# rows keep their meaning under the new model instead of silently losing it.
_V2_MIGRATE_EXISTING_DATA = (
    "UPDATE cards SET is_reverse_holo = 1, variant = 'Holo' WHERE variant = 'Reverse Holo';",
    "UPDATE cards SET is_first_edition = 1, variant = 'Normal' WHERE variant = '1st Edition';",
    "UPDATE cards SET is_first_edition = 1, variant = 'Holo' WHERE variant = '1st Edition Holo';",
    "UPDATE cards SET variant = 'Normal' WHERE variant = 'Unlimited';",
)


# --- Version 5: sealed products (booster boxes, ETBs, displays, ...) ------ #
# A separate table, not a variant of `cards`: sealed products have no card
# number and no condition ladder (Cardmarket only ever sells them sealed --
# "Opened products cannot be sold", confirmed live on a real product page),
# so they'd otherwise be mostly-empty columns on every row. `category` is
# free text (e.g. "Booster Box", "Elite Trainer Box"), parsed off Cardmarket's
# own breadcrumb where possible, not a fixed enum -- there are too many
# product types to enumerate up front. `cardmarket_url` is always the
# user-pasted link (there is no pokemontcg.io-style catalogue for sealed
# product, so "manuell eintragen" is the only way to add one).

_V5_SEALED_PRODUCTS = """
CREATE TABLE IF NOT EXISTS sealed_products (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id     INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    name              TEXT    NOT NULL,
    category          TEXT    NOT NULL DEFAULT '',
    language          TEXT    NOT NULL DEFAULT 'EN',
    quantity          INTEGER NOT NULL DEFAULT 1,
    notes             TEXT    NOT NULL DEFAULT '',
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

_V5_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_sealed_products_collection "
    "ON sealed_products(collection_id);",
)


# --- Version 6: sealed products no longer belong to a collection ---------- #

_V6_DROP_SEALED_COLLECTION_ID = """
CREATE TABLE sealed_products_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    category          TEXT    NOT NULL DEFAULT '',
    language          TEXT    NOT NULL DEFAULT 'EN',
    quantity          INTEGER NOT NULL DEFAULT 1,
    notes             TEXT    NOT NULL DEFAULT '',
    cardmarket_url    TEXT,
    current_price     REAL,
    price_currency    TEXT    NOT NULL DEFAULT 'EUR',
    price_quality     TEXT    NOT NULL DEFAULT 'no_price',
    price_rationale   TEXT,
    price_updated_at  TEXT,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL
);
INSERT INTO sealed_products_new (
    id, name, category, language, quantity, notes, cardmarket_url,
    current_price, price_currency, price_quality, price_rationale,
    price_updated_at, created_at, updated_at
)
SELECT
    id, name, category, language, quantity, notes, cardmarket_url,
    current_price, price_currency, price_quality, price_rationale,
    price_updated_at, created_at, updated_at
FROM sealed_products;
DROP TABLE sealed_products;
ALTER TABLE sealed_products_new RENAME TO sealed_products;
DROP INDEX IF EXISTS idx_sealed_products_collection;
"""


# --- Version 7: sealed product photo + price history --------------------- #
# Sealed products get a `photo_path` column (mirrors cards' -- filled in by a
# best-effort Cardmarket screenshot capture, since there's no pokemontcg.io-
# style image API for them) and their own `sealed_price_history` table
# (mirrors `price_history`), so the Sealed tab can show an artwork panel and
# a price-over-time graph the same way the Karten tab already does.

_V7_SEALED_PRODUCTS_PHOTO_PATH = """
ALTER TABLE sealed_products ADD COLUMN photo_path TEXT;
"""

_V7_SEALED_PRICE_HISTORY = """
CREATE TABLE IF NOT EXISTS sealed_price_history (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    sealed_product_id  INTEGER NOT NULL REFERENCES sealed_products(id) ON DELETE CASCADE,
    price              REAL    NOT NULL,
    currency           TEXT    NOT NULL DEFAULT 'EUR',
    price_quality      TEXT    NOT NULL DEFAULT 'no_price',
    rationale          TEXT    NOT NULL DEFAULT '',
    source             TEXT    NOT NULL DEFAULT '',
    recorded_at        TEXT    NOT NULL
);
"""

_V7_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_sealed_price_history_product "
    "ON sealed_price_history(sealed_product_id);",
)

# --- Version 8: correct EX Series set names ------------------------------- #

#: pokemontcg.io's own /sets response drops the "EX " era prefix for the
#: whole EX Series (live-confirmed for all 16, "ex1" through "ex16",
#: cross-checked against Bulbapedia's official expansion list) -- already
#: corrected going forward for newly added/searched cards (see
#: app.catalog.pokemontcg_client._EX_SERIES_SET_NAMES), this backfills
#: cards added before that fix so they don't keep showing the wrong,
#: prefix-dropped set name forever.
_V8_EX_SERIES_NAMES = (
    ("ex1", "EX Ruby & Sapphire"),
    ("ex2", "EX Sandstorm"),
    ("ex3", "EX Dragon"),
    ("ex4", "EX Team Magma vs Team Aqua"),
    ("ex5", "EX Hidden Legends"),
    ("ex6", "EX FireRed & LeafGreen"),
    ("ex7", "EX Team Rocket Returns"),
    ("ex8", "EX Deoxys"),
    ("ex9", "EX Emerald"),
    ("ex10", "EX Unseen Forces"),
    ("ex11", "EX Delta Species"),
    ("ex12", "EX Legend Maker"),
    ("ex13", "EX Holon Phantoms"),
    ("ex14", "EX Crystal Guardians"),
    ("ex15", "EX Dragon Frontiers"),
    ("ex16", "EX Power Keepers"),
)

_V8_BACKFILL_EX_SERIES_NAMES = tuple(
    f"UPDATE cards SET set_name = '{name}' WHERE set_code = '{set_code}';"
    for set_code, name in _V8_EX_SERIES_NAMES
)

# --- Version 9: wantlist (cards not yet owned, tracked against a target
# price) -- a global list like sealed_products, always identified by a
# directly pasted Cardmarket link (no catalogue integration in this first
# version). No price-history table of its own: unlike owned cards/sealed
# products, there's no "value over time" to chart for something not owned
# yet -- just the latest known price vs. the target. --------------------- #

_V9_WANTLIST_ITEMS = """
CREATE TABLE IF NOT EXISTS wantlist_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    set_name          TEXT    NOT NULL DEFAULT '',
    card_number       TEXT    NOT NULL DEFAULT '',
    language          TEXT    NOT NULL DEFAULT 'en',
    condition         TEXT    NOT NULL DEFAULT 'near_mint',
    target_price      REAL    NOT NULL,
    notes             TEXT    NOT NULL DEFAULT '',
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

_V9_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_wantlist_items_name ON wantlist_items(name);",
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
    Migration(
        version=2,
        description="Card extras (Reverse Holo/Signed/1st Edition/Altered) as flags.",
        statements=(*_V2_ADD_COLUMNS, *_V2_MIGRATE_EXISTING_DATA),
    ),
    Migration(
        version=3,
        description="Drop the now-redundant `variant` column (Normal/Holo/Promo/Staff).",
        statements=("ALTER TABLE cards DROP COLUMN variant;",),
    ),
    Migration(
        version=4,
        description=(
            "Add manual_cardmarket_url: a user-supplied override for Japanese/"
            "Korean/Chinese prints, whose pokemontcg.io cardmarket_url always "
            "points at the wrong (Western) product."
        ),
        statements=("ALTER TABLE cards ADD COLUMN manual_cardmarket_url TEXT;",),
    ),
    Migration(
        version=5,
        description="Sealed products (booster boxes, ETBs, displays, ...) as their own table.",
        statements=(_V5_SEALED_PRODUCTS, *_V5_INDEXES),
    ),
    Migration(
        version=6,
        description=(
            "Drop sealed_products.collection_id: unlike cards (kept in physical "
            "folders/binders, so collections make sense), sealed products aren't "
            "sorted that way -- forcing a collection on them was user-confirmed "
            "as illogical. SQLite can't ALTER TABLE DROP COLUMN a column that's "
            "part of a foreign key, so the table is rebuilt without it."
        ),
        statements=(_V6_DROP_SEALED_COLLECTION_ID,),
    ),
    Migration(
        version=7,
        description=(
            "Sealed products get a photo (screenshot-captured from Cardmarket, "
            "unlike cards' pokemontcg.io image) and their own price history "
            "table, mirroring cards' price_history -- bringing the Sealed tab "
            "up to the same detail-panel/price-graph structure as Karten."
        ),
        statements=(_V7_SEALED_PRODUCTS_PHOTO_PATH, _V7_SEALED_PRICE_HISTORY, *_V7_INDEXES),
    ),
    Migration(
        version=8,
        description=(
            "Correct EX Series set names: pokemontcg.io's own set names drop "
            "the leading 'EX ' era prefix (e.g. its 'Sandstorm' vs. "
            "Cardmarket's 'EX Sandstorm', both the same set) -- backfills "
            "cards added before app.catalog.pokemontcg_client's own "
            "correction existed."
        ),
        statements=_V8_BACKFILL_EX_SERIES_NAMES,
    ),
    Migration(
        version=9,
        description=(
            "Wantlist: cards not yet owned, tracked against a target price -- "
            "a global list (mirrors sealed_products), always identified by a "
            "directly pasted Cardmarket link."
        ),
        statements=(_V9_WANTLIST_ITEMS, *_V9_INDEXES),
    ),
)
