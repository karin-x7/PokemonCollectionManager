# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier chronologisch
dokumentiert. Format angelehnt an [Keep a Changelog](https://keepachangelog.com);
Versionierung nach [SemVer](https://semver.org).

## [Unreleased]

### Hinzugefügt — UI/Design-Überarbeitung
- Neues, einziges dunkles Navy-Theme mit orange/gelben Akzenten (Light/Dark-
  Umschalter entfernt).
- Preisverlauf ist jetzt ein einklappbares Dock rechts (`PriceHistoryDock`)
  statt im Kartendetail-Panel eingebettet: redesignter Chart mit
  Achsentiteln, %-Änderung zum vorherigen Preis (grün/rot), Liste der
  letzten 10 Preis-Updates, "Historie zurücksetzen"-Button mit
  Sicherheitsabfrage (löscht nur den Verlauf, nicht den aktuellen Preis).
- Kartenansicht deutlich vergrößert und mit eigenem "Bühnen"-Hintergrund
  versehen, damit die Karte nicht in leerem Raum wirkt.
- Mindestfenstergröße und Panel-Mindestbreiten erhöht, damit normales
  Verkleinern nie mehr Text verdeckt.
- "Suchen"-Button neben der Toolbar-Katalogsuche (bisher nur Enter).
- Neues App-Icon (stilisierter Kartenfächer, mit PySide6 selbst gezeichnet,
  kein Pokémon-Logo/Charakter).

### Behoben — UI-Nachbesserungen (vom Nutzer live gefunden)
- Kartenbild wurde nicht zugeschnitten (Letterboxing) und Textfelder rückten
  zu dicht ans Bild heran — Bühne hat jetzt echtes Kartenseitenverhältnis
  mit Crop-to-fill, plus mehr Abstand zu Feldern/Buttons.
- Diagramm: kaputtes „€"-Zeichen in Achsenticks, überlappende
  Datumsbeschriftungen bei mehreren Einträgen — behoben (Einheit nur im
  Titel, kürzeres/gekipptes Datumsformat, begrenzte Tickanzahl, sichtbare
  Datenpunkte).
- Verlaufsliste brauchte horizontales Scrollen — jetzt zweizeilige, breite
  Einträge statt einer zu langen Zeile.
- Filterleiste und die beiden Detail-Buttons wurden bei normaler
  Fensterbreite abgeschnitten — Filterleiste ist jetzt zweizeilig, Buttons
  stehen untereinander.
- Preisverlauf-Dock quetschte beim Öffnen die drei Hauptspalten zusammen —
  das Fenster wird jetzt automatisch mit verbreitert/verschmälert.
- "Preisverlauf anzeigen" war Einbahnstraße — jetzt ein echter Umschalter
  (Button-Text synchronisiert sich auch, wenn das Dock über sein eigenes
  Schließen-Symbol geschlossen wird).

### Geändert — „Zusätze" → „Extra"; `Variante` entfernt
- Das alte `Variant`-Feld (Normal/Holo/Promo/Staff) war seit der Umstellung
  auf die vier Ja/Nein-Flags redundant und wurde komplett entfernt
  (Schema-Migration v3: `DROP COLUMN variant`, gegen echte Nutzerdaten
  verifiziert und angewendet).
- UI-Label „Zusätze" → „Extra" in Kartenliste, Detail-Panel und
  Bearbeiten-Dialog.

### Verworfen — automatische Cardmarket-Versions-Korrektur
- Ein Fix-Versuch für falsch verlinkte Vintage-Produktseiten (Base Set
  Bisaflor öffnete die englische statt der deutschen Produktseite) öffnete
  bei einem Sprach-Mismatch bis zu 6 zusätzliche Cardmarket-Tabs ohne Pause
  und löste dadurch eine temporäre Cardmarket-Kontosperre aus. Vollständig
  zurückgerollt. Soll später mit strikter Drosselung (Pause zwischen Tabs,
  max. 1–2 Kandidaten) erneut angegangen werden.

### Behoben — Fenstererkennung bei lokalisierten Kartennamen
- Preisabruf scheiterte zuverlässig bei nicht-englischen Kartennamen (z. B.
  „Charizard VMAX" auf Deutsch: Seitentitel „Glurak VMAX | Cardmarket"),
  weil die Fenstererkennung nach dem (englischen) Katalognamen statt nach
  „cardmarket" (sprachunabhängig) suchte. Live mit einer echten deutschen
  Charizard-VMAX-Karte gefunden und behoben.

### Hinzugefügt — Kartenzusätze als Ja/Nein-Flags (Reverse Holo/Signiert/1st Edition/Altered)
- `Variant`-Enum auf Normal/Holo/Promo/Staff reduziert; die vier Zusätze
  sind jetzt unabhängige `bool`-Felder auf `Card`/`CardDetailsValues` —
  beliebig kombinierbar (z. B. signiert *und* Reverse Holo).
- Schema-Migration v2 (neue Spalten + Migration bestehender `variant`-Werte
  wie `'1st Edition'`), gegen die echte Nutzerdatenbank verifiziert.
- `CardDetailsDialog` bekommt vier Checkboxen; `CardDetailPanel` zeigt sie
  als „Zusätze"-Feld an.
- Preis-Engine filtert jetzt zusätzlich nach Cardmarkets eigenen
  `extra[isSigned]`/`extra[isFirstEd]`/`extra[isAltered]` (live aus dem
  DOM bestätigte Parameter) auf **jeder** Leiter-Stufe. Reverse Holo hat
  auf Cardmarket keinen Filter und bleibt rein informativ.
- 14 neue/angepasste Tests. Gesamt: 247 Tests grün.

### Hinzugefügt — Schritt 9: Filter & Volltextsuche
- Filterleiste oberhalb der Kartenliste: Textsuche (Name/Set/Nummer/
  Notizen), Dropdowns für Set/Sprache/Variante/Zustand, Preis-von/-bis,
  „Zurücksetzen".
- Umschaltbar per Checkbox zwischen „nur aktuelle Sammlung" und „alle
  Sammlungen durchsuchen" — Letzteres funktioniert auch ohne
  Sammlungsauswahl in der Seitenleiste.
- `CardFilter`-DTO, `CardRepository.search`/`distinct_set_names`,
  `CardService.search_cards`/`list_set_names`.
- Bugfix während der Testphase: `Variant`-Combobox lieferte durch Qt's
  Item-Data-Marshalling einen rohen `str` statt des Enums zurück (derselbe
  Bug wie in Schritt 5) — behoben mit `Variant.from_value(...)`.
- 27 neue Tests. Gesamt: 239 Tests grün.

### Hinzugefügt — Schritt 8: Preisverlauf-Diagramm
- `PriceHistoryChartView`: eingebettetes Liniendiagramm im
  Kartendetails-Panel (`PySide6.QtCharts`, keine neue Abhängigkeit).
  Platzhaltertext bei 0/1 Einträgen statt leerem Diagramm.
- `CardController` lädt beim Anzeigen einer Karte jetzt auch deren
  Preisverlauf (optionaler `price_repository`-Parameter, abwärtskompatibel).
- Visueller Feinschliff (Farben/Abstände/Beschriftung) bewusst auf einen
  späteren Zeitpunkt verschoben — ausdrücklicher Nutzerwunsch.
- 10 neue Tests. Gesamt: 212 Tests grün.

### Behoben — Schritt 7: Fenster-/Tab-Kontamination bei der Preis-Auslese
- Ein per Nutzer entdeckter, falscher Preis (78,90 € statt echter 200,00 €)
  deckte zwei reale Bugs auf: (1) `window.descendants()` las den kompletten
  Accessibility-Baum eines Browserfensters, nicht nur den sichtbaren Tab —
  Text aus fremden Hintergrund-Tabs (YouTube, eBay, …) wurde fälschlich als
  Angebot geparst; behoben durch einen `is_visible()`-Filter. (2) Die reine
  Titelsuche über alle offenen Fenster konnte einen alten, unbeteiligten Tab
  statt des neuen treffen; behoben durch Beschränkung auf das tatsächliche
  Vordergrundfenster (`GetForegroundWindow`) statt aller Fenster.
- Preis-Ladder nutzt jetzt Cardmarkets eigene `?language=&minCondition=`
  Filter pro Stufe (`build_filtered_url`), statt einer einzigen ungefilterten
  Seite mit rein client-seitiger Filterung — kürzerer, robusterer Seiteninhalt
  pro Abruf. Sprach-IDs live aus dem DOM verifiziert (nicht durchlaufend:
  EN=1, FR=2, **DE=3**, ES=4, IT=5, PT=8); Japanisch/Koreanisch/Chinesisch
  sind bei Cardmarket eigene Produkte, kein Sprachfilter auf derselben Seite.
- Auf Nutzerwunsch: Die Preis-Auslese öffnet jetzt immer gezielt **Google
  Chrome** (`subprocess.Popen`, Pfad über die Windows-Registry ermittelt)
  statt des Systemstandardbrowsers, plus zusätzliche „chrome" im
  Fenstertitel"-Prüfung als zweite Absicherung gegen Fensterverwechslung.
- **Drei weitere Bugs, gefunden über echte Klicks im laufenden Programm:**
  (4) `PriceLookupWorker` lief in einem eigenen `QThread`, nutzte aber die
  SQLite-Verbindung des Haupt-Threads — verboten, Exception verschwand
  spurlos unter `pythonw.exe` (keine Konsole). Behoben durch breitere
  Exception-Behandlung (`logger.exception`, nie mehr stumm) und eine
  Factory (`OpenPriceService`), die *innerhalb* des Worker-Threads eine
  eigene, frische Datenbankverbindung öffnet. (5) `cardmarket_url` ist ein
  pokemontcg.io-Tracking-Shortlink mit fest einprogrammiertem Redirect-Ziel
  — angehängte `?language=`/`?minCondition=`-Filter wurden beim Redirect
  stillschweigend verworfen. Behoben durch `resolve_cardmarket_url()`
  (löst den Redirect per `requests` vorab auf, Ergebnis wird zusätzlich als
  Self-Healing zurück in die Karte gespeichert). (6) Bei „nur Sprache
  gefiltert, alle Zustände" verdecken viele günstige Angebote (z. B. „Poor")
  die teureren, gesuchten (z. B. „Near Mint") außerhalb dessen, was
  Cardmarkets Seite tatsächlich rendert. Behoben durch kombinierten
  Sprache-**und**-Zustand-Filter in der ersten Leiter-Stufe.
- **Live im laufenden Programm bestätigt:** Karte „Xatu" (NM/Englisch)
  liefert jetzt korrekt 200,00 € (`PriceQuality.EXACT`).
- 10 neue Tests. Gesamt: 202 Tests grün.

### Hinzugefügt — Schritt 7: Cardmarket-Preis pro Karte (Bildschirm-Auslese)
- **Kursänderung gegenüber dem ursprünglichen Plan:** Ein Playwright-
  gesteuerter Browser sollte Cardmarket-Angebotsseiten automatisiert
  auslesen. Live getestet und gescheitert: per Playwright gesteuertes
  Chrome (auch über das echte installierte Chrome, `channel="chrome"`)
  blieb in drei Tests (bis zu 80+ Sekunden) zuverlässig auf Cloudflares
  „Nur einen Moment"-Prüfseite hängen, während eine interaktive
  Browser-Sitzung in ~7 Sekunden durchlief — Playwright steuert über das
  Chrome DevTools Protocol (CDP), ein bekanntes Automatisierungssignal, das
  Cloudflare erkennt. Es wurde bewusst **nicht** versucht, das per Stealth-/
  Anti-Erkennungs-Tricks zu umgehen.
- **Finales Design:** ein Knopf pro Karte für **genau eine** Karte pro
  Klick — kein automatisierter Sammel-Lauf über die Sammlung. Klick öffnet
  die Cardmarket-Seite im normalen Standardbrowser (`webbrowser.open`,
  keine Fernsteuerung); das Programm liest den bereits geladenen
  Fensterinhalt per **Windows UI Automation** (`pywinauto`) aus — dieselbe
  Technik wie Screenreader, kein DOM-/Netzwerkzugriff; danach wird genau
  dieser eine Tab wieder geschlossen. Für die nächste Karte muss der
  Nutzer erneut klicken.
- `CatalogCard.cardmarket_url` + `PokemonTcgClient.get_card_by_id`
  (`app/catalog/`): pokemontcg.io liefert pro Karte eine Cardmarket-
  Produkt-URL — löst die Zuordnung eigener Karten zu Cardmarket-Seiten,
  ohne eine eigene Cardmarket-Suche zu bauen.
- `CardmarketOffer` (`app/pricing/models.py`, neu), `browser_price_reader.py`
  (`app/pricing/`, neu): `read_offers_for_card` öffnet/pollt/liest/schließt
  wie oben beschrieben; `_parse_offer_lines` (reine, vollständig
  unit-getestete Funktion) gruppiert die flache Text-Token-Liste zu
  Angeboten (Zustands-Codes `MT/NM/EX/GD/LP/PL/PO`, Sprachname gegen
  `Language.label`, deutsches Preisformat).
- `PriceRepository` (`app/database/repositories/price_repository.py`, neu),
  `CardRepository.update_price`/`update_cardmarket_url` (Erweiterung).
- `PriceService` (`app/services/price_service.py`, neu):
  `update_price_for_card` mit Self-Healing-URL-Backfill für Karten von vor
  Schritt 7, sowie der bereits seit Schritt 1 definierten
  `PriceQuality`-Fallback-Leiter (EXACT → ESTIMATED_FROM_CONDITION →
  ESTIMATED_FROM_LANGUAGE → AVERAGE → NO_PRICE); Lesefehler führen zu
  `NO_PRICE` mit Rationale statt einem Absturz.
- `PriceLookupWorker` (`app/ui/workers/price_lookup_worker.py`, neu,
  `QThread`) und `PriceController` (`app/ui/controllers/price_controller.py`,
  neu) verdrahten den (umbenannten) Kartendetails-Knopf „Preis von
  Cardmarket abrufen" mit `PriceService`, ohne die GUI einzufrieren.
- 39 neue Tests (`_parse_offer_lines` mit realen Token-Sequenzen,
  Repository, alle fünf Preisqualitäts-Stufen mit Fake-Reader/-Client,
  Worker-Signale, Controller-Wiring). Gesamt: 184 Tests grün.
- **Noch offen:** manueller Smoke-Test im laufenden Programm (echtes
  Browserfenster lässt sich nicht sinnvoll automatisiert testen) — siehe
  `PROJECT_PROGRESS.md`, Abschnitt „Übergabe-Hinweis".

### Hinzugefügt — Schritt 6: Kartenbild-Download & Reverse-Holo-Overlay
- `ensure_card_image` (`app/catalog/card_image_cache.py`): lädt das Artwork
  einer Katalog-Karte (`CatalogCard.image_large_url`) herunter und speichert
  es unter `config.PHOTOS_DIR`, Dateiname stabil aus der `external_id`
  abgeleitet — mehrere eigene Kopien derselben Karte teilen sich dieselbe
  Datei, kein Mehrfach-Download. Netzwerkfehler/fehlende URL → `None` statt
  Exception, verhindert nie das Anlegen der Karte selbst.
- `CardService` bekommt einen injizierbaren `image_downloader`-Parameter
  (Standard `ensure_card_image`); `add_card_from_catalog` setzt
  `Card.photo_path` daraus.
- `CardArtworkView` (`app/ui/widgets/card_artwork_view.py`, neu): zeigt das
  geladene Artwork (oder „Kein Foto“) und überlagert bei Reverse Holo einen
  halbtransparenten, diagonalen Regenbogen-Gradient — dieselbe rein optische
  Kennzeichnung wie bei physischen Reverse-Holo-Karten/Cardmarket, da
  pokemontcg.io nur ein Bild pro Karte liefert (unabhängig von Normal/Holo/
  Reverse Holo). Reine Qt-Bordmittel (`QPainter`/`QLinearGradient`), keine
  neue Abhängigkeit.
- `CardDetailPanel` zeigt jetzt echtes Artwork statt eines statischen
  Platzhalters.
- 16 neue Tests. Gesamt: 145 Tests grün.

### Hinzugefügt — Schritt 5: Karten zu Sammlungen hinzufügen
- `CardRepository` (`app/database/repositories/card_repository.py`): reine
  SQL-Zugriffsschicht für Karten (`list_by_collection`, `get`, `create`,
  `update_details`, `delete`); `create` nimmt ein ganzes `Card`-Objekt statt
  Einzelparametern (Karten haben ~15 Felder).
- `CardService` (`app/services/card_service.py`) mit Mengen-Validierung und
  `CardNotFoundError` (`app/services/exceptions.py`).
- `CardDetailsValues` (`app/models/card.py`): geteiltes DTO
  (Variante/Sprache/Zustand/Menge/Notizen) zwischen `CardDetailsDialog` (UI)
  und `CardService` (Persistenz), für Anlegen und Bearbeiten gleichermaßen.
- `CardDetailsDialog` (`app/ui/dialogs/card_details_dialog.py`): Formular für
  die eigene Kopie einer Karte; Anlege- und Bearbeiten-Modus.
- `CatalogSearchResultsDialog` (Schritt 4) hat jetzt einen „Hinzufügen“-
  Button (`add_requested`-Signal), nur aktiv bei Zeilenauswahl.
- `CardListPanel` von Platzhalter auf echte Datenbankdaten umgebaut:
  Auswahl, Bearbeiten (Doppelklick/Kontextmenü), Löschen (mit Bestätigung),
  Übernahme aus der Katalogsuche — alles über Signale, echte Persistenz nur
  über `CardService`. `CardDetailPanel` zeigt jetzt echte `Card`-Daten
  (`show_card`).
- `CardController` (`app/ui/controllers/card_controller.py`) verdrahtet
  beide Panels mit `CardService`; verfolgt die aktuell gewählte Sammlung.
- 39 neue Tests. Gesamt: 129 Tests grün.

### Behoben — zwei Bugs beim manuellen Test (Schritt 5)
- **Variante wurde beim Speichern zu einem `AttributeError`:** `Variant` ist
  ein `str`-Enum; Qt's Combobox-Item-Data-Marshalling wandelt es beim
  Auslesen (`currentData()`) live nachweislich stillschweigend in einen
  reinen `str` um (`Language`/`Condition`, reine Enums, sind davon nicht
  betroffen). Das ließ `CardRepository.create` mit
  `AttributeError: 'str' object has no attribute 'value'` abstürzen, sobald
  eine Karte gespeichert wurde. Die bestehenden Tests bemerkten es nicht, weil
  `Variant == "Normal"` als String-Vergleich trotzdem wahr ist. Behoben durch
  `Variant.from_value(...)` beim Auslesen in `CardDetailsDialog.get_values()`;
  Tests geprüft auf `type(...) is Variant`, nicht nur `==`.
- **Kartendetails-Panel blieb nach dem Bearbeiten auf alten Werten stehen:**
  Bleibt die bearbeitete Zeile an derselben Tabellenposition (z. B. einzige
  Karte in der Sammlung), feuert Qts `currentCellChanged` nicht erneut, weil
  sich der Zeilenindex nicht ändert — das Detail-Panel wurde dadurch nie neu
  befüllt. Behoben durch `CardController.refresh()`, das nach jedem Neuladen
  explizit mit der aktuellen Tabellenauswahl resynchronisiert statt sich
  allein auf das Signal zu verlassen.

### Hinzugefügt — Schritt 4: Kartenkatalog & intelligente Suche
- `PokemonTcgClient` (`app/catalog/pokemontcg_client.py`): read-only
  HTTP-Client für die pokemontcg.io-Katalog-API (`build_query` als reine,
  testbare Query-Builder-Funktion; `list_sets()` für die Set-Liste). Nur
  Trailing-Wildcards (`term*`) werden verwendet — Leading-Wildcards wurden
  live gemessen und sind zu langsam/brechen ab; ein zitierter Mehrwort-
  Begriff kombiniert mit Wildcard (`"a b"*`) liefert zudem einen 400
  (ebenfalls live verifiziert) und wird deshalb als exakte Phrase ohne
  Wildcard gesendet. Sets werden über `set.id` (exakt, einzelnes Token)
  gefiltert statt über `set.name` — siehe Reprint-Fix unten.
- `CardTraderClient` (`app/cardmarket/cardtrader_client.py`): read-only
  Zugriff auf CardTrader-Sets (`list_pokemon_expansions`); die API ignoriert
  den `game_id`-Query-Parameter serverseitig, daher clientseitiges Filtern +
  Caching. `app/cardmarket/` war zuvor ein leeres, für Schritt 7 reserviertes
  Paket — enthält jetzt zusätzlich den Set-Client. Wird in der Suche
  **nicht** verwendet (siehe Reprint-Fix), bleibt aber für Schritt 7
  (Preis-Angebote) bestehen.
- `CatalogSearchService` (`app/services/catalog_search_service.py`): tolerante
  Suche über Name/Set/Nummer/Teilbegriffe. Erkennt Kartennummern per Regex,
  löst Set-Namen fuzzy/als Teilbegriff-Präfix gegen pokemontcg.io`s eigene
  Set-Liste auf (z. B. „skyrige“ → „Skyridge“, „base“ → „Base“) und lockert
  die Anfrage schrittweise, wenn ein strukturierter Filter 0 Treffer liefert.
  Ein Kartenname, der zufällig ein unabhängiges, längeres Set präfigiert,
  wird durch eine Mindest-Längenverhältnis-Schwelle nicht fälschlich als Set
  erkannt. Ein Ausfall der Set-Auflösung degradiert zu einer reinen
  Namenssuche statt die gesamte Suche fehlschlagen zu lassen.
- Toolbar-Suche (`MainWindow.search_submitted`) ist jetzt an
  `CatalogSearchController` (`app/ui/controllers/catalog_search_controller.py`)
  angebunden; Treffer erscheinen in `CatalogSearchResultsDialog`
  (`app/ui/dialogs/catalog_search_results_dialog.py`) — reine Anzeige
  (Name/Set/Nr./Rarität), kein Hinzufügen zur Sammlung (folgt Schritt 5).
- `CatalogSearchError` (`app/services/exceptions.py`) für nicht erreichbare
  Katalog-Backends.
- 35 neue Tests (Client-Parsing/-Fehler gemockt, Suchlogik mit Fake-Clients,
  Controller-Wiring headless). Gesamt: 90 Tests grün.

### Behoben — Reprints/Wiederauflagen bei der Set-Erkennung (Schritt 4)
Nutzerhinweis während der manuellen Prüfung: „Base Set“-Glurak (Charizard)
hat eine Wiederauflage „Base Set 2“ — die Set-Erkennung durfte diese nicht
verwechseln. Beim Testen bestätigt, dass die erste Fassung genau das tat:
- **Ursache 1:** CardTrader und pokemontcg.io benennen dasselbe Set
  unterschiedlich (CardTrader: „Base Set“, pokemontcg.io: „Base“). Die Suche
  löste den Set-Namen gegen CardTraders Vokabular auf und filterte
  pokemontcg.io dann nach diesem (falschen) Namen.
- **Ursache 2:** `set.name` ist bei pokemontcg.io ein tokenisiertes Feld —
  sowohl ein Wildcard-Präfix (`set.name:base*`) als auch eine zitierte Phrase
  (`set.name:"base"`) trafen live nachweislich **beide** Base-Set-Varianten
  gleichzeitig, unabhängig vom verwendeten Namen.
- **Fix:** Die Set-Auflösung nutzt jetzt ausschließlich pokemontcg.io's
  eigene `/sets`-Liste (`PokemonTcgClient.list_sets()`), und die Kartensuche
  filtert nach der exakten, eindeutigen `set.id` (z. B. `base1`) statt nach
  `set.name`. `CatalogSearchService` benötigt dafür keinen CardTrader-Client
  mehr. Regressionstest: `test_reprint_sets_are_resolved_by_id_not_name_to_
  avoid_ambiguity` in `tests/test_catalog_search_service.py`.

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
