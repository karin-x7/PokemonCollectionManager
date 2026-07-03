# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier chronologisch
dokumentiert. Format angelehnt an [Keep a Changelog](https://keepachangelog.com);
Versionierung nach [SemVer](https://semver.org).

## [Unreleased]

### Geändert
- **Preisquelle finalisiert:** Primärquelle ist nun **CardTrader** (europäischer
  Marktplatz mit echten Einzelangeboten pro Zustand/Sprache/Preis) statt reiner
  Aggregatpreise. pokemontcg.io bleibt für Katalog/Suche/Bilder und als
  Preis-Fallback. Machbarkeit mit einem normalen CardTrader-Konto getestet und
  bestätigt (nur lesender Zugriff).

### Hinzugefügt
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
