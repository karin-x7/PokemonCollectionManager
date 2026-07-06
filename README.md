# Pokémon Collection Manager

Eine native Windows-Desktop-Anwendung zum Verwalten einer Pokémon-Karten-
und Sealed-Produkt-Sammlung mit automatischer Preisermittlung auf Basis
von Cardmarket-Daten.

Der Fokus liegt auf sauberer, modularer Architektur, hoher Codequalität und
langfristiger Wartbarkeit — kein Prototyp, sondern ein erweiterbares Fundament.

---

## Funktionsumfang

- Beliebig viele **Sammlungen** (Binder/Ordner) mit beliebig vielen **Karten**
  — Name, Set, Nummer, Sprache, Zustand, Reverse-Holo/Signiert/1st-Edition/
  Verändert, Menge, Notizen, Foto.
- **Sealed-Produkte** (Booster-Boxen, Displays, ETBs, ...) als eigener,
  sammlungsunabhängiger Bereich mit fester Kategorienliste.
- **Preisermittlung**: pokemontcg.io für Kartendaten/Katalog, echte
  Cardmarket-Preise durch Auslesen einer bereits geöffneten Cardmarket-Seite
  im normalen Browser (siehe Hinweis unten) — keine Preis-APIs, die diese
  Werte nur schätzen.
- Preisqualität, Preisbegründung und Preisverlauf (Chart) pro Karte/Produkt.
- Toleranteste Katalogsuche: normalisiert (Akzente/Sonderzeichen), erkennt
  fremdsprachige Pokémon-Namen (z. B. "Glurak" → "Charizard") und fremd-
  sprachige Trainer-/Item-Kartennamen (z. B. "Lillys Entschlossenheit" →
  "Lillie's Determination", live über tcgdex.dev aufgelöst).
- Manuelles Eintragen einer Karte/eines Sealed-Produkts per Cardmarket-Link
  (für vintage Mehrfachversionen, JP/KO/Traditionelles-Chinesisch, oder wenn
  die automatische Zuordnung danebenliegt) — inklusive automatischem
  Foto-Screenshot von der Produktseite.
- Statistik-Tab: Gesamtwert, Aufschlüsselung nach Sammlung/Set, veraltete
  Preise auf einen Blick mit Sammel-Update-Button.
- Filter, Mehrfachauswahl, Verschieben zwischen Sammlungen, Export
  (CSV / Excel / JSON / PDF).
- Automatische SQLite-Backups vor jeder Schema-Migration.
- In-App Hilfe/Anleitung unter "Infos und Einstellungen".

> **Hinweis zur Preisquelle.** Ein automatisierter Bot-Zugriff auf
> cardmarket.com (z. B. per Playwright/CDP) wird bewusst **nicht**
> umgesetzt — live getestet, scheitert an Cloudflares Bot-Erkennung, und
> wäre ohnehin eine Grenze, die dieses Projekt nicht überschreitet.
> Stattdessen öffnet die App die Cardmarket-Seite im **normalen**
> Standardbrowser des Nutzers (ein Klick = eine Seite, kein Sammel-Lauf)
> und liest den bereits geladenen Bildschirminhalt per Windows UI
> Automation aus — dieselbe Technik wie ein Screenreader, kein DOM-/
> Netzwerkzugriff auf die Seite. Details und die Architektur-Historie dazu
> siehe `PROJECT_PROGRESS.md`.

---

## Systemvoraussetzungen

Diese App läuft **ausschließlich unter Windows** und benötigt eine
Installation von **Google Chrome**. Grund: Die Preisermittlung liest eine
bereits geöffnete Cardmarket-Seite über Windows UI Automation aus (siehe
Hinweis oben) — das ist eine reine Windows-API, es gibt keine macOS-/
Linux-Entsprechung. Ein Umbau auf eine plattformunabhängige Lösung wurde
bewusst verworfen (siehe `PROJECT_PROGRESS.md`).

## Installation (aus dem Quellcode)

Voraussetzungen: **Windows**, **Python 3.13+**, **Google Chrome** und Git.

```bash
# Repository holen
git clone <repo-url>
cd PokemonCollectionManager

# Virtuelles Environment anlegen
py -3.13 -m venv .venv

# Aktivieren
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   Windows (Git Bash):
source .venv/Scripts/activate

# Abhängigkeiten installieren
pip install -r requirements.txt        # Laufzeit
pip install -r requirements-dev.txt    # inkl. Test-Tools
```

Die SQLite-Datenbank und die Logdatei werden beim ersten Start **automatisch**
angelegt (unter `data/` bzw. `logs/`).

---

## Startanleitung

```bash
# Anwendung starten
python -m app.main

# Tests ausführen
python -m pytest -q
```

---

## Eigenständige .exe bauen

Für die Weitergabe an andere (z. B. zum Testen) lässt sich eine
eigenständige, portable `.exe` bauen — kein Python/venv beim Empfänger
nötig:

```bash
pip install -r requirements-build.txt
pyinstaller PokemonCollectionManager.spec
```

Ergebnis liegt danach unter `dist/PokemonCollectionManager.exe`. Die Datei
ist portabel: Datenbank, Fotos, Backups und Logs landen automatisch in
Unterordnern direkt neben der `.exe`, unabhängig davon, wohin sie kopiert
wird. Google Chrome muss auf dem Zielrechner trotzdem installiert sein
(siehe Systemvoraussetzungen).

---

## Projektstruktur

```
PokemonCollectionManager/
├── app/
│   ├── config.py            # Pfade & Konstanten
│   ├── logging_config.py    # zentrales Logging (logs/application.log)
│   ├── bootstrap.py         # Start-Sequenz (Logging → Verzeichnisse → DB)
│   ├── main.py              # Einstiegspunkt
│   ├── models/               # Domänenobjekte (Dataclasses) + Enums
│   ├── database/              # SQLite: Connection, Schema, Migrationen,
│   │                           # Backups, Repositories
│   ├── catalog/                # pokemontcg.io/tcgdex: Kartendaten, Namens-
│   │                           # übersetzung, Set-Icons, Bild-Cache
│   ├── pricing/                # Cardmarket-Preisermittlung (Windows UI
│   │                           # Automation) & Bild-Screenshot-Capture
│   ├── services/               # Business-Logik (einzige Schicht, die die
│   │                           # UI aufrufen darf)
│   ├── export/                  # CSV / Excel / JSON / PDF
│   └── ui/                     # PySide6-Oberfläche (Widgets, Controller,
│                               # Dialoge, Hintergrund-Worker)
├── tests/                   # pytest-Suite
├── data/                    # SQLite-DB, Fotos, Backups (lokal, nicht versioniert)
├── logs/                    # application.log (nicht versioniert)
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── PROJECT_PROGRESS.md      # aktueller Entwicklungsstand (Sync zwischen PCs)
├── CHANGELOG.md             # chronologische Änderungshistorie
└── README.md
```

Geschäftslogik liegt niemals in der GUI: Die Oberfläche spricht ausschließlich
mit der `services`-Schicht, diese mit `database`/`catalog`/`pricing`/`export`.

---

## Verwendete Bibliotheken

| Bibliothek | Zweck |
|-----------|-------|
| **PySide6** | Native Qt-Desktop-Oberfläche |
| **requests** | HTTP-Client für pokemontcg.io/tcgdex |
| **pywinauto** | Preis-/Bild-Lookup: liest eine bereits geöffnete Cardmarket-Seite aus |
| **openpyxl** | Excel-Export (.xlsx) |
| **reportlab** | PDF-Export |
| **pytest** | Test-Framework (Dev) |

Die Standardbibliothek (`sqlite3`, `logging`, `dataclasses`, `enum`, `pathlib`,
`csv`, `json`) deckt Datenbank, Logging, Domänenmodell und einen Teil des
Exports ohne Zusatzabhängigkeiten ab. Weitere Bibliotheken werden erst
hinzugefügt, wenn sie tatsächlich gebraucht werden ("keine unnötigen
Abhängigkeiten").

---

## Entwicklungsvorgehen

Das Projekt wird streng iterativ entwickelt. Nach jeder Änderung gilt:
Code schreiben → testen → Fehler beheben → `PROJECT_PROGRESS.md` und
`CHANGELOG.md` aktualisieren → auf Freigabe warten.
