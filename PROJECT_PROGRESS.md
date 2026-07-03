# Projektfortschritt — Pokémon Collection Manager

> Synchronisationsdatei zwischen mehreren PCs. Enthält jederzeit den aktuellen
> Entwicklungsstand. Wird nach **jedem** Entwicklungsschritt aktualisiert.

**Letzter Schritt:** Schritt 7 — Cardmarket-Preis pro Karte, vollständig
nachgebessert und **live im laufenden Programm bestätigt**
**Datum:** 2026-07-03
**Version:** 0.1.0
**TestStatus:** ✅ 202 Tests grün (`pytest`) · ✅ **manueller Klick-Test im
laufenden Programm erfolgreich** — Karte „Xatu" (NM/Englisch) liefert
korrekt **200,00 €**, `PriceQuality.EXACT` (siehe „Nachbesserung" unten für
die komplette, fünfteilige Fehlersuche)

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
- ✅ **Kartenkatalog & Suche:** pokemontcg.io-Client (Kartendaten/Bilder/Sets)
  ist die alleinige Quelle für die Suche; CardTrader-Set-Client existiert
  bereits (für Schritt 7 — Preis-Engine), wird aber wegen abweichender
  Set-Namen gegenüber pokemontcg.io **nicht** für die Suche verwendet
  (Details unten). Toolbar-Suche ist an eine tolerante Such-Service-Schicht
  angebunden (Name/Set/Nummer/Teilbegriffe, Tippfehler-tolerant, Reprints
  wie „Base“ vs. „Base Set 2“ werden über die eindeutige Set-ID
  unterschieden); Treffer erscheinen in einem Anzeige-Dialog.
- ✅ **Karten-CRUD (echt, persistent):** Aus einem Katalog-Suchtreffer heraus
  mit Variante/Sprache/Zustand/Menge/Notizen zu einer Sammlung hinzufügen;
  Bearbeiten (Doppelklick/Kontextmenü) und Löschen (mit Bestätigung).
  `CardListPanel`/`CardDetailPanel` sind an echte Datenbankdaten gebunden.
- ✅ **Kartenbild & Reverse-Holo-Overlay:** Beim Hinzufügen wird das
  Katalog-Artwork automatisch heruntergeladen und lokal gecacht
  (`config.PHOTOS_DIR`); `CardDetailPanel` zeigt es an. Reverse-Holo-Karten
  bekommen einen gemalten, halbtransparenten Regenbogen-Overlay (wie bei
  physischen Reverse-Holo-Karten/Cardmarket) — pokemontcg.io liefert nur ein
  Bild pro Karte, die Variante wird rein optisch in der eigenen UI markiert.
- ✅ Bootstrap + CLI-Einstiegspunkt (`--check` für Headless-Health-Check).
- ✅ **Desktop-/Startmenü-Verknüpfung** zum Starten ohne Terminal
  (`pythonw.exe -m app.main`, kein Konsolenfenster).
- ✅ Test-Suite (Datenbank, Modelle, Repository, Service, GUI-Smoke- und
  GUI-Wiring-Tests headless via `offscreen`).
- ✅ **Cardmarket-Preis pro Karte:** Knopf in den Kartendetails öffnet die
  Cardmarket-Produktseite der Karte im normalen Standardbrowser des Nutzers
  (`webbrowser.open`, keine Fernsteuerung) und liest die bereits geladene
  Seite per Windows UI Automation aus (wie ein Screenreader — kein DOM-/
  Netzwerkzugriff); Angebote werden nach Zustand/Sprache gegen die eigene
  Karte gematcht (Fallback-Leiter EXACT → ESTIMATED_FROM_CONDITION →
  ESTIMATED_FROM_LANGUAGE → AVERAGE → NO_PRICE), Ergebnis + Preisverlauf-
  Eintrag werden persistiert. **Bewusst kein Batch-/Sammel-Lauf** — pro
  Klick genau eine Karte (Details unten).
- ✅ Dokumentation: `README.md`, `CHANGELOG.md`, dieses Dokument.

---

## ⚠️ Korrektur zum folgenden Abschnitt: Smoke-Test-Ergebnis war falsch

Der Preis **78,90 €** unten stellte sich später als **falsch** heraus (echter
Preis: 200,00 €) — Ursache und Behebung im Abschnitt „Nachbesserung: Fenster-/
Tab-Kontamination" direkt darunter. Abschnitt bleibt unten stehen, um die
Fehlersuche nachvollziehbar zu dokumentieren.

## ❌ (korrigiert) Smoke-Test-Ergebnis (PC-Wechsel, 2026-07-03, fortgesetzt)

Der im Übergabe-Hinweis geforderte manuelle Smoke-Test wurde auf der Ziel-
maschine nachgeholt (nicht über Klicks in der GUI, da kein GUI-Automatisierungs-
zugriff verfügbar war, sondern direkt über `PriceService.update_price_for_card`
gegen die echte `data/collection.db` — exakt derselbe Code-Pfad, den der
Button auslöst; die eigentliche Risikofläche, die echte `pywinauto`-
Fensterauslese gegen ein echtes, gerade geöffnetes Browserfenster, wurde damit
vollständig real durchlaufen):

1. **Vorab-Rebuild nötig:** Das mitkopierte `.venv` verwies auf den Python-
   Pfad des Ursprungs-PCs (`pyvenv.cfg` → nicht existierender Pfad) und
   schlug fehl. Neu erstellt mit `py -3.13 -m venv .venv` + Reinstallation
   aus `requirements-dev.txt`. Reiner Build-Artefakt-Konflikt, kein Code-
   Problem — `.venv` ist git-ignoriert und war nie Teil der eigentlichen
   Quelltext-Übertragung.
2. **Testsuite:** 184/184 Tests grün nach dem Rebuild.
3. **Karte „Xatu" (ID 2, `Testbinder`):** `cardmarket_url` war wie erwartet
   `None`. Aufruf hat sie live über `PokemonTcgClient.get_card_by_id`
   nachgezogen (Self-Healing-Backfill ✅), einen echten Standardbrowser-Tab
   geöffnet, über `pywinauto` ausgelesen und automatisch wieder geschlossen
   (kein Warn-Log zum Schließen). Ergebnis: **78,90 €**,
   `PriceQuality.ESTIMATED_FROM_LANGUAGE`, Rationale „Geschätzt aus
   unbekannter Sprache statt English, gleicher Zustand (Near Mint)."; Karte
   *und* `price_history` korrekt aktualisiert. Plausibilitätscheck: liegt
   nahe an pokemontcg.io's unabhängigem `avg1`-Aggregat (74,99 €) für
   dieselbe Karte — spricht für echte, sinnvolle Live-Daten statt einer
   Fehlparsung.
   *Nebenbefund (kein Bug):* Die von pokemontcg.io gelieferte
   `cardmarket.url` zeigt auf `prices.pokemontcg.io/cardmarket/<id>`, nicht
   direkt auf `cardmarket.com` — verifiziert als sauberer HTTP-302-Redirect
   (mit `utm_*`-Tracking-Parametern) zur echten Cardmarket-Produktseite;
   verhält sich in einem echten Browser identisch zu einem direkten Link.
4. **Fehlerfall:** Temporäre Karte ganz ohne `external_card_id`/
   `cardmarket_url` angelegt (in `Testbinder`, danach sofort wieder
   gelöscht) → sauber `PriceQuality.NO_PRICE` mit Rationale „Keine
   Cardmarket-Zuordnung für diese Karte bekannt.", **kein Absturz**.
   Datenbank ist wieder im ursprünglichen Zustand (nur „Xatu").

**Ergebnis: Schritt 7 vollständig verifiziert, keine offenen Punkte.**

**Weiterhin kein Git-Commit vorgenommen** (Standard-Konvention dieses
Projekts: nur auf ausdrückliche Nutzeranfrage). `git` lief auf dieser
Maschine ohne `safe.directory`-Zusatz problemlos.

---

## Nachbesserung: Fenster-/Tab-Kontamination bei der Preis-Auslese (2026-07-03)

**Auslöser:** Der Nutzer prüfte den obigen 78,90-€-Treffer manuell auf
Cardmarket nach und stellte fest: Der echte Preis für NM+Englisch ist
**200,00 €**. Das deckte einen echten, ernsten Bug im Kern der Schritt-7-
Auslese auf — hier die vollständige Fehlersuche und Behebung.

### Bug 1 — Kreuzkontamination zwischen Browser-Tabs

`window.descendants()` auf dem per Titel gefundenen Browserfenster liest
**den gesamten Accessibility-Baum**, nicht nur den sichtbaren, aktiven Tab —
ein mehrfach genutztes Browserfenster hält den Inhalt aller offenen Tabs
(auch im Hintergrund) im selben Baum. Bei mehreren gleichzeitig offenen
„Xatu"-Tabs (Reste aus Testläufen) wurden Texte aus völlig fremden Tabs
(YouTube, eBay, ELSTER, WhatsApp) versehentlich mitgelesen und als Angebot
fehlinterpretiert.
**Behoben:** `descendant.is_visible()`-Filter beim Baum-Durchlauf — nur der
tatsächlich sichtbare (= aktive) Tab liefert Text.

### Bug 2 — Falsches Fenster durch bloße Titelsuche

Selbst mit Bug 1 behoben: `Desktop(backend="uia").windows()` durchsucht
**alle** offenen Fenster nach dem Kartennamen im Titel — trifft dabei
genauso gut einen alten, längst offenen Cardmarket-Tab (oder sogar ein
Chrome-Fenster einer parallel laufenden manuellen Prüfung) wie den gerade
neu geöffneten. Live nachgewiesen: Ein Testlauf griff dadurch einen alten,
unbeteiligten Chrome-Tab statt des neuen Firefox-Tabs.
**Behoben:** Nur noch das **tatsächliche Vordergrundfenster**
(`win32gui.GetForegroundWindow()`) wird geprüft, wiederholt abgefragt bis
Titel **und** Kartenname passen — ein alter Hintergrund-Tab kann so
grundsätzlich nicht mehr getroffen werden. Falls das Fenster nicht rechtzeitig
in den Vordergrund kommt, schlägt die Auslese jetzt **ehrlich mit Fehlermeldung
fehl**, statt einen plausibel aussehenden, aber falschen Preis zu liefern.

### Bug-Fund 3 (kein Bug, echte Marktdaten) — URL-Parameter-IDs falsch geraten

Beim Nachbau des vom Nutzer entdeckten URL-Filter-Ansatzes
(`?language=X&minCondition=Y`) wurde zunächst geraten (`language=2`
= Deutsch) — live per DOM-Auslese widerlegt: Cardmarkets IDs sind **nicht
durchlaufend** (Englisch=1, Französisch=2, **Deutsch=3**, Spanisch=4,
Italienisch=5, Portugiesisch=8; Zustand dagegen sauber 1–7 Mint…Poor).
Korrekte Werte direkt aus dem Filterformular des DOM ausgelesen, nicht
geraten.

### Architektur-Umbau: Preis-Leiter nutzt jetzt Cardmarkets eigene Filter

Statt einer einzigen, ungefilterten Seite pro Preisabruf wird jetzt **pro
Leiter-Stufe** eine passend gefilterte Cardmarket-URL aufgerufen
(`build_filtered_url` in `app/pricing/browser_price_reader.py`):

1. Sprache der Karte gefiltert (falls Cardmarket das unterstützt — Englisch,
   Französisch, Deutsch, Spanisch, Italienisch, Portugiesisch; Japanisch/
   Koreanisch/Chinesisch sind bei Cardmarket **eigene Produkte**, kein
   Sprachfilter auf derselben Seite) → exakter oder nächstbester Zustand.
2. Bei keinem Treffer: Zustand gefiltert (`minCondition`), beliebige Sprache.
3. Bei weiterhin keinem Treffer: komplett ungefiltert → Durchschnitt.

Vorteil: deutlich weniger/kürzerer Seiteninhalt pro Abruf (weniger
Fehlerquelle), und die Sprache muss für Stufe 1 nicht mehr zuverlässig aus
dem Flaggen-Icon erkannt werden (der Server garantiert sie bereits).
`app/services/price_service.py` entsprechend umgebaut (`_determine_price`
statt der alten `_select_price`, die nur einmal ausgelesene Rohdaten
client-seitig filterte).

### Architektur-Entscheidung: Immer Chrome statt Standardbrowser

Auf ausdrücklichen Nutzerwunsch öffnet die Preis-Auslese jetzt **immer
gezielt Google Chrome** (`app/pricing/browser_price_reader.py:_open_in_chrome`,
per `subprocess.Popen([chrome_pfad, url])` — Pfad über die Windows-Registry
`App Paths\chrome.exe` ermittelt, mit Fallback auf den Standard-Installationspfad),
**unabhängig vom als Standardbrowser eingestellten Programm** (bei diesem
Nutzer aktuell Firefox). Grund: Firefox-Verhalten hatte die obige Bug-2-Suche
erschwert; mit einem einzigen, bekannten Ziel-Browser kann die
Fenstersuche zusätzlich verlangen, dass „chrome" im Fenstertitel vorkommt
(zweite, günstige Absicherung gegen Fenster-Verwechslung).

### Drei weitere Bugs, gefunden über echte Klicks im laufenden Programm

Der obige Umbau allein reichte nicht — drei weitere, unabhängige Bugs kamen
erst beim tatsächlichen Klicken auf den echten Knopf zum Vorschein (jeweils
vom Nutzer gemeldet und live nachgestellt):

**Bug 4 — SQLite-Objekt über Threads hinweg geteilt.** Erster Klick zeigte
„quasi gar nichts" — Ursache: `PriceLookupWorker` lief in einem eigenen
`QThread`, nutzte aber dieselbe `sqlite3`-Verbindung, die im Hauptthread
erstellt worden war. SQLite verbietet das explizit
(`SQLite objects created in a thread can only be used in that same thread`)
und die Exception verschwand spurlos, weil `pythonw.exe` keine Konsole hat.
Sichtbar gemacht durch breitere Exception-Behandlung in
`PriceLookupWorker.run()` (`except Exception` statt nur `ServiceError`, mit
`logger.exception(...)`) — seitdem landet **jede** Exception in der Logdatei,
nicht nur die erwarteten. Behoben durch Architekturwechsel:
`PriceController`/`MainWindow` übergeben jetzt eine **Factory**
(`OpenPriceService`), die *innerhalb* von `PriceLookupWorker.run()` eine
komplett neue `Database`-Verbindung zur selben Datei öffnet — nie eine aus
dem GUI-Thread wiederverwendet. Verbindung wird in `finally` wieder
geschlossen.

**Bug 5 — pokemontcg.io-Redirect verwirft alle Filter.** Erster korrekter
Klick lieferte danach 25,99 € statt ~200 €. Ursache: `card.cardmarket_url`
ist ein Tracking-Shortlink (`prices.pokemontcg.io/cardmarket/<id>`), dessen
Redirect-Ziel auf pokemontcg.io-Seite **fest einprogrammiert** ist — jeder an
den Shortlink angehängte `?language=`/`?minCondition=`-Parameter wird beim
302-Redirect **stillschweigend verworfen**, Chrome landet immer auf der
komplett ungefilterten Seite. Live per HTTP-Check bestätigt (`Location`-
Header enthält nur feste `utm_*`-Parameter). Behoben durch
`resolve_cardmarket_url()` (`app/pricing/browser_price_reader.py`): löst den
Redirect **einmal vorab per `requests`** auf (kein Browser nötig, reine
Redirect-Auflösung), bevor die Filter angehängt werden; die aufgelöste
echte URL wird zusätzlich zurück in die Karte gespeichert (Self-Healing,
analog zum bestehenden `cardmarket_url`-Backfill).

**Bug 6 — Paginierung/Lazy-Loading verdeckt teure Angebote.** Auch mit
korrekt aufgelöster URL kam zunächst 39,00 € (ein „Poor"-Preis) statt 200 €
(„Near Mint"). Ursache: Bei „nur Sprache gefiltert, alle Zustände" hat Xatu
so viele günstige Poor-Angebote, dass die viel teureren NM-Angebote weiter
unten in der (nach Preis sortierten) Liste liegen, als Cardmarkets Seite im
DOM tatsächlich rendert/exponiert — unsere Auslese sah nie mehr als die
günstigsten paar Zeilen. Behoben durch **kombinierten** Filter in Stufe 1:
Sprache **und** `minCondition` gemeinsam server-seitig anfragen (statt nur
Sprache), was die Ergebnisliste von vornherein kurz genug hält. Nur falls
diese Stufe komplett leer bleibt (keine Karte in dieser Sprache in
mindestens dem gesuchten Zustand vorhanden), gibt es eine zusätzliche,
zweite Anfrage mit reinem Sprachfilter für den „nächstschlechterer Zustand"-
Fall — akzeptiert das gleiche Paginierungsrisiko, aber nur in diesem
selteneren Pfad.

### ✅ Live im laufenden Programm bestätigt

Karte „Xatu" (NM, Englisch) in „Testbinder" ausgewählt, „Preis von
Cardmarket abrufen" geklickt: Chrome öffnet sich korrekt, Tab schließt sich
automatisch, Ergebnis **`quality=exact price=200.0`** — exakt der real
verifizierte Preis. Vom Nutzer bestätigt: „nun steht 200€ passt!"

### Testerweiterung

- 10 neue Tests: `build_filtered_url`/`supports_language_filter`/
  `resolve_cardmarket_url` (`tests/test_browser_price_reader.py`),
  Preis-Leiter mit mehrstufigen, URL-abhängigen Fake-Antworten inkl.
  nicht-abbildbarer Sprache, Redirect-Auflösung + Self-Healing, Fallback auf
  schlechteren Zustand (`tests/test_price_service.py`),
  `PriceLookupWorker`-Datenbankschließung + breite Exception-Behandlung
  (`tests/test_price_lookup_worker.py`). Gesamt: **202 Tests grün**.
- `read_offers_for_card`/`_open_in_chrome` selbst bleiben bewusst
  **nicht automatisiert getestet** (echtes Browserfenster nötig) — das gilt
  unverändert seit Schritt 7. Alle sechs hier beschriebenen Bugs wurden
  ausschließlich durch echte, manuelle Klicks im laufenden Programm
  gefunden — automatisierte Tests allein hätten keinen davon entdeckt, da
  sie alle in der bewusst ungetesteten Integrationsschicht liegen.

---

## Heute umgesetzt (Schritt 7 — Cardmarket-Preis pro Karte)

**Ursprünglicher Plan verworfen:** Ein Playwright-gesteuerter Browser sollte
Cardmarket-Angebotsseiten automatisiert auslesen. Live getestet und
gescheitert: per Playwright gesteuertes Chrome (auch über das echte
installierte Chrome via `channel="chrome"`) blieb in drei Tests (bis zu
80+ Sekunden Wartezeit) zuverlässig auf Cloudflares „Nur einen Moment"-
Prüfseite hängen, während eine *interaktive* Browser-Sitzung in ~7 Sekunden
durchlief. Ursache: Playwright steuert den Browser über das Chrome
DevTools Protocol (CDP) — ein bekanntes Automatisierungssignal, das
Cloudflare erkennt, unabhängig vom verwendeten Browser-Binary. Es wurde
bewusst **nicht** versucht, das über Stealth-/Anti-Erkennungs-Tricks zu
umgehen — das wäre ein Umgehen von Bot-Schutz gewesen, keine legitime
Nutzung.

**Vereinbarte Alternative (nach Diskussion mit dem Nutzer):** kein
automatisierter Lauf über die Sammlung. Stattdessen pro Karte ein Knopf,
den der Nutzer selbst für **genau eine** Karte drückt:

1. Klick öffnet die Cardmarket-URL der Karte im **normalen** Standard-
   browser des Nutzers (`webbrowser.open`, keine Fernsteuerung, kein CDP —
   technisch nicht von einem Nutzer zu unterscheiden, der einen Link
   anklickt).
2. Das Programm liest den Bildschirminhalt des bereits geladenen Fensters
   über **Windows UI Automation** (`pywinauto`) aus — dieselbe Technik, die
   Screenreader nutzen; kein DOM-/Netzwerkzugriff, rein OS-seitiges Ablesen
   von ohnehin sichtbarem Text.
3. Das Programm schließt danach genau diesen einen Tab wieder.
4. Für die nächste Karte muss der Nutzer den Knopf erneut drücken — **kein**
   automatischer Lauf über mehrere Karten. Das ist die bewusst gezogene
   Grenze: eine menschliche Entscheidung pro Seitenaufruf, keine
   unbeaufsichtigte Schleife einer Software gegen eine Seite mit
   Bot-Schutz.

Der Großteil der bereits entworfenen Preislogik (Modelle, Matching-Leiter,
Persistenz) blieb beim Wechsel von Playwright auf Fensterauslese
unverändert gültig — nur die *Beschaffungs*-Schicht wurde ausgetauscht.

**Neue Bausteine:**
- **`CatalogCard.cardmarket_url`** (`app/catalog/models.py`) +
  **`PokemonTcgClient.get_card_by_id`** (`app/catalog/pokemontcg_client.py`):
  pokemontcg.io liefert pro Karte ein `cardmarket.url`-Feld, das auf die
  echte Cardmarket-Produktseite umleitet (live verifiziert) — löst das
  Problem, die richtige Cardmarket-Seite für eine beliebige eigene Karte zu
  finden, ohne eine eigene Cardmarket-Suche zu bauen.
- **`CardmarketOffer`** (`app/pricing/models.py`, neu): DTO für ein
  einzelnes Verkaufsangebot (Verkäufer, Zustand, Sprache, Preis, Kommentar).
- **`browser_price_reader.py`** (`app/pricing/`, neu): `read_offers_for_card`
  öffnet die Seite, pollt per `pywinauto.Desktop(backend="uia")` auf ein
  Fenster mit dem Kartennamen im Titel, sammelt die Text-Deszendenten,
  parst sie über die reine Funktion `_parse_offer_lines` (Zustands-Codes
  `MT/NM/EX/GD/LP/PL/PO` inkl. `MT`→`Condition.MINT`-Sonderfall,
  Sprachnamen gegen `Language.label`, deutsches Preisformat per Regex) und
  schließt den Tab per `Strg+W` — auch im Fehlerfall (`finally`), damit nie
  ein Tab hängen bleibt. Live an Cardmarkets echter Seitenstruktur
  verifiziert (Claude-in-Chrome, `get_page_text`/`find`): Zustands-Badges
  sind Klartext, Sprache nur ein Flaggen-Icon mit `title`-Attribut wie
  „Italian" — beides landet als eigener Text-Knoten in der Accessibility-
  Baumreihenfolge.
- **`PriceRepository`** (`app/database/repositories/price_repository.py`,
  neu) + **`CardRepository.update_price`/`update_cardmarket_url`**
  (Erweiterung): Persistenz für `price_history` bzw. den aktuellen
  Karten-Preis.
- **`PriceService`** (`app/services/price_service.py`, neu):
  `update_price_for_card(card_id)` — lädt die Karte, holt bei fehlender
  `cardmarket_url` (Karten von vor Schritt 7) die URL über
  `PokemonTcgClient.get_card_by_id` nach und speichert sie zurück
  (Self-Healing); ruft `read_offers_for_card` auf und wendet die bereits
  seit Schritt 1 definierte `PriceQuality`-Fallback-Leiter an (EXACT →
  ESTIMATED_FROM_CONDITION → ESTIMATED_FROM_LANGUAGE → AVERAGE →
  NO_PRICE); fängt `BrowserPriceReaderError` ab und liefert `NO_PRICE` mit
  Rationale statt abzustürzen.
- **`PriceLookupWorker`** (`app/ui/workers/price_lookup_worker.py`, neu):
  `QThread`, führt **genau eine** `PriceService`-Anfrage pro Start aus,
  damit die GUI während der einige Sekunden dauernden Fensteraktion nicht
  einfriert. Bewusst kein Batch-Parameter.
- **`PriceController`** (`app/ui/controllers/price_controller.py`, neu):
  verdrahtet den Kartendetails-Knopf mit dem Worker; verhindert einen
  zweiten Start während ein Lookup noch läuft; deaktiviert den Knopf
  währenddessen; ruft nach Abschluss `CardController.refresh()` auf (nutzt
  die bereits in Schritt 5 gebaute Resync-Logik, statt selbst am privaten
  Panel-Zustand zu hantieren — bleibt korrekt, auch wenn der Nutzer
  zwischenzeitlich eine andere Karte auswählt).
- **`CardDetailPanel`**: Button „Auf Cardmarket öffnen" (bisher
  Platzhalter) umbenannt zu „Preis von Cardmarket abrufen" und mit echtem
  Signal `price_lookup_requested(int)` verdrahtet; nur aktiv, solange eine
  Karte angezeigt wird und kein Lookup läuft.
- Toolbar-Aktion „Preise aktualisieren" bleibt bewusst der bestehende
  Platzhalter (jetzt mit klarstellender Meldung: Preise werden pro Karte
  einzeln abgerufen, kein Sammel-Lauf) — ein Bulk-Lauf über die ganze
  Sammlung wäre genau die unbeaufsichtigte Automatisierung, die vermieden
  werden soll.

**Testphilosophie:** `_parse_offer_lines` (reine Funktion, keine Fenster-/
Browserabhängigkeit) ist vollständig unit-getestet mit realen, live
beobachteten Token-Sequenzen. `read_offers_for_card` selbst (öffnet ein
echtes Fenster) bleibt bewusst dünn und wird **nicht** automatisiert
getestet — das wäre nicht deterministisch reproduzierbar und würde
denselben menschlichen Auslöser bräuchen, den das Feature gerade
respektiert. Verifikation dafür ist der manuelle Smoke-Test (siehe
Übergabe-Hinweis oben).

- 39 neue Tests (Modelle/Client-Erweiterung, `_parse_offer_lines`,
  Repository, Service inkl. aller fünf Preisqualitäts-Stufen, Worker,
  Controller-Wiring). Gesamt: 184 Tests grün.

---

## Heute umgesetzt (Schritt 6 — Kartenbild-Download & Reverse-Holo-Overlay)

Vom Nutzer vorgeschlagen: Beim Hinzufügen einer Karte soll automatisch das
Artwork geladen werden (Sprache egal, nur Übersicht), und Holo/Non-Holo/
Reverse Holo sollen optisch unterscheidbar sein. Bestätigt: Reverse Holo ist
auch bei Cardmarket nur ein „Ölfilm“-Overlay-Effekt auf demselben Artwork,
keine eigene Bilddatei.

- **`ensure_card_image`** (`app/catalog/card_image_cache.py`, neu): lädt
  `CatalogCard.image_large_url` herunter und speichert das Bild unter
  `config.PHOTOS_DIR`. Dateiname stabil aus der `external_id` abgeleitet
  (z. B. `ecard3-H32.png`) — mehrere eigene Kopien derselben Karte (auch mit
  unterschiedlicher Variante) teilen sich dieselbe Datei, kein Mehrfach-
  Download bei erneutem Hinzufügen. Fehlende URL oder Netzwerkfehler/
  Timeout (10 s) → `None` statt Exception, verhindert nie das Anlegen der
  Karte selbst — gleiche Toleranz-Philosophie wie die Suche (Schritt 4).
  `photos_dir`/`session`-Parameter für Testbarkeit (Muster wie
  `Database(db_path)`).
- **`CardService`** bekommt einen injizierbaren `image_downloader`-Parameter
  (Standard `ensure_card_image`); `add_card_from_catalog` setzt
  `Card.photo_path` daraus. Bestehende Tests (`test_card_service.py`,
  `test_card_controller.py`) mit einem No-Op-Downloader ausgestattet, damit
  die Suite weiterhin ohne echte Netzwerk-/Dateisystemzugriffe läuft.
- **`CardArtworkView`** (`app/ui/widgets/card_artwork_view.py`, neu): malt
  das geladene `QPixmap` (zentriert, skaliert) oder den „Kein Foto“-Text;
  bei Reverse Holo zusätzlich ein halbtransparenter, diagonaler
  `QLinearGradient` als Overlay. Reine Qt-Bordmittel — kein Pillow, keine
  neue Abhängigkeit, da PySide6 PNG/JPEG bereits nativ über `QPixmap(pfad)`
  lädt. Respektiert das QSS-`#Panel`-Styling weiterhin über
  `style().drawPrimitive(...)`, da ein eigenes `paintEvent` das sonst
  umgeht.
- **`CardDetailPanel`** ersetzt den bisherigen statischen Platzhalter durch
  `CardArtworkView`; `show_card`/`show_empty` delegieren entsprechend.
- Manuell im laufenden Programm verifiziert: Karte über Suche mit Variante
  „Reverse Holo“ hinzugefügt → Artwork lädt, Regenbogen-Overlay sichtbar;
  per Bearbeiten auf „Holo“ geändert → Overlay verschwindet, Artwork bleibt;
  Bilddatei tatsächlich unter `data/photos/` abgelegt.
- 16 neue Tests (Download/Cache gemockt, Service-Wiring, Artwork-View-
  Zustand, Panel-Delegation). Gesamt: 145 Tests grün.

---

## Heute umgesetzt (Schritt 5 — Karten zu Sammlungen hinzufügen)

- **`CardRepository`** (`app/database/repositories/card_repository.py`):
  reine SQL-Zugriffsschicht (`list_by_collection`, `get`, `create`,
  `update_details`, `delete`). `create` nimmt ein ganzes `Card`-Objekt
  (nicht einzelne Parameter wie bei `CollectionRepository.create`), weil
  eine Karte ~15 Felder hat.
- **`CardService`** (`app/services/card_service.py`): Mengen-Validierung
  (`>= 1`), `CardNotFoundError` (`app/services/exceptions.py`). Einzige
  Schicht, die die GUI für Karten-Operationen aufrufen darf.
- **`CardDetailsValues`** (`app/models/card.py`): geteiltes DTO
  (Variante/Sprache/Zustand/Menge/Notizen) zwischen UI-Dialog und Service —
  gleiche Werteklasse für Anlegen und Bearbeiten.
- **`CardDetailsDialog`** (`app/ui/dialogs/card_details_dialog.py`):
  Formular-Dialog; ohne `initial` Anlege-Modus (Standardwerte), mit
  `initial` Bearbeiten-Modus (vorbefüllt).
- **`CatalogSearchResultsDialog`** (Schritt 4) erweitert: „Hinzufügen“-Button
  (nur aktiv bei Zeilenauswahl), neues `add_requested`-Signal.
  `CatalogSearchController` leitet das über ein neues `card_add_requested`-
  Signal weiter, ohne selbst Business-Logik zu übernehmen.
- **`CardListPanel`** von Platzhalter auf echte Daten umgebaut (Muster wie
  `CollectionPanel` in Schritt 3): `set_cards`, Auswahl, Kontextmenü
  (Bearbeiten/Löschen), Doppelklick zum Bearbeiten, Löschbestätigung,
  `prompt_add_from_catalog` für die Übernahme aus der Suche. Bleibt reine
  Präsentations-Shell — alle Dialoge sind Interaktion, keine Persistenz.
- **`CardDetailPanel`** ergänzt um `show_card(card)` für echte Anzeige.
- **`CardController`** (`app/ui/controllers/card_controller.py`): verdrahtet
  beide Panels mit dem Service; verfolgt die aktuell gewählte Sammlung
  (gesetzt von `MainWindow` bei Sammlungs-Auswahl).
- **Zwei echte Bugs beim manuellen Test gefunden und behoben** (Details im
  Abschnitt „Bekannte Bugs“ unten):
  1. `Variant` (ein `str`-Enum) wurde durch Qt's Combobox-Item-Data-
     Marshalling beim Auslesen stillschweigend zu einem reinen `str`
     — das ließ das Speichern einer Karte abstürzen
     (`AttributeError: 'str' object has no attribute 'value'`). Die
     automatisierten Tests bemerkten es zunächst nicht, weil der
     Gleichheitsvergleich (`==`) bei einem `str`-Enum auch mit einem reinen
     `str` wahr ist — behoben durch `Variant.from_value(...)` beim Auslesen
     und durch `type(...) is Variant`-Assertions in den Tests.
  2. Nach dem Bearbeiten einer Karte, die an derselben Tabellenposition
     blieb (z. B. einzige Karte in der Sammlung), zeigte das Kartendetails-
     Panel weiterhin die alten Werte, weil Qts `currentCellChanged` nicht
     feuert, wenn sich der Zeilenindex nicht ändert — behoben durch
     explizite Resynchronisierung in `CardController.refresh()`.
- Manuell im laufenden Programm verifiziert: Sammlung anlegen/auswählen,
  Karte über Suche hinzufügen (inkl. Variantenwahl), Bearbeiten (Menge
  ändern, Detail-Panel aktualisiert sich korrekt), Löschen (mit
  Bestätigung), „keine Sammlung ausgewählt“-Fehlermeldung, Persistenz über
  einen App-Neustart hinweg — alle Fälle ohne Absturz.

---

## Heute umgesetzt (Schritt 4 — Kartenkatalog & intelligente Suche)

- **`PokemonTcgClient`** (`app/catalog/pokemontcg_client.py`): read-only
  HTTP-Client für die pokemontcg.io-Katalog-API. `build_query()` ist eine
  reine, ohne HTTP testbare Funktion. Zwei Verhaltensweisen der echten API
  wurden live gemessen und fließen ins Design ein: (1) Leading-Wildcards
  (`*term*`) sind so langsam, dass sie teils in den Timeout laufen (>15 s) —
  es werden deshalb nur Trailing-Wildcards (`term*`, Präfix-Suche) verwendet;
  (2) eine zitierte Mehrwort-Phrase kombiniert mit Wildcard (`"a b"*`) liefert
  einen 400 Bad Request — Mehrwort-Begriffe werden deshalb als exakte Phrase
  ohne Wildcard gesendet.
- **`CardTraderClient`**-Erweiterung (`app/cardmarket/cardtrader_client.py`,
  bisher leeres Paket): `list_pokemon_expansions()` liest die Set-Liste.
  Live verifiziert: `/expansions` ignoriert den `game_id`-Query-Parameter
  serverseitig und liefert immer alle ~3700 Sets aller Spiele — Filterung auf
  Pokémon (`game_id=5`) passiert deshalb clientseitig, das Ergebnis wird pro
  Client-Instanz gecacht. **Wird von der Suche letztlich nicht verwendet**
  (siehe Reprint-Bugfix unten) — bleibt für Schritt 7 (Preis-Angebote)
  bestehen.
- **`CatalogSearchService`** (`app/services/catalog_search_service.py`):
  tolerante Suche über Name/Set/Nummer/Teilbegriffe. Erkennt einen
  Kartennummer-artigen Token per Regex; löst einen Set-Namen aus den
  restlichen Tokens gegen eine Set-Liste auf — entweder als Teilbegriff-
  Präfix („base“ → „Base“) oder per Tippfehler-Fuzzy-Match („skyrige“ →
  „Skyridge“); lockert die Anfrage schrittweise (erst Nummer, dann Set
  weglassen), wenn ein strukturierter Filter 0 Treffer liefert; degradiert
  bei einem Ausfall der Set-Auflösung auf reine Namenssuche statt die gesamte
  Suche fehlschlagen zu lassen.
  **Bugfix 1 während der Testphase (manueller Smoke-Test):** Die erste
  Fassung des Teilbegriff-Präfix-Matchings erkannte jeden Token, der zufällig
  ein *beliebiges* Set literal präfigiert, sofort als sicheren Set-Treffer.
  Damit wurde „charizard“ (Kartenname) fälschlich als Referenz auf ein
  reales, unabhängiges, längeres Set interpretiert und aus der Namenssuche
  entfernt. Behoben durch eine Mindest-Längenverhältnis-Schwelle (der
  getippte Teilbegriff muss mindestens die Hälfte der Länge des offiziellen
  Namens abdecken) — kurze Sets wie „Base“ bleiben ein sicherer Treffer,
  lange, zufällig ähnlich beginnende Namen fallen auf den (niedrigeren)
  Fuzzy-Wert zurück und zählen nicht mehr als Set-Treffer.
  **Bugfix 2, gemeldet vom Nutzer (Reprints/Wiederauflagen):** Die erste
  Fassung löste den Set-Namen gegen CardTraders Set-Liste auf und filterte
  pokemontcg.io dann nach `set.name`. Das brach live in zwei Punkten: (a)
  CardTrader und pokemontcg.io benennen dasselbe Set unterschiedlich
  (CardTrader „Base Set“ vs. pokemontcg.io „Base“ für den 1999er Original-Satz
  — pokemontcg.io reserviert „Base Set 2“ für die 2000er-Wiederauflage); (b)
  `set.name` ist bei pokemontcg.io tokenisiert — sowohl ein Wildcard-Präfix
  (`set.name:base*`) als auch eine zitierte Phrase (`set.name:"base"`) trafen
  live nachweislich **beide** Base-Set-Varianten gleichzeitig. Konkret führte
  die Suche nach „charizard base 4“ zum falschen Ergebnis „Charizard | Base
  Set 2 | 4“ statt der Originalkarte „Charizard | Base | 4“. Behoben durch
  zwei Änderungen zusammen: Set-Auflösung nutzt jetzt ausschließlich
  pokemontcg.io's eigene `/sets`-Liste (`PokemonTcgClient.list_sets()`, neu),
  und die Kartensuche filtert über die exakte, eindeutige `set.id` (z. B.
  `base1`) statt über `set.name`. `CatalogSearchService` braucht dafür keinen
  CardTrader-Client mehr (Konstruktor-Signatur vereinfacht). Im laufenden
  Programm erneut verifiziert: „charizard base 4“ liefert jetzt korrekt
  „Charizard | Base | 4 | Rare Holo“.
- **`CatalogSearchResultsDialog`** (`app/ui/dialogs/catalog_search_results_
  dialog.py`): reine Anzeige der Treffer (Name/Set/Nr./Rarität), „Keine
  Treffer“-Leerzustand. Kein Hinzufügen-Button — folgt Schritt 5, sobald
  Karten persistiert werden können.
- **`CatalogSearchController`** (`app/ui/controllers/catalog_search_
  controller.py`) verdrahtet die bereits vorhandene Toolbar-Suche
  (`MainWindow.search_submitted`) mit dem Service; leerer Suchbegriff zeigt
  einen Statusleisten-Hinweis statt eine Anfrage auszulösen; Backend-Fehler
  werden als Meldung angezeigt statt die Anwendung abstürzen zu lassen.
- **`CatalogSearchError`** (`app/services/exceptions.py`) für nicht
  erreichbare Katalog-Backends.
- Manuell im laufenden Programm verifiziert: Tippfehler im Set-Namen,
  Teilbegriff-Präfix, Kartennummer-Erkennung, leerer Suchbegriff, sowie der
  oben beschriebene Bugfix — alle Fälle ohne Absturz und mit den erwarteten
  Treffern.

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

## Dateien geändert / neu angelegt (Schritt 7)

**Neu:**
- `app/pricing/{models,browser_price_reader}.py`
- `app/database/repositories/price_repository.py`
- `app/services/price_service.py`
- `app/ui/workers/{__init__,price_lookup_worker}.py`
- `app/ui/controllers/price_controller.py`
- `tests/{test_browser_price_reader,test_price_repository,
  test_price_service,test_price_lookup_worker,test_price_controller}.py`

**Geändert:**
- `app/catalog/models.py` (`CatalogCard.cardmarket_url`)
- `app/catalog/pokemontcg_client.py` (`_parse_card` liest `cardmarket.url`;
  neu `get_card_by_id`)
- `app/services/card_service.py` (`cardmarket_url` beim Anlegen übernehmen)
- `app/database/repositories/card_repository.py` (`update_price`,
  `update_cardmarket_url`)
- `app/database/repositories/__init__.py`, `app/services/__init__.py`,
  `app/ui/controllers/__init__.py` (Re-Exports)
- `app/ui/widgets/card_detail_panel.py` (Button umbenannt, echtes
  `price_lookup_requested`-Signal, `set_price_lookup_running`)
- `app/ui/main_window.py` (`PriceService`/`PriceController`-Verdrahtung;
  Toolbar-Platzhaltertext präzisiert)
- `requirements.txt` (`pywinauto` statt des zwischenzeitlich getesteten,
  wieder verworfenen `playwright`-Eintrags)
- `tests/{test_pokemontcg_client,test_card_service}.py` (neue Tests /
  `cardmarket_url`-Fixture)

---

## Dateien geändert / neu angelegt (Schritt 6)

**Neu:**
- `app/catalog/card_image_cache.py`
- `app/ui/widgets/card_artwork_view.py`
- `tests/{test_card_image_cache,test_card_artwork_view,
  test_card_detail_panel}.py`

**Geändert:**
- `app/catalog/__init__.py` (`ensure_card_image`, `CatalogSet` Re-Export
  nachgetragen)
- `app/services/card_service.py` (`image_downloader`-Parameter,
  `photo_path` beim Anlegen)
- `app/ui/widgets/card_detail_panel.py` (`CardArtworkView` statt
  statischem Platzhalter)
- `tests/test_card_service.py` (neue Tests + Fixture mit No-Op-Downloader)
- `tests/test_card_controller.py` (Fixture mit No-Op-Downloader)

---

## Dateien geändert / neu angelegt (Schritt 5)

**Neu:**
- `app/database/repositories/card_repository.py`
- `app/services/card_service.py`
- `app/ui/dialogs/card_details_dialog.py`
- `app/ui/controllers/card_controller.py`
- `tests/{test_card_repository,test_card_service,test_card_details_dialog,
  test_card_panel,test_card_controller,test_catalog_search_results_dialog}.py`

**Geändert:**
- `app/models/card.py` (`CardDetailsValues`), `app/models/__init__.py`
- `app/database/repositories/__init__.py`, `app/services/__init__.py`,
  `app/ui/controllers/__init__.py` (Re-Exports)
- `app/services/exceptions.py` (`CardNotFoundError`)
- `app/ui/widgets/card_list_panel.py` (komplett von Platzhalter auf echte
  Daten umgebaut)
- `app/ui/widgets/card_detail_panel.py` (`show_card`)
- `app/ui/dialogs/catalog_search_results_dialog.py` (Hinzufügen-Button,
  `add_requested`)
- `app/ui/controllers/catalog_search_controller.py` (`card_add_requested`)
- `app/ui/main_window.py` (Card-Repository/Service/Controller-Verdrahtung;
  `collection_controller.selection_changed` → `card_controller.
  set_collection`; `catalog_search_controller.card_add_requested` →
  `card_controller.add_from_catalog`)
- `tests/test_catalog_search_controller.py` (Test für die
  `card_add_requested`-Weiterleitung)

---

## Dateien geändert / neu angelegt (Schritt 4)

**Neu:**
- `app/catalog/{__init__,models,pokemontcg_client}.py`
- `app/cardmarket/{models,cardtrader_client}.py`
- `app/services/catalog_search_service.py`
- `app/ui/dialogs/{__init__,catalog_search_results_dialog}.py`
- `app/ui/controllers/catalog_search_controller.py`
- `tests/{test_pokemontcg_client,test_cardtrader_client,
  test_catalog_search_service,test_catalog_search_controller}.py`

**Geändert:**
- `app/cardmarket/__init__.py` (Docstring: Set-Client wurde in Schritt 4
  gebaut, aber die Suche nutzt pokemontcg.io's eigene Set-Liste statt dessen —
  siehe Reprint-Bugfix; Preis-Angebote weiterhin Schritt 7; Re-Exports)
- `app/services/exceptions.py` (`CatalogSearchError`)
- `app/services/__init__.py`, `app/ui/controllers/__init__.py` (Re-Exports)
- `app/ui/main_window.py` (Toolbar-Suche an `CatalogSearchController`
  angebunden statt Platzhalter-Statusmeldung; instanziiert nur noch
  `PokemonTcgClient`, kein `CardTraderClient` mehr)

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

## Neue Klassen (Schritt 4)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `CatalogCard`, `CatalogSet` | `catalog.models` | DTOs: Katalog-Karte + Katalog-Set (pokemontcg.io) |
| `PokemonTcgClient`, `PokemonTcgClientError` | `catalog.pokemontcg_client` | Read-only Katalog-API-Client (Karten + Sets) |
| `CardTraderExpansion` | `cardmarket.models` | DTO: CardTrader-Set (aktuell ungenutzt, für Schritt 7) |
| `CardTraderClient`, `CardTraderClientError` | `cardmarket.cardtrader_client` | Read-only Set-Liste (CardTrader, für Schritt 7) |
| `CatalogSearchService`, `CatalogSearchError` | `services.catalog_search_service` / `services.exceptions` | Tolerante Suchlogik (nutzt nur `PokemonTcgClient`) |
| `CatalogSearchResultsDialog` | `ui.dialogs.catalog_search_results_dialog` | Anzeige der Suchtreffer |
| `CatalogSearchController` | `ui.controllers.catalog_search_controller` | Verdrahtet Toolbar-Suche ↔ Service |

## Neue Klassen (Schritt 5)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `CardDetailsValues` | `models.card` | DTO: Variante/Sprache/Zustand/Menge/Notizen |
| `CardRepository` | `database.repositories.card_repository` | SQL-CRUD für Karten |
| `CardService`, `CardNotFoundError` | `services.card_service` / `services.exceptions` | Validierung + Orchestrierung |
| `CardDetailsDialog` | `ui.dialogs.card_details_dialog` | Formular für Anlegen/Bearbeiten |
| `CardController` | `ui.controllers.card_controller` | Verdrahtet Karten-Panels ↔ Service |

## Neue Klassen (Schritt 6)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `ensure_card_image` | `catalog.card_image_cache` | Lädt/cached Kartenbilder lokal |
| `CardArtworkView` | `ui.widgets.card_artwork_view` | Zeigt Artwork + Reverse-Holo-Overlay |

## Neue Klassen (Schritt 7)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `CardmarketOffer` | `pricing.models` | DTO: ein einzelnes Cardmarket-Verkaufsangebot |
| `BrowserPriceReaderError`, `read_offers_for_card` | `pricing.browser_price_reader` | Öffnet die Cardmarket-Seite normal, liest sie per UI Automation aus, schließt den Tab |
| `PriceRepository` | `database.repositories.price_repository` | SQL-Zugriff auf `price_history` |
| `PriceService` | `services.price_service` | Self-Healing-URL-Backfill + Preis-Matching-Leiter + Persistenz |
| `PriceLookupWorker` | `ui.workers.price_lookup_worker` | Führt eine einzelne Preis-Abfrage im Hintergrund-Thread aus |
| `PriceController` | `ui.controllers.price_controller` | Verdrahtet den Kartendetails-Knopf ↔ `PriceService` |

---

## Datenbankänderungen

Keine Schemaänderung (weiterhin **Version 1**). GUI ist jetzt sowohl für
Sammlungen als auch für Karten an die echte Datenbank gebunden.

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

**Offene Mapping-Aufgaben für Schritt 7:**
- CardTrader-Zustandsskala (Mint · Near Mint · Slightly/Moderately Played ·
  Played · Heavily Played · Poor) → kanonische `Condition`-Skala.
- Sprachkürzel (`de`, `en`, …) → `Language`-Enum.
- Varianten (Holo/Reverse/1st Ed.) → CardTrader-Blueprints + `foil`-Property.

**Architektur-Entscheidung (Update 2026-07-03): Cardmarket-Zugriff via
gesteuertem Browser statt CardTrader als primäre Preisquelle.**

Hintergrund: CardTraders Verkäuferauswahl ist gegenüber Cardmarket deutlich
kleiner; der Nutzer will für seine (überschaubare) Sammlung genaue,
zustands-/sprachgenaue Cardmarket-Preise, nicht nur Aggregate, und nimmt das
AGB-Risiko für den rein privaten Gebrauch bewusst in Kauf.

Zwei Alternativen geprüft und verworfen:
- **[Cardmonitor/cardmarket-api](https://github.com/Cardmonitor/cardmarket-api)**
  (PHP-Wrapper um die *offizielle* Cardmarket-API) — nutzlos, solange
  Cardmarket keine neuen API-Anträge annimmt (siehe oben); löst das
  Zugangsproblem nicht.
- **tcggopro „CardMarket API TCG“** (bezahlter Drittanbieter, RapidAPI /
  [cardmarket-api.com](https://www.cardmarket-api.com/)) — legal (Anbieter
  trägt das Scraping-Risiko), aber liefert nur **Aggregatpreise** (günstigster
  Near-Mint pro Land, 7d/30d-Schnitt), keine Einzelangebote nach Zustand/
  Sprache. Deckt den Anwendungsfall nicht.

**Live-Test (2026-07-03) via Claude-in-Chrome-Erweiterung:** direkter
HTTP-Fetch auf eine Cardmarket-Produktseite → sofort `403 Forbidden`.
Über einen echten, gesteuerten Browser dagegen: Cloudflare-
Sicherheitsprüfung („Verifiziere...“) erschien, lief nach ein paar Sekunden
Warten **automatisch** durch (kein Captcha manuell gelöst), danach war die
echte Angebotsliste mit Einzelangeboten (Preis, Zustand NM/EX/GD/LP/MT,
Länderflagge/Sprache, Verkäufer, Kommentar) sichtbar — genau die
Granularität, die weder CardTrader noch die Aggregator-API liefern.

**Entscheidung des Nutzers:** Cardmarket wird die primäre Preisquelle, über
einen gesteuerten Browser (nicht rohe HTTP-Requests) — CardTrader bleibt
vermutlich als Fallback. Bewusst **kein** schnelles Bulk-Scraping: der
Nutzer möchte ein System, das sich Zeit lässt (z. B. nachts durchlaufen,
mit Pausen zwischen Anfragen), um Erkennungsmuster gar nicht erst
auszulösen — passt zur überschaubaren Sammlungsgröße.

**Umgesetzt als Schritt 7 (siehe Abschnitt „Heute umgesetzt (Schritt 7 —
Cardmarket-Preis pro Karte)" weiter oben) — abweichend vom hier
skizzierten Plan:** kein Playwright/CDP-gesteuerter Browser (live an
Cloudflares Bot-Erkennung gescheitert, siehe dort), kein nächtlicher
Bulk-Lauf mit Pausen. Stattdessen ein pro-Karte-Knopf: normaler
`webbrowser.open` + Windows-UI-Automation-Auslese des bereits geladenen
Fensters, ein Tab pro Klick, keine Schleife über mehrere Karten. Die
`PriceProvider`-Kette oben wird dadurch **ersetzt**: Cardmarket (per
Fensterauslese) ist jetzt die alleinige automatisierte Quelle;
CardTrader-Client bleibt im Code (`app/cardmarket/cardtrader_client.py`),
wird aber aktuell nirgends aufgerufen — Kandidat für Entfernung oder
späteren Fallback, falls sich das als nötig erweist.

---

## Offene Aufgaben (priorisiert)

1. **Schritt 8 — Preisverlauf & Diagramme.**
2. **Schritt 9 — Filter & Volltextsuche.**
3. **Schritt 10 — Statistiken.**
4. **Schritt 11 — Export (CSV/Excel/JSON/PDF).**
5. **Schritt 12 — Webcam-Scanner (OCR/Bildvergleich).**

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
- pokemontcg.io: Leading-Wildcard-Queries (`*term*`) sind sehr langsam bis
  timeout-anfällig (live gemessen) — der Client verwendet deshalb nur
  Trailing-Wildcards; siehe „Heute umgesetzt (Schritt 4)". Kein Bug, sondern
  eine Eigenschaft der externen API.
- pokemontcg.io: eine zitierte Mehrwort-Phrase kombiniert mit Wildcard
  (`"a b"*`) liefert einen 400 Bad Request — der Client sendet Mehrwort-
  Begriffe deshalb als exakte Phrase ohne Wildcard. Ebenfalls eine
  API-Eigenschaft, kein Bug im eigenen Code.
- Behoben während Schritt 4: Das Teilbegriff-Präfix-Matching gegen die
  Set-Liste erkannte ohne Mindest-Längenverhältnis auch kurze, generische
  Präfixe unabhängiger Sets fälschlich als sicheren Treffer — siehe Bugfix 1
  oben bei „Heute umgesetzt (Schritt 4)".
- Behoben während Schritt 4, vom Nutzer gemeldet: Reprints/Wiederauflagen
  (z. B. „Base“ vs. „Base Set 2“) konnten verwechselt werden, weil die Suche
  ursprünglich CardTraders Set-Vokabular auflöste und pokemontcg.io dann nach
  `set.name` filterte — beides war live nachweislich unzuverlässig (siehe
  Bugfix 2 oben). Behoben durch Set-Auflösung + Filterung ausschließlich über
  pokemontcg.io's eigene, exakte `set.id`.
- Behoben während Schritt 5: `Variant` (ein `str`-Enum) wurde durch Qt's
  Combobox-Item-Data-Marshalling beim Auslesen stillschweigend zu einem
  reinen `str` — ließ das Speichern einer Karte abstürzen; behoben in
  `CardDetailsDialog.get_values()` durch `Variant.from_value(...)`.
- Behoben während Schritt 5: Kartendetails-Panel aktualisierte sich nach dem
  Bearbeiten nicht, wenn die Zeile an derselben Tabellenposition blieb
  (Qts `currentCellChanged` feuert nur bei geändertem Zeilenindex); behoben
  durch explizite Resynchronisierung in `CardController.refresh()`.
- **Bekannte Einschränkung (kein Bugfix, entdeckt beim manuellen Test von
  Schritt 5):** Die tolerante Suche (Schritt 4) erkennt Varianten-/Rarität-
  Wörter wie „holo“ nicht als Teilbegriff und behandelt sie als Teil des
  Namensfelds — eine Suche nach „xatu skyridge holo“ liefert deshalb 0
  Treffer, während „xatu skyridge“ funktioniert. Nicht behoben, da außerhalb
  des Schritt-5-Umfangs (Karten-CRUD); Kandidat für eine spätere
  Verbesserung der Suchlogik.
- Schritt 7: sechs reale Bugs über mehrere Runden echter Klick-Tests gefunden
  und behoben (Tab-Kontamination, falsches Fenster, SQLite-Cross-Thread,
  verworfener Redirect-Filter, Paginierung — siehe „Nachbesserung" weiter
  oben) — live bestätigt, keine offenen Punkte mehr.

---

## Nächster Entwicklungsschritt

Schritt 7 ist jetzt vollständig abgeschlossen und live bestätigt — keine
offenen Punkte mehr.

**Schritt 8 — Preisverlauf & Diagramme.** Aufbauend auf der bereits
seit Schritt 1 bestehenden `price_history`-Tabelle (jetzt aktiv befüllt
durch `PriceService`/`PriceRepository` aus Schritt 7): Preisverlauf pro
Karte visualisieren (Diagramm-Widget, vermutlich `QtCharts` oder
Matplotlib-Embed — Abwägung noch offen), plus eine einfache
Verlaufsansicht in den Kartendetails. Danach kurze Zusammenfassung und
Warten auf Freigabe.
