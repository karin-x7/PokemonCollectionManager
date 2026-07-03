# Pokémon Collection Manager

Eine native Desktop-Anwendung zum Verwalten einer Pokémon-Kartensammlung mit
automatischer Preisermittlung auf Basis von Cardmarket-Daten.

Der Fokus liegt auf sauberer, modularer Architektur, hoher Codequalität und
langfristiger Wartbarkeit — kein Prototyp, sondern ein erweiterbares Fundament.

---

## Projektbeschreibung

- Verwaltung beliebig vieler **Sammlungen** (z. B. *Binder*, *PSA Submission*,
  *Vintage*, *Verkauf*) mit beliebig vielen Karten.
- Erfassung aller relevanten Karteninformationen (Name, Set, Nummer, Variante,
  Sprache, Zustand, Menge, Notizen, Foto).
- **Preisermittlung** über eine austauschbare Provider-Abstraktion. Standard-
  Provider ist [pokemontcg.io](https://pokemontcg.io) (liefert Kartendaten und
  Cardmarket-Preisaggregate — legal und kostenlos mit API-Key).
- Preisqualität, Preisbegründung und Preisverlauf pro Karte.
- Filter, Suche, Statistiken und Export (CSV / Excel / JSON / PDF).
- Kartenerkennung per Webcam (OCR / Bildvergleich) sowie intelligente manuelle
  Suche.

> **Hinweis zur Preisquelle.** Ein direkter, automatisierter Zugriff auf
> cardmarket.com (Scraping) verstößt gegen deren Nutzungsbedingungen und wird
> bewusst **nicht** umgesetzt. Die volle Zustands-/Sprach-Granularität der
> Fallback-Regeln setzt die offizielle (gewerbliche) Cardmarket-API voraus.
> Deshalb ist die Preisermittlung hinter einer `PriceProvider`-Schnittstelle
> gekapselt: Standard = pokemontcg.io, optional = offizielle Cardmarket-API,
> Fallback = manuelle Eingabe. Details siehe `PROJECT_PROGRESS.md`.

---

## Installation

Voraussetzungen: **Python 3.13+** und Git.

```bash
# Repository holen
git clone <repo-url>
cd PokemonCollectionManager

# Virtuelles Environment anlegen
py -3.13 -m venv .venv

# Aktivieren
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   Windows (Git Bash) / Linux / macOS:
source .venv/Scripts/activate      # bzw. .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt        # Laufzeit
pip install -r requirements-dev.txt    # inkl. Test-Tools
```

Die SQLite-Datenbank und die Logdatei werden beim ersten Start **automatisch**
angelegt (unter `data/` bzw. `logs/`).

---

## Startanleitung

```bash
# Anwendung starten (aktuell: Bootstrap-/Statusbericht; GUI ab Schritt 2)
python -m app.main

# Tests ausführen
python -m pytest -q
```

---

## Projektstruktur

```
PokemonCollectionManager/
├── app/
│   ├── config.py            # Pfade & Konstanten
│   ├── logging_config.py    # zentrales Logging (logs/application.log)
│   ├── bootstrap.py         # Start-Sequenz (Logging → Verzeichnisse → DB)
│   ├── main.py              # Einstiegspunkt
│   ├── models/              # Domänenobjekte (Dataclasses) + Enums
│   ├── database/            # SQLite: Connection, Schema, Migrationen
│   ├── services/            # Business-Logik (ab Schritt 3)
│   ├── pricing/             # Preis-Engine & Provider-Abstraktion (Schritt 6)
│   ├── cardmarket/          # Cardmarket-Integration (Schritt 6)
│   ├── recognition/         # OCR / Bildvergleich (später)
│   ├── scanner/             # Webcam-Erfassung (später)
│   ├── export/              # CSV / Excel / JSON / PDF (später)
│   ├── ui/                  # PySide6-Oberfläche (ab Schritt 2)
│   └── utils/               # kleine Helfer
├── tests/                   # pytest-Suite
├── data/                    # SQLite-DB & Fotos (lokal, nicht versioniert)
├── logs/                    # application.log (nicht versioniert)
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── PROJECT_PROGRESS.md      # aktueller Entwicklungsstand (Sync zwischen PCs)
├── CHANGELOG.md             # chronologische Änderungshistorie
└── README.md
```

Geschäftslogik liegt niemals in der GUI: Die Oberfläche spricht ausschließlich
mit der `services`-Schicht, diese mit `database`/`pricing`/`export`.

---

## Verwendete Bibliotheken

| Bibliothek | Zweck | Ab Schritt |
|-----------|-------|-----------|
| **PySide6** | Native Qt-Desktop-Oberfläche | 2 |
| **requests** | HTTP-Client für den pokemontcg.io-Provider | 4 |
| **pytest** | Test-Framework (Dev) | 1 |

Die Standardbibliothek (`sqlite3`, `logging`, `dataclasses`, `enum`, `pathlib`)
deckt Datenbank, Logging und Domänenmodell ohne Zusatzabhängigkeiten ab.
Export- und Erkennungsbibliotheken werden erst hinzugefügt, wenn die jeweiligen
Schritte umgesetzt werden ("keine unnötigen Abhängigkeiten").

---

## Entwicklungsvorgehen

Das Projekt wird streng iterativ entwickelt. Nach jedem Schritt gilt:
Code schreiben → testen → Fehler beheben → `PROJECT_PROGRESS.md` und
`CHANGELOG.md` aktualisieren → auf Freigabe warten.
