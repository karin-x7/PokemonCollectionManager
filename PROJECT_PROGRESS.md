# Projektfortschritt — Pokémon Collection Manager

> Synchronisationsdatei zwischen mehreren PCs. Enthält jederzeit den aktuellen
> Entwicklungsstand. Wird nach **jedem** Entwicklungsschritt aktualisiert.

**Letzter Schritt:** Schritt 2 — GUI-Grundgerüst (PySide6)
**Datum:** 2026-07-03
**Version:** 0.1.0
**TestStatus:** ✅ 19 Tests grün (`pytest`)

---

## Aktueller Stand

- ✅ Modulare Projektstruktur (`app/` mit allen geplanten Sub-Paketen).
- ✅ Zentrale Konfiguration & Pfad-Auflösung, per Umgebungsvariablen überschreibbar.
- ✅ Zentrales Logging in Konsole **und** `logs/application.log` (rotierend).
- ✅ SQLite-DB mit automatischer Erstellung + forward-only Migrations-Framework.
- ✅ Domänenmodell: `Collection`, `Card`, `PriceRecord` + Enums.
- ✅ Lokales, git-ignoriertes Secrets-Handling (CardTrader-JWT).
- ✅ **GUI-Grundgerüst (PySide6):** Hauptfenster mit Drei-Spalten-Layout,
  Toolbar, Hell-/Dunkelmodus. Startet über `python -m app.main`.
- ✅ Bootstrap + CLI-Einstiegspunkt (`--check` für Headless-Health-Check).
- ✅ Test-Suite (Datenbank, Modelle, GUI-Smoke-Tests headless via `offscreen`).
- ✅ Dokumentation: `README.md`, `CHANGELOG.md`, dieses Dokument.

---

## Heute umgesetzt (Schritt 2 — GUI-Grundgerüst)

- **Theme-System** (`app/ui/theme.py`): `Theme`-Enum (Hell/Dunkel), Farb-
  paletten und komplettes Qt-Stylesheet (QSS) — zentral, keine Farbliterale in
  den Widgets.
- **Drei Panels** (`app/ui/widgets/`):
  - `CollectionPanel` — Sammlungsliste (links) + „Neue Sammlung"-Button.
  - `CardListPanel` — Kartentabelle (Mitte) mit Spalten Name/Set/Nr./Variante/
    Sprache/Zustand/Menge/Preis.
  - `CardDetailPanel` — Kartendetails (rechts): Foto-Platzhalter, Feldliste,
    „Auf Cardmarket öffnen"-Button.
  - Panels sind **reine Präsentations-Shells** und geben Signale ab; echte
    Datenbindung folgt ab Schritt 3/5. (Platzhalterinhalte klar markiert.)
- **Hauptfenster** (`app/ui/main_window.py`): Toolbar mit Suchfeld, Aktionen
  Scanner / Cardmarket-Preise aktualisieren / Export sowie Theme-Toggle
  (rechts); `QSplitter`-Layout; Statusleiste. Exponiert Signale
  (`search_submitted`, `scan_requested`, `update_prices_requested`,
  `export_requested`) — **keine Business-Logik im Fenster**; vorerst nur
  Statusleisten-Feedback.
- **App-Factory** (`app/ui/app.py`): `build_application()` (Fusion-Style),
  `run_gui()`; headless testbar via `offscreen`.
- **`main.py`**: startet nun die GUI; `--check` läuft headless (Bootstrap +
  Statusbericht).
- **Tests** (`tests/test_ui_smoke.py`): 6 GUI-Smoke-Tests (offscreen).
- Visuell verifiziert (Hell + Dunkel gerendert; App live gestartet).

---

## Dateien geändert / neu angelegt (Schritt 2)

**Neu:**
- `app/ui/theme.py`
- `app/ui/app.py`
- `app/ui/main_window.py`
- `app/ui/widgets/{__init__,collection_panel,card_list_panel,card_detail_panel}.py`
- `tests/test_ui_smoke.py`
- `.gitattributes` (Zeilenenden-Normalisierung für Multi-PC-Sync)

**Geändert:**
- `app/main.py` (GUI-Start + `--check`)

---

## Neue Klassen (Schritt 2)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `Theme` | `ui.theme` | Hell/Dunkel-Enum inkl. `toggled()` |
| `Palette` | `ui.theme` | Farbpalette pro Theme |
| `CollectionPanel` | `ui.widgets.collection_panel` | Sammlungs-Sidebar |
| `CardListPanel` | `ui.widgets.card_list_panel` | Kartentabelle |
| `CardDetailPanel` | `ui.widgets.card_detail_panel` | Kartendetails |
| `MainWindow` | `ui.main_window` | Hauptfenster + Toolbar + Layout |

---

## Datenbankänderungen

Keine (Schema unverändert bei **Version 1**). GUI ist noch nicht an die DB
gebunden — das erfolgt ab Schritt 3.

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

1. **Schritt 3 — Sammlungen-CRUD:** Repository + Service + UI-Anbindung
   (Sammlungen anlegen/umbenennen/löschen/sortieren; `CollectionPanel` an echte
   Daten binden).
2. **Schritt 4 — Kartenkatalog & intelligente Suche** (pokemontcg.io/CardTrader).
3. **Schritt 5 — Karten zu Sammlungen hinzufügen** (Variante/Sprache/Zustand/…).
4. **Schritt 6 — Preis-Engine + CardTrader-Provider + „Preise aktualisieren".**
5. **Schritt 7 — Preisverlauf & Diagramme.**
6. **Schritt 8 — Filter & Volltextsuche.**
7. **Schritt 9 — Statistiken.**
8. **Schritt 10 — Export (CSV/Excel/JSON/PDF).**
9. **Schritt 11 — Webcam-Scanner (OCR/Bildvergleich).**

---

## Bekannte Bugs

- Keine funktionalen Bugs.
- Windows-Konsole zeigt Sonderzeichen je nach Codepage als `�`; Logdatei ist
  korrektes UTF-8 (rein kosmetisch).
- Offscreen-Rendering (nur für Test-Screenshots) zeigt Text als Kästchen, weil
  keine System-Schrift geladen wird — auf echtem Bildschirm normal. Kein Bug.
- CardTrader: `/blueprints/export?expansion_id=` liefert oft „Data is not
  ready" → Live-Endpunkt `/blueprints?expansion_id=` verwenden.

---

## Nächster Entwicklungsschritt

**Schritt 3 — Sammlungen-CRUD.** Repository (`app/database/`), Service
(`app/services/`) und Anbindung des `CollectionPanel` an echte Daten:
Sammlungen anlegen, umbenennen, löschen, sortieren; Auswahl lädt die zugehörige
Kartenliste (zunächst leer). Danach kurze Zusammenfassung und Warten auf
Freigabe.
