# Projektfortschritt — Pokémon Collection Manager

> Synchronisationsdatei zwischen mehreren PCs. Enthält jederzeit den aktuellen
> Entwicklungsstand. Wird nach **jedem** Entwicklungsschritt aktualisiert.

**Letzter Schritt:** Schritt 1 — Projektfundament
**Datum:** 2026-07-02
**Version:** 0.1.0
**TestStatus:** ✅ 13 Tests grün (`pytest`)

---

## Aktueller Stand

Das Fundament der Anwendung steht und ist eigenständig lauffähig/testbar:

- ✅ Modulare Projektstruktur (`app/` mit allen geplanten Sub-Paketen).
- ✅ Zentrale Konfiguration & Pfad-Auflösung (`app/config.py`), per Umgebungs-
  variablen überschreibbar.
- ✅ Zentrales Logging in Konsole **und** `logs/application.log` (rotierend).
- ✅ SQLite-Datenbank wird beim Start automatisch erstellt.
- ✅ Forward-only **Migrations-Framework** mit `schema_migrations`-Tracking.
- ✅ Domänenmodell: `Collection`, `Card`, `PriceRecord` (Dataclasses) sowie
  Enums `Variant`, `Condition`, `Language`, `PriceQuality`.
- ✅ Bootstrap-Sequenz + CLI-Einstiegspunkt (`python -m app.main`).
- ✅ Test-Suite (Datenbank + Modelle).
- ✅ Dokumentation: `README.md`, `CHANGELOG.md`, dieses Dokument.

---

## Heute umgesetzt (Schritt 1)

- Projektgerüst inkl. `.venv` (Python 3.13.14), `.gitignore`, `pyproject.toml`,
  `requirements.txt`, `requirements-dev.txt`.
- `config.py`: App-Konstanten, Pfade (`DATA_DIR`, `LOGS_DIR`, `DB_PATH`, …),
  `ensure_directories()`.
- `logging_config.py`: `configure_logging()` / `get_logger()` mit rotierendem
  Datei-Handler (UTF-8) und Konsolen-Handler.
- `utils/time.py`: einheitliche UTC-ISO-Zeitstempel.
- Domänenmodell in `models/` (siehe „Neue Klassen").
- Datenbank-Layer in `database/`:
  - `schema.py`: DDL als versionierte Migrationen (Version 1).
  - `migrations.py`: atomarer, forward-only Migration-Runner.
  - `connection.py`: `Database`-Klasse (Context-Manager, PRAGMAs).
- `bootstrap.py` + `main.py`: Start-Sequenz und Statusausgabe.
- Tests: `tests/test_database.py`, `tests/test_models.py`, `conftest.py`.

---

## Dateien geändert / neu angelegt

**Neu:**
- `.gitignore`, `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- `README.md`, `PROJECT_PROGRESS.md`, `CHANGELOG.md`
- `app/__init__.py`, `app/config.py`, `app/logging_config.py`,
  `app/bootstrap.py`, `app/main.py`
- `app/models/{__init__,enums,collection,card,price}.py`
- `app/database/{__init__,schema,migrations,connection}.py`
- `app/utils/{__init__,time}.py`
- `app/{ui,services,pricing,cardmarket,recognition,scanner,export}/__init__.py`
  (Platzhalter-Pakete)
- `tests/{__init__,conftest,test_database,test_models}.py`
- **Nachtrag (Preis-Infrastruktur):** `app/secrets.py` (lokaler Secrets-Loader),
  `config/secrets.example.json` (Vorlage), `config/secrets.json` (lokal,
  git-ignoriert), `.gitignore` um Secrets erweitert.

---

## Neue Klassen

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `Variant` | `models.enums` | Kartenvariante (Normal, Holo, Reverse, 1st Edition, …) |
| `Condition` | `models.enums` | Zustand mit Ordnung (`order`) + Code (Mint…Poor) |
| `Language` | `models.enums` | Sprache mit Code (EN, DE, …) |
| `PriceQuality` | `models.enums` | Preisqualität inkl. deutscher Labels |
| `Collection` | `models.collection` | Sammlung (Dataclass) |
| `Card` | `models.card` | Karteneintrag (Dataclass) inkl. `total_value` |
| `PriceRecord` | `models.price` | Ein Punkt im Preisverlauf (Dataclass) |
| `Migration` | `database.schema` | Versionierte Schemaänderung |
| `Database` | `database.connection` | SQLite-Connection-Verwaltung |
| `BootstrapError` | `bootstrap` | Fehler bei der Initialisierung |

---

## Datenbankänderungen

**Schema-Version:** 1 (Migration angewandt).

**Neue Tabellen:**
- `collections` (id, name*unique*, description, position, created_at, updated_at)
- `cards` (id, collection_id→collections, name, set_name, set_code, card_number,
  variant, language, condition, quantity, notes, photo_path, external_card_id,
  cardmarket_url, current_price, price_currency, price_quality, price_rationale,
  price_updated_at, created_at, updated_at)
- `price_history` (id, card_id→cards, price, currency, price_quality, rationale,
  source, recorded_at)
- `settings` (key, value, updated_at)
- `schema_migrations` (version, description, applied_at)

**Indizes:** `idx_cards_collection`, `idx_cards_name`, `idx_cards_set`,
`idx_price_history_card`.

**Migrationen:** Migration 1 „Initial schema" angelegt und angewandt.

---

## Architektur-Entscheidung: Preisquelle (aktualisiert)

Direkter Zugriff auf cardmarket.com (Scraping) ist AGB-widrig; die offizielle
Cardmarket-API nimmt derzeit keine neuen Anträge an. Als vollwertige,
**europäische** Alternative mit Einzelangeboten wird **CardTrader** genutzt
(getestet und bestätigt: ein normales Konto genügt für Lese-Zugriff).

`PriceProvider`-Kette:

1. **Primär (granular):** **CardTrader** — echte Einzelangebote mit
   Zustand + Sprache + Foil + Preis. Ermöglicht exakte Treffer und die volle
   Fallback-Leiter sowie die Option „nur exakte Treffer".
2. **Sekundär (Katalog + Fallback):** pokemontcg.io — Kartendaten/Bilder für
   Suche/Erkennung und Aggregatpreis, falls CardTrader kein Angebot hat.
3. **Fallback:** manuelle Preiseingabe/-import.

Machbarkeit verifiziert (Base-Set-Charizard: 100 Angebote mit Preis/Zustand/
Sprache lesbar). Endpunkte: `/info`, `/games`, `/expansions`, `/blueprints?
expansion_id=`, `/marketplace/products?blueprint_id=`.

**Sicherheit:** Der CardTrader-JWT liegt ausschließlich lokal in
`config/secrets.json` (git-ignoriert), wird nie geloggt und nie committet. Die
API wird **strikt lesend** verwendet — keine Kauf-/Verkaufs-Endpunkte.

**Offene Mapping-Aufgaben für Schritt 6:**
- CardTrader-Zustandsskala (Mint · Near Mint · Slightly/Moderately Played ·
  Played · Heavily Played · Poor) → kanonische `Condition`-Skala.
- Sprachkürzel (`de`, `en`, …) → `Language`-Enum.
- Varianten (Holo/Reverse/1st Ed.) → CardTrader-Blueprints + `foil`-Property.

---

## Offene Aufgaben (priorisiert)

1. **Schritt 2 — GUI-Grundgerüst:** PySide6-Hauptfenster, 3-Spalten-Layout
   (Sammlungen | Kartenliste | Kartendetails), obere Toolbar, Hell-/Dunkelmodus.
2. **Schritt 3 — Sammlungen-CRUD:** Repository + Service + UI-Anbindung.
3. **Schritt 4 — Kartenkatalog & intelligente Suche** (pokemontcg.io-Import).
4. **Schritt 5 — Karten zu Sammlungen hinzufügen** (Variante/Sprache/Zustand/…).
5. **Schritt 6 — Preis-Engine + Provider-Abstraktion + „Preise aktualisieren".**
6. **Schritt 7 — Preisverlauf & Diagramme.**
7. **Schritt 8 — Filter & Volltextsuche.**
8. **Schritt 9 — Statistiken.**
9. **Schritt 10 — Export (CSV/Excel/JSON/PDF).**
10. **Schritt 11 — Webcam-Scanner (OCR/Bildvergleich).**

---

## Bekannte Bugs

- Keine bekannten Bugs. (Windows-Konsole zeigt Sonderzeichen je nach Codepage
  ggf. als `�` an; die Logdatei ist korrektes UTF-8 — rein kosmetisch.)
- Hinweis CardTrader: `/blueprints/export?expansion_id=` liefert für viele Sets
  „Data is not ready" (Cache-Endpunkt). Lösung: Live-Endpunkt
  `/blueprints?expansion_id=` verwenden (bestätigt funktionierend).

---

## Nächster Entwicklungsschritt

**Schritt 2 — GUI-Grundgerüst (PySide6).** Hauptfenster mit Drei-Spalten-Layout,
Toolbar (Suche · Scanner · Preise aktualisieren · Export), umschaltbarer Hell-/
Dunkelmodus, ohne Business-Logik in der GUI. Danach kurze Zusammenfassung und
Warten auf Freigabe.
