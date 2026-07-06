# Pokémon Collection Manager

A native Windows desktop app for managing a Pokémon card and sealed-product
collection, with automatic price discovery based on real Cardmarket data.

## Features

- Collections/binders with cards (name, set, number, language, condition,
  reverse holo/signed/1st edition/altered, quantity, notes, photo) and
  sealed products (booster boxes, ETBs, displays, ...).
- Real Cardmarket prices, price quality/rationale, and price history per
  card/product — read from an already-open Cardmarket page via Windows UI
  Automation, not scraping or a bot.
- Tolerant catalogue search, including foreign-language Pokémon and
  Trainer/Item card names.
- Manual entry via a pasted Cardmarket link (vintage prints, JP/KO/zh-Hant
  cards), with automatic photo capture.
- Statistics tab, filtering, multi-select, export (CSV/Excel/JSON/PDF),
  automatic DB backups before migrations.

## Requirements

**Windows only**, plus **Google Chrome** installed (price discovery reads
an already-open Cardmarket page via Windows UI Automation — a Windows-only
API).

## Installation (from source)

Requirements: Python 3.13+, Google Chrome, Git.

```bash
git clone <repo-url>
cd PokemonCollectionManager

py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1        # or: source .venv/Scripts/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt    # for running tests
```

The database and log file are created automatically on first launch
(`data/`, `logs/`).

## Running

```bash
python -m app.main      # launch the app
python -m pytest -q     # run tests
```

## Building a standalone .exe

```bash
pip install -r requirements-build.txt
pyinstaller PokemonCollectionManager.spec
```

Result: `dist/PokemonCollectionManager.exe` — portable, no Python needed on
the target machine. Database/photos/backups/logs live in folders next to
the `.exe`. Google Chrome still needs to be installed.

---

See `CHANGELOG.md` for the full change history and `PROJECT_PROGRESS.md`
for development notes.
