# Pokémon Collection Manager

A native Windows desktop application for managing a Pokémon card and
sealed-product collection, with automatic price discovery based on
Cardmarket data.

The focus is on clean, modular architecture, high code quality, and
long-term maintainability — not a prototype, but an extensible foundation.

---

## Features

- Any number of **collections** (binders/folders) holding any number of
  **cards** — name, set, number, language, condition, reverse holo/
  signed/1st edition/altered, quantity, notes, photo.
- **Sealed products** (booster boxes, displays, ETBs, ...) as their own,
  collection-independent area with a fixed category list.
- **Price discovery**: pokemontcg.io for card data/catalogue, real
  Cardmarket prices by reading an already-open Cardmarket page in a
  normal browser (see note below) — no price APIs that merely estimate
  these values.
- Price quality, price rationale, and price history (chart) per card/
  product.
- Highly tolerant catalogue search: normalises accents/special
  characters, recognises foreign-language Pokémon names (e.g. "Glurak" →
  "Charizard") and foreign-language Trainer/Item card names (e.g. "Lillys
  Entschlossenheit" → "Lillie's Determination", resolved live via
  tcgdex.dev).
- Manually entering a card/sealed product via a Cardmarket link (for
  vintage multi-version prints, Japanese/Korean/Traditional Chinese
  prints, or whenever automatic matching gets it wrong) — including an
  automatic photo screenshot of the product page.
- Statistics tab: total value, breakdown by collection/set, stale prices
  at a glance with a bulk-update button.
- Filtering, multi-select, moving cards between collections, export
  (CSV / Excel / JSON / PDF).
- Automatic SQLite backups before every schema migration.
- In-app help/tutorial under "Infos und Einstellungen".

> **A note on the price source.** Automated bot access to cardmarket.com
> (e.g. via Playwright/CDP) is deliberately **not** implemented — live-
> tested, it runs straight into Cloudflare's bot detection, and would be a
> line this project isn't willing to cross anyway. Instead, the app opens
> the Cardmarket page in the user's **normal** default browser (one click
> = one page, no bulk crawling) and reads the already-rendered screen
> content via Windows UI Automation — the same technique a screen reader
> uses, no DOM/network access to the page itself. See
> `PROJECT_PROGRESS.md` for details and the architectural history behind
> this decision.

---

## System requirements

This app runs **exclusively on Windows** and requires an installation of
**Google Chrome**. Reason: price discovery reads an already-open
Cardmarket page via Windows UI Automation (see note above) — a Windows-
only API with no macOS/Linux equivalent. A platform-independent rewrite
was deliberately ruled out (see `PROJECT_PROGRESS.md`).

## Installation (from source)

Requirements: **Windows**, **Python 3.13+**, **Google Chrome**, and Git.

```bash
# Clone the repository
git clone <repo-url>
cd PokemonCollectionManager

# Create a virtual environment
py -3.13 -m venv .venv

# Activate it
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   Windows (Git Bash):
source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # includes test tooling
```

The SQLite database and log file are created **automatically** on first
launch (under `data/` and `logs/`, respectively).

---

## Running

```bash
# Launch the application
python -m app.main

# Run the test suite
python -m pytest -q
```

---

## Building a standalone .exe

To hand the app to someone else (e.g. for testing), a standalone, portable
`.exe` can be built — no Python/venv needed on the recipient's machine:

```bash
pip install -r requirements-build.txt
pyinstaller PokemonCollectionManager.spec
```

The result lands at `dist/PokemonCollectionManager.exe`. The file is
portable: the database, photos, backups, and logs are created
automatically in subfolders right next to the `.exe`, regardless of where
it's copied. Google Chrome still needs to be installed on the target
machine (see System requirements).

---

## Project structure

```
PokemonCollectionManager/
├── app/
│   ├── config.py            # paths & constants
│   ├── logging_config.py    # central logging (logs/application.log)
│   ├── bootstrap.py         # startup sequence (logging → directories → DB)
│   ├── main.py              # entry point
│   ├── models/               # domain objects (dataclasses) + enums
│   ├── database/              # SQLite: connection, schema, migrations,
│   │                           # backups, repositories
│   ├── catalog/                # pokemontcg.io/tcgdex: card data, name
│   │                           # translation, set icons, image cache
│   ├── pricing/                # Cardmarket price discovery (Windows UI
│   │                           # Automation) & photo screenshot capture
│   ├── services/               # business logic (the only layer the UI
│   │                           # is allowed to call into)
│   ├── export/                  # CSV / Excel / JSON / PDF
│   └── ui/                     # PySide6 interface (widgets, controllers,
│                               # dialogs, background workers)
├── tests/                   # pytest suite
├── data/                    # SQLite DB, photos, backups (local, not versioned)
├── logs/                    # application.log (not versioned)
├── requirements.txt
├── requirements-dev.txt
├── requirements-build.txt
├── PokemonCollectionManager.spec  # PyInstaller build config
├── pyproject.toml
├── PROJECT_PROGRESS.md      # development log (sync file across machines)
├── CHANGELOG.md             # chronological change history
└── README.md
```

Business logic never lives in the GUI: the interface only ever talks to
the `services` layer, which in turn talks to `database`/`catalog`/
`pricing`/`export`.

---

## Libraries used

| Library | Purpose |
|---------|---------|
| **PySide6** | Native Qt desktop interface |
| **requests** | HTTP client for pokemontcg.io/tcgdex |
| **pywinauto** | Price/photo lookup: reads an already-open Cardmarket page |
| **openpyxl** | Excel export (.xlsx) |
| **reportlab** | PDF export |
| **pytest** | Test framework (dev) |

The standard library (`sqlite3`, `logging`, `dataclasses`, `enum`,
`pathlib`, `csv`, `json`) covers the database, logging, domain model, and
part of the export without extra dependencies. Further libraries are only
added once a given feature actually needs them ("no unnecessary
dependencies").

---

## Development approach

The project is developed strictly iteratively. After every change:
write code → test → fix bugs → update `PROJECT_PROGRESS.md` and
`CHANGELOG.md` → wait for sign-off.
