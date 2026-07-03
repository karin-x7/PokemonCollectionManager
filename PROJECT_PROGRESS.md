# Projektfortschritt — Pokémon Collection Manager

> Synchronisationsdatei zwischen mehreren PCs. Enthält jederzeit den aktuellen
> Entwicklungsstand. Wird nach **jedem** Entwicklungsschritt aktualisiert.

**Letzter Schritt:** Schritt 3 — Sammlungen-CRUD
**Datum:** 2026-07-03
**Version:** 0.1.0
**TestStatus:** ✅ 55 Tests grün (`pytest`)

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
- ✅ **Sammlungen-CRUD (echt, persistent):** Anlegen, Umbenennen, Löschen
  (mit Bestätigung, kaskadiert auf Karten), Umsortieren per Drag & Drop.
  `CollectionPanel` ist an echte Datenbankdaten gebunden.
- ✅ Bootstrap + CLI-Einstiegspunkt (`--check` für Headless-Health-Check).
- ✅ **Desktop-/Startmenü-Verknüpfung** zum Starten ohne Terminal
  (`pythonw.exe -m app.main`, kein Konsolenfenster).
- ✅ Test-Suite (Datenbank, Modelle, Repository, Service, GUI-Smoke- und
  GUI-Wiring-Tests headless via `offscreen`).
- ✅ Dokumentation: `README.md`, `CHANGELOG.md`, dieses Dokument.

---

## Heute umgesetzt (Schritt 3 — Sammlungen-CRUD)

- **Repository** (`app/database/repositories/collection_repository.py`):
  reine SQL-Zugriffsschicht (`list_all`, `get`, `create`, `rename`, `delete`,
  `reorder`) — keine Validierung, nur Datenzugriff. Duplikate werden als
  `sqlite3.IntegrityError` (UNIQUE-Constraint) durchgereicht.
- **Service** (`app/services/collection_service.py`): Validierung (Name
  trimmen, nicht leer, max. 100 Zeichen), übersetzt SQL-Fehler in typisierte,
  deutschsprachige Exceptions (`app/services/exceptions.py`:
  `ValidationError`, `DuplicateCollectionError`, `CollectionNotFoundError`).
  Dies ist die **einzige** Schicht, die die GUI für Sammlungs-Operationen
  aufrufen darf.
- **`CollectionPanel`** überarbeitet: zeigt echte `Collection`-Objekte,
  Kontextmenü (Umbenennen/Löschen), Doppelklick zum Umbenennen,
  Löschbestätigung, Drag-&-Drop-Umsortierung. Bleibt eine reine
  Präsentations-Shell — Dialoge sind Interaktions-, keine Business-Logik;
  echte Validierung/Persistenz läuft ausschließlich über den Service.
- **`CollectionController`** (`app/ui/controllers/collection_controller.py`):
  einzige Klebeschicht zwischen Panel-Signalen und Service. Fängt
  `ServiceError` ab und zeigt sie als Fehlermeldung im Panel; nach
  erfolgreichem Erstellen wird die neue Sammlung automatisch ausgewählt.
- **`MainWindow`** baut Repository → Service → Controller auf und verdrahtet
  `collection_controller.selection_changed`; erzeugt bei Bedarf automatisch
  eine In-Memory-Datenbank (Test-/Demo-Komfort), schließt sie beim Schließen
  des Fensters, falls selbst erzeugt.
- **Desktop-/Startmenü-Verknüpfung** (`pythonw.exe -m app.main`, kein
  Konsolenfenster) für den Start ohne Terminal.
- **Bugfix während der Testphase:** Ein Test emittierte das `rename_requested`-
  bzw. `delete_requested`-Signal (`Signal(int, str)` / `Signal(int)`) mit
  `None` als ID, weil neu erstellte Sammlungen bis dahin nicht automatisch
  ausgewählt wurden. PySide6/Shiboken wirft dabei keinen normalen Python-
  Fehler, sondern hängt den Prozess auf ("Cannot copy-convert NoneType to
  C++"). Behoben durch echte UX-Verbesserung: `CollectionController._on_create`
  wählt die neu erstellte Sammlung jetzt automatisch aus
  (`CollectionPanel.select_collection`). In der echten Oberfläche konnte der
  Fehler nie auftreten (Kontextmenü/Doppelklick liefern immer ein echtes
  Element), betraf also nur die Testroutine — die Korrektur behebt aber
  zugleich eine echte Lücke: neu angelegte Sammlungen waren vorher nicht
  automatisch ausgewählt.

---

## Dateien geändert / neu angelegt (Schritt 3)

**Neu:**
- `app/database/repositories/{__init__,collection_repository}.py`
- `app/services/{collection_service,exceptions}.py`
- `app/ui/controllers/{__init__,collection_controller}.py`
- `tests/{test_collection_repository,test_collection_service,test_collection_panel,test_collection_controller}.py`

**Geändert:**
- `app/ui/widgets/collection_panel.py` (echte Daten statt Platzhalter,
  Dialoge, Kontextmenü, Drag & Drop, `select_collection`)
- `app/ui/main_window.py` (Repository/Service/Controller-Verdrahtung,
  In-Memory-DB-Fallback, `closeEvent`)
- `app/services/__init__.py` (Re-Exports)

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

## Neue Klassen (Schritt 3)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `CollectionRepository` | `database.repositories.collection_repository` | SQL-CRUD für Sammlungen |
| `CollectionService` | `services.collection_service` | Validierung + Orchestrierung |
| `ServiceError`, `ValidationError`, `DuplicateCollectionError`, `CollectionNotFoundError` | `services.exceptions` | Typisierte, deutschsprachige Fehler |
| `CollectionController` | `ui.controllers.collection_controller` | Verdrahtet Panel ↔ Service |

---

## Datenbankänderungen

Keine Schemaänderung (weiterhin **Version 1**). GUI ist jetzt für Sammlungen
an die echte Datenbank gebunden (Karten folgen in Schritt 5).

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

1. **Schritt 4 — Kartenkatalog & intelligente Suche** (pokemontcg.io/CardTrader).
2. **Schritt 5 — Karten zu Sammlungen hinzufügen** (Variante/Sprache/Zustand/…;
   `CardListPanel` an echte Daten binden).
3. **Schritt 6 — Preis-Engine + CardTrader-Provider + „Preise aktualisieren".**
4. **Schritt 7 — Preisverlauf & Diagramme.**
5. **Schritt 8 — Filter & Volltextsuche.**
6. **Schritt 9 — Statistiken.**
7. **Schritt 10 — Export (CSV/Excel/JSON/PDF).**
8. **Schritt 11 — Webcam-Scanner (OCR/Bildvergleich).**

---

## Bekannte Bugs

- Keine funktionalen Bugs.
- Windows-Konsole zeigt Sonderzeichen je nach Codepage als `�`; Logdatei ist
  korrektes UTF-8 (rein kosmetisch).
- Offscreen-Rendering (nur für Test-Screenshots) zeigt Text als Kästchen, weil
  keine System-Schrift geladen wird — auf echtem Bildschirm normal. Kein Bug.
- CardTrader: `/blueprints/export?expansion_id=` liefert oft „Data is not
  ready" → Live-Endpunkt `/blueprints?expansion_id=` verwenden.
- Behoben während Schritt 3: Signale mit `int`-Parametern dürfen nie mit
  `None` emittiert werden (PySide6/Shiboken bricht dabei ohne normale
  Python-Exception ab, statt eines sauberen Fehlers) — siehe Hinweis oben bei
  „Heute umgesetzt (Schritt 3)". Betraf nur Testcode, nicht die echte UI.

---

## Nächster Entwicklungsschritt

**Schritt 4 — Kartenkatalog & intelligente Suche.** Anbindung an
pokemontcg.io (Katalog/Bilder) und CardTrader (Sets/Blueprints); tolerante
Suche über Name/Set/Nummer/Teilbegriffe mit Auswahlliste bei mehreren
Treffern. Danach kurze Zusammenfassung und Warten auf Freigabe.
