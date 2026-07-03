# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier chronologisch
dokumentiert. Format angelehnt an [Keep a Changelog](https://keepachangelog.com);
Versionierung nach [SemVer](https://semver.org).

## [Unreleased]

### Hinzugefügt — Schritt 3: Sammlungen-CRUD
- `CollectionRepository` (`app/database/repositories/collection_repository.py`):
  reine SQL-Zugriffsschicht für Sammlungen.
- `CollectionService` (`app/services/collection_service.py`) mit Validierung
  und typisierten, deutschsprachigen Fehlern (`app/services/exceptions.py`).
- `CollectionController` (`app/ui/controllers/collection_controller.py`)
  verbindet `CollectionPanel` und `CollectionService`.
- `CollectionPanel` an echte Daten gebunden: anlegen, umbenennen (Doppelklick
  oder Kontextmenü), löschen (mit Bestätigung, kaskadiert auf Karten),
  Umsortieren per Drag & Drop. Neu erstellte Sammlungen werden automatisch
  ausgewählt.
- Desktop- und Startmenü-Verknüpfung zum Starten ohne Terminal
  (`pythonw.exe -m app.main`, kein Konsolenfenster).
- 21 Tests für Repository/Service, 15 Tests für Panel/Controller-Wiring.
  Gesamt: 55 Tests grün.

### Behoben
- Ein `Signal(int, ...)` durfte nie mit `None` emittiert werden — PySide6/
  Shiboken meldet dies nicht als reguläre Python-Exception, sondern hängt den
  Prozess auf. Ursache war eine fehlende Auto-Auswahl neu erstellter
  Sammlungen; behoben, indem `CollectionController._on_create` die neue
  Sammlung nach dem Anlegen automatisch selektiert. In der echten
  Bedienoberfläche war das nie auslösbar (Kontextmenü/Doppelklick liefern
  immer ein reales Element) — die Korrektur ist zugleich eine echte
  UX-Verbesserung.

### Hinzugefügt — Schritt 2: GUI-Grundgerüst (PySide6)
- Hauptfenster (`app/ui/main_window.py`) mit Drei-Spalten-Layout
  (Sammlungen · Kartenliste · Kartendetails) über `QSplitter`.
- Toolbar mit Suchfeld und Aktionen Scanner / Cardmarket-Preise aktualisieren /
  Export sowie Theme-Umschalter; Statusleiste.
- Umschaltbarer **Hell-/Dunkelmodus** über zentrales QSS-Theme
  (`app/ui/theme.py`).
- Präsentations-Panels (`app/ui/widgets/`) ohne Business-Logik; kommunizieren
  über Qt-Signale.
- App-Factory (`app/ui/app.py`); `main.py` startet nun die GUI, `--check`
  bleibt headless.
- 6 GUI-Smoke-Tests (headless via `offscreen`). Gesamt: 19 Tests grün.
- `.gitattributes` zur Zeilenenden-Normalisierung (Multi-PC-Sync).

### Geändert
- **Preisquelle finalisiert:** Primärquelle ist nun **CardTrader** (europäischer
  Marktplatz mit echten Einzelangeboten pro Zustand/Sprache/Preis) statt reiner
  Aggregatpreise. pokemontcg.io bleibt für Katalog/Suche/Bilder und als
  Preis-Fallback. Machbarkeit mit einem normalen CardTrader-Konto getestet und
  bestätigt (nur lesender Zugriff).
- `main.py` startet die grafische Oberfläche (vorher nur Statusbericht).

### Hinzugefügt (Infrastruktur)
- Lokales, git-ignoriertes Secrets-Handling: `app/secrets.py`,
  `config/secrets.example.json`, `config/secrets.json`. Tokens werden nie
  geloggt oder committet.

## [0.1.0] — 2026-07-02 — Schritt 1: Projektfundament

### Hinzugefügt
- Modulare Projektstruktur (`app/` mit Sub-Paketen `models`, `database`,
  `services`, `pricing`, `cardmarket`, `recognition`, `scanner`, `export`,
  `ui`, `utils`).
- Virtuelles Environment mit **Python 3.13.14**; `pyproject.toml`,
  `requirements.txt`, `requirements-dev.txt`, `.gitignore`.
- Zentrale Konfiguration (`app/config.py`) mit über Umgebungsvariablen
  überschreibbaren Pfaden.
- Zentrales Logging (`app/logging_config.py`) mit rotierendem
  `logs/application.log` (UTF-8) und Konsolenausgabe.
- Domänenmodell: Dataclasses `Collection`, `Card`, `PriceRecord` sowie Enums
  `Variant`, `Condition`, `Language`, `PriceQuality`.
- SQLite-Datenbank-Layer: automatische DB-Erstellung, `Database`-Context-
  Manager mit Foreign-Keys/WAL, forward-only Migrations-Framework mit
  `schema_migrations`-Tracking.
- Initiales Schema (Migration 1): Tabellen `collections`, `cards`,
  `price_history`, `settings` inkl. Indizes.
- Bootstrap-Sequenz (`app/bootstrap.py`) und CLI-Einstiegspunkt
  (`app/main.py`, `python -m app.main`).
- Test-Suite (`pytest`): Datenbank- und Modelltests (13 Tests).
- Dokumentation: `README.md`, `PROJECT_PROGRESS.md`, `CHANGELOG.md`.

### Architektur-Entscheidungen
- **Preisquelle:** Direkter Zugriff auf cardmarket.com (Scraping) wird als
  AGB-widrig verworfen. Stattdessen `PriceProvider`-Abstraktion mit
  pokemontcg.io als Standard, optionaler offizieller Cardmarket-API und
  manueller Eingabe als Fallback.
- **Python-Zielversion:** 3.13 (wie gefordert) installiert und aktiv.
