# Projektfortschritt — Pokémon Collection Manager

> Synchronisationsdatei zwischen mehreren PCs. Enthält jederzeit den aktuellen
> Entwicklungsstand. Wird nach **jedem** Entwicklungsschritt aktualisiert.

**Letzter Schritt:** Release v0.10.0-alpha.1: seit dem letzten Release
angesammelte Arbeit (Update-Hinweis, Backup-Wiederherstellung, Gesamtwert-
Verlauf, Wantlist mit Preisalarm, CSV/Excel/JSON-Import, Duplikat-Warnung,
Wantlist→Sammlung-Übernahme) in einem Commit auf GitHub gebracht, Version
in `app/config.py`/`pyproject.toml` auf `0.10.0-alpha.1` gesetzt,
CHANGELOG.md-Unreleased-Abschnitt zu `[0.10.0-alpha.1]` geschnitten, neue
`.exe` gebaut und als GitHub-Release veröffentlicht (Snapshot-Feature war
zwischenzeitlich testweise gebaut und auf Nutzerwunsch wieder komplett
entfernt -- daher kein Niederschlag im Diff).

**Vorheriger Schritt:** Kleiner, vom Nutzer nach dem v0.9.0-alpha.1-Release
gemeldeter Bug: Zeilen in der Kartentabelle waren unterschiedlich hoch.
Ursache gefunden: `CardListPanel.set_cards()` rief bisher
`self._table.resizeRowsToContents()` auf, was jede Zeile nach ihrem
größten Zellinhalt bemisst — Set-Icons werden aber von unterschiedlichen
Quellen (pokemontcg.io, tcgdex-Fallback) in unterschiedlicher nativer
Auflösung geladen (`app/ui/set_icon_provider.py`s `QIcon(path)` ohne jede
Größennormalisierung), wodurch jede Zeile je nach enthaltenem Set-Icon
eine andere Höhe bekam. Fix: `resizeRowsToContents()`-Aufruf entfernt,
stattdessen einmalig in `_build()` eine feste Zeilenhöhe gesetzt
(`verticalHeader().setSectionResizeMode(Fixed)` +
`setDefaultSectionSize(_ROW_HEIGHT)`, 36px — bequem für das größte fixe
Icon, das 18px hohe Zustands-Badge, plus die schon bestehenden 8px
Zell-Innenabstände aus der QSS). Live gegen die echte, 20 Karten
umfassende `data/collection.db` verifiziert: `table.rowHeight(r)` liefert
für alle 20 Zeilen exakt `36`, unabhängig vom jeweiligen Set-Icon
(darunter auch die Zeile, deren Set-Icon-Download zuvor mit 404
fehlgeschlagen war). `test_card_panel.py` (24 Tests) weiterhin grün,
`compileall` sauber.

Davor: Fertigstellung/Release-Vorbereitung für den ersten
Alpha-Release (Nutzerwunsch, alle 5 Punkte einer entsprechenden Nachfrage
bestätigt: committen, README aktualisieren, Version 0.9.0-alpha.1, eine
echte .exe bauen, Changelog/Testlauf/Tag). Wichtiger Fund dabei: der letzte
echte Git-Commit (`164b8f2`) lag weit vor Sealed-Produkten, Statistik-Tab,
UI-Redesign, Export und praktisch allen Bugfixes dieser und vieler
vorheriger Sitzungen — 59 Dateien, ~9800 Zeilen lagen komplett unkommittiert
im Arbeitsverzeichnis. `README.md` komplett neu geschrieben (war noch auf
"Schritt 7"-Stand, kannte weder Sealed-Produkte noch Statistik-Tab noch
Export noch die inzwischen Englisch-only-UI); `app/cardmarket/`
(CardTrader-Client, nirgendwo mehr importiert) sowie die leeren
`app/recognition/`/`app/scanner/`-Stubs als Aufräum-Kandidat per
`spawn_task` an eine separate Sitzung ausgelagert (keine Löschung ohne
gesonderte Bestätigung). Version in `app/config.py`/`pyproject.toml` auf
`0.9.0-alpha.1`; CHANGELOG.md bekam einen echten `## [0.9.0-alpha.1]`-
Abschnitt (vorher lief seit dem letzten Release alles nur unter
`[Unreleased]`). Neues `PokemonCollectionManager.spec` für einen
PyInstaller-Onefile-Build (kein Konsolenfenster, bündelt `app/resources/`
+ die vorab generierte Namensübersetzungstabelle, explizite
`hiddenimports` für `PySide6.QtCharts` und die pywin32-Module, da diese
sonst vom automatischen PySide6/pywin32-Hook nicht zuverlässig erkannt
werden). Dabei einen echten, für die Verteilung kritischen Bug gefunden und
behoben: `app/config.py`s `BASE_DIR` wurde bisher immer aus `__file__`
abgeleitet — in einer PyInstaller-Onefile-`.exe` liegt das aber im
temporären Extraktionsverzeichnis (`sys._MEIPASS`), das nach jedem
Programmende gelöscht wird, hätte Datenbank/Fotos/Logs also bei jedem
Neustart stillschweigend verloren. Fix: `BASE_DIR` erkennt jetzt
`sys.frozen` und zeigt in dem Fall auf das Verzeichnis der `.exe` selbst
(`Path(sys.executable).resolve().parent`) statt auf `__file__`. Neue
Tests in `test_config.py` (per `importlib.reload()` mit gepatchtem
`sys.frozen`/`sys.executable`). Live end-to-end bestätigt: gebaute `.exe`
in ein leeres, projektfremdes Verzeichnis kopiert und dort gestartet —
Datenbank, automatisches Backup und Log landen korrekt direkt neben der
`.exe`, GUI startet fehlerfrei (`app.ui.app | GUI started.` ohne
Tracebacks im Log). `.gitignore` überarbeitet: die bisherige, zu enge
`data/*.db`-Regel ließ `data/backups/`, `data/sealed_photos/` und
`data/set_icons/` als unversioniert-aber-nicht-ignoriert zurück (`git
status` zeigte den kompletten `data/`-Ordner als neu an) — jetzt blockweise
`data/` komplett ausgeschlossen; `build/`/`dist/` (PyInstaller-Ausgaben)
ergänzt, `*.spec` selbst bleibt bewusst versioniert (Build-Konfiguration,
kein Artefakt). Finaler kompletter Testlauf: 745 Tests grün, 0 Fehlschläge (Laufzeit
45:53 min — durchgehend durch echte, teils langsame externe API-Aufrufe in
einigen Tests, kein Zusammenhang mit den heutigen Änderungen). Live-
Durchklick: App mit dem finalen Stand neu gestartet, Log fehlerfrei
(Version korrekt "0.9.0-alpha.1"), Export/Sealed-Produkte heute nicht
erneut angefasst und daher nicht separat nachgetestet.

Zwei geplante Commits (Nachhol- + Release-Prep-Commit) wurden zu einem
einzigen zusammengefasst: README.md/CHANGELOG.md/PROJECT_PROGRESS.md/
`app/config.py` enthielten schon vor dem Commit eine untrennbare Mischung
aus altem, historisch akkumuliertem Inhalt und den heutigen Release-Prep-
Änderungen (README z. B. per `Write` komplett neu geschrieben, aber
inhaltlich über die gesamte Feature-Historie) — eine saubere Trennung hätte
riskantes zeilenweises `git add -p` auf einem 24k-Zeilen-Diff erfordert.
Stattdessen: **ein** Commit `d52a756` ("Catch up on accumulated work since
last commit, prepare v0.9.0-alpha.1"), 167 Dateien, +24156/-561 Zeilen,
danach Tag `v0.9.0-alpha.1` gesetzt. `app/resources/icon - Kopie.ico`
(alte Icon-Backup-Datei) bewusst vom Commit ausgeschlossen (liegt weiter
unversioniert auf der Platte, dient weiter als informelle Sicherung).

Damit ist die für heute besprochene Fertigstellung/Release-Vorbereitung
komplett: committet, README aktuell, Version gesetzt, CHANGELOG-Release-
Abschnitt geschnitten, volle Testsuite grün, eigenständige `.exe` gebaut
und live verifiziert, getaggt.

Davor: Die eben gebaute Standard-Sammlung "All Cards" (siehe
voriger Absatz unten) wieder auf Nutzerwunsch komplett entfernt ("das will
ich vielleicht doch nicht so haben") — stattdessen die simple Variante:
beim App-Start wird einfach die in der Sammlungsliste zuoberst stehende,
bereits existierende Sammlung automatisch ausgewählt, kein Auto-Anlegen
mehr. Vollständig zurückgebaut: Migration 9 aus `schema.py` entfernt,
`Collection.is_default`-Feld, `CollectionRepository.get_default()/
create_default()/mark_default()`, `CollectionService.
ensure_default_collection()` und der Löschschutz in `delete_collection()`,
`CollectionPanel`s Kontextmenü-Sonderfall, alle zugehörigen Tests. Neue,
viel kleinere `CollectionController.select_first_collection()` (wählt
`list_collections()[0]`, No-op wenn keine Sammlung existiert), in
`main_window.py` an derselben Stelle wie zuvor aufgerufen. Die echte
`data/collection.db` war zu diesem Zeitpunkt bereits über die App-Neustarts
dieser Sitzung auf Migration 9 gelandet (mit einer leeren "All Cards"-
Sammlung, 0 Karten laut Kartenzahl-Check vor dem Löschen) — vor dem
Code-Revert per Backup (`collection.db.bak-before-all-cards-revert`) und
direktem SQL (`DELETE FROM collections WHERE id=... AND is_default=1`,
`ALTER TABLE collections DROP COLUMN is_default`, `DELETE FROM
schema_migrations WHERE version=9`) manuell zurückgebaut, damit die reale
Datenbank exakt so aussieht, als hätte es Migration 9 nie gegeben (bewusste
Ausnahme von der sonst geltenden "Migrationen nie rückwirkend ändern"-Regel,
gerechtfertigt weil: nur diese eine, lokale Maschine betroffen, Feature
lebte noch keine Stunde, keine echten Kartendaten betroffen). Live
bestätigt (Skript gegen die echte `data/collection.db`): "Testbinder" (20
echte Karten) wird jetzt korrekt automatisch ausgewählt, "All Cards"
taucht nirgends mehr auf. Alle betroffenen Tests grün, `compileall` sauber.

Davor: Neuer Nutzerwunsch: eine Standard-Sammlung "All Cards"
soll beim App-Start immer sofort ausgewählt sein (statt einer leeren
Kartenliste, bis man von Hand eine Sammlung anlegt) — konkret als *echte*
Sammlung gewünscht (Rückfrage per AskUserQuestion beantwortet), nicht als
reine "alle Sammlungen kombiniert anzeigen"-Filteransicht: Karten sollen
wirklich dort landen wie in jedem anderen Ordner, man kann sie später in
einen Binder verschieben oder direkt einen Binder anklicken und dort
einfügen. Migration 9 (`app/database/schema.py`): neue `is_default`-Spalte
auf `collections`. `Collection`-Modell/`CollectionRepository` bekamen das
Feld; neue Repo-Methoden `get_default()`, `create_default(name)` (sortiert
per `_previous_position()` immer VOR jede bestehende Sammlung, funktioniert
sowohl für eine frische als auch eine bereits bestückte Datenbank) und
`mark_default(id)`. `CollectionService.ensure_default_collection()`: idempotent
(bei jedem App-Start aufrufbar), legt "All Cards" beim ersten Aufruf an;
degradiert bei einem (extrem unwahrscheinlichen) Namenskonflikt (Nutzer hatte
schon vorher zufällig selbst eine Sammlung "All Cards" angelegt) auf
"diese bestehende Sammlung nachträglich als Standard markieren" statt
abzustürzen. `delete_collection()` weist jetzt einen Löschversuch auf die
Standard-Sammlung mit `ValidationError` zurück (Umbenennen bleibt erlaubt).
`CollectionPanel`s Kontextmenü zeigt für die Standard-Sammlung konsequent gar
keinen "Löschen"-Eintrag (nicht nur einen deaktivierten). Neue
`CollectionController.ensure_default_collection_selected()`, in
`main_window.py` einmalig nach `_connect_signals()` aufgerufen -- feuert
zuverlässig `selection_changed` bis zum `CardController`, da die Signal-
Verbindung zu dem Zeitpunkt schon steht. Live end-to-end bestätigt (Skript
gegen ein frisches `MainWindow`): "All Cards" existiert, ist ausgewählt,
`card_controller.collection_id` zeigt korrekt darauf. Ein Test
(`test_collection_panel.py`s Kontextmenü-Test) hing beim ersten Anlauf
tatsächlich unendlich -- `QMenu.exec()` ließ sich in diesem Projekt nicht
zuverlässig per `monkeypatch` abfangen (echter modaler Event-Loop blockierte),
Test ersatzlos entfernt statt mit einem riskanteren Workaround erzwungen
(mirrors die bereits bestehende Projekt-Konvention: `_show_context_menu`
wird nirgendwo sonst unit-getestet). Volle Testsuite mehrfach ohne einen
einzigen Fehlschlag durchlaufen (Laufzeit stark schwankend, 15 bis über 40
Minuten -- einige Tests verifizieren laut Projekt-Konvention bewusst live
gegen echte externe APIs wie pokemontcg.io/tcgdex, deren aktuelle
Antwortzeit stark schwankt; kein Zusammenhang mit den heutigen Änderungen),
`compileall` sauber.
Nebenbei, direkt danach gefragt: ob die tcgdex-Suchstufe (siehe voriger
Schritt) zusätzlich *parallel* zur ersten pokemontcg.io-Anfrage laufen soll
(statt erst danach) für noch etwas mehr Tempo -- Nutzer hat sich per
AskUserQuestion bewusst dagegen entschieden (würde bei jeder einzelnen
Suche, auch ganz normalen englischen Treffern, 5 zusätzliche tcgdex-
Hintergrundanfragen auslösen), aktueller Stand (~5s statt >1 Minute) bleibt
also unverändert.

Davor: Neues Problem vom Nutzer: die bestehende Übersetzungs-
tabelle (`name_translation.py`, aus PokeAPI generiert) kennt nur Pokémon-
*Spezies*-Namen ("Glurak" -> "Charizard") — Trainer-/Item-/Stadium-Karten wie
"Lillys Entschlossenheit" (deutsch für "Lillie's Determination") kommen bei
PokeAPI gar nicht vor, die Katalogsuche fand sie also nicht. Live geprüft und
bestätigt: tcgdex.dev (im Projekt schon für JP/KO/ZH-Bezeichnungen genutzt,
`tcgdex_designation_lookup.py`) teilt sich für die westlichen Sprachen
(Englisch/Deutsch/Französisch/Spanisch/Italienisch/Portugiesisch) EIN
gemeinsames Set-ID/Kartennummer-Schema — anders als Japanisch/Koreanisch/
Chinesisch, die eine komplett eigene Nummerierung je Sprache haben. Konkret
bestätigt: `me01-184` heißt unter `/de/` "Lillys Entschlossenheit" und unter
`/en/` "Lillie's Determination" — exakt dieselbe ID. Neues Modul
`app/catalog/tcgdex_name_translation.py`: `translate_foreign_card_name(query)`
sucht live in de/fr/es/it/pt nach `query` (tcgdex' Namenssuche filtert bereits
locker per Teilstring), rankt exakte vor lockeren Treffern (eigene
`_ranked()`-Hilfsfunktion, normalisiert wie der Rest der Suche), und liest
für den besten Treffer direkt die `en`-Variante derselben ID -- kein
Pokédex-Nummer-Abgleich nötig wie bei der JP/KO/ZH-Variante, da die IDs
selbst schon sprachübergreifend identisch sind. Bewusst als *letzte*,
Live-Fallback-Stufe in `CatalogSearchService._search_name_tolerantly()`
eingehängt (nach Spezies-Tabelle und schrumpfendem Präfix, die beide lokal/
schnell sind und bei einer echten Fremdsprachen-Anfrage ohnehin nichts
finden) -- ein zusätzlicher Live-Request lohnt sich nur, wenn jede billigere
Stufe schon fehlgeschlagen ist. Nie werfend: ein tcgdex-Ausfall degradiert zu
"keine Übersetzung gefunden", bricht die Suche nie ab. End-to-end live
bestätigt: `service.search("Lillys Entschlossenheit")` gegen die echte
pokemontcg.io-API findet jetzt alle 4 echten Drucke von "Lillie's
Determination". Neue Tests in `test_tcgdex_name_translation.py` (6, mit
Fake-Session wie beim Schwester-Modul) und drei neue Tests in
`test_catalog_search_service.py` (Trainer-Karte über die neue Stufe
gefunden, Stufe wird bei früherem Erfolg übersprungen, kein Treffer bleibt
leer). Volle Testsuite bis 88%+ ohne einen einzigen Fehlschlag durchgelaufen
(danach abgebrochen, da versehentlich ein zweiter Lauf parallel gestartet
war), `compileall` sauber.

Davor: Todo #90 (Shadowless-Bild per Cardmarket-Screenshot)
gebaut, live getestet und auf Nutzerwunsch wieder komplett verworfen: die
automatische Fenster-/Bild-Erkennung ("`Image`-Control auf der
Cardmarket-Seite finden, per `PrintWindow` zuschneiden") erwies sich in der
Praxis als nicht robust genug ("diese automatische Erkennung funktioniert
nicht gut"). Da der bereits bestehende Base-Set-Split (siehe voriger Schritt
unten) den Cardmarket-Link schon korrekt der Shadowless-Version zuordnet und
das dem Nutzer ausdrücklich reicht ("solange der Link aber zu der richtigen
Version führt, ist alles ok"), wurde der komplette Umbau rückgängig gemacht:
`CatalogCard.capture_photo_from_cardmarket`, `CardService.
add_card_from_catalog()`s `temp_photo_path`-Parameter samt
`_finalize_photo()`-`prefix`-Parameter, `browser_price_reader.
capture_product_photo()`, der neue `CardPhotoCaptureWorker` und
`CardController`s Worker-Verzweigung inkl. aller zugehörigen Tests wieder
entfernt — die Shadowless-Variante zeigt jetzt wieder ganz normal das
generische pokemontcg.io-Bild (Aufgabe #90 dauerhaft als "kein Foto,
Link reicht" beendet statt als offenes Todo). Volle Testsuite (742 Tests)
grün, `compileall` sauber. Nebenbei im selben Aufräumdurchgang: der Nutzer
hat das App-Icon selbst vom umschließenden Kasten freigestellt (eigene
Bildbearbeitung) und als neues `icon.ico` eingesetzt — mein eigener
Freistellungsversuch per BFS-Flood-Fill (siehe verworfene Skripte im
Scratchpad) kam an eine echte Grenze der Rasterquelle (zwei der drei Karten
im Fächer hatten keine wiederherstellbare Füllfarbe mehr), der Nutzer hat
das Problem stattdessen selbst gelöst.

Davor: Base-Set-Fix nachgeschärft: statt nur eine Fehlermeldung
zu zeigen (siehe voriger Schritt unten), bietet die Katalogsuche für
Base-Set-Treffer jetzt zwei Einträge an — "Base" und "Base (Shadowless)" —
mit jeweils korrekt aufgelöstem Cardmarket-Link, Nutzerwunsch nach dem
initialen Fix ("kannst du nicht quasi alle base set einträge duplizieren").
`CatalogSearchService.search()` bekam eine neue `_expand_ambiguous_variants()`
-Nachbearbeitung: für jeden Treffer aus einem mehrdeutigen Set (aktuell nur
`"base1"`) wird der pokemontcg.io-Shortlink aufgelöst
(`resolve_cardmarket_url`, reines `requests`, kein Chrome nötig) und per
`find_alternate_version_url()` (bereits bestehende "-V<n>-"-Geschwister-Logik
aus `browser_price_reader.py`, live bestätigt: niedrigere Versionsnummer =
Normal/Unlimited, höhere = Shadowless) die jeweils andere Variante ermittelt
— daraus werden zwei separate `CatalogCard`-Einträge (per `dataclasses.
replace()`) mit demselben Namen aber unterschiedlichem `set_name`/
`cardmarket_url`. Best-effort: schlägt die Auflösung fehl (Netzwerkfehler)
oder gibt es keine "-V<n>-"-Geschwisterversion, bleibt der ursprüngliche,
einzelne Treffer unverändert bestehen, keine Exception nach oben.
`pokemontcg_client.py`s `_parse_card()` wurde dafür zurückgebaut auf einen
reinen Passthrough (liefert `cardmarket_url` jetzt wieder unverändert, auch
für `"base1"`) — die Entscheidung, ob ein Link vertrauenswürdig ist, liegt
jetzt komplett bei den Konsumenten: `CatalogSearchService` löst auf und
splittet, `PriceService` prüft bei einer bereits gespeicherten Karte
zusätzlich per neuer `is_unresolved_pokemontcg_shortlink()`-Hilfsfunktion
(`browser_price_reader.py`), ob der gespeicherte Link noch der unaufgelöste,
mehrdeutige pokemontcg.io-Shortlink ist (dann weiterhin Fehlermeldung statt
falscher Preis) oder schon ein spezifischer, aufgelöster cardmarket.com-Link
(z. B. aus der neuen Splitting-Logik oder manuell gesetzt) — dann normal
verwendet. 708+ Tests grün (neue Tests für Splitting in
`test_catalog_search_service.py`, für die Shortlink-Unterscheidung in
`test_price_service.py`, für `is_unresolved_pokemontcg_shortlink` in
`test_browser_price_reader.py`), `compileall` sauber.

Davor: Vier kleinere, vom Nutzer live gemeldete Punkte
nacheinander behoben: (1) `STALE_PRICE_THRESHOLD_DAYS` von 90 auf 60 Tage
(2 Monate) gesenkt. (2) Base-Set-Mehrdeutigkeit: der Nutzer hat live
gemeldet, dass eine über die Katalogsuche hinzugefügte Base-Set-Karte
(Charizard) automatisch mit dem Cardmarket-Link der Shadowless-Variante
verknüpft wurde, obwohl er die normale (Unlimited) Version wollte —
live-verifiziert (`api.pokemontcg.io/v2/cards?q=set.id:base1 name:Charizard`
liefert genau einen Datensatz `base1-4`, dessen `cardmarket.url`-Shortlink
nach Auflösung des Redirects auf `.../Charizard-V2-BS4` (Shadowless) zeigt;
`.../Charizard-V1-BS4` wäre die normale Version, aber pokemontcg.io kennt
nur den einen Link). Da Shadowless ausschließlich auf Englisch existiert,
ist der Auto-Link für jede andere Sprache schlicht falsch, und selbst für
Englisch nicht das, was der Nutzer meinte. `pokemontcg_client.py`s
`_parse_card()` lässt `cardmarket_url` jetzt für `set_code == "base1"`
bewusst leer (neue `_AMBIGUOUS_VARIANT_SET_CODES`-Konstante + öffentliche
`has_ambiguous_cardmarket_variants()`-Hilfsfunktion) — `price_service.py`
zeigt dafür eine spezifische Meldung ("führt mehrere Druckvarianten... als
getrennte Cardmarket-Produkte") statt der generischen "keine Zuordnung
bekannt", die auf "Eigener Cardmarket-Link" verweist (gleiches Muster wie
schon bei Japanisch/Koreanisch/Chinesisch). Nebenbei aufgefallen: die
`price_rationale` eines Preis-Lookups wurde bisher nirgendwo in der UI
angezeigt (komplett ungenutzt) — jetzt als Tooltip auf dem
"Preisqualität"-Feld in Karten- und Sealed-Detailpanel sichtbar. (3) Beide
Such-Ergebnis-Dialoge (Katalogsuche, Cardmarket-Suche) zeigen jetzt sofort
beim Öffnen einen Ladezustand ("Suche läuft…" + unbestimmter
`QProgressBar`) statt leer/erst nach Abschluss zu erscheinen — der Nutzer
hatte gemeldet, dass die App währenddessen wie abgestürzt wirkte. Die
Katalogsuche lief bisher komplett synchron im GUI-Thread (nur Wartecursor);
neuer `CatalogSearchWorker` (QThread) mirrors den bereits bestehenden
`CardmarketSearchWorker`-Aufbau. Eine Falle dabei gefunden und behoben: der
Ergebnis-Dialog darf nicht in `_cleanup_worker()` (an `worker.finished`
gehängt) auf `None` gesetzt werden, da bei synchron gemockten Workern (Tests)
die gesamte succeeded/finished-Kette bereits **vor** dem eigentlichen
`dialog.exec()`-Aufruf durchläuft — sonst crasht `self._results_dialog.exec()`
mit `AttributeError` auf `None`. (4) Neue gemeinsame Basisklasse
`DimmedDialog` (`app/ui/dialogs/dimmed_dialog.py`): überlagert das
Hauptfenster mit einem halbtransparenten Overlay-Widget, solange irgendein
eigener Dialog offen ist (Nutzerwunsch: Popups sollen sich optisch vom
Hauptfenster abheben, nicht wie ein eingefrorenes Programm wirken) — alle
9 eigenen Dialogklassen der App erben jetzt davon statt direkt von
`QDialog`; `QMessageBox`-Aufrufe bewusst ausgenommen (Umfang begrenzt auf
die eigenen Dialogklassen). Davor, in derselben Sitzung: zwei kleinere
Doku-Bugs im neuen Help-Tab behoben (deutsche Restsätze in der
Quellen-Liste, die nie durch `tr()` liefen; ein erfundener "Graded cards"-
Abschnitt entfernt, nachdem Code-Grep bestätigte, dass es dieses Feature
trotz gegenteiliger Aufgabenlisten-Einträge #59/#60 gar nicht gibt) und der
Help-Tab-Text selbst auf Wunsch des Nutzers von ausführlichen Absätzen auf
knappe, WikiHow-artige Einzeiler gekürzt. Volle Testsuite grün, `compileall`
sauber, App-Neustart live durch den Nutzer bestätigt.

Davor: Drei Features nacheinander gebaut: (1) Sammel-Button
"Alle aktualisieren" bei "Karten/Sealed-Produkte mit veraltetem Preis" in
der Statistik — `PriceController`/`SealedPriceController` bekamen
`start_bulk_update(ids)`, das eine interne Warteschlange abarbeitet (ein
Preis-Lookup nach dem anderen, wiederverwendet dasselbe
Single-Worker-Slot-Muster wie `start_lookup`), inkl. Fortschrittsanzeige in
der Statusleiste ("Preis 2/5 wird von Cardmarket abgerufen…") und
Button-Deaktivierung während des Laufs über neue
`StatisticsController.set_bulk_card_update_running()`/
`set_bulk_sealed_update_running()`. (2) UI komplett auf Englisch umgestellt
(Nutzer-Entscheidung: "wir behalten die app nur auf englisch") — der
DE/EN-Umschalter in "Infos und Einstellungen" ist komplett entfernt,
`app/i18n.py`s `tr()` übersetzt jetzt bedingungslos ins Englische (die
deutschen Quelltexte an den Aufrufstellen bleiben als interne
Nachschlage-Keys bestehen, das war der einfachste risikoarme Weg, ohne
hunderte Aufrufstellen umzuschreiben). Wichtig: das betrifft NUR die
UI-Sprache — die Datenbank/Karten-Sprache (`Language`-Enum, JP/KO/EN/DE/...)
bleibt komplett unverändert mehrsprachig, das ist ein völlig anderes
Konzept. Der freigewordene zweite Tab in "Infos und Einstellungen" wurde zu
einer neuen "Help"-Sektion (`QTextBrowser`) mit Erklärungen zu nicht
offensichtlichen Programmteilen (manuelles Eintragen per Cardmarket-Link,
warum JP/KO/Traditionelles-Chinesisch keinen automatischen Sprachfilter
bekommen können, Preisverlauf, veraltete Preise, Sammlungen vs. Sealed,
automatische Backups) — Nutzer-Wunsch nach einem Tutorial, weil die App
ohne Hintergrundwissen nicht immer eindeutig ist. (3) Mehrfachauswahl in
Karten- und Sealed-Tabelle (Shift/Strg-Klick, `ExtendedSelection` statt
`SingleSelection`): `delete_requested`/`move_requested` tragen jetzt immer
eine Liste von IDs statt einer einzelnen — Rechtsklick auf eine Zeile
außerhalb der aktuellen Auswahl wählt zuerst nur diese Zeile an (Windows-
Explorer-Verhalten), "Bearbeiten" (und bei Sealed: "Preis aktualisieren")
verschwinden aus dem Kontextmenü, sobald mehr als eine Zeile markiert ist,
da Einzel-Bearbeitung bei mehreren Karten keinen Sinn ergibt.
`CardController`/`SealedProductController` verarbeiten die ID-Liste
sequenziell und sammeln Fehler zu einer gemeinsamen Meldung statt beim
ersten Fehler abzubrechen. 691 Tests grün, `compileall` sauber, App-Start
headless verifiziert (`MainWindow` baut fehlerfrei, beide Tabellen zeigen
`SelectionMode.ExtendedSelection`). Noch offen (Nutzer-Wunsch, als nächstes
dran): Sammel-Button für Statistik ist erledigt, aber es gibt zusätzlich
export/pricing-fremde Folgepunkte aus derselben Ideensammlung, die noch
nicht angefasst wurden (siehe Aufgabenliste). Davor: Automatische
DB-Backups gebaut (erster von zwei
Nutzer-Vorschlägen aus einer Ideen-Sammlung, zweiter folgt: Sammel-Preis-
Update). Neues `app/database/backup.py`: sichert `collection.db` mit
Zeitstempel nach `data/backups/`, bevor `Database.initialize()`
Migrationen laufen lässt — nur falls die Datei schon existiert, übersprungen
falls die letzte Sicherung jünger als 24h ist (verhindert Backup-Flut bei
häufigen Neustarts, wie in dieser Session beobachtet), max. 20 Sicherungen
behalten. Dabei einen Testisolations-Bug gefunden und behoben: ohne
Gegenmaßnahme hätte `Database.initialize()`'s neuer Backup-Aufruf während
Testläufen echte Dateien in den echten `data/backups/`-Ordner geschrieben
(live beobachtet: ein `idem_...`-Testartefakt landete dort) — neue,
automatisch aktive Fixture `_no_real_database_backups` in
`tests/conftest.py` lenkt das für jeden Test in ein Temp-Verzeichnis um,
mirrors die bereits bestehende `_no_real_set_icon_downloads`-Fixture.
21 Tests grün, `compileall` sauber, live gegen die echte `collection.db`
verifiziert. Davor: Cardmarket-Sucheautomatisierung mit Bestätigungsdialog
gebaut (Nutzer-Wunsch, nachdem der manuelle Link für "Poké Pad" als einzige
Lösung übrig blieb): neuer Button "Cardmarket-Link suchen" im
Kartendetail-Panel durchsucht Cardmarket direkt (Live-Spike bestätigt:
Cardmarkets Suchergebnisseite hat echte Hyperlink-Elemente mit Text wie
"Poké Pad Perfect Order  Poké Pad (POR 113) From 9,00 €" — kein href per UI
Automation auslesbar, aber `link.invoke()` (UIA Invoke-Pattern statt
simuliertem Klick) navigiert zuverlässig zum echten Produkt, dessen
Adresszeile danach normal lesbar ist). Zweistufiger Ablauf: Suche
(`CardmarketSearchWorker`) → Bestätigungsdialog
(`CardmarketSearchResultsDialog`) → Auflösung der echten URL
(`CardmarketSearchResolveWorker`, erneute Suche + Klick, da der erste Tab
schon geschlossen ist) → `CardService.set_manual_cardmarket_url()`. Live
end-to-end verifiziert: aufgelöste URL für "Poke Pad"/"Perfect Order
(POR 113)" stimmt exakt mit dem vom Nutzer bereitgestellten Link überein.
176 Tests grün, `compileall` sauber. Cardmarket-ID-Redirect- und
Slug-Raten-Ideen (für dieselbe fehlende Verknüpfung) waren zuvor bereits
verworfen worden (siehe Eintrag unten). Davor: Set-Icon-Fallback über
tcgdex.dev gebaut (Nutzer-Sorge:
pokemontcg.io könnte neue Sets vernachlässigen — Beleg: "Perfect Order",
27.03.2026 erschienen, hatte dort Monate später immer noch kein Icon).
Live geprüft: tcgdex.dev hat das Set längst vollständig inkl. Icon. Neues
Modul `app/catalog/tcgdex_set_icon.py`, eingehängt in
`set_icon_cache.ensure_set_icon()` als Fallback bei 404/Fehler (Zuordnung
über Set-Namen, da tcgdex eigene Set-IDs nutzt). Cardmarket-ID-Redirect-
Idee (für die fehlende Preis-Verknüpfung) verworfen: drei plausible
URL-Muster live getestet, keins führt zur echten Produktseite. Live
end-to-end verifiziert (Perfect-Order-Icon lädt jetzt), 12 neue/angepasste
Tests grün, `compileall` sauber. Davor: Karten-Tab-Feinschliff auf Nutzerwunsch: Sprache/
Zustand/Menge-Spaltenüberschriften abgekürzt ("Spr."/"Zust."/"Anz.", da die
vollen Wörter in den bewusst schmalen Spalten abgeschnitten wurden) und
Kartendetail-Panel schmaler gemacht (260px Mindestbreite statt 320px,
Splitter-Anfangswerte 800/290 statt 730/360) — Kartenbilder sind ohnehin
schmal, die frei werdende Breite kommt der Kartentabelle zugute. Außerdem
noch offen aus derselben Nachricht: Katalogsuche fand "Poké Pad" ohne
Akzent nicht (behoben, siehe unten), fehlendes Set-Icon für "Perfect
Order" und fehlender Cardmarket-Link für dieselbe Karte sind beides
bestätigte pokemontcg.io-Datenlücken (kein eigener Bug) — Icon lädt
automatisch nach, sobald pokemontcg.io es nachreicht (kein negatives
Caching), Preis-Link lässt sich über "Eigener Cardmarket-Link" im
Bearbeiten-Dialog manuell nachtragen. Davor: EX-Serie-Set-Namen korrigiert: pokemontcg.io lässt bei
allen 16 EX-Sets (EX Ruby & Sapphire bis EX Power Keepers, IDs `ex1`-`ex16`)
das führende "EX " weg — Nutzer hat die offizielle Set-Liste geliefert,
live gegen alle 16 IDs bestätigt. Neue `_EX_SERIES_SET_NAMES`-Zuordnung in
`app/catalog/pokemontcg_client.py` korrigiert das jetzt in `list_sets()`
und beim Kartensuche-Parsing; Migration 8 backfillt bereits bestehende
Karten in der DB. 92 Tests grün (gezielt), `compileall` sauber. Davor:
Set-Icon-Lücke für manuell per Cardmarket-Link
eingetragene Karten geschlossen: neue `PokemonTcgClient.resolve_set_code()`
löst den pokemontcg.io-Set-Code best-effort aus dem freien Set-Namen auf
(Cardmarkets "EX Sandstorm" vs. pokemontcg.io's "Sandstorm"/`ex2`, live
bestätigt), läuft im Hintergrund-Thread des "Karte manuell eintragen"-Flows
(`ProductInfoWorker`), threaded durch `ProductInfo.set_code` →
`manual_add_confirmed`-Signal → `CardService.add_card_manual()`. 115 Tests
grün, `compileall` sauber. Davor: Reverse-Holo/Signed/1st-Ed/Altered-Filter
korrigiert:
`isSigned`/`isFirstEd`/`isAltered` waren fälschlich als `extra[isSigned]`
usw. verschachtelt (eine frühere, falsch verifizierte Annahme) — Cardmarkets
eigene Filter-Sidebar erzeugt für alle vier Extras (inkl. `isReverseHolo`)
bare Top-Level-Parameter, live vom Nutzer anhand der echten, per Klick auf
die Filter-Checkboxen erzeugten URLs bestätigt. Die falsch verschachtelten
Parameter haben das serverseitige Filtern vermutlich komplett lahmgelegt
(nicht nur ignoriert), was den ursprünglich gemeldeten Bug erklärt (eine
"nicht Reverse Holo"-Karte bekam trotzdem den Reverse-Preis). Erste
Einschätzung dazu war falsch (siehe unten, jetzt korrigiert): kein
Cardmarket-Datenproblem, sondern unser eigener, jetzt behobener Fehler.
Davor: Set-Name-Erkennung für nummerlose Karten ergänzt
(Breadcrumb-Auswertung statt nur Titel, siehe `_find_breadcrumb_set_name`).
Dabei zwei weitere Nutzer-Meldungen untersucht: (1) "findet bei keiner
manuell angelegten Karte mehr Infos" stellte sich als vorübergehende
Fenster-Fokus-Kollision durch eigene Diagnose-Skripte heraus (mehrere
offene Chrome/Firefox-Tabs mit "Cardmarket" im Titel), kein Code-Bug —
nach Neustart/Aufräumen ging es wieder. (2) Reverse-Holo-Filter lieferte
für eine manuell eingetragene Karte (Cacturne/Noktuska, EX Sandstorm) einen
16€-Preis, obwohl das die Reverse-Variante ist (normale Holo ab 28€) — der
Nutzer hat den von uns gebauten `isReverseHolo=N`-Link selbst direkt in
seinem Browser geöffnet und bestätigt, dass Cardmarket das Angebot
trotzdem anzeigt. Erste Einschätzung hier ("kein Bug in unserem Code",
Cardmarket-Datenproblem) war **falsch** — siehe den korrigierten Eintrag
oben im aktuellen "Letzter Schritt": tatsächlich waren `isSigned`/
`isFirstEd`/`isAltered` falsch als `extra[isSigned]` usw. verschachtelt,
was das serverseitige Filtern insgesamt lahmgelegt hat. Davor:
Karten manuell per Cardmarket-Link eintragen bekommt
jetzt auch eine Bild-Erfassung (Screenshot-Crop, derselbe Mechanismus wie
bei Sealed-Produkten, unverändert wiederverwendet) — vorher blieb
`photo_path` für solche Karten bewusst leer. Beim Live-Test dabei einen
zweiten, unabhängigen Bug gefunden und behoben: Karten ohne gedruckte
Nummer (z. B. "Shining Mew", Cardmarket-Kategorie "Unnumbered Promos")
ließen den ganzen "Karte manuell eintragen"-Ablauf lautlos scheitern (Tab
öffnete sich, aber keine Karte wurde angelegt) — Cardmarkets Titel lässt
für solche Karten die komplette "(Nummer) - Set"-Klausel weg, statt sie
leer zu lassen, sodass das Erkennungsmuster nie traf. Fällt jetzt auf
dasselbe schlichte Titel-Muster zurück, das Sealed-Produkte schon nutzen.
Beides live gegen die echte Cardmarket-Seite verifiziert (Name korrekt
erkannt, Bild korrekt erfasst). Davor: Bug korrekt behoben (erster Versuch
beruhte auf einer falschen Annahme, vom Nutzer per Screenshot widerlegt):
Sealed-Produkte mit
Sprache Japanisch/Koreanisch/Chinesisch bekamen beim Anlegen/Bearbeiten nie
einen `?language=N`-Filter auf den gespeicherten Cardmarket-Link, obwohl
Cardmarket diesen Filter (anders als bei Einzelkarten) auch auf
Sealed-Produktseiten für genau diese drei Sprachen anbietet
(live bestätigt: Japanisch=7, Koreanisch=10, Trad. Chinesisch=11). Ohne
Filter las die App die volle, ungefilterte Angebotsliste, wodurch Angebote
der gesuchten Sprache "weiter unten" landen und vom automatisierten
Auslesen verpasst werden konnten. Neue, Sealed-spezifische
Sprach-ID-Zuordnung ergänzt (bestehende, Karten-spezifische Zuordnung
bleibt unverändert, da Karten dort tatsächlich getrennte Produkte sind);
der "kein Ausweich-Preis"-Schutz bleibt für diese drei Sprachen zusätzlich
bestehen, jetzt korrekt begründet. Davor:
Sealed-Produkt-hinzufügen-Flow auf Nutzerwunsch von
zwei Dialogen (Link, dann Bestätigung) auf einen Dialog (Link + Sprache +
Menge + Notizen) zusammengelegt — Name und Kategorie kommen jetzt ohne
zweite Bestätigung automatisch von Cardmarket. Davor: nach dem
Sealed-Detailpanel-Ausbau drei Live-Bugs vom Nutzer gemeldet und behoben:
(1) Preis-Button im Detailpanel war nicht verdrahtet, (2) Preis-Abruf fand
nie ein Angebot (Sprachwort-Mismatch bei deutscher Cardmarket-Oberfläche),
(3) auf Nutzerwunsch grundsätzlich auf Locale-Kanonisierung (immer Englisch
für den technischen Preis-Abruf, unabhängig von der Sprache des
eingefügten Links) umgestellt, da die App perspektivisch öffentlich für
Nutzer in vielen Ländern gedacht ist. Dabei zusätzlich einen
Cardmarket-Cookie-Consent-Banner entdeckt und automatisch behandelt.
Außerdem neue "Gesamtpreis"-Spalte (Einzelpreis × Menge) in der
Sealed-Tabelle auf Nutzerwunsch.
**Datum:** 2026-07-06
**Version:** 0.1.0
**TestStatus:** ✅ 586 Tests grün (`pytest`, voller Lauf) · ✅ `compileall`
sauber · alle Fixes einzeln live gegen echte Cardmarket-Seiten verifiziert,
gezielte Testläufe (145 Sealed-Tests) nach dem Sprachfallback-Fix grün

---

## Sealed-Preis bei JP/KO/ZH: echter Sprachfilter statt "kein Fallback" (2026-07-06)

**Vom Nutzer gemeldet:** Sealed-Produkt "Abyss Eye Booster Box" mit Sprache
"Japanisch" angelegt (Link:
`cardmarket.com/en/Pokemon/Products/Booster-Boxes/Abyss-Eye-Booster-Box`).
Preis-Abruf lieferte einen Preis, der aber falsch war (stammte, wie ein
Screen-Reader-Dump zeigte, ausschließlich von **koreanischen** Angeboten).

**Erste, falsche Annahme:** Wie bei Einzelkarten seien Japanisch/
Koreanisch/Chinesisch bei Cardmarket eigenständige Produkte mit eigenem
Link (siehe `price_service.py`s `supports_language_filter()`), sodass ein
Fund nur koreanischer Angebote heißt "falscher Link verlinkt" — Fix
(inzwischen überholt): `SealedPriceService` bricht ohne exakten Treffer bei
diesen drei Sprachen mit `NO_PRICE` ab, statt auf eine andere Sprache
auszuweichen.

**Korrektur durch den Nutzer:** Per Screenshot gezeigt, dass Cardmarkets
eigene Filter-Sidebar auf genau dieser Sealed-Produktseite Japanisch/
Koreanisch/Trad. Chinesisch als Checkboxen anbietet — und live durch
eigenes Klicken bestätigt: `?language=7` (Japanisch), `?language=10`
(Koreanisch), `?language=11` (Trad. Chinesisch) filtern alle **dieselbe**
Seite. Bei Sealed-Produkten (anders als bei Einzelkarten) ist das also eine
reine Sprachvariante derselben Seite, keine getrennten Produkte.

**Eigentliche Ursache:** `SealedProductService._with_language_filter()`
nutzte die Karten-spezifische `supports_language_filter()` (liefert für
JP/KO/ZH bewusst `False`), wodurch der gespeicherte Sealed-Link für diese
drei Sprachen nie einen `?language=N`-Filter bekam. Ohne Filter las die App
die volle, ungefilterte Angebotsliste — die japanischen Angebote lagen in
diesem konkreten Fall weiter unten auf der Seite, als das automatisierte
Auslesen erreichte, sodass am Ende nur koreanische Angebote ankamen
(dieselbe Klasse Bug, die bei Karten schon durch serverseitiges Filtern
gelöst ist).

**Fix:** Neue, Sealed-spezifische Funktionen in `browser_price_reader.py`:
`_SEALED_CARDMARKET_LANGUAGE_IDS` (erweitert die bestehende, für Karten
unverändert bleibende Zuordnung um Japanisch=7/Koreanisch=10/Trad.
Chinesisch=11), `sealed_supports_language_filter()`,
`build_sealed_filtered_url()`. `SealedProductService._with_language_filter()`
nutzt jetzt diese statt der Karten-Funktionen, sodass der gespeicherte Link
für alle neun Sprachen korrekt gefiltert wird. Der bestehende
"kein Ausweich-Preis"-Schutz in `SealedPriceService._determine_price()`
bleibt für JP/KO/ZH bestehen (prüft weiterhin die Karten-spezifische
`supports_language_filter()` — die ist als "Fallback über Sprachen hinweg
ist hier riskant" weiterhin korrekt, unabhängig vom technischen
Filter-Mechanismus), Rationale-Text aber korrigiert: nicht mehr "eigenes
Produkt", sondern "aktuell keine Angebote in dieser Sprache".

**Tests:** `test_sealed_product_service.py` — Japanisch/Koreanisch/
Chinesisch bekommen jetzt ebenfalls den passenden `?language=N`-Filter
(vorher: unverändert gelassen). `test_browser_price_reader.py` — neue Tests
für `sealed_supports_language_filter`/`build_sealed_filtered_url`.
`test_sealed_price_service.py` — bestehende Tests weiterhin grün, Kommentar
korrigiert. Voller Testlauf grün, `compileall` sauber.

**Nachtrag, selber Tag:** Nutzer hat live nachgetestet und gemeldet, dass
weiterhin die volle, ungefilterte Liste durchsucht wird. Ursache: der
`?language=N`-Filter wurde nur beim Anlegen/Bearbeiten in den
gespeicherten Link geschrieben — das getestete Produkt existierte aber
schon von vorher (per DB-Check bestätigt: gespeicherter Link ganz ohne
Query-String), sodass sich am gespeicherten Link nie etwas ändert, egal wie
oft der Preis aktualisiert wird. Zweiter, robusterer Fix: `SealedPriceService.
_determine_price()` berechnet den Filter jetzt bei **jedem** Preis-Abruf
frisch aus `product.language` (mirrors `PriceService`, das für Karten
genauso arbeitet), statt sich auf den gespeicherten Link zu verlassen —
behebt damit auch alle bereits bestehenden Sealed-Produkte ohne erneutes
Bearbeiten. Dafür musste `build_sealed_filtered_url` idempotent gemacht
werden (ersetzt einen vorhandenen `?language=`-Parameter statt ihn
zweimal anzuhängen), da sonst neuere, schon gefilterte Links beim
Preis-Abruf `?language=X&language=Y` bekommen hätten. Neue Tests in
`test_sealed_price_service.py` (fehlender Filter wird ergänzt, vorhandener
nicht dupliziert) und `test_browser_price_reader.py`
(`test_build_sealed_filtered_url_is_idempotent_replaces_not_stacks`).

---

## Sealed-Produkt hinzufügen: ein Dialog statt zwei (2026-07-06)

**Ausgangslage:** Beim Testen des neuen Detailpanels fiel dem Nutzer auf,
dass beim Anlegen eines Sealed-Produkts zwischen dem Link-Dialog und dem
Bestätigungsdialog ein Chrome-Tab kurz aufflackert, ohne dass ersichtlich
ist, wofür — "dieses random Öffnen war vorher nicht da und es nervt
bisschen". Nachgefragt, ob sich der Zwischenschritt ganz vermeiden lässt.

**Analyse:** Der zweite Dialog (`SealedProductDetailsDialog`) hatte
ohnehin schon ein eigenes Cardmarket-Link-Feld (vorausgefüllt aus dem
ersten Dialog) — der erste, reine Link-Dialog war also strukturell
redundant. Einzig Name/Kategorie sind zum Zeitpunkt des ersten Dialogs noch
nicht bekannt (die kommen erst nach dem Cardmarket-Abruf).

**Geklärt mit dem Nutzer:** Erste Rückfrage war, ob die Kategorie stattdessen
selbst per Dropdown ausgewählt werden soll (analog zur Sprache) — Antwort:
"eigentlich will ich nicht viel selbst eintragen". Also: Name **und**
Kategorie bleiben komplett automatisch (Kategorie weiterhin per
Texterkennung geraten wie bisher), keine manuelle Auswahl nötig.

**Umsetzung:**
- Neue `SealedProductAddDialog` (`app/ui/dialogs/sealed_product_add_dialog.py`):
  nur Cardmarket-Link + Sprache + Menge + Notizen, keine Name-/Kategorie-Felder.
- `SealedEntryController`: zeigt jetzt diesen einen Dialog, startet danach
  den Hintergrund-Worker (Chrome-Tab-Lookup wie gehabt), und ruft bei Erfolg
  direkt `SealedProductController.add_product(name, category, values, photo_path)`
  auf -- kein zweiter, vom Panel gezeigter Dialog mehr dazwischen.
- `SealedProductController`: `_on_add_confirmed()` (Signal-Handler) zu
  öffentlichem `add_product()` gemacht, direkt aufrufbar.
- Aufgeräumt: `SealedProductListPanel.prompt_add()` und das
  `add_confirmed`-Signal komplett entfernt (nichts ruft sie mehr auf).

**Tests:** `test_sealed_entry_controller.py` neu geschrieben (Fake-Dialog
liefert jetzt auch `get_values()`, Fake-Controller hat `add_product()` statt
`prompt_add()`), `test_sealed_product_controller.py` angepasst (direkte
`add_product()`-Aufrufe statt Signal-Emits), neue
`test_sealed_product_add_dialog.py`. 143 Sealed-Tests grün.

---

## Sealed-Preisabruf: Locale-Kanonisierung + Cookie-Banner + Live-Bugfixes (2026-07-05)

**Ausgangslage:** Nach dem Detailpanel-Ausbau meldete der Nutzer beim
Live-Test drei aufeinanderfolgende Probleme:

1. **"Preis von Cardmarket abrufen" tat nichts.** Ursache: beim Anlegen des
   neuen Detailpanels wurde dessen `price_lookup_requested`-Signal schlicht
   nie mit dem `SealedPriceController` verbunden — reiner Verdrahtungsfehler
   beim Ausbau. Behoben: `SealedPriceController` bekommt jetzt optional das
   Detailpanel übergeben (mirrors `PriceController` bei Karten exakt),
   verbindet das Signal und deaktiviert den Button während der Abfrage.

2. **Button öffnete jetzt Chrome, fand aber nie einen Preis.** Live-Diagnose
   (temporäre Logzeile, die bei "keine Angebote erkannt" die kompletten
   erfassten Bildschirmtext-Zeilen mitloggt) zeigte: die Seite wurde
   korrekt gelesen (100+ Zeilen, echte Angebote sichtbar), aber
   `_parse_sealed_offer_lines` erkannte keine einzige Zeile als Angebot.
   **Ursache gefunden:** die Cardmarket-Angebotstabelle zeigt die Sprache
   pro Angebot in der Sprache der aufgerufenen Seite an ("Deutsch" auf
   `/de/`-URLs) — der Code kannte aber nur `Language.label` (englische
   Wörter wie "German"). Bei Karten fällt das nie auf, weil die
   dort das sprachunabhängige Zustands-Kürzel ("NM" etc.) als Anker nutzt;
   Sealed-Produkte haben keinen Zustand, also ist die Sprache dort der
   einzige Zeilen-Anker. Direkt gegen die echten geloggten Zeilen mit einem
   Test-Skript reproduziert und den Fix verifiziert (Erstversion: deutsche
   Wortliste ergänzt, 3/3 echte Angebote danach korrekt erkannt).

3. **Nutzer-Rückfrage:** Da die App perspektivisch öffentlich für Nutzer in
   vielen Ländern gedacht ist (Franzosen, Spanier etc. haben ihr eigenes
   Cardmarket auf ihre Sprache eingestellt), wäre eine Wortliste pro Sprache
   nicht skalierbar. Gemeinsam entschieden: strikte Trennung zwischen
   Datenbank/Suche (bleibt multilingual, betrifft Sealed-Produkte aber kaum,
   da es dafür keine feste Namensliste wie bei Pokémon-Arten gibt) und dem
   **technischen** Cardmarket-Scraping (soll auf eine kanonische Locale
   normalisiert werden). Umgesetzt: neue `with_canonical_locale()`-Funktion
   schreibt die URL nur für den eigentlichen Preis-Abruf auf `/en/` um
   (Name/Kategorie-Erfassung bleibt unangetastet bei der Original-URL); der
   **gespeicherte** Link bleibt in der Sprache, in der der Nutzer ihn
   eingefügt hat. Die deutsche Wortliste aus Schritt 2 bleibt als
   zusätzliches Sicherheitsnetz bestehen.

4. **Beim Live-Test der Locale-Kanonisierung zusätzlich entdeckt:**
   Cardmarkets eigener Cookie-Consent-Banner blockierte beim allerersten
   Besuch einer Locale (in diesem Fall `/en/`, erstmals in diesem
   Chrome-Profil aufgerufen) kurzzeitig die eigentliche Seite — ein Problem,
   das **jeden neuen Nutzer** bei seinem allerersten Preis-Abruf treffen
   würde, nicht nur ein Locale-Wechsel-Artefakt. Live als intermittierend
   bestätigt (nicht bei jedem Seitenaufruf). Behoben: neue
   `_dismiss_cookie_banner()`-Funktion sucht nach Klick auf "Nur
   erforderliche Cookies" (datensparsame Wahl, nicht "Alle akzeptieren"),
   best-effort und niemals blockierend; die bestehende
   "zu wenig Zeilen gelesen, nochmal versuchen"-Wiederholungslogik wurde um
   die Bedingung "Cookie-Banner-Text noch sichtbar" erweitert, da der
   Banner manchmal erst nach einem zweiten Anlauf zuverlässig weg-klickbar
   war (live bestätigt).

**Zusätzlich (Nutzerwunsch, parallel):** neue "Gesamtpreis"-Spalte
(Einzelpreis × Menge) in der Sealed-Produkttabelle — bei mehreren
Exemplaren desselben Produkts war der Gesamtwert vorher nicht direkt
ablesbar. Sortierbar, mit demselben ⚠️-Veraltet-Hinweis wie die anderen
Preis-Spalten.

**Tests:** neue Tests für `with_canonical_locale()` (Locale-Rewrite,
Query-String-Erhalt, No-op bei bereits-Englisch/unbekannter URL,
konfigurierbare Ziel-Locale) und `_has_cookie_banner()`; erweiterter
Regressionstest für die deutsche Sprachwort-Erkennung
(`test_parse_sealed_offer_lines_finds_offers_on_a_german_locale_page`);
neue Tests für die Detailpanel-Preis-Button-Verdrahtung
(`test_detail_panel_price_button_click_triggers_lookup`,
`test_button_is_reenabled_after_a_completed_lookup`) und die
Gesamtpreis-Spalte (Berechnung, Sortierung, "kein Preis"-Fall).

---

## Sealed-Tab: Detailpanel, Produktbild, Preisverlauf + Sprachlink-Fix (2026-07-05)

**Auftrag:** Der Sealed-Tab sollte strukturell genauso aufgebaut sein wie
der Karten-Tab (nur ohne Sammlungszuordnung): Detailpanel mit Produktbild,
"Preis aktualisieren"-Button, ausklappbarer Preisverlauf-Graph. Dazu:
konkret gemeldeter Bug, dass der beim manuellen Eintragen angegebene
Cardmarket-Link nicht um den Sprachfilter (`?language=N`) ergänzt wurde,
obwohl der Nutzer per eigenem Test bestätigt hat, dass Cardmarket diesen
Filter auch auf Sealed-Produktseiten unterstützt (Deutsch = `language=3`,
deckt sich mit der für Einzelkarten bereits live bestätigten Zuordnung).

**Recherche vor der Umsetzung:**
- Card-Architektur nachvollzogen: `CardDetailPanel` + `CardArtworkView`
  (Bild aus lokalem Cache, von pokemontcg.io heruntergeladen) +
  `PriceHistoryDock` (QtCharts-Liniendiagramm) + `price_history`-Tabelle,
  verdrahtet über `CardController` bei Selektionswechsel.
- Für Sealed-Produkte gibt es keine offizielle Bild-API wie pokemontcg.io
  — ein generischer HTTP-Fetch auf eine Cardmarket-Seite (`WebFetch`)
  ergab **HTTP 403** (Bot-Schutz), was erklärt, warum
  `browser_price_reader.py` bewusst kein HTTP-Scraping macht, sondern ein
  echtes, bereits offenes Chrome-Fenster per Windows UI-Automation ausliest.
- **Live-Spike durchgeführt:** echtes Chrome geöffnet, UI-Automation-Baum
  einer echten Cardmarket-Produktseite durchsucht — von 634 Elementen gab
  es genau 2 `Image`-Controls, eines mit `name` exakt gleich dem
  Produktnamen und einer sauberen ~478×478-Bounding-Box (eindeutig das
  Hauptproduktfoto, Icons/Logos waren andere Control-Typen). Bestätigt:
  das Bild lässt sich zuverlässig per Namensabgleich finden und per
  `PrintWindow`-Screenshot-Zuschnitt erfassen (dieselbe Technik, die diese
  Session schon für Screenshot-Verifikation nutzt).
- End-to-End-Spike gegen eine echte Cardmarket-Seite bestätigt: Name/
  Kategorie korrekt geparst, Bild korrekt zugeschnitten und gespeichert
  (visuell per Bildvorschau geprüft — tatsächlich das Booster-Pack-Foto,
  nicht verzerrt/falsch zugeschnitten).

**Umsetzung:**
- Migration 7 (append-only, wie gewohnt): `sealed_products.photo_path`
  (Spalte) + neue `sealed_price_history`-Tabelle (spiegelt `price_history`,
  `sealed_product_id` statt `card_id`).
- Neue Dateien: `app/models/sealed_price.py` (`SealedPriceRecord`),
  `app/database/repositories/sealed_price_repository.py`
  (`SealedPriceRepository`), `app/pricing/sealed_image_capture.py`
  (`capture_sealed_product_image()` — Bild-Element per Namensabgleich
  finden, per PrintWindow zuschneiden; best-effort, wirft nie, mirrors
  `ensure_card_image()`'s "never raises"-Vertrag),
  `app/ui/widgets/sealed_artwork_view.py` (`SealedArtworkView`, quadratisch
  statt 2.5:3.5, kein Reverse-Holo-Overlay),
  `app/ui/widgets/sealed_product_detail_panel.py`
  (`SealedProductDetailPanel`), `app/ui/widgets/sealed_price_history_dock.py`
  (`SealedPriceHistoryDock`, spiegelt `PriceHistoryDock` fast wörtlich).
- `_open_and_capture_visible_text()` (in `browser_price_reader.py`) bekam
  einen optionalen `on_window_ready`-Callback, aufgerufen direkt nach dem
  Text-Read, bevor der Tab geschlossen wird — damit lässt sich der
  Bild-Capture im selben, schon offenen Chrome-Tab durchführen, statt
  Chrome ein zweites Mal zu öffnen (Risiko: manche Seiten werten
  wiederholtes automatisiertes Öffnen als verdächtig).
- Da die Produkt-`id` erst nach dem DB-Insert bekannt ist (Autoincrement),
  wird das Bild zunächst in eine temporäre Datei erfasst und nach
  `repository.create()` per neuer `update_photo_path()`-Methode auf den
  finalen, ID-basierten Dateinamen umbenannt.
- `main_window.py`: Sealed-Tab von nacktem Panel auf einen Splitter
  (Liste | Detailpanel) umgebaut, ohne Sammlungsspalte (Sealed bleibt
  global/unscoped). Neues `SealedPriceHistoryDock` genauso ein-/ausklappbar
  wie das bestehende Karten-Dock; `_on_central_tab_changed()` blendet beim
  Tab-Wechsel automatisch das jeweils nicht mehr relevante Dock aus.
- `SealedProductController` verbindet jetzt (bisher ungenutzt!)
  `panel.selection_changed`, um Detailpanel + Preisverlauf-Dock zu
  synchronisieren — mirrors `CardController` fast 1:1.
- `SealedPriceService._record()` schreibt jetzt zusätzlich zum
  Preis-Schnappschuss (unverändert, Statistik hängt daran) einen
  `SealedPriceRecord` in die neue Historie-Tabelle.
- Sprachlink-Fix: neue Hilfsfunktion `_with_language_filter()` in
  `SealedProductService`, wiederverwendet die für Karten bereits
  bestehenden `supports_language_filter()`/`build_filtered_url()` aus
  `browser_price_reader.py`. Wird beim Anlegen UND Bearbeiten angewendet.
  Japanisch/Koreanisch/Chinesisch bleiben unverändert (separate
  Cardmarket-Produkte, kein Filter auf derselben Seite).
- `sealed_price_service.py`'s Modul-Docstring korrigiert (behauptete
  vorher fälschlich, der Filter sei "nie live geprüft" für Sealed-Produkte
  — ist jetzt live bestätigt).

**Tests:** neue Dateien `test_sealed_price_repository.py`,
`test_sealed_artwork_view.py`, `test_sealed_product_detail_panel.py`,
`test_sealed_price_history_dock.py`, `test_sealed_image_capture.py`
(Fake-UI-Automation-Objekte statt echtem Chrome), Migration-7-Tests in
`test_database.py`; bestehende Tests angepasst
(`test_sealed_product_controller.py`, `test_sealed_product_service.py`,
`test_sealed_entry_controller.py`, `test_sealed_price_service.py`).

---

## Alle Tabellenspalten sortierbar (Karten, Sealed, Statistik) (2026-07-05)

**Auftrag:** "mach die spalten alle sortierbar... mach das ruhig bei allem"
— bisher waren in der Kartenliste nur Name/Set/Sprache/Zustand sortierbar.

**Umsetzung:**
- Kartenliste: `_SORTABLE_COLUMNS` auf alle 8 Spalten erweitert; neue
  `_NumericItem`-Klasse (separat gespeicherter Zahlenwert statt
  angezeigtem Text) für Menge/Preis, da eine reine Textsortierung "10" vor
  "2" bzw. "1550.00" vor "20.00" einsortieren würde. Unbepreiste Karten
  sortieren als billigste (Sentinel `-1.0`, willkürliche aber konsistente
  Wahl).
- Sealed-Tab (nutzt Qt's eingebautes `setSortingEnabled`, nicht die
  Karten-eigene manuelle Sortierlogik): dieselbe `_NumericItem`-Klasse für
  Menge/Preis ergänzt.
- Statistik-Tab: alle reinen Übersichtstabellen sortierbar gemacht. Die
  beiden Tabellen mit eingebettetem "Preis aktualisieren"-Button pro Zeile
  sortieren stattdessen manuell (Qt's eingebautes Sortieren würde Cell-
  Widgets nicht mit den Zeilen mitverschieben) — Klick auf Kopfzeile sortiert
  die gespeicherten Einträge und rendert komplett neu.

**Tests:** `test_card_panel.py` erweitert (Ersatz für den jetzt ungültigen
"nicht-sortierbare-Spalte"-Test), neue Datei
`test_sealed_product_list_panel.py`, `test_statistics_panel.py` erweitert.
Voller Lauf: 540 Tests grün.

---

## Erkenntnis: Automatische Versions-Erkennung durch Fehl-Listing ausgetrickst (2026-07-04)

**Vom Nutzer erneut gemeldet:** Trotz des gedrosselten Umschalt-Mechanismus
(siehe voriger Eintrag) öffnete der Preis-Abruf für die Bisaflor-Karte
(Base Set, DE, 1st Edition) weiterhin die falsche Produktseite
("Shadowless" Englisch, `-V2-BS15`) statt der korrekten,
mehrsprachigen (`-V1-BS15`).

**Ursache gefunden:** Der Umschalt-Mechanismus prüft, ob die aktuelle
Sprache auf der Seite buchstäblich **null** Angebote hat, bevor er auf die
Alternativ-Version wechselt. Live bestätigt: auf der falschen `-V2-`-Seite
existierte tatsächlich **ein** deutsches Angebot (Zustand „Excellent",
nicht „Light Played" wie die echte Karte) — vermutlich ein Verkäufer, der
sein Base-Set-Exemplar auf der falschen Produktseite eingestellt hat (oder
eine Überschneidung in Cardmarkets eigener Kategorisierung). Dieses eine
Fehl-Listing reichte aus, damit die „keine Angebote"-Bedingung nie zutraf
— der Mechanismus schaltete nie auf die richtige Version um und lieferte
stattdessen einen geschätzten Preis (390 €, ESTIMATED_FROM_CONDITION) von
der falschen Seite.

**Bedeutung:** Die "keine Angebote = falsche Seite"-Heuristik ist damit
als **nicht ausreichend zuverlässig** für diesen Fall bestätigt — ein
einzelnes Fehl-Listing auf der falschen Seite kann sie täuschen. Der
Mechanismus selbst bleibt bestehen (er half in den Unit-Tests und könnte
in saubereren Fällen ohne Fehl-Listings noch greifen), aber er ist kein
verlässlicher Ersatz für eine bestätigte, manuell hinterlegte URL bei
bekannten kniffligen Vintage-Karten.

**Sofortmaßnahme:** Bisaflor-Karte (id 5) bekam den vom Nutzer erneut
bestätigten Link
(`https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Venusaur-V1-BS15`)
über „Eigener Cardmarket-Link" hinterlegt. Live-Ergebnis sofort danach:
„Exakter Treffer: German, Light Played", 164,90 € — ein klar präziserer
Treffer als die vorherigen 390 € (falsche Seite, geschätzter Zustand).

**Empfehlung für ähnliche Vintage-Fälle:** Sobald ein Nutzer den
korrekten Link für eine knifflige Vintage-Karte (mehrere
Cardmarket-Produktversionen) einmal bestätigt hat, diesen über „Eigener
Cardmarket-Link" hinterlegen, statt sich auf die automatische Erkennung
zu verlassen — sie bleibt ein nützlicher Versuch für den Normalfall, aber
kein Garant bei echten Fehl-Listings.

---

---

## Vintage-Multi-Versionen-Bug: gedrosselter Wiederaufgriff (2026-07-04)

**Vorgeschichte:** Ein erster Versuch (siehe „Verworfener Versuch" weiter
unten) öffnete bis zu 6 Kandidaten-Tabs ohne Pause und löste eine
temporäre Cardmarket-Sperre aus. Der Nutzer bat, das Thema später mit
strikter Drosselung erneut anzugehen. Vor der Umsetzung nochmal explizit
nachgefragt (gedrosselt-automatisch vs. nur manueller Link) — Nutzer
entschied sich für die gedrosselt-automatische Variante.

**Umsetzung, bewusst minimal riskant:**
- `app/pricing/browser_price_reader.py`: neue Funktion
  `find_alternate_version_url(url)` — erkennt ein Cardmarket-Produkt-Slug-
  Suffix `-V<n>` und gibt **genau eine** Alternativ-Version zurück (die
  nächstniedrigere zuerst, da der bestätigte Realfall — Base Set — die
  mehrsprachige Version bei der niedrigeren Nummer hat; sonst die nächst-
  höhere). Kein Kandidaten-Loop — es gibt nur diese eine Rückgabe pro Aufruf.
  - **Bug bei mir selbst gefunden, bevor er auffiel:** Die erste Regex-
    Version verlangte ein abschließendes „-" nach der Versionsnummer
    (`-V(\d+)-`). Ein Abgleich gegen die echten URLs in der Datenbank
    zeigte: das stimmt nicht immer — z. B. endet
    „.../Umbreon-VMAX-V1?utm_source=..." direkt am "?", ganz ohne
    folgenden Bindestrich. Behoben durch eine lockerere Regex
    (`-V(\d+)`) und direktes Ersetzen nur der Ziffern-Spanne (statt einer
    Template-Substitution), damit alles danach (Bindestrich, "?query",
    oder Stringende) unangetastet bleibt.
- `app/services/price_service.py`: neue Ladder-Stufe „2.5" — nur wenn
  Stufe 2 (gleiche Sprache, jede Zustandsstufe) buchstäblich **null**
  Angebote fand (nicht nur „kein exakter Treffer", sondern wirklich keine
  einzige Zeile), UND die URL ein Versions-Suffix hat: nach einer
  bewusst spürbaren Pause (Standard 3 Sekunden, per Konstruktor-Parameter
  überschreibbar) wird **genau ein** alternativer Versions-Tab probiert.
  Erfolg → korrigierte URL wird dauerhaft auf der Karte gespeichert
  (wie schon bei der Kurzlink-Auflösung). Kein Erfolg → normale Leiter
  läuft mit der ursprünglichen URL unverändert weiter, kein zweiter
  Alternativ-Versuch.

**Tests:** 4 neue Tests in `tests/test_browser_price_reader.py`
(niedrigere Version bevorzugt, Rückfall auf höhere bei V1, kein
Suffix → `None`, Suffix ohne abschließenden Bindestrich), 5 neue Tests in
`tests/test_price_service.py` (Umschalt-Erfolg inkl. URL-Persistierung,
kein Umschalt-Versuch bei modernen Karten ohne Suffix, kein Versuch wenn
Stufe 2 schon Angebote fand, sauberer Rückfall wenn auch die Alternative
leer bleibt, **die Pause wird tatsächlich aufgerufen** — verifiziert per
`monkeypatch` auf `time.sleep`) — 380 Tests insgesamt grün, `compileall`
sauber.

**Live-Check gegen die echte Bisaflor-Karte (id 5):** Preis-Abruf fand
diesmal echte deutsche Angebote **auf der bisherigen (V2-)Seite** (390 €,
„Geschätzt aus German, Zustand Excellent") — die URL blieb unverändert,
der neue Umschalt-Mechanismus griff also korrekt **nicht** ein, weil es
nicht nötig war (Cardmarkets Lagerbestand hat sich seit dem ursprünglichen
Bug-Report offenbar verändert). Der Umschalt-Pfad selbst wurde dadurch
live nicht ausgelöst — als zusätzliche, bewusste Vorsicht wurde kein
weiterer echter Cardmarket-Aufruf provoziert, nur um das zu erzwingen;
die Korrektheit des Mechanismus stützt sich auf die Unit-Tests, die direkt
mit den echten URL-Mustern aus der Datenbank des Nutzers aufgebaut sind.

---

---

## Schritt 11 — Export (CSV/Excel/JSON/PDF) (2026-07-04)

**Nutzerentscheidung:** Webcam-Scanner (Schritt 12) vorerst verwerfen,
stattdessen Export (Schritt 11) und die zwei bekannten Bugs angehen.

**Umsetzung:**
- Neue Abhängigkeiten: `openpyxl` (Excel), `reportlab` (PDF) — beide pure
  Python, keine externen Systemvoraussetzungen.
- `app/export/models.py`: `ExportRow` — eine flache, bereits formatierte
  Momentaufnahme einer Karte, unabhängig vom `Card`-Domänenobjekt, damit
  jeder Format-Writer nur mit einfachen Werten arbeitet.
- `app/export/csv_export.py`, `json_export.py`, `excel_export.py`,
  `pdf_export.py`: je ein Writer pro Format. CSV mit `utf-8-sig`-BOM
  (Excel erkennt die Kodierung sonst nicht zuverlässig, z. B. bei
  japanischen Kartennamen). JSON behält `price`/`quantity` als echte
  Zahlen (maschinenlesbar), die tabellarischen Formate formatieren den
  Preis als Text. PDF: Querformat-A4-Tabelle mit gewichteten
  Spaltenbreiten (lange Textspalten wie Name/Notizen breiter als kurze
  wie Nr./Sprache).
- `app/services/export_service.py`: `ExportService.export(format, path,
  collection_id)` — holt Karten (optional auf eine Sammlung
  eingeschränkt) + Sammlungsnamen, baut `ExportRow`s, delegiert an den
  passenden Writer. `manual_cardmarket_url` hat Vorrang vor der
  automatischen `cardmarket_url`, genau wie bei der Preisermittlung.
- `app/ui/dialogs/export_dialog.py` + `app/ui/controllers/
  export_controller.py`: Format- und Sammlungs-Auswahl, dann natives
  „Speichern unter"; die Dateiendung wird notfalls automatisch an das
  gewählte Format angepasst. Ersetzt den bisherigen Platzhalter am
  bereits existierenden Toolbar-„Export"-Knopf (der vorher nur „Export
  folgt in einem späteren Schritt" anzeigte).

**Bug gefunden und behoben, bevor er in Tests auffiel:** reportlabs
`Paragraph` interpretiert seinen Text als kleine XML-ähnliche
Auszeichnungssprache — eine Notiz wie "Zustand < NM" (ein einzelnes,
nicht geschlossenes "<") ließ den Parser abstürzen. Behoben durch
Escaping (`xml.sax.saxutils.escape`) jedes Zellenwerts vor der Übergabe.

**Bug gefunden und behoben, bevor er in Tests auffiel:** Die
Formatwiederg abe (`_MODULES`) band die Writer-Funktionen ursprünglich
beim Modul-Import fest gebunden — ein Test-Mock auf das Attribut des
Untermoduls hätte dadurch nie gegriffen. Behoben durch Referenzierung des
**Moduls** (nicht der Funktion), sodass `.write` bei jedem Aufruf frisch
nachgeschlagen wird.

**Tests:** 6 neue Testdateien (`test_csv_export.py`, `test_json_export.py`,
`test_excel_export.py`, `test_pdf_export.py`, `test_export_service.py`,
`test_export_dialog.py`, `test_export_controller.py`) — 34 neue Tests.

**Live-Check:** Echte Sammlung (19 Karten) in alle vier Formate
exportiert und Inhalt stichprobenartig geprüft (u. a. der manuelle
Cardmarket-Link erscheint korrekt statt der automatischen URL);
Export-Dialog per Offscreen-Rendering visuell bestätigt.

---

## Bugfix: Tolerante Suche scheiterte an Varianten-Wörtern wie "holo" (2026-07-04)

**Bekannte Einschränkung seit Schritt 5, jetzt behoben:** "xatu skyridge
holo" fand 0 Treffer, obwohl "xatu skyridge" funktionierte.

**Ursache:** pokemontcg.io behandelt einen mehrwortigen Namen als exakte
Phrase — "holo" beschreibt aber die physische Druckvariante, nicht Teil
des tatsächlichen Kartennamens ("Xatu" enthält nirgends das Wort "holo").
Der Name-Query enthielt "holo" trotzdem, wodurch die exakte Phrase nie
traf.

**Fix:** Neue Funktion `_strip_variant_words()` in
`catalog_search_service.py` entfernt bekannte Druckvarianten-Wörter/
-Phrasen ("holo", "reverse holo", "1st edition", "foil", "unlimited",
"shadowless", "promo") aus der Namens-Suche, **bevor** die Anfrage
überhaupt gestellt wird — es wird nicht versucht, danach zu filtern (da
pokemontcg.ios Raritäts-Daten bereits als unzuverlässig bekannt sind,
siehe früherer Eintrag), sondern nur verhindert, dass diese Wörter den
Namensabgleich stören. Bewusst **nicht** entfernt: "ex"/"gx"/"vmax" usw.
— die sind Teil der tatsächlichen Karten-Identität (eine andere,
eigenständige Karte), keine Druckvariante.

**Tests:** 4 neue Tests in `tests/test_catalog_search_service.py`
("holo" wird entfernt, "reverse holo"-Phrase wird entfernt, "1st
edition"-Phrase wird entfernt, "vmax" bleibt unangetastet) — 371 Tests
insgesamt grün, `compileall` sauber.

**Live-Check:** Gegen die echte API bestätigt — "xatu skyridge holo"
liefert jetzt beide echten Xatu-Karten aus Skyridge.

---

---

## Kartenliste: sortierbare Spalten (2026-07-04)

**Nutzerwunsch:** Kartenliste per Klick auf die Spaltenköpfe alphabetisch
sortierbar machen — konkret Name, Set, Sprache, Zustand.

**Umsetzung** (`app/ui/widgets/card_list_panel.py`):
- Nur die vier gewünschten Spalten sind klickbar-sortierbar
  (`_SORTABLE_COLUMNS`); Nr./Extra/Menge/Preis bleiben unverändert in der
  gegebenen Reihenfolge, da ein reiner Alphabet-Sort für eine gemischte
  Kartennummer oder einen Preis wenig sinnvoll wäre.
- Klick auf einen Spaltenkopf sortiert aufsteigend, nochmaliger Klick auf
  denselben kehrt auf absteigend um (wie in einer Tabellenkalkulation);
  ein kleiner Pfeil im Spaltenkopf zeigt Spalte + Richtung an.
- Neue `_CaseInsensitiveItem`-Klasse sorgt für echte alphabetische
  Sortierung ohne Berücksichtigung von Groß-/Kleinschreibung (Qt's
  Standardvergleich ist sonst case-sensitiv, "eevee" würde nach "Zebra"
  sortieren).
- Die gewählte Sortierung wird gemerkt und nach jedem `set_cards()`-Aufruf
  (z. B. nach dem Bearbeiten einer Karte) automatisch erneut angewendet,
  statt beim nächsten Aktualisieren stillschweigend verloren zu gehen.

**Tests:** 6 neue Tests in `tests/test_card_panel.py` (aufsteigend/
absteigend, Groß-/Kleinschreibung, nicht-sortierbare Spalte ignoriert,
Sortierung übersteht `set_cards()`, Auswahl bleibt beim Sortieren
erhalten) — 337 Tests insgesamt grün, `compileall` sauber.

**Live-Check:** Per Offscreen-Rendering gegen die echte Sammlung bestätigt
— Sortierung nach Name (auf-/absteigend) und nach Sprache (DE→EN→FR→JP)
funktioniert korrekt, Sortier-Pfeil im Spaltenkopf sichtbar.

---

---

## Bugfix: Seiteninhalt zu früh ausgelesen (nur Chrome-Oberfläche erfasst) (2026-07-04)

**Vom Nutzer gemeldet:** Neu hinzugefügte deutsche "Psiana VMAX" (Espeon
VMAX, Fusion Strike): Preis-Button öffnete die korrekte Cardmarket-Seite,
speicherte aber wieder keinen Preis. Zusätzlicher Hinweis: cardmarket_url
kommt tatsächlich immer von pokemontcg.io (dabei einen weiteren
Timeout-Bug bei der Link-Auflösung gefunden und behoben, siehe voriger
Eintrag).

**Live reproduziert und Ursache gefunden:** Ein Diagnose-Skript öffnete
dieselbe echte Karte und dumpte den rohen erfassten Text: nur **21
Zeilen**, praktisch nur Chrome-Oberfläche (Minimieren/Schließen/
Adressleiste) — der Fenstertitel zeigte aber schon korrekt "Psiana VMAX |
Cardmarket". Das beweist: die Seite hatte sich schon umbenannt (JS setzt
den Titel beim Navigationsstart), aber der eigentliche Seiteninhalt (die
Angebotstabelle) war beim Auslesen (nach der festen 2-Sekunden-Wartezeit)
noch nicht fertig gerendert.

**Fix:** `_open_and_capture_visible_text()` prüft jetzt, ob die erste
Erfassung auffällig wenig ergibt (unter 30 Zeilen) — wenn ja, wartet sie
automatisch noch einmal 2 Sekunden und liest erneut, bevor sie aufgibt.

**Live-Check:** Zweiter Versuch bei derselben Karte: aus 20 sparsamen
Zeilen wurden 145 echte Zeilen mit 3 erkannten Angeboten (194,99 €,
199,99 €, 200,00 €) — Preis wurde korrekt gespeichert ("Exakter Treffer:
German, Excellent", 194,99 €).

**Tests:** 1 neuer Test in `tests/test_browser_price_reader.py`
(`test_read_visible_text_skips_invisible_and_empty_and_errored_nodes`,
für die neu extrahierte, jetzt testbare `_read_visible_text()`-Hilfsfunktion)
— 331 Tests insgesamt grün, `compileall` sauber.

---

---

## Robustheit: Wiederholung auch bei der Cardmarket-Link-Auflösung (2026-07-04)

**Vom Nutzer beobachtet:** Bei einer neu hinzugefügten deutschen "Psiana
ex"-Karte (Espeon) mit gesetztem eigenem Link zeigte der erste Klick auf
"Preis abrufen" eine URL, die "von der API" kam und nicht lud; der Nutzer
schloss den Tab manuell und klickte erneut — dann lud die echte
Cardmarket-Seite. Der Preis wurde trotzdem nicht gespeichert.

**Ursache gefunden:** `resolve_cardmarket_url()` (löst pokemontcg.ios
Tracking-Kurzlink `prices.pokemontcg.io/cardmarket/<id>` zur echten
`cardmarket.com`-Seite auf, bevor der Browser geöffnet wird) hatte **gar
keine Wiederholung** bei einem Timeout — nur einen einzelnen Versuch mit
10 Sekunden Timeout, danach stiller Rückfall auf den **unaufgelösten**
Kurzlink. Da `prices.pokemontcg.io` vom selben, zu diesem Zeitpunkt
nachweislich kurzzeitig langsamen Anbieter (pokemontcg.io, siehe voriger
Eintrag) bedient wird, erklärt das genau das erste Klick-Erlebnis: ein
Timeout bei der Auflösung öffnete den rohen Kurzlink im Browser (der keine
echte Produktseite ist), ein zweiter Klick traf auf einen weniger
ausgelasteten Moment und funktionierte.

**Fix:** `resolve_cardmarket_url()` wiederholt jetzt genau wie
`PokemonTcgClient` einmal bei Timeout/Verbindungsfehler, bevor auf den
unaufgelösten Link zurückgefallen wird.

**Noch ungeklärt:** Die zugehörige "Psiana ex"-Karte selbst war zum
Zeitpunkt der Recherche in der echten Datenbank nicht auffindbar (höchste
vorhandene Karten-ID war 20, "Espeon VMAX") — beim Nutzer nachgefragt, ob
die Karte tatsächlich gespeichert wurde, um den "trotz korrektem Link kein
Preis gespeichert"-Teil der Meldung weiter zu untersuchen.

**Tests:** 1 neuer Test in `tests/test_browser_price_reader.py`
(`test_resolve_cardmarket_url_retries_once_on_timeout_and_succeeds`),
bestehender Fehlerfall-Test um `retry_delay=0` + Aufruf-Zähler ergänzt —
330 Tests insgesamt grün, `compileall` sauber.

---

---

## Robustheit: Wiederholung bei pokemontcg.io-Timeouts (2026-07-04)

**Vom Nutzer gemeldet:** Suche nach "psiana vmax" zeigte "Der Kartenkatalog
(pokemontcg.io) ist gerade nicht erreichbar." — direkt im Anschluss an den
Suche-Bugfix von eben, daher zunächst als möglicher neuer Fehler geprüft.

**Ursache live bestätigt, kein Code-Bug:** Direkte Testabfragen
(`curl`/eigenes Python-Skript) gegen die echte pokemontcg.io-API zeigten
zum Zeitpunkt der Meldung tatsächlich **~30 Sekunden Antwortzeit** für
dieselbe Anfrage — deutlich über dem konfigurierten 20-Sekunden-Timeout
des Clients. Log bestätigte zwei aufeinanderfolgende `Read timed out`-
Fehler. pokemontcg.io war zu diesem Zeitpunkt selbst spürbar langsam,
kurz danach wieder normal.

**Verbessert:** `PokemonTcgClient` (`app/catalog/pokemontcg_client.py`)
wiederholt eine Anfrage jetzt automatisch einmal bei Timeout/
Verbindungsfehler (mit kurzer Pause dazwischen), bevor der bisherige
Fehler ("Kartenkatalog nicht erreichbar") geworfen wird — ein einzelner,
kurzer Aussetzer beim Anbieter lässt die Suche jetzt nicht mehr sofort
scheitern. Ein echter HTTP-Fehlerstatus (404/500) wird weiterhin nicht
wiederholt, da das eine konkrete Server-Antwort ist, keine transiente
Störung.

**Tests:** 2 neue Tests in `tests/test_pokemontcg_client.py`
(`test_search_retries_once_on_timeout_and_succeeds`,
`test_search_raises_after_exhausting_retries_on_persistent_timeout`);
bestehende Fehlerfall-Tests bekamen `retry_delay=0`, damit sie nicht durch
die neue Wartezeit verlangsamt werden — 329 Tests insgesamt grün,
`compileall` sauber.

**Live-Check:** Gegen die echte, zu diesem Zeitpunkt weiterhin langsame
API bestätigt — "psiana vmax" liefert jetzt zuverlässig echte Treffer
(Espeon VMAX, Evolving Skies #65 und Fusion Strike #270).

---

---

## Bugfix: Zweisprachige Suche scheiterte an Karten-Suffixen wie "VMAX" (2026-07-04)

**Vom Nutzer gemeldet:** "Jolteon VMAX" fand Treffer, "Blitza VMAX"
(deutscher Name) gar keine — mit der Frage, ob wirklich alle
Karten-Übersetzungen vorhanden sind.

**Ursache gefunden:** Nicht die Übersetzungsdaten fehlten (die reale
Tabelle hat 3584 Einträge, `"blitza"` → `"Jolteon"` ist enthalten und
funktioniert einzeln einwandfrei) — sondern `_search_name_tolerantly()`
übergab den **kompletten** Suchtext ("Blitza VMAX") an
`translate_to_english()`. Die interne Normalisierung verschmilzt Text zu
einem einzigen String ("blitzavmax"), und dieser zusammengesetzte String
existiert nirgends als Schlüssel in der Tabelle (nur die reine
Artnamen-Form "blitza" tut es) — die Übersetzung schlug also für jede
Suche mit Karten-Suffix (VMAX/EX/GX/V/ex — praktisch jede moderne Karte)
komplett fehl.

**Fix:** Neue Funktion `_translate_name_with_suffix()` in
`catalog_search_service.py` probiert beim Übersetzen zunächst den
kompletten Text, dann schrittweise kürzere Wort-Präfixe (von hinten
abschneidend) durch, bis eine Übersetzung greift, und hängt den
unübersetzten Rest (z. B. "VMAX") wieder an — aus "Blitza VMAX" wird so
korrekt "Jolteon VMAX".

**Tests:** 1 neuer Test in `tests/test_catalog_search_service.py`
(`test_foreign_language_name_with_card_type_suffix_is_translated`) — 327
Tests insgesamt grün, `compileall` sauber.

**Live-Check:** Gegen die echte Katalog-API bestätigt — "Blitza VMAX"
liefert jetzt "Jolteon VMAX" (Evolving Skies #51 und SWSH Black Star
Promos).

---

---

## Bugfix: Bezeichnungsvorschlag schlug einen 16 Jahre falschen Kandidaten vor (2026-07-04)

**Vom Nutzer angestoßen:** Frage, wie moderne japanische Karten (Beispiel:
Umbreon VMAX, die es auch auf Japanisch gibt) gelöst werden. Direkter
Live-Test zeigte: der bestehende Bezeichnungsvorschlag (siehe vorheriger
Eintrag) schlug für Umbreon VMAX (Evolving Skies, EN 2021) "Umbreon
（デルタ種）" aus dem Set "ホロンの研究塔" (Holon Research Tower, **2005**)
vor — 16 Jahre Abstand, eindeutig eine andere, viel ältere Karte.

**Ursache:** tcgdex hat schlicht **keinen echten japanischen Sword-&-
Shield-Ära-Eintrag** für diese Karte (dieselbe Abdeckungslücke, die schon
beim ersten tcgdex-Test auffiel). Der "zeitlich nächstgelegene Kandidat
vor dem Erscheinungsdatum"-Algorithmus wählte trotzdem den einzigen
verfügbaren Kandidaten mit passender Pokédex-Nummer, ganz gleich wie weit
entfernt — es gab keine Plausibilitätsprüfung.

**Fix:** `app/catalog/tcgdex_designation_lookup.py` lehnt jetzt jeden
Kandidaten ab, dessen Set-Erscheinungsdatum mehr als 730 Tage (2 Jahre) vom
westlichen Erscheinungsdatum entfernt liegt — eine echte Lokalisierungs-
Verzögerung liegt selbst bei alten Sets nie annähernd so weit auseinander
(Neo Revelation z. B. nur ~10 Monate). In diesem Fall liefert die Funktion
jetzt korrekt `None` ("kein verlässlicher Vorschlag") statt zu raten.

**Für den Nutzer bedeutet das konkret:** Für moderne japanische Karten wie
Umbreon VMAX, die tcgdex nicht kennt, gibt es (noch) keinen automatischen
Bezeichnungsvorschlag — der Preis-Abbruch zeigt dann nur die bestehende
Meldung ohne Zusatz-Hinweis. Die richtige Cardmarket-Bezeichnung muss in
diesem Fall weiterhin selbst recherchiert werden (z. B. über Bulbapedia)
und über "Eigener Cardmarket-Link" hinterlegt werden.

**Tests:** 1 neuer Test in `tests/test_tcgdex_designation_lookup.py`
(`test_implausibly_distant_candidate_is_rejected_instead_of_guessed`,
mit den echten Umbreon-VMAX-Daten nachgebaut) — 326 Tests insgesamt grün,
`compileall` sauber.

**Live-Check:** Gegen die echte API bestätigt — Umbreon VMAX liefert jetzt
`None`, Ho-Oh liefert weiterhin korrekt "めざめる伝説".

---

---

## Bugfix: Preis-Erkennung scheiterte an englischem Zahlenformat (2026-07-04)

**Vom Nutzer gemeldet:** Preis-Lookup öffnete wieder die richtige
Cardmarket-Seite, registrierte aber wieder keinen Preis ("keine Angebote
gefunden") — diesmal bei einer westlichen (englischsprachigen) Karte
(Umbreon VMAX #215), nicht bei einem Fokus-/Timing-Problem wie zuvor.

**Ursache gefunden:** `_PRICE_RE` in `app/pricing/browser_price_reader.py`
war fest auf deutsches Zahlenformat kodiert (`\d{1,3}(?:\.\d{3})*,\d{2}`,
also z. B. "1.550,00"). Cardmarkets aufgelöste URL kann aber je nach
Session/Redirect auf verschiedene Sprachpräfixe zeigen (`/de/` vs. `/en/`)
— unter `/en/` rendert die Seite Preise im englischen Format
("1,550.00 €", Komma als Tausender-, Punkt als Dezimaltrennzeichen). Die
alte Regex matchte das gar nicht, jede Angebotszeile wurde stillschweigend
verworfen, obwohl die Seite voller echter Angebote war.

**Fix:** `_PRICE_RE` erkennt jetzt beide Trennzeichen (`[.,]`) vor den
letzten beiden Nachkommastellen; `_parse_price()` bestimmt das tatsächliche
Dezimaltrennzeichen dynamisch als das **letzte** vorkommende Komma/Punkt
(alles davor sind Tausendertrennzeichen, werden einfach entfernt) —
funktioniert damit unabhängig von der Locale.

**Tests:** 2 neue Tests in `tests/test_browser_price_reader.py`
(`test_english_locale_number_format_is_parsed_correctly`,
`test_english_locale_number_format_without_thousands_separator`) — 325
Tests insgesamt grün, `compileall` sauber.

**Live-Check:** Gegen die echte, reale Umbreon-VMAX-Karte (#215) bestätigt
— Preis-Lookup fand jetzt korrekt 1.550,00 EUR ("Exakter Treffer: English,
Near Mint"), wo vorher "keine Angebote gefunden" kam.

---

---

## tcgdex.dev nur für Bezeichnungen (nie Preise) wieder eingebaut (2026-07-04)

**Nutzerwunsch nach dem tcgdex-Preis-Revert:** „nutze nur die API für die
Bezeichnung von japanischen Karten, die so über CM gefunden werden können“
— also ausschließlich Namen/Set-Bezeichnungen, niemals Preise.

**Recherchiert, wie eine sprachübergreifende Zuordnung überhaupt zuverlässig
möglich ist** (live gegen die echte API getestet, am eigenen Ho-Oh-Fall
verifiziert):
- tcgdex vergibt pro **Locale eine eigene, unabhängige Set-ID-Sequenz** —
  dieselbe ID (z. B. `"neo3"`) bedeutet auf Englisch "Neo Revelation", auf
  Japanisch aber "めざめる伝説" (Awakening Legend, ein komplett anderes
  Set)! IDs dürfen also nie locale-übergreifend wiederverwendet werden.
- Funktionierender Ansatz: die eigene, bereits gespeicherte
  `external_card_id` (identisch zu pokemontcg.io) gegen tcgdex' `/en/`-
  Locale auflösen → liefert die nationale Pokédex-Nummer (`dexId`) und das
  Erscheinungsdatum des westlichen Sets. Damit dann in der Ziel-Locale
  (`ja`/`ko`/`zh-tw`) nach allen Karten mit derselben `dexId` suchen (meist
  nur eine Handvoll Kandidaten) und denjenigen wählen, dessen Set am
  nächsten **vor** dem westlichen Erscheinungsdatum herauskam (eine
  fremdsprachige Erstveröffentlichung geht der westlichen Lokalisierung
  praktisch immer zeitlich voraus).
- **Live am eigenen Ho-Oh-Fall bestätigt:** Neo Revelation (EN, erschienen
  2001-09-21) → korrekt als "めざめる伝説"/Awakening Legend (JA, erschienen
  2000-11-23) identifiziert — exakt der vom Nutzer selbst unabhängig
  bestätigte Cardmarket-Link, unter drei Kandidaten mit gleicher `dexId`
  (die anderen beiden: ein 2005er- und ein 2024er-Reprint, klar zu weit
  entfernt).
- **Bekannte Lücke:** Koreanisch und Chinesisch (`zh-tw`/`zh-cn`) lieferten
  für dieselbe, sehr verbreitete Spezies **null Kandidaten** — die Funktion
  wird also praktisch nur für japanische Karten etwas finden, degradiert
  aber sauber auf "keine Vorschlag" statt zu raten oder zu fehlern.

**Umsetzung:**
- `app/catalog/tcgdex_designation_lookup.py` (neu):
  `find_localized_designation(external_card_id, language)` — reine Namens-
  /Set-Auflösung wie oben beschrieben, **kein Preisfeld wird je gelesen**.
- `PriceService._designation_hint()`: wird ausschließlich in der bereits
  bestehenden JP/KO/ZH-Abbruch-Meldung (kein eigener Cardmarket-Link
  gesetzt) angehängt — ergänzt die Begründung um "Mögliche Bezeichnung auf
  Cardmarket (via tcgdex.dev): „ho-oh“, Set „めざめる伝説“, Nr. 011.", ändert
  aber nie `current_price`/`price_quality`. Bestehendes Verhalten (Abbruch,
  manueller Link hat Vorrang) bleibt unverändert.

**Tests:** `tests/test_tcgdex_designation_lookup.py` (neu, 7 Tests, u. a.
der reale Ho-Oh-Fall mit gefälschten HTTP-Antworten), 2 neue Tests in
`tests/test_price_service.py` (Bezeichnungs-Vorschlag erscheint in der
Begründung; ein Lookup-Fehler lässt den bestehenden Abbruch unverändert
funktionieren) — 323 Tests insgesamt grün, `compileall` sauber.

**Live-Check:** Gegen die echte API und die echte Ho-Oh-Karte des Nutzers
bestätigt (manueller Link temporär entfernt, Vorschlag geprüft, Link exakt
wiederhergestellt) — Begründung enthielt korrekt „めざめる伝説“/Nr. 011,
`current_price` blieb `None`.

---

## tcgdex.dev als Preisquelle wieder entfernt (2026-07-04)

**Vom Nutzer live widerlegt:** Direkter Vergleich mit der echten Cardmarket-
Seite zeigte, dass tcgdex' Preisdaten unzuverlässig sind — für Xatu
(Skyridge #H32) lieferte tcgdex 3,09 EUR, während der echte Cardmarket-
Preis-Trend bei ~197,78 € liegt (Screenshot-Vergleich). Nutzerentscheidung:
tcgdex nur noch für Bezeichnungen/Stammdaten in Betracht ziehen, **niemals
für Preise** — Preisermittlung ist wieder ausschließlich Cardmarket
("CM only").

**Rückgängig gemacht:**
- `app/pricing/tcgdex_client.py` und `tests/test_tcgdex_client.py` gelöscht.
- `PriceService.update_price_for_card()`: der tcgdex-Vorab-Check entfernt,
  Preisermittlung läuft wieder unverändert wie vor dem tcgdex-Einbau (nur
  Cardmarket-Automatisierung + manueller Link für JP/KO/ZH).
- `tests/test_price_service.py`: `FakeTcgdexClient` und die 6 tcgdex-
  spezifischen Tests entfernt, `_service()`-Helfer zurückgebaut.
- `PriceQuality.MARKET_TREND` bleibt als Enum-Wert bestehen (nicht mehr
  produziert, aber nötig, damit bereits gespeicherte Datensätze mit diesem
  Wert weiterhin korrekt geladen werden können) — Docstring als „Legacy“
  gekennzeichnet.

**Echte Datenbank bereinigt:** 5 Karten hatten durch den kurzen Testzeitraum
einen falschen tcgdex-Preis gespeichert (u. a. Xatu #H32: 3,09 € statt
korrekt; Umbreon VMAX #215: 2701 € ungeprüft übernommen). Alle 5 auf
„Kein Preis“ zurückgesetzt (inkl. der zugehörigen fehlerhaften
Preisverlauf-Einträge), mit dem Hinweis, künftig manuell über den
bestehenden Cardmarket-Button zu aktualisieren.

**Tests:** 314 Tests grün (Stand vor dem tcgdex-Einbau wiederhergestellt),
`compileall` sauber.

---

---

## tcgdex.dev als vorgelagerte Preisquelle eingebaut (2026-07-04)

**Umsetzung** (siehe Recherche-Eintrag oben für den Hintergrund):
- `app/pricing/tcgdex_client.py` (neu): `TcgdexClient.get_market_price(card_id)`
  — ruft `GET https://api.tcgdex.net/v2/en/cards/{card_id}` auf (derselbe
  `external_card_id`, den pokemontcg.io für westliche Karten schon liefert)
  und liest `pricing.cardmarket.trend` (+ `avg30`/`low`/`updated`) aus.
  Liefert `None` bei fehlender Abdeckung, wirft `TcgdexClientError` nur bei
  echtem Netzwerk-/HTTP-Fehler.
- `PriceQuality.MARKET_TREND` (neu): kennzeichnet einen von tcgdex
  übernommenen Preis als das, was er ist — ein ungefilterter Marktpreis-
  Trend, keine exakte Sprache/Zustand-Übereinstimmung wie bei den
  bestehenden Stufen.
- `PriceService.update_price_for_card()`: versucht tcgdex **nur** für
  Sprachen mit gemeinsamer westlicher Cardmarket-Produktseite
  (`supports_language_filter(card.language)`) **und nur**, wenn kein
  eigener Cardmarket-Link gesetzt ist (ein bewusster Nutzer-Override darf
  nie stillschweigend übersprungen werden). Bei Treffer wird die
  Chrome-basierte Preisermittlung komplett übersprungen. Japanisch/
  Koreanisch/Chinesisch bleiben unverändert beim Sicherheits-Abbruch bzw.
  eigenen Link, da tcgdex dafür auf das falsche (westliche) Produkt zeigen
  würde — siehe die Recherche-Lücken oben.

**Bug gefunden und behoben, bevor er live ausgeliefert wurde:** Die erste
Implementierung ging (basierend auf einer per Webabruf zusammengefassten
Beschreibung der API) von einem obersten `cardmarket`-Feld aus. Ein
direkter Live-Abruf zeigte: das Feld liegt tatsächlich unter
`pricing.cardmarket`, nicht auf oberster Ebene — die Zusammenfassung hatte
die Verschachtelungstiefe falsch wiedergegeben. Behoben durch Anpassen des
Zugriffspfads; danach live gegen die echte API erneut bestätigt (siehe
unten). **Lehre:** externe API-Strukturen vor dem Implementieren immer mit
einem echten, rohen HTTP-Aufruf verifizieren, nicht nur mit einer per
Sprachmodell zusammengefassten Beschreibung.

**Ebenfalls beim Einbau behoben:** `tests/test_price_service.py`s
`_service()`-Test-Helfer erzeugte bisher kein Fake für die neue,
standardmäßig echte `TcgdexClient()`-Abhängigkeit — jeder bestehende Test
mit einer westsprachigen Karte hätte sonst einen echten Netzwerkaufruf an
tcgdex.dev ausgelöst. Durch eine neue `FakeTcgdexClient` (liefert
standardmäßig „keine Abdeckung“) im Helfer behoben, bevor es in den echten
Testlauf ging.

**Live-Check gegen die echte Sammlung:**
- Umbreon VMAX #215 (Evolving Skies, id 13, Englisch): tcgdex lieferte den
  echten, aktuellen Marktpreis (2701 EUR Trend) — kein Chrome-Tab wurde
  geöffnet.
- Ho-Oh (Japanisch, id 9, mit gesetztem eigenen Cardmarket-Link): tcgdex
  wurde korrekt übersprungen, die bestehende Ladder lief stattdessen gegen
  den manuellen Link (wie zuvor schon bestätigt).

**Tests:** `tests/test_tcgdex_client.py` (neu, 7 Tests), Erweiterungen in
`tests/test_price_service.py` (6 neue Tests: Treffer, keine Abdeckung →
Fallback, nie versucht bei JP/KO/ZH, manueller Link hat Vorrang, Fehler →
Fallback, kein `external_card_id` → übersprungen) — 327 Tests insgesamt
grün, `compileall` sauber.

---

## Recherche: tcgdex.dev als Zusatz-Preisquelle (2026-07-04)

**Anlass:** Nutzer wies auf `https://tcgdex.dev/` hin (wirbt mit "10+
Sprachen") als möglichen Ausweg aus dem JP/KO/ZH-Preisproblem.

**Live gegen die echte API getestet** (`https://api.tcgdex.net/v2/...`):
- Bietet echte, sprachspezifische Kartendaten — `GET /v2/ja/cards/neo3-011`
  liefert für Ho-Oh korrekt das japanische Set `"めざめる伝説"` (Awakening
  Legend), nicht das westliche "Neo Revelation". Gezielte Namensfilter
  (`?name=like:...`, auch mit japanischer Schrift) funktionieren zuverlässig.
- Enthält teils ein eingebautes `cardmarket`-Preisfeld direkt in den
  Kartendaten (inkl. `idProduct`, `avg`/`low`/`trend`/`avg1`/`avg7`/`avg30`)
  — für die westliche Umbreon VMAX (Evolving Skies #215) vollständig befüllt.
- **Lücken, die eine automatische Lösung verhindern:**
  - Für die eigene Ho-Oh-Karte des Nutzers (Neo Revelation/Awakening Legend)
    ist das `cardmarket`-Feld `null` — keine Preisdaten für genau den
    Fall, den wir lösen wollen.
  - Umbreon VMAX (Sword & Shield-Ära, ~2021) taucht unter der `ja`-Locale
    **gar nicht** auf, weder unter "Umbreon" noch unter der japanischen
    Schreibweise "ブラッキー" — die japanische Kartendatenbank selbst hat
    Lücken, nicht nur die Preisdaten.
  - `ko`-Locale lieferte für dieselbe Suche **null Treffer** — Korea-
    Abdeckung wirkt praktisch nicht vorhanden, zumindest unter diesem Namen.
  - Kein Verknüpfungsfeld zwischen einer englischen Karte und ihrem
    japanischen Pendant — die Zuordnung müsste weiterhin selbst hergestellt
    werden (Namensübersetzung + Kartennummer + Set), ähnlich wie bei der
    bestehenden Suchtoleranz.

**Bewertung:** Echte, risikofreie (kein Bot-Schutz, direkte API) Zusatzquelle
mit echten Cardmarket-Preisen für manche Karten — aber Abdeckung für
JP/KO/ZH lückenhaft, gerade bei älteren/selteneren Karten (also genau denen,
bei denen die bestehende Zwischenlösung/manueller Link gebraucht wird).
Eingeplant als **zusätzliche, vorgelagerte Quelle** ("erst tcgdex versuchen,
sonst bestehende Methode/manueller Link"), nicht als Ersatz.

**Nutzerentscheidung:** Recherche festhalten (hier erledigt), dann direkt
mit dem Einbau von tcgdex weitermachen.

---

## Zwischenlösung: JP/KO/ZH-Cardmarket-Zuordnung (2026-07-04)

**Ausgangslage:** Cardmarket führt japanische/koreanische/chinesische
Drucke als eigenständige Produkte unter dem *japanischen* Set-Namen (z. B.
Neo Revelations Ho-Oh als "Awakening Legends"), nicht als Sprachfilter auf
derselben Produktseite. `pokemontcg.io`s `cardmarket_url` zeigt für diese
Karten daher immer auf das falsche (westliche) Produkt — die Preis-Leiter
fiel bisher unbemerkt bis zur letzten, ungefilterten Stufe durch und
berechnete einen Preis aus unbeteiligten westlichen Angeboten.

**Recherchiert, warum keine automatische Auflösung möglich ist:**
- Bulbapedias einzelne Set-Seiten nennen zwar die japanischen Quell-Sets
  im Fließtext (z. B. Evolving Skies ← Skyscraping Perfection + Blue Sky
  Stream + Eevee Heroes + Reste aus drei weiteren Sets) — aber das ist kein
  1:1-Mapping, sondern pro Karte unterschiedlich, und nur per Einzel-
  Recherche pro Set nutzbar.
- Cardmarkets eigene Website-Suche (die diese Zuordnung offensichtlich
  intern kennt) ist per automatisiertem Abruf nicht nutzbar: ein einzelner,
  bewusster Test-Tab auf die Cardmarket-Suchergebnisseite zeigte statt der
  Ergebnisse Cloudflares Bot-Check-Zwischenseite ("Just a moment...") —
  automatisiert lösen/umgehen wird grundsätzlich nicht gemacht. Einzelne
  *Produktseiten* (wie beim bestehenden Preis-Lookup) sind davon nicht
  betroffen, nur die Such-/Listing-Seite.

**Umgesetzt (Zwischenlösung, bis eine vollständige Lösung feststeht):**
- `app/services/price_service.py`: `update_price_for_card()` bricht für
  Karten mit einer Sprache ohne Cardmarket-Sprachfilter (JP/KO/ZH) sofort
  mit einer klaren `NO_PRICE`-Begründung ab, *bevor* die Leiter überhaupt
  läuft — kein stiller Falschpreis mehr.
- Neues Feld `manual_cardmarket_url` (`Card`, `CardDetailsValues`,
  Migration 4, `CardRepository`): der Nutzer kann selbst den korrekten
  Cardmarket-Link hinterlegen (Feld „Eigener Cardmarket-Link“ im
  Bearbeiten-/Hinzufügen-Dialog, mit Tooltip-Erklärung). Ist er gesetzt,
  nutzt die Preisermittlung ihn anstelle der (falschen) automatischen URL —
  funktioniert auch für jede andere Karte als genereller Override, falls die
  automatische Zuordnung aus anderen Gründen falsch liegt.

**Live-Check gegen die echte Sammlung:** Der Nutzer besitzt bereits genau
diesen Fall (Karte id 9, Ho-oh, Japanisch, Neo Revelation #7).
Preis-Lookup ohne manuellen Link → korrekt abgebrochen, keine
Cardmarket-Anfrage ausgelöst. Mit dem vom Nutzer bestätigten Link
(`.../Awakening-Legends/Ho-Oh-AL`) gesetzt → die App öffnete tatsächlich
die korrekte Produktseite (Fenstertitel bestätigt: "Ho-Oh () - Awakening
Legends | Cardmarket"). Das anschließende Auslesen lief in ein Timeout —
dieselbe, bereits bekannte gelegentliche Fenster-Erkennungs-Flakigkeit
(nicht die Fokus-Diebstahl-Ursache von vorhin, da das Fenster nachweislich
mit korrektem Titel existierte), keine Regression durch diese Änderung.

**Tests:** `tests/test_price_service.py` (Fallback-Bail-out-Test ersetzt +
1 neuer Override-Test), `tests/test_card_repository.py` (1 neuer
Persistenz-Test), `tests/test_card_details_dialog.py` (1 neuer Feld-Test),
`tests/test_database.py` (Migrationszähler auf 4 aktualisiert) — 314 Tests
insgesamt grün, `compileall` sauber.

**Offen / später:** Eine vollautomatische Auflösung bleibt ungelöst (siehe
Recherche oben) — die manuelle Link-Eingabe ist bewusst die dauerhafte
Zwischenlösung, keine Übergangslösung auf dem Weg zu etwas Automatischerem.

---

## Design: Set-Symbole überall eingebaut (2026-07-04)

**Vom Nutzer gewünscht:** Kleine Set-Icons (wie auf der echten Karte
aufgedruckt) neben jedem Set-Namen.

**Umsetzung:**
- `app/catalog/set_icon_cache.py` (neu): lädt und cached pokemontcg.io's
  offizielles Symbol-Icon pro Set — keine zusätzliche API-Anfrage nötig, die
  Bild-URL folgt einem vorhersagbaren Muster
  (`https://images.pokemontcg.io/{set_code}/symbol.png`), live bestätigt für
  ein modernes (`swsh7`) und ein altes (`base1`) Set.
- `app/ui/set_icon_provider.py` (neu): In-Memory-`QIcon`-Cache obendrauf, damit
  ein Tabellen-Redraw nicht bei jedem Redraw erneut von der Festplatte lädt.
- Eingebaut in: Kartenliste (`card_list_panel.py`, Set-Spalte),
  Kartendetails (`card_detail_panel.py`, kleines Icon neben dem Set-Feld),
  Katalog-Suchergebnisse (`catalog_search_results_dialog.py`),
  Statistik-Tabellen (`statistics_panel.py` — "Karten mit veraltetem Preis",
  "Teuerste Karten", "Wert nach Set"; Sprache/Zustand haben naturgemäß kein
  Set-Icon).
- `ValueBreakdownEntry` (in `statistics_service.py`) hat jetzt ein optionales
  `set_code`-Feld, nur für die Set-Aufschlüsselung befüllt.

**Bug gefunden und behoben, bevor er in den Test-Vorschriften auffiel:** Da
Icons jetzt beim Rendern (nicht beim Hinzufügen einer Karte) lazy geladen
werden, hätten UI-Tests mit echten `Card`/`CatalogCard`-Objekten sonst einen
echten Netzwerk-Aufruf ausgelöst (langsam, unzuverlässig, und da kein
`icons_dir` übergeben wird, direkt in das echte `data/set_icons`-Verzeichnis
schreibend). Behoben durch eine neue `autouse`-Fixture in `tests/conftest.py`,
die `app.ui.set_icon_provider.ensure_set_icon` für jeden Test durch einen
No-Op ersetzt — verifiziert, dass danach kein Testlauf mehr etwas in das
echte Verzeichnis schreibt.

**Bekannte Einschränkung:** Der erste Render eines noch nicht gecachten Sets
lädt synchron (blockierend) — bei der Katalogsuche (bis zu 25 Treffer
verschiedener Sets) oder der "Wert nach Set"-Tabelle mit vielen
verschiedenen Sets kann das beim allerersten Anzeigen kurz spürbar sein.
Kein Problem danach, da für immer lokal gecacht. Gleicher Trade-off wie beim
bestehenden Kartenbild-Download.

**Tests:** `tests/test_set_icon_cache.py` (5 neue), `tests/test_statistics_
service.py` (1 neuer Test für die `set_code`-Weitergabe), 311 Tests
insgesamt grün, `compileall` sauber.

**Live-Check:** Per Offscreen-Rendering-Skript bestätigt — Icons erscheinen
korrekt in Kartenliste, Kartendetails und allen drei relevanten
Statistik-Tabellen.

---

## Bugfix: Preis-Lookup fand den geöffneten Cardmarket-Tab nicht (2026-07-04)

**Vom Nutzer gemeldet:** Bei einer Umbreon VMAX (Kartennummer 95, Evolving
Skies) öffnete der Preis-Lookup-Button die korrekte Cardmarket-Seite im
Browser, aktualisierte den Preis in der App aber nicht.

**Ursache (aus dem Log/der DB bestätigt):** `price_rationale` für diese
Karte lautete „Cardmarket-Tab für „Umbreon VMAX" wurde nicht rechtzeitig
gefunden." — die Seite war also tatsächlich korrekt geöffnet, aber
`app/pricing/browser_price_reader.py`s Fenster-Erkennung
(`GetForegroundWindow()`-Polling, siehe `_open_and_capture_visible_text`)
lief in ihr 30-Sekunden-Timeout, weil das neu geöffnete Chrome-Fenster nie
tatsächlich zum Vordergrundfenster wurde. Root Cause: Windows verweigert
einem bereits laufenden Chrome-Fenster den Fokuswechsel, wenn die
Aktivierungs-Anfrage von einem Hintergrund-Thread eines nicht im Vordergrund
stehenden Prozesses kommt (`PriceLookupWorker` läuft in einem eigenen
`QThread`, nicht im GUI-Haupt-Thread) — eine bekannte Windows-
Fokus-Diebstahl-Sperre.

**Fix:** `_open_in_chrome()` ruft jetzt vor `subprocess.Popen(...)` die
Windows-API `AllowSetForegroundWindow(ASFW_ANY)` (über `ctypes.windll.
user32`) auf — das erlaubt dem nächsten `SetForegroundWindow`-Aufruf (Chrome
aktiviert damit sein eigenes Fenster für den neuen Tab) zu funktionieren,
unabhängig von der Hintergrund-Prozess-Sperre. Nicht-Windows/kein `ctypes.
windll`: `try`/`except` fängt das ab, reine Best-Effort-Maßnahme.

**Tests:** `tests/test_browser_price_reader.py` — 2 neue Tests
(`test_allow_chrome_to_take_focus_calls_the_windows_api`,
`test_allow_chrome_to_take_focus_is_a_noop_off_windows`), 305 Tests
insgesamt grün, `compileall` sauber.

**Live-Check:** App neu gestartet mit dem Fix; ein erneuter Klick auf
"Preis aktualisieren" für dieselbe Karte im laufenden Programm steht durch
den Nutzer noch aus, da dieser Fehler nur bei echtem Fokuswechsel im
realen Betrieb reproduzierbar ist (keine weiteren automatisierten
Cardmarket-Seitenaufrufe ausgelöst, um die bekannte Sperr-Vorsicht bei
Cardmarket-Automatisierung zu wahren).

---

## Toleranteres Suchen: Sonderzeichen + zweisprachige Namen (2026-07-04)

**Ausgangslage (vom Nutzer gemeldet):** Die Suche war zu streng bei
Sonderzeichen ("poke pad"/"pokepad" fand "Poképad" nicht, nur die exakte
Schreibweise mit é; "hooh"/"ho oh" fand "Ho-Oh" nicht, nur mit Bindestrich)
und kannte nur englische Kartennamen — eine Suche nach der deutschen
Bezeichnung (z. B. "Turtok" für "Blastoise") fand weder im Katalog noch in
der eigenen Sammlung etwas.

**Umsetzung:**
- `app/utils/text_normalize.py` (neu): `normalize_for_search()` faltet
  Akzente (Unicode-NFKD + Streichen der Kombinationszeichen) und streicht
  alle Nicht-alphanumerischen Zeichen (Bindestrich/Leerzeichen/Apostroph).
  Wird von beiden Suchpfaden genutzt.
- `app/catalog/pokemon_name_translations.json` (neu, statisch, committet):
  3584 Einträge `{"<normalisierter fremdsprachiger Name>": "<englischer
  Name>"}`, einmalig gegen die echte PokeAPI (1025 Spezies) generiert — die
  App selbst ruft PokeAPI nie zur Laufzeit auf.
- `app/catalog/name_translation.py` (neu): `translate_to_english()` schlägt
  einen normalisierten Suchbegriff in der Tabelle nach.
- `app/services/catalog_search_service.py`: zwei neue Lockerungsstufen nach
  der bestehenden Leiter — zuerst Versuch mit der übersetzten englischen
  Form, dann ein schrumpfender Namens-Präfix (6→4→3 Zeichen, max. ~4
  Zusatz-Requests), dessen Treffer client-seitig gegen den normalisierten
  Suchbegriff gefiltert werden.
- `app/database/connection.py`: registriert `normalize_for_search` als
  SQLite-Funktion `normalize_text` auf jeder neuen Verbindung.
- `app/database/repositories/card_repository.py`: der `search_text`-Teil
  der WHERE-Klausel nutzt jetzt `normalize_text(name) LIKE ?` (usw. für
  set_name/card_number/notes) mit einem vor-normalisierten Parameter;
  liefert `translate_to_english()` einen Treffer, wird eine zweite Gruppe
  derselben vier Spalten mit dem übersetzten, normalisierten Begriff
  OR-verknüpft ergänzt.

**Live-Check (echte Datenbank, gleicher Repository-Code-Pfad wie die
Filterleiste):** "hooh"/"ho oh"/"ho-oh" finden die lokal gespeicherte Karte
"Ho-oh"; "Bisaflor" (deutscher Name) findet die lokal gespeicherte Karte
"Venusaur". Ein manueller Klick-Test im laufenden Programm-Fenster selbst
stand am Ende dieser Runde noch aus.

**Tests:** `tests/test_text_normalize.py` (6), `tests/test_name_translation.py`
(5), Erweiterungen in `tests/test_catalog_search_service.py` (3 neue) und
`tests/test_card_repository.py` (3 neue) — 303 Tests insgesamt grün,
`compileall` sauber.

---

## Korrektur: Reverse Holo ist doch ein echter Cardmarket-Filter (2026-07-04)

**Frühere Aussage war falsch.** Bei Schritt 5 (siehe "Vier neue Extra-Felder"
weiter oben) wurde recherchiert, Cardmarket biete keinen Reverse-Holo-Filter
an, und `build_filtered_url()` entsprechend gebaut. Der Nutzer widersprach
mit einem echten, funktionierenden Link:
`.../Legendary-Collection/Venusaur-LC18?isReverseHolo=Y`.

**Live nachgeprüft, bevor der Code geändert wurde:** Ein echter Chrome-Tab
mit genau dieser URL zeigt im Filterformular tatsächlich ein "Only Reverse?"
Ja/Nein-Feld, und die zurückgegebenen Angebote sind alle explizit mit
"Reverse Holo" markiert — der Filter funktioniert wirklich. Anders als
`isSigned`/`isFirstEd`/`isAltered` ist `isReverseHolo` ein **nackter**
Top-Level-Parameter, nicht unter `extra[...]` verschachtelt.

**Behoben:**
- `build_filtered_url()`: neuer Parameter `reverse_holo: bool | None`, hängt
  `isReverseHolo=Y`/`N` an; falsche Doku-Aussage ("kein Filter") entfernt.
- `PriceService._determine_price()`: `extras`-Dict enthält jetzt auch
  `"reverse_holo": card.is_reverse_holo` — wie bei Signiert/1st Edition/
  Altered ein hartes Muss auf jeder Leiter-Stufe, kein loslassbarer Schritt.
- `app/models/card.py`: falscher Kommentar bei den Extra-Feldern korrigiert.
- Tests: `tests/test_browser_price_reader.py` (2 neue/angepasste),
  `tests/test_price_service.py` (`_NO_EXTRAS` + Extras-Test angepasst) —
  380 Tests weiterhin grün.

**Lehre:** Frühere Recherche-Ergebnisse sind nicht für immer gültig — sowohl
weil Cardmarket sein Filterformular geändert haben könnte, als auch weil die
ursprüngliche Recherche schlicht unvollständig gewesen sein könnte. Ein vom
Nutzer gemeldeter, konkreter Gegenbeweis (ein echter, funktionierender Link)
wiegt schwerer als ein alter Code-Kommentar.

---

## Dritte Nachbesserungsrunde zu Schritt 10 (2026-07-04)

Auf weiteres Nutzerfeedback nach der zweiten Nachbesserung:

1. **"Preis aktualisieren"-Button in der Statistik-Tabelle war wiederholt
   abgeschnitten/verzerrt.** Zwei verschiedene Ursachen nacheinander
   gefunden und behoben: zuerst war die Spaltenbreite zu schmal
   (`resizeColumnToContents()` erfasst keine Cell-*Widgets* zuverlässig,
   nur `QTableWidgetItem`-Text — jetzt eine feste Breite aus einer
   Konstante `_UPDATE_BUTTON_WIDTH`); dann war die **Zeilenhöhe** zu
   niedrig (derselbe `resizeRowsToContents()`-Blindspot für Cell-Widgets),
   wodurch der fett/gepolsterte Button-Text oben/unten abgeschnitten wurde
   und "doppelt" aussah — behoben durch explizites `setRowHeight()` aus
   `button.sizeHint().height()` je Zeile, mit großzügigem Puffer (+24px).
2. **Name/Set-Spalten in "Karten mit veraltetem Preis"/"Teuerste Karten"
   auf 50:50** — beide Spalten sind jetzt `Stretch` statt nur "Set" (vorher
   quetschte das lange Set-Namen).
3. **Splitter-/Fensterbreiten:** Sammlungen-Panel schmaler (200→160px),
   Kartenliste breiter (min. 420→480px, Startgröße 620→730px), Fenster
   insgesamt breiter (1280→1360px) — die Kartenliste brauchte vorher
   horizontales Scrollen.
4. **Lade-Feedback bei der Katalogsuche:** Die Suche ist ein synchroner,
   blockierender Netzwerkaufruf — vorher wirkte das Programm dabei wie
   eingefroren. `CatalogSearchController.handle_search()` zeigt jetzt
   sofort "Suche läuft für „…“ …" in der Statusleiste + Wartecursor, mit
   `QApplication.processEvents()` erzwungenem Repaint davor.
5. **Eingabefelder im Bearbeiten-Dialog abgehoben:** `QLineEdit`/
   `QComboBox`/`QSpinBox`/`QPlainTextEdit` nutzen jetzt `panel_raised`
   statt der Fensterfarbe als Hintergrund, damit sie sich vom Dialog
   abheben.
6. **Checkbox-Häkchen:** Ein weißes Häkchen (`app/resources/check.png`,
   mit `QPainter` erzeugt wie das App-Icon) erscheint jetzt im angehakten
   Kästchen — die komplett angepasste `::indicator`-Optik hatte das
   native Häkchen-Glyph vorher ersatzlos entfernt.
7. **Hover-Effekte wieder entfernt:** Mehrere Versuche, Tabellenzeilen und
   Dropdown-Einträge beim Drüberfahren hervorzuheben, blieben erfolglos
   (u. a. falsche CSS-Klasse `QAbstractItemView` statt der konkreten
   `QComboBox QListView`, die Qt intern für Dropdown-Popups nutzt — auch
   nach der Korrektur funktionierte es beim Nutzer weiterhin nicht). Auf
   Nutzerwunsch komplett zurückgerollt (nur `QPushButton:hover` u. Ä.
   bleiben) — wird später erneut angegangen, wenn Zeit dafür ist.

**Tests:** weiterhin 286 grün — Anpassungen betrafen ausschließlich Layout/
Styling, keine neue Testlogik nötig (Verhalten unverändert).

---

## Hinweis zur Testlaufzeit (2026-07-04)

Der volle `pytest -q`-Lauf brauchte während dieser Session mehrfach deutlich
länger als üblich (teils mehrere Minuten statt der sonst üblichen ~90–100s)
und wirkte dabei zeitweise wie aufgehängt. Isolierte Läufe derselben
Testdateien liefen jedes Mal in wenigen Sekunden fehlerfrei durch, und ein
finaler vollständiger Lauf hat am Ende sauber mit **286 grünen Tests in
111s** abgeschlossen — die Verlangsamung lag an Systemauslastung durch die
vielen in dieser Session parallel gelaufenen Hintergrundprozesse (mehrere
Chrome-Instanzen, mehrere Python-Prozesse, Screenshot-Skripte), nicht an
einem echten Fehler im Code.

Ein tatsächlicher Test-Bug wurde beim Nachforschen trotzdem gefunden und
behoben: `tests/test_price_controller.py` versuchte, eine bereits
verbundene Signal-Methode nachträglich per Instanz-Attribut zu ersetzen
(`main_window.price_controller.start_lookup = calls.append`) — das
überschreibt in Qt **nicht** die schon bestehende Signal-Verbindung, wodurch
beim `emit()` zusätzlich der echte `PriceController.start_lookup()` gelaufen
wäre (mit echtem Chrome/Cardmarket-Zugriff für eine nicht existierende
Karten-ID). Behoben nach demselben Muster wie der Toolbar-Suchtest: echte
Verbindung trennen, dann einen Spy verbinden.

---

## Zweite Nachbesserungsrunde zu Schritt 10 (2026-07-04)

Auf weiteres Nutzerfeedback nach der ersten Nachbesserung:

1. **Suchleiste nur im "Karten"-Tab:** Es ergab keinen Sinn, die
   Toolbar-Katalogsuche auch anzuzeigen, während man im "Statistik"-Tab ist.
   `MainWindow._on_central_tab_changed()` blendet Suchfeld + Suchen-Button
   jetzt je nach aktivem Tab ein/aus.
2. **Text statt Icons für die Tab-Navigation:** Die Icons für "Karten"/
   "Statistik" waren nicht selbsterklärend. Beide `QAction`s sind jetzt
   reiner Text, keine Icons mehr.
3. **"!"-Preis-Reminder in der Kartenliste:** Karten mit einem Preis, der
   älter als die Stale-Schwelle ist, zeigen jetzt ein "!" hinter dem
   Preis in der Kartenliste (`app/ui/widgets/card_list_panel.py`). Nutzt
   dieselbe `is_price_stale()`-Logik wie die Statistik-Übersicht (neu aus
   `app/services/statistics_service.py` exportiert, gemeinsam mit
   `days_since_price_update()`) — eine einzige Definition von "veraltet",
   nicht zwei. Karten ganz ohne Preis zeigen weiterhin nur "—" (kein "!"
   nötig, das Fehlen ist schon offensichtlich).
4. **Inline "Preis aktualisieren" direkt in der Statistik-Tabelle:** Jede
   Zeile in "Karten mit veraltetem Preis" hat jetzt einen echten
   "Preis aktualisieren"-Button (4. Spalte), der denselben Cardmarket-Lookup
   auslöst wie der große Button im Kartendetail-Panel — kein Platzhalter.
   Dafür: neues `StatisticsPanel.price_lookup_requested`-Signal;
   `PriceController.start_lookup()` ist jetzt public (vorher
   `_start_lookup`) und bekommt optional einen `statistics_controller`, den
   es nach einem erfolgreichen Lookup ebenfalls aktualisiert, damit die
   Zeile in der Statistik-Tabelle sofort verschwindet/sich aktualisiert,
   ohne auf den nächsten Tab-Wechsel warten zu müssen.
5. **Fußnote mit dem Zeitraum:** Unter der Tabelle steht jetzt explizit
   „Karten, deren Preis seit mehr als 90 Tagen nicht aktualisiert wurde
   oder noch nie ermittelt wurde." (nutzt `STALE_PRICE_THRESHOLD_DAYS`
   direkt, bleibt also korrekt, falls der Schwellwert sich mal ändert).

**Tests:** neue Fälle in `test_card_panel.py` ("!"-Anzeige),
`test_statistics_panel.py` (Inline-Button emittiert Karten-ID),
`test_price_controller.py` (Statistik-Refresh nach Lookup, Verdrahtung des
Statistik-Buttons), `test_ui_smoke.py` (Suchleisten-Sichtbarkeit,
Text-Buttons).

---

## Erste Nachbesserung zu Schritt 10 (2026-07-04)

Auf Nutzerwunsch nach dem ersten Statistiken-Durchlauf:

1. **Größere Headlines:** Abschnitts-Überschriften im Statistiken-Tab waren
   optisch kaum von normalen Feldbeschriftungen zu unterscheiden — neuer
   QSS-Selektor `QLabel#SectionHeader` (12pt, fett, normale statt gedämpfte
   Textfarbe) in `app/ui/theme.py`, von `StatisticsPanel._section_label()`
   verwendet statt des bisherigen `#FieldLabel`.
2. **Stand-Datum + Genauigkeits-Hinweis:** Der Gesamtwert kann veraltet sein,
   da er auf dem jeweils letzten bekannten Preis je Karte basiert. Neues
   `StatisticsOverview.as_of`-Feld (jüngstes `price_updated_at` über alle
   Karten) wird direkt unter dem Gesamtwert angezeigt, zusammen mit dem
   festen Hinweistext, dass die Zahl veraltet sein kann.
3. **"Karten mit veraltetem Preis":** Neue Übersicht (Idee des Nutzers:
   „diese Karte hast du seit 3 Monaten nicht aktualisiert"). Neues
   `StatisticsService.STALE_PRICE_THRESHOLD_DAYS = 90` (genau der vom
   Nutzer genannte Zeitraum) plus `StalePriceEntry`/`stale_price_cards`:
   listet jede Karte, deren `price_updated_at` älter als 90 Tage ist oder
   die noch nie einen Preis hatte (letztere zuerst, dann absteigend nach
   Alter). `now` ist im Service injizierbar (`Callable[[], datetime]`) für
   deterministische Tests.
4. **Toolbar-Navigation:** `MainWindow`s Zentral-`QTabWidget` versteckt jetzt
   seine eigene Tab-Leiste (`tabs.tabBar().hide()`); Umschalten läuft
   stattdessen über zwei neue, sich gegenseitig ausschließende
   (`QActionGroup`) Toolbar-Buttons "Karten"/"Statistik" mit Icons, an der
   Stelle, an der vorher die kaum genutzten Platzhalter-Buttons saßen.
   Auswahlzustand bleibt über `_on_central_tab_changed` synchron, auch wenn
   der Tab auf anderem Weg wechselt.

**Tests:** 279 grün — neue Fälle für `as_of`/`stale_price_cards` in
`test_statistics_service.py`, neue Anzeige-Tests in `test_statistics_panel.py`,
neue Toolbar-Navigationstests in `test_ui_smoke.py`.

**Noch offen (auf Wunsch des Nutzers zurückgestellt):** weiterer optischer
Feinschliff am Statistiken-Tab (Tabellen-Styling, Abstände) bei Bedarf
später nachziehen.

---

## Schritt 10 — Statistiken (2026-07-04)

Neuer "Statistiken"-Tab neben "Karten" (`MainWindow`s Zentral-Widget ist
jetzt ein `QTabWidget`, statt direkt der 3-Spalten-Splitter — der Splitter
ist jetzt einfach der Inhalt des ersten Tabs). Wird nur neu berechnet, wenn
der Tab aktiv wird (`QTabWidget.currentChanged`), nicht laufend im
Hintergrund.

Mit dem Nutzer vorab geklärt: alle Detail-Statistiken (Wert nach
Set/Sprache/Zustand, teuerste Karten, größte Preissteigerung) laufen immer
über **alle Sammlungen** (kein Eingrenzungs-Dropdown); kein separater
"Durchschnittswert" — nur der tatsächliche Gesamtwert zählt.

**Neu:**
- `app/services/statistics_service.py`: `StatisticsService.compute_overview()`
  aggregiert einmalig alle Karten (`CardService.search_cards(CardFilter(collection_id=None))`)
  rein in Python (keine Aggregations-Queries in den Repositories vorhanden) zu:
  - `per_collection` (Wert + Kartenzahl je Sammlung, inkl. leerer Sammlungen
    mit 0) + `grand_total` (Summe über alle Sammlungen) — beide gleichzeitig
    sichtbar, wie ursprünglich gewünscht.
  - `value_by_set`/`_language`/`_condition`: nach `total_value` absteigend
    sortierte Gruppierungen.
  - `most_expensive_cards`: Top 10 nach `total_value`, Karten ohne Preis
    ausgeschlossen.
  - `biggest_price_increase`: iteriert alle Karten mit bekanntem Preis,
    vergleicht je Karte die letzten zwei `PriceRecord`s (gleiche Definition
    wie das %-Label im `PriceHistoryDock`), Karte mit größter **positiver**
    Änderung gewinnt; `None` wenn keine qualifiziert.
- `app/ui/widgets/statistics_panel.py`: presentation-only, `show_overview()`
  befüllt Tabellen/Labels für jeden Abschnitt.
- `app/ui/controllers/statistics_controller.py`: `refresh()` ruft
  `compute_overview()` und füttert das Panel.
- `app/ui/main_window.py`: Splitter in `QTabWidget`-Tab "Karten" gepackt,
  neuer Tab "Statistiken".

**Tests:** 268 grün — 10 neue in `tests/test_statistics_service.py`
(Gruppierung, Grand Total, Top-10, Preissteigerung inkl. Edge Cases: keine
Historie, nur fallende Preise, `current_price is None`), 5 neue in
`tests/test_statistics_panel.py`.

**Verifiziert:** Screenshot aller Abschnitte (auch nach Scrollen) bestätigt
korrektes Rendering; Zahlen von Hand gegen die echte `data/collection.db`
nachgerechnet (Xatu 200 € + Charizard VMAX 160 € + Venusaur ohne Preis =
360 € Gesamtwert; größte Steigerung Charizard VMAX 155 €→160 €, +3,2 % —
beides stimmt mit der Anzeige überein).

---

## Nachbesserungen zur UI-Überarbeitung (2026-07-04, vom Nutzer live gefunden)

Nach dem ersten Durchlauf hat der Nutzer im laufenden Programm mehrere
konkrete Probleme gefunden, die im Offscreen-Screenshot nicht auffielen:

1. **Kartenbild nicht zugeschnitten + Felder ragen ins Bild:**
   `CardArtworkView` malte vorher einen Panel-Hintergrund über das komplette
   (oft sehr hohe) Widget, mit `KeepAspectRatio` (Letterboxing) für das Bild
   — sichtbar leerer Rand oben/unten. Behoben durch eine card-shaped "Bühne"
   mit echtem Kartenseitenverhältnis (2,5:3,5), zentriert im Widget, und
   `KeepAspectRatioByExpanding` + Clipping (Crop-to-fill statt Letterbox).
2. **Diagramm unübersichtlich:** `€`-Zeichen im Achsen-Tick-Format rendert im
   Chart-Font als „?"; Datumsbeschriftungen („03...03...") überlappten bei
   mehr als ein paar Datenpunkten. Behoben: Einheit nur noch im Achsentitel,
   kürzeres Datumsformat, `setTickCount` begrenzt auf max. 6, Labels um -45°
   gekippt, Datenpunkte jetzt als sichtbare Marker, Chart-Mindesthöhe erhöht.
3. **Verlaufsliste brauchte horizontales Scrollen:** Einzeilige, mit „·"
   verbundene Einträge waren zu lang für die Dock-Breite. Behoben durch
   zweizeilige Einträge (Datum+Preis / Qualität) mit Wortumbruch, Dock
   verbreitert (300→380px). *(Ein Zwischenversuch, das Dock zusätzlich in
   eine `QScrollArea` zu packen, hat das Chart-Rendering kaputt gemacht —
   wieder entfernt.)*
4. **Filterleiste und Detail-Buttons abgeschnitten:** Eine einzige Zeile mit
   Suche + 3 Dropdowns + 2 Preisfeldern + Checkbox + Button (Filterleiste)
   bzw. zwei lange Button-Texte nebeneinander (Detail-Panel) passten bei
   normaler Fensterbreite nicht — Text wurde abgeschnitten statt umzubrechen.
   Behoben: Filterleiste jetzt zweizeilig (`card_filter_bar.py`); die beiden
   Detail-Buttons stehen jetzt untereinander statt nebeneinander
   (`card_detail_panel.py`).
5. **Preisverlauf-Dock verdrängte die drei Spalten:** `QDockWidget` nimmt
   seinen Platz aus dem Zentral-Widget statt zu überlagern — ohne
   Fenster-Vergrößerung quetschte das Öffnen des Docks Sammlungen/Karten/
   Details zusammen (abgeschnittener Text). Behoben: `MainWindow` vergrößert
   das Fenster beim Öffnen um genau die Dock-Breite (380px) und verkleinert
   es beim Schließen wieder.
6. **Button war Einbahnstraße:** "Preisverlauf anzeigen" öffnete das Dock,
   hatte aber keine Möglichkeit, es über denselben Button wieder zu
   schließen. Jetzt ein echter Umschalter (`set_history_panel_visible()`,
   an `QDockWidget.visibilityChanged` gehängt) — Button-Text wechselt
   zwischen "anzeigen"/"ausblenden", bleibt auch korrekt, wenn das Dock über
   sein eigenes Schließen-Symbol (nicht den Button) geschlossen wird.
7. **Kartenbild zu dominant / Abstände zu Feldern/Buttons zu knapp:**
   Kartenbild-Maximalhöhe auf 420px begrenzt (vorher unbegrenzt), Abstand
   zwischen Bild↔Feldern und Feldern↔Buttons auf einheitlich 20px erhöht.

**Tests:** 253 grün, u. a. neuer Toggle-Test in `test_ui_smoke.py`
(`test_history_button_toggles_dock_and_window_width`).

---

## UI/Design-Überarbeitung (2026-07-04)

Auf Nutzerwunsch: dunkles/dunkelblaues, modernes Theme mit orange/gelben
Akzenten; kein Text soll durch Fenstergröße verdeckt werden; die Kartenansicht
soll die Karte groß/zentriert zeigen statt in leerem Raum zu wirken; das
Preisdiagramm wandert in ein einklappbares Panel rechts mit Verlaufsliste,
%-Änderung und Reset (mit Sicherheitsabfrage); ein "Suchen"-Button für die
Toolbar-Katalogsuche; ein neues App-Icon.

Geklärt mit dem Nutzer vorab: Light/Dark-Umschalter entfällt (nur noch ein
dunkles Theme); der Suchen-Button kommt an die Toolbar-Katalogsuche (die
Filterleiste sucht schon live); Historie-Reset leert nur Diagramm/Verlauf,
der aktuell angezeigte Preis bleibt stehen.

**Umgesetzt:**
- `app/ui/theme.py`: `Theme`-Enum/Light-Palette entfernt, eine einzige dunkle
  Palette (Fenster `#10141c`, Panel `#1a2233`, Akzent orange `#ff9d45`,
  sekundär gelb `#ffd166`). QSS modernisiert (Rundungen, Hover-States,
  Akzent-Fokusrahmen, neue `#ArtworkStage`/`#Danger`/`#PercentPositive`/
  `#PercentNegative`-Selektoren).
- `app/ui/main_window.py`: Theme-Toggle-Button entfernt; Mindestfenstergröße
  auf 1100×700 erhöht plus `setMinimumWidth` auf allen drei Splitter-Panels,
  damit ein normales Verkleinern nie mehr Text verdeckt (nur bewusstes
  Verkleinern unter das Minimum); neuer "Suchen"-Button neben der
  Toolbar-Katalogsuche (gleicher Signalpfad wie Enter); App-Icon gesetzt.
- `app/ui/widgets/card_artwork_view.py`: deutlich vergrößert (min. 360px)
  und mit eigenem `#ArtworkStage`-Hintergrund (Panel + Akzent-Rahmen) versehen,
  damit die Karte sichtbar auf einer "Bühne" steht statt in leerem Raum.
- `app/ui/widgets/card_detail_panel.py`: eingebettetes Preisdiagramm entfernt
  (wandert komplett ins neue Dock); neuer "Preisverlauf anzeigen"-Button.
  Alte `app/ui/widgets/price_history_chart.py` (jetzt unbenutzt) gelöscht.
- **Neu:** `app/ui/widgets/price_history_dock.py` (`PriceHistoryDock`,
  `QDockWidget`, rechts andockbar): redesignter Chart mit Achsentiteln
  ("Datum"/"Preis (€)") und theme-farbigen Gridlines/Linie; %-Änderung
  zum vorherigen Preis darunter (grün bei positiv, rot bei negativ); Liste
  der letzten 10 Preis-Updates (neueste zuerst); "Historie zurücksetzen"-
  Button mit `QMessageBox`-Sicherheitsabfrage (löscht nur den Verlauf,
  nicht den aktuell angezeigten Preis der Karte).
- `app/database/repositories/price_repository.py`: neue
  `delete_for_card(card_id)` (Hard-Delete, kein Schema-Change nötig).
- `app/ui/controllers/card_controller.py`: neuer optionaler
  `history_dock`-Parameter; befüllt/leert das Dock an denselben Stellen, an
  denen bisher `show_price_history`/`show_empty` am Detail-Panel liefen;
  neuer `_on_history_reset`-Handler ruft `PriceRepository.delete_for_card`
  auf und aktualisiert das Dock, falls die betroffene Karte noch ausgewählt
  ist.
- **App-Icon:** einmaliges Generierungsskript (nicht Teil der Runtime-
  Abhängigkeiten) zeichnet mit `QPainter`/`QImageWriter` (beides bereits in
  PySide6 enthalten, keine neue Abhängigkeit) einen stilisierten,
  orange/gelben Kartenfächer auf dunklem Grund — bewusst kein Pokémon-Logo/
  Charakter (Marken-/Urheberrecht). Gespeichert als
  `app/resources/icon.ico`, in `app/ui/app.py` (App-Icon) und
  `app/ui/main_window.py` (Fenster-Icon) gesetzt.

**Tests:** 252 grün — u. a. neue `tests/test_price_history_dock.py`,
Erweiterungen in `tests/test_price_repository.py` (`delete_for_card`) und
`tests/test_card_controller.py` (Dock-Befüllung + Reset-Flow); alte
Theme-Toggle-/eingebettete-Chart-Tests entfernt oder umgeschrieben.

**Visuell geprüft:** Screenshot der laufenden App (echte Datenbank, echte
Venusaur-Karte) bestätigt Layout, Farben und das geöffnete Preisverlauf-Dock
(Chart mit Achsen, grünes %-Label, Verlaufsliste, roter Reset-Button). Text
erscheint im Offscreen-Screenshot als Kästchen — bekanntes, bereits
dokumentiertes Rendering-Artefakt ohne Systemschrift, kein Bug (siehe
„Bekannte Bugs" unten). Finale Bestätigung auf echtem Bildschirm steht noch
vom Nutzer aus.

---

## Nachbesserung (2026-07-04): „Extra"-Umbenennung, `Variante` entfernt

Nutzer-Feedback: „Zusätze" im UI heißt jetzt „Extra"; das alte `Variante`-Feld
(Normal/Holo/Promo/Staff) war seit der Umstellung auf die vier Ja/Nein-Flags
(Reverse Holo/Signiert/1st Edition/Altered) redundant und wurde auf
ausdrücklichen Wunsch **komplett entfernt**:

- `Variant`-Enum aus `app/models/enums.py` entfernt, alle Referenzen in
  Modellen/Repository/Service/UI/Tests bereinigt.
- **Migration v3:** `ALTER TABLE cards DROP COLUMN variant;` — gegen eine
  Kopie der echten Nutzer-Datenbank getestet (Daten inkl. `is_first_edition`
  blieben korrekt erhalten), danach auf die echte DB angewendet.
- UI: Spalte/Label „Variante"/„Zusätze" → „Extra" in Kartenliste, Detail-
  Panel und Bearbeiten-Dialog.

## Verworfener Versuch (2026-07-04): automatische Versions-Korrektur führte zu Cardmarket-Sperre

Gemeldeter Bug: Ein deutsches Base-Set-Bisaflor (Venusaur) mit 1st Edition
öffnete beim Preis-Update die falsche Cardmarket-Produktseite (englische
„1st Edition Shadowless"-Version statt der mehrsprachigen Version). Ursache
live bestätigt: Cardmarket führt für Base Set **zwei komplett getrennte
Produkte** (`Venusaur-V2-BS15`, nur Englisch, vs. `Venusaur-V1-BS15`,
mehrsprachig) — pokemontcg.io verlinkt für diese Karte die falsche Version.

Ein erster Fix-Versuch (automatische Erkennung über die „Sprache"-Filter-
Sidebar + automatisches Durchprobieren der `-V<n>-`-Geschwisterversionen)
wurde implementiert, getestet (7 neue Unit-Tests, alle grün) und live
ausprobiert — dabei hat die Kandidaten-Suche bis zu 6 zusätzliche
Cardmarket-Tabs ohne Pause direkt hintereinander geöffnet. Das hat eine
**temporäre Cardmarket-Sperre** des Nutzer-Accounts ausgelöst (mittlerweile
wieder abgelaufen). Verstößt gegen das Projekt-Grundprinzip „ein Klick = eine
Karte, kein Batch/Loop" (siehe Architektur-Entscheidung unten).

**Vollständig zurückgerollt:** Der gesamte Korrektur-Mechanismus (neue
Funktionen in `browser_price_reader.py`, neue Konstruktor-Parameter in
`PriceService`, alle zugehörigen Tests) wurde wieder entfernt. Der Stand ist
identisch zum Stand vor diesem Versuch (245 Tests, unverändertes Preis-
Ladder-Verhalten).

**Nutzer-Entscheidung (2026-07-04):** Das Bisaflor-Problem soll später erneut
angegangen werden, aber mit strikter Drosselung (spürbare Pause zwischen
Tabs, max. 1–2 Kandidatenversionen statt 6) statt der bisherigen
Kandidatenschleife. Bis dahin: Preis für solche Vintage-Karten notfalls
manuell auf Cardmarket nachschauen.

---

## Nachbesserung (2026-07-03, nach Schritt 9): zwei vom Nutzer gemeldete Bugs

### Bug A — Fenstererkennung scheiterte bei lokalisierten Kartennamen

Nutzer fügte eine deutsche „Charizard VMAX" hinzu; Preisabruf öffnete
nachweislich den richtigen Tab, lieferte aber dauerhaft „Tab nicht
gefunden". Ursache: Cardmarket rendert die Seite bei `language=DE` mit dem
**deutschen** Pokémon-Namen im Titel („Glurak VMAX | Cardmarket" — „Glurak"
ist Charizards deutscher Name), während unser `match_hint` immer der
englische Katalogname war. Bei „Xatu" fiel das nie auf, weil der Name in
beiden Sprachen zufällig gleich ist.
**Behoben:** Fenstererkennung verlangt jetzt „cardmarket" (sprachunabhängig,
steht auf jeder Produktseite) statt des Kartennamens im Titel; `match_hint`
dient nur noch der Fehlermeldung. Live mit der echten Charizard-VMAX-Karte
verifiziert.

### Bug/Feature B — Kartenzusätze als echte Ja/Nein-Flags

Nutzer wies darauf hin: Cardmarkets „Extra"-Filter (Reverse Holo/Signiert/
1st Edition/Altered) lassen beim **Suchen** „Egal" zu, aber eine reale Karte
**muss** bei jedem dieser Merkmale eindeutig Ja oder Nein sein — unklar
vermischt in einem einzigen `Variant`-Dropdown wie bisher, unvollständig
(Signiert/Altered fehlten komplett) und für die Preisermittlung ungenau
(z. B. hätte eine signierte Karte gegen unsignierte Angebote gematcht werden
können).

**Live recherchiert (nicht geraten):** Cardmarkets tatsächliche Filter sind
`extra[isSigned]`, `extra[isFirstEd]`, `extra[isAltered]` (`0`=Egal,
`Y`=Ja, `N`=Nein) — bestätigt direkt aus dem Filterformular-DOM. **Reverse
Holo ist auf Cardmarket kein Filter** (weder auf der Produktseite noch als
eigenes Produkt gefunden) — bleibt rein informativ/für den eigenen
Bildüberlagerungs-Effekt, fließt nicht in die Preisfilter ein.

**Umgesetzt:**
- `Variant`-Enum auf reine Drucktypen reduziert: `Normal`/`Holo`/`Promo`/
  `Staff` (Reverse Holo/1st Edition/1st Edition Holo/Unlimited entfernt —
  jetzt durch die neuen Flags abgedeckt).
- `Card`/`CardDetailsValues` bekommen vier neue Felder:
  `is_reverse_holo`, `is_signed`, `is_first_edition`, `is_altered`
  (alle `bool`, unabhängig kombinierbar — z. B. „signiert **und**
  Reverse Holo" ist jetzt darstellbar, vorher nicht).
- **Schema-Migration Version 2:** vier neue Spalten
  (`is_reverse_holo`/`is_signed`/`is_first_edition`/`is_altered`,
  `INTEGER NOT NULL DEFAULT 0`) + Datenmigration bestehender `variant`-Werte
  (`'Reverse Holo'` → `is_reverse_holo=1` + `variant='Holo'`; `'1st Edition'`
  → `is_first_edition=1` + `variant='Normal'`; `'1st Edition Holo'` →
  `is_first_edition=1` + `variant='Holo'`; `'Unlimited'` → `variant='Normal'`).
  **Gegen die echte Datenbank verifiziert:** Die bestehende Karte „Venusaur"
  (`variant='1st Edition'`) wurde korrekt zu `variant='Normal'`,
  `is_first_edition=1` migriert; „Xatu"/„Charizard VMAX" blieben unberührt.
- `CardDetailsDialog`: vier neue Checkboxen (Reverse Holo/Signiert/
  1st Edition/Altered) neben dem Variante-Dropdown.
- `CardDetailPanel`: neues Feld „Zusätze" zeigt die aktiven Flags
  kommagetrennt an (z. B. „Reverse Holo, Signiert") oder „—".
- **Preis-Engine:** `build_filtered_url` bekommt `signed`/`first_edition`/
  `altered`-Parameter; `PriceService._determine_price` reicht sie in
  **jede** Leiter-Stufe durch (auch die „ungefilterte" Durchschnitts-Stufe
  ist nur bezüglich Sprache/Zustand ungefiltert, nie bezüglich der Extras) —
  eine signierte Karte kann so nie mehr gegen unsignierte Angebote gematcht
  werden.
- 14 neue/angepasste Tests (Migration, Dialog-Checkboxen, Detail-Panel-
  Anzeige, URL-Filter-Parameter, Preis-Leiter mit Extras). Gesamt:
  **247 Tests grün.**

**⚠️ Noch offen:** Finaler Klick-Test im laufenden Programm (Karte mit
Zusätzen anlegen/bearbeiten, Charizard-VMAX-Preis erneut abrufen) steht
noch aus.

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
  Cardmarket-Produktseite der Karte gezielt in **Google Chrome** und liest
  die bereits geladene Seite per Windows UI Automation aus (wie ein
  Screenreader — kein DOM-/Netzwerkzugriff); Angebote werden nach Zustand/
  Sprache gegen die eigene Karte gematcht (Fallback-Leiter EXACT →
  ESTIMATED_FROM_CONDITION → ESTIMATED_FROM_LANGUAGE → AVERAGE → NO_PRICE,
  jede Stufe über Cardmarkets eigene URL-Filter serverseitig vorgefiltert),
  Ergebnis + Preisverlauf-Eintrag werden persistiert. **Bewusst kein
  Batch-/Sammel-Lauf** — pro Klick genau eine Karte (Details unten).
- ✅ **Preisverlauf-Diagramm:** Eingebettetes Liniendiagramm (QtCharts, Teil
  von PySide6 — keine neue Abhängigkeit) direkt im Kartendetails-Panel,
  zeigt `price_history` über die Zeit; Platzhaltertext bei 0 oder 1
  Einträgen statt eines leeren/nutzlosen Diagramms. Visueller Feinschliff
  bewusst zurückgestellt (siehe „Nächster Entwicklungsschritt").
- ✅ **Filter & Volltextsuche:** Filterleiste oberhalb der Kartenliste
  (Textsuche über Name/Set/Nummer/Notizen, Dropdowns für Set/Sprache/
  Variante/Zustand, Preis-von/-bis, „Zurücksetzen"). Umschaltbar zwischen
  „nur aktuelle Sammlung“ und „alle Sammlungen durchsuchen“ (Checkbox) —
  Letzteres funktioniert auch ohne Sammlungsauswahl in der Seitenleiste.
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

*(Zum Zeitpunkt dieses Abschnitts noch nicht committet — inzwischen erledigt,
siehe Commit `dca383b` weiter unten in der Git-Historie.)*

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

## Heute umgesetzt (Schritt 9 — Filter & Volltextsuche)

Vom Nutzer präzisiert: Filterleiste oberhalb der Kartenliste (statt eigenem
Panel), umschaltbar zwischen aktueller Sammlung und sammlungsübergreifender
Suche.

- **`CardFilter`** (`app/models/card.py`, neu): unveränderliches DTO mit
  allen Filterkriterien (`collection_id`, `search_text`, `set_name`,
  `language`, `variant`, `condition`, `min_price`, `max_price`) — jedes auf
  seinem Default bedeutet „nicht gefiltert“; `collection_id=None` durchsucht
  alle Sammlungen.
- **`CardRepository.search(card_filter)`** (neu): baut die SQL-`WHERE`-
  Klausel dynamisch aus den gesetzten Kriterien zusammen (Textsuche über
  Name/Set/Nummer/Notizen per `LIKE`, restliche Felder exakt bzw. als
  Preisspanne). **`CardRepository.distinct_set_names(collection_id)`**
  (neu): liefert die für das Set-Dropdown nötigen, tatsächlich vorkommenden
  Set-Namen (scoped auf eine Sammlung oder `None` für alle).
  `CardService.search_cards`/`list_set_names` delegieren unverändert weiter.
- **`CardFilterBar`** (`app/ui/widgets/card_filter_bar.py`, neu): Textfeld,
  vier Dropdowns (Set/Sprache/Variante/Zustand, erster Eintrag „Alle“),
  Preis-von/-bis-Felder (tolerant gegenüber Komma statt Punkt, ungültige
  Eingaben werden als „nicht gesetzt“ behandelt statt eines Fehlers),
  „Alle Sammlungen“-Checkbox, „Zurücksetzen“-Knopf. Reine
  Präsentations-Komponente — emittiert bei jeder Änderung `filter_changed`
  (ein `CardFilter`, `collection_id` bleibt unbelegt) bzw. `scope_changed`
  (Checkbox-Zustand); keine eigene Filterlogik.
  **Bugfix während der Testphase:** `Variant` (ein `str`-Enum) wurde durch
  Qt's Combobox-Item-Data-Marshalling beim Auslesen wieder zu einem reinen
  `str` — derselbe Bug wie in Schritt 5 bei `CardDetailsDialog`, hier
  ebenso durch `Variant.from_value(...)` behoben.
- **`CardListPanel`** bettet die Filterleiste zwischen Überschrift und
  Tabelle ein (`self.filter_bar`, öffentlich für den Controller).
- **`CardController`** hält jetzt zusätzlichen Zustand (`_filter_fields`,
  `_search_all_collections`); `refresh()` kombiniert beides mit der
  Sammlungsauswahl aus der Seitenleiste zu einem `CardFilter` und ruft
  `CardService.search_cards(...)` statt des bisherigen `list_cards(...)`
  auf (mit leerem Filter identisches Ergebnis, kein Verhaltensbruch);
  aktualisiert nebenbei die Set-Dropdown-Optionen. „Alle Sammlungen“
  funktioniert bewusst auch **ohne** eine in der Seitenleiste gewählte
  Sammlung — Hinzufügen neuer Karten bleibt davon unberührt und verwendet
  weiterhin die zuletzt in der Seitenleiste gewählte Sammlung.
- Manuell im laufenden Programm bestätigt.
- 27 neue Tests (`CardRepository.search`/`distinct_set_names`,
  `CardService`-Delegation, `CardFilterBar`-Zustände/Signale,
  `CardController`-Verdrahtung inkl. sammlungsübergreifender Suche ohne
  Sammlungsauswahl). Gesamt: **239 Tests grün**.

---

## Heute umgesetzt (Schritt 8 — Preisverlauf-Diagramm)

Vom Nutzer gewünscht: eingebettetes Diagramm statt eigenem Dialog, damit die
Preisentwicklung ohne zusätzlichen Klick sichtbar ist.

- **`PriceHistoryChartView`** (`app/ui/widgets/price_history_chart.py`, neu):
  reine Präsentations-Komponente auf Basis von `PySide6.QtCharts`
  (`QChart`/`QChartView`/`QLineSeries`/`QDateTimeAxis`/`QValueAxis`) — bereits
  Teil der bestehenden PySide6-Installation, **keine neue Abhängigkeit**.
  `show_history(records)`: bei 0 oder 1 Einträgen ein kurzer Platzhaltertext
  statt eines leeren/nutzlosen Diagramms (Erklärung: kein Preisverlauf bzw.
  „Preis bisher nur einmal ermittelt"); ab 2 Einträgen ein Liniendiagramm
  (X-Achse Datum, Y-Achse Preis). `show_empty()` setzt auf den
  Platzhalter zurück.
- **`CardDetailPanel`** erweitert um die Chart-Komponente (unterhalb der
  Kartenfelder, oberhalb des Preis-Abrufen-Knopfs) und `show_price_history(...)`.
- **`CardController`** bekommt einen optionalen `price_repository`-Parameter;
  wann immer eine Karte angezeigt wird (`_show_card`, zentralisiert aus den
  beiden vorherigen `show_card`-Aufrufstellen), wird zusätzlich
  `price_repository.list_for_card(card.id)` geholt und ans Panel
  weitergereicht. Ohne übergebenes Repository (z. B. in bestehenden Tests)
  bleibt das Verhalten unverändert — kein Pflichtparameter, kein Bruch
  bestehender Aufrufer.
- **`MainWindow`** übergibt dafür eine `PriceRepository(self._database)`-
  Instanz an den `CardController` (Lesezugriff auf dem GUI-Thread, keine
  Threading-Problematik wie beim `PriceLookupWorker` — hier wird nichts an
  einen Hintergrund-Thread weitergereicht).
- Manuell im laufenden Programm verifiziert: Diagramm erscheint korrekt für
  die Karte „Xatu" mit den (aus der Fehlersuche von Schritt 7 stammenden,
  daher unregelmäßigen) sechs echten Preispunkten. Funktional vom Nutzer
  bestätigt; **visueller Feinschliff (Farben, Abstände, Beschriftung)
  bewusst auf einen späteren Zeitpunkt kurz vor Projektabschluss verschoben**
  (ausdrücklicher Nutzerwunsch — Funktionalität hat während der laufenden
  Entwicklung Vorrang vor Ästhetik).
- 10 neue Tests (`PriceHistoryChartView`-Zustände: leer/ein Punkt/mehrere
  Punkte/Platzhalter-Rücksetzung/Serien-Ersetzung/Paint-Smoke-Test;
  `CardDetailPanel`-Delegation; `CardController`-Verdrahtung mit und ohne
  `price_repository`). Gesamt: **212 Tests grün**.

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

## Dateien geändert / neu angelegt (Schritt 9)

**Neu:**
- `app/ui/widgets/card_filter_bar.py`
- `tests/test_card_filter_bar.py`

**Geändert:**
- `app/models/card.py` (`CardFilter`)
- `app/database/repositories/card_repository.py` (`search`,
  `distinct_set_names`)
- `app/services/card_service.py` (`search_cards`, `list_set_names`)
- `app/ui/widgets/card_list_panel.py` (Filterleiste eingebettet)
- `app/ui/controllers/card_controller.py` (Filter-/Scope-Zustand,
  `refresh()` umgebaut)
- `tests/{test_card_repository,test_card_service,test_card_controller}.py`
  (neue Tests)

---

## Dateien geändert / neu angelegt (Schritt 8)

**Neu:**
- `app/ui/widgets/price_history_chart.py`
- `tests/test_price_history_chart.py`

**Geändert:**
- `app/ui/widgets/card_detail_panel.py` (Chart-Widget eingebettet,
  `show_price_history`)
- `app/ui/controllers/card_controller.py` (`price_repository`-Parameter,
  zentralisiertes `_show_card`)
- `app/ui/main_window.py` (`PriceRepository` an `CardController` übergeben)
- `tests/{test_card_detail_panel,test_card_controller}.py` (neue Tests)

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

## Neue Klassen (Schritt 8)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `PriceHistoryChartView` | `ui.widgets.price_history_chart` | Eingebettetes Preisverlauf-Liniendiagramm (QtCharts) |

## Neue Klassen (Schritt 9)

| Klasse / Enum | Modul | Zweck |
|---------------|-------|-------|
| `CardFilter` | `models.card` | DTO: alle Such-/Filterkriterien für Karten |
| `CardFilterBar` | `ui.widgets.card_filter_bar` | Filterleiste über der Kartenliste |

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

1. ~~Schritt 11 — Export (CSV/Excel/JSON/PDF).~~ **Erledigt (2026-07-04).**
2. ~~Vintage-Multi-Versionen-Cardmarket-Bug.~~ **Erledigt (2026-07-04),
   gedrosselt.**
3. **Schritt 12 — Webcam-Scanner (OCR/Bildvergleich).** Auf Nutzerwunsch
   vorerst verworfen (2026-07-04) — einziger verbleibender Posten, falls
   später wieder aufgegriffen.

---

## Bekannte Bugs

- ~~Vintage-Sets mit mehreren Cardmarket-„Versionen"...~~ **Behoben am
  2026-07-04** (gedrosselt, max. 1 zusätzlicher Tab) — siehe „Vintage-
  Multi-Versionen-Bug: gedrosselter Wiederaufgriff" weiter oben.
- Keine weiteren funktionalen Bugs.
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
- ~~Bekannte Einschränkung: Die tolerante Suche erkennt Varianten-/Rarität-
  Wörter wie „holo“ nicht als Teilbegriff...~~ **Behoben am 2026-07-04** —
  siehe „Bugfix: Tolerante Suche scheiterte an Varianten-Wörtern" weiter
  oben.
- Schritt 7: sechs reale Bugs über mehrere Runden echter Klick-Tests gefunden
  und behoben (Tab-Kontamination, falsches Fenster, SQLite-Cross-Thread,
  verworfener Redirect-Filter, Paginierung — siehe „Nachbesserung" weiter
  oben) — live bestätigt, keine offenen Punkte mehr.

---

## Karte manuell per Cardmarket-Link eintragen + Toolbar aufgeräumt (2026-07-04)

**Ausgangslage:** Der Nutzer wollte eine Möglichkeit, eine Karte direkt über
ihren Cardmarket-Link einzutragen, statt (wie bisher als Workaround) eine
"falsche" Katalog-Karte anzulegen und danach zu korrigieren — v. a. gedacht
für genau die Fälle, in denen die automatische Katalog-Zuordnung ohnehin
scheitert (Vintage-Mehrfachversionen, JP/KO/ZH-Drucke).

**Umsetzung:**
- `app/pricing/models.py`: neues `ProductInfo` (name/set_name/card_number).
- `app/pricing/browser_price_reader.py`: `_parse_product_info()` (pure,
  testbar) + `read_product_info()` (öffnet einen Chrome-Tab, liest das
  Fenster, schließt ihn wieder — exakt derselbe Mechanismus wie beim
  Preis-Lookup). Cardmarkets eigener Seitentitel folgt live-bestätigt dem
  Muster `"<Name> (<Nummer>) - <Set> | Cardmarket"` — die Nummer ist leer
  bei Produkten ohne gedruckte Nummer (manche Promos).
- `app/ui/workers/product_info_worker.py`: `ProductInfoWorker` (QThread,
  spiegelt `PriceLookupWorker`) — Seiten-Lookup blockiert die GUI nicht.
- `app/ui/dialogs/manual_entry_dialog.py`: einfacher Dialog, nur ein
  Link-Feld.
- `app/ui/dialogs/card_details_dialog.py`: neuer Parameter
  `editable_identity` — Name/Set/Kartennummer werden bei diesem Flow zu
  editierbaren Feldern statt reiner Anzeige (es gibt keine garantiert
  korrekte Quelle wie bei einem Katalog-Treffer), plus `get_identity()`.
- `app/ui/controllers/manual_entry_controller.py`: startet den Flow (Link
  abfragen → Hintergrund-Lookup → Hinzufügen-Dialog vorausgefüllt).
- `CardService.add_card_manual()`: legt die Karte ohne Katalog-Zuordnung an,
  `manual_cardmarket_url` wird direkt gesetzt (kein `photo_path`, kein
  `external_card_id`, kein automatischer `cardmarket_url`).
- Neuer Toolbar-Knopf "Karte manuell eintragen" neben "Export".

**Toolbar gleichzeitig aufgeräumt (Nutzerwunsch):** Scanner- und
"Cardmarket-Preise aktualisieren"-Knopf entfernt (Scanner ist vorerst
verworfen; der Sammel-Update-Knopf hatte ohnehin nur eine Erklärung
angezeigt, nie einen echten Sammel-Lauf ausgelöst). Alle verbleibenden
Toolbar-Aktionen sind jetzt reine Textbuttons ohne Icon, wie schon die
Karten/Statistik-Navigation.

**Tests:** `tests/test_browser_price_reader.py` (3 neue für
`_parse_product_info`), `tests/test_card_details_dialog.py` (2 neue für
`editable_identity`/`get_identity`), `tests/test_card_service.py` (2 neue
für `add_card_manual`), `tests/test_card_controller.py` (3 neue),
`tests/test_product_info_worker.py` (neu, 3), `tests/test_manual_entry_
controller.py` (neu, 5), `tests/test_ui_smoke.py` angepasst (Scanner/
Update-Assertions entfernt, Icon-losigkeit + neuer Knopf geprüft).

**Live-Check (echte Cardmarket-Seite, kein Mock):**
`read_product_info()` gegen die reale Bisaflor-Legendary-Collection-Seite
liefert `ProductInfo(name='Venusaur', set_name='Legendary Collection',
card_number='18')`. End-to-end (`CardService.add_card_manual()` →
`PriceService.update_price_for_card()`, Karte mit `is_reverse_holo=True` und
diesem Link) liefert korrekt "Exakter Treffer: English, Light Played" bei
30,00 € — beide Korrekturen dieser Runde (manuelle Eintragung + Reverse-
Holo-Filter) funktionieren zusammen wie erwartet.

**⚠️ Noch offen:** Ein Klick-Test über die echte GUI (Knopf klicken, Link
einfügen, Dialog bestätigen) steht noch aus — die Logik selbst ist aber
bereits live gegen die reale Cardmarket-Seite bestätigt.

---

## "Infos und Einstellungen" + zweisprachige UI DE/EN (2026-07-04)

**Ausgangslage:** Der Nutzer wollte einen Menüpunkt mit App-Infos/Quellen
sowie eine komplett zweisprachige Oberfläche (Deutsch/Englisch), umschaltbar
in den Einstellungen.

**Architektur-Entscheidung (mit dem Nutzer geklärt):** Sprachwechsel wird
erst nach einem Neustart wirksam, nicht live. Begründung: Die App besteht
komplett aus handgebauten Widgets (keine Qt-Linguist-/`.ui`-Infrastruktur)
— jedes Widget beim Umschalten aktiv neu zu beschriften wäre deutlich
aufwendiger und fehleranfälliger, für vergleichsweise wenig Nutzen.

**Umsetzung:**
- `app/i18n.py` (neu): minimaler Nachschlage-Übersetzer. Jeder Aufrufort
  bleibt ein lesbares `tr("Deutscher Text")`; der deutsche String selbst
  ist der Schlüssel in einer statischen `_EN`-Tabelle (kein Symbol-basiertes
  i18n-Schema) — hält den Diff an jeder Stelle minimal. Ein fehlender
  Eintrag fällt auf Deutsch zurück statt abzustürzen.
- `app/database/repositories/settings_repository.py` (neu): einfacher
  Get/Set-Zugriff auf die schon seit Migration 1 bestehende, bis dahin
  ungenutzte `settings`-Tabelle. Schlüssel `"ui_language"`.
- `app/ui/dialogs/settings_dialog.py` + `app/ui/controllers/settings_
  controller.py` (neu): Dialog mit zwei Reitern ("Info": App-Name/Version/
  Quellen wie pokemontcg.io, Cardmarket, PokeAPI, PySide6, openpyxl,
  reportlab, pywinauto; "Einstellungen": Sprachauswahl DE/EN). Neuer
  Toolbar-Knopf "Infos und Einstellungen".
- `MainWindow`: lädt die gespeicherte Sprache über `set_ui_language()`,
  **bevor** Toolbar/Panels gebaut werden (sonst würden `tr()`-Aufrufe
  während des Konstruierens noch die alte Sprache sehen).
- Über 130 Einträge in der Übersetzungstabelle: komplette Toolbar, alle
  Dialoge (Karte hinzufügen/bearbeiten/manuell eintragen, Export,
  Einstellungen, Katalogsuche), alle Panels (Kartenliste, Kartendetails,
  Sammlungen, Filterleiste, Statistiken, Preisverlauf), Status-/
  Fehlermeldungen aus den Controllern und der Services-Schicht
  (`exceptions.py`, `collection_service.py`, `card_service.py`,
  `browser_price_reader.py`).
- `Language`/`Condition`/`ExportFormat`.label bleiben **unübersetzt** (sind
  bereits englische Fachbegriffe, z. B. "German"/"Near Mint"/"CSV") —
  nur `PriceQuality.label` ist echter deutscher Fließtext und wurde
  übersetzt.
- Export-Dateiinhalte (CSV/Excel/JSON/PDF) bleiben bewusst unübersetzt:
  eine exportierte Datei ist ein Datenartefakt, kein Live-UI-Element: ein
  Export in Deutsch und einer in Englisch mit unterschiedlichen
  Spaltenüberschriften wäre eher verwirrend als hilfreich.

**Zwei Bugs beim Übersetzen selbst gefunden und behoben (bevor sie
auffielen):**
1. **Modul-Ebene-`tr()`-Falle:** Mehrere Spaltenüberschriften-Listen
   (`card_list_panel.py`, `catalog_search_results_dialog.py`) waren
   ursprünglich Modul-Konstanten mit `tr(...)`-Aufrufen direkt beim Import
   — das hätte für immer die Sprache eingefroren, die beim allerersten
   Import aktiv war (meist Deutsch, noch bevor `MainWindow` die gespeicherte
   Einstellung lädt), unabhängig von der tatsächlichen Auswahl. Behoben:
   solche Listen sind jetzt Funktionen (`_columns()`), die bei jedem
   Dialog-/Panel-Aufbau neu ausgewertet werden.
2. **Tab-Wechsel-Erkennung über übersetzten Text:** `MainWindow.
   _on_central_tab_changed()` verglich `tabText(index) == "Statistiken"`,
   um zu entscheiden, ob die Statistik neu berechnet wird — das schlägt in
   Englisch fehl, weil der Tab-Text dann "Statistics" ist. Behoben: Vergleich
   jetzt über den reinen Index (`index == 1`), sprachunabhängig.

**Ein echter Testbug beim Schreiben selbst gefunden:** `test_manual_entry_
action_emits_signal`/die neue `test_settings_action_emits_signal` lösten
beim Klick auf die Toolbar-Aktion **auch den echten, verdrahteten
Controller** aus (nicht nur den Test-eigenen Listener) — der öffnete einen
echten `ManualEntryDialog`/`SettingsDialog` und rief `.exec()` auf, was den
gesamten Testlauf minutenlang hängen ließ (mehrere Testläufe in dieser
Runde liefen deshalb ungewöhnlich lange, bevor die Ursache gefunden wurde).
Behoben nach demselben, bereits etablierten Muster wie beim Such-Button-Test:
den echten Controller-Slot vor dem Trigger explizit trennen
(`disconnect()`), dann einen Test-eigenen Listener anhängen.

**Tests:** `tests/test_i18n.py` (4, neu), `tests/test_settings_repository.py`
(3, neu), `tests/test_settings_dialog.py` (3, neu),
`tests/test_settings_controller.py` (3, neu) — 426 Tests insgesamt grün,
`compileall` sauber.

**⚠️ Noch offen:** Ein Klick-Test über die echte GUI (Sprache umschalten,
Neustart, übersetzte Oberfläche bestätigen) steht noch aus.

---

## Datum/Uhrzeit-Abstand + Sprachflaggen + farbige Zustands-Badges (2026-07-04)

Drei kleinere, vom Nutzer per Screenshot/Text angefragte UI-Anpassungen:

1. **Datum/Uhrzeit zu eng zusammen:** `app/utils/time.py::format_display_
   datetime()` (neu, gemeinsam genutzt von `statistics_panel.py` und
   `card_detail_panel.py`) fügt drei Leerzeichen zwischen Datum und Uhrzeit
   ein statt nur eines. `price_history_dock.py`s Qt-eigenes Zeitformat
   ebenso erweitert. Nebenbei behoben: `card_detail_panel.py` zeigte
   "Letzte Aktualisierung" bisher als **rohen ISO-String**
   (z. B. "2026-07-04T20:05:27+00:00") an, nie formatiert — jetzt einheitlich
   mit dem gleichen Helfer formatiert.
2. **Sprachflaggen statt Kürzel:** `app/ui/language_icon_provider.py`
   (neu) zeichnet vereinfachte, aber erkennbare Flaggen für alle 9
   Sprachen direkt per `QPainter` (gleiches Prinzip wie App-Icon/
   Checkbox-Häkchen — kein Download, keine Bilddatei). In der Kartenliste
   ersetzt das Flaggen-Icon jetzt den Sprachcode-Text; der Text bleibt
   (unsichtbar, `foreground` transparent) für die bestehende alphabetische
   Sortierung erhalten.
3. **Farbige Zustands-Badges wie Cardmarket:** `app/ui/condition_colors.py`
   (neu) ordnet jedem `Condition`-Wert eine Hintergrund-/Textfarbe zu,
   angelehnt an Cardmarkets eigene Farbcodierung (Mint/Near Mint grün,
   Excellent oliv, Good gold, Light Played orange, Played/Poor dunkelrot) —
   angenähert, nicht pixelgenau aus Cardmarkets CSS übernommen. In der
   Kartenliste wird die Zustands-Zelle jetzt entsprechend eingefärbt.

**Live geprüft (da kein GUI-Screenshot-Tool verfügbar):** Alle 9 Flaggen und
alle 7 Zustandsfarben wurden über ein Wegwerf-Skript als PNG gerendert und
visuell inspiziert (Datei danach gelöscht, nicht Teil des Commits) — alle
erkennbar und farblich stimmig.

**Tests:** `tests/test_time.py` (2, neu),
`tests/test_language_icon_provider.py` (10, neu) — 426 Tests weiterhin
grün (die Kartenlisten-Änderungen selbst sind rein visuell, ohne
bestehende Text-basierte Test-Assertions zu berühren).

**Nachbesserung (Nutzerfeedback nach dem ersten Klick-Test):**
1. **"Karte manuell eintragen" direkt neben "Suchen"** verschoben (vorher
   ganz rechts neben Export).
2. **Aktiver Reiter farblich hervorgehoben:** `QToolBar QToolButton:checked`
   fehlte komplett im Stylesheet — "Karten"/"Statistik" sahen aktiv wie
   inaktiv identisch aus. Neue Regel in `theme.py` (Akzentfarbe als
   Hintergrund, wie ein gedrückter Zustand).
3. **Sprachflaggen zentriert + Zustands-Zelle als Badge-Icon statt
   Volltonfarbe:** `_CenteredIconDelegate` (neu, `card_list_panel.py`) —
   ein `QStyledItemDelegate`, der das Icon manuell mittig zeichnet, da der
   Standard-Delegate ein Icon ohne sichtbaren Text trotzdem am linken
   Zellenrand verankert (Icon und Text sind zwei getrennte Layout-Slots,
   auch wenn der Text unsichtbar ist). `app/ui/condition_icon_provider.py`
   (neu) zeichnet dieselben Cardmarket-Farben jetzt als kleine, abgerundete
   Badge-Icons mit dem Zustands-Kürzel drauf (wie auf Cardmarket), statt
   die ganze Tabellenzelle einzufärben.

**"Manuell eintragen geht nicht"** stellte sich als Bedienfehler heraus:
ohne zuvor ausgewählte Sammlung erscheint nur eine leicht zu übersehende
Statusleisten-Meldung — kein Bug, vom Nutzer selbst bestätigt.

**Live geprüft:** Echte `CardListPanel` mit drei Beispielkarten
(Deutsch/Englisch/Japanisch, drei verschiedene Zustände) gerendert und als
PNG inspiziert — Flaggen und Zustands-Badges sitzen sichtbar zentriert.

**Tests:** `tests/test_condition_icon_provider.py` (10, neu).

---

## Sealed-Produkte (Booster-Boxen, Displays, ETBs, ...) (2026-07-05)

**Ausgangslage (Nutzervorschlag):** Cardmarket handelt auch mit versiegelten
Produkten (Booster-Boxen, Displays, Elite Trainer Boxes, ...) — Vorschlag,
dafür eine eigene Kategorie in der App anzulegen, analog zu Karten.

**Recherchiert, bevor mit dem Bau begonnen wurde:** Eine echte Cardmarket-
Sealed-Seite (Base Set Booster Box) live per Chrome-Fensterauslese geprüft.
Zwei wichtige strukturelle Unterschiede zu Einzelkarten gefunden:
1. **Kein Zustand.** Cardmarket erlaubt Sealed-Produkte nur versiegelt zu
   verkaufen ("Opened products cannot be sold", wörtlich auf der Seite) —
   keine MT/NM/EX/GD/LP/PL/PO-Leiter, jedes Angebot hat nur eine Sprache.
2. **Anderer Seitentitel.** Einzelkarten: `"<Name> (<Nr>) - <Set> |
   Cardmarket"`. Sealed: nur `"<Name> | Cardmarket"` — keine Nummer, kein
   Set-Anhang. Die Kategorie (z. B. "Booster Boxes") steht stattdessen in
   der Breadcrumb, im selben Textknoten wie der Produktname noch einmal
   wiederholt ("Base Set Booster Box Booster Boxes").

Deshalb bewusst **kein** Wiederverwenden der Karten-Preislogik 1:1, sondern
eigene, einfachere Parsing-/Preisfunktionen (gleicher Chrome-Fenster-
Lesemechanismus, andere Auswertung).

**Architektur-Entscheidung (mit dem Nutzer geklärt):** Sealed-Produkte
laufen in einem eigenen, dritten Reiter ("Sealed" neben "Karten"/
"Statistik"), nicht als Filter innerhalb von "Karten" — andere Felder
(keine Kartennummer/Zustand, dafür Kategorie), eigene, einfachere Tabelle.

**Umgesetzt:**
- **Datenmodell/DB:** `app/models/sealed_product.py`
  (`SealedProduct`/`SealedProductDetailsValues`/`SealedProductFilter`),
  Migration 5 (`sealed_products`-Tabelle, eigener Index),
  `SealedProductRepository` (CRUD, Textsuche über Name/Kategorie/Notizen).
- **Browser-Parsing** (`app/pricing/browser_price_reader.py`):
  `_SEALED_TITLE_RE` (`"<Name> | Cardmarket"`), `_parse_sealed_product_info`
  (Name aus Titel, Kategorie aus der Breadcrumb-Zeile, die mit `"<name> "`
  beginnt — Titel-Zeilen selbst werden dabei über den `"Cardmarket"`-String
  ausgeschlossen, sonst hätte die Titel-Zeile selbst fälschlich als
  Kategorie-Treffer gezählt), `read_sealed_product_info()`;
  `_parse_sealed_offer_lines` (spiegelt `_parse_offer_lines`, aber die
  **Sprache** validiert eine Angebotszeile statt des Zustands — eine bei
  Cardmarket verkaufte, aber im eigenen `Language`-Enum fehlende Sprache
  wie Niederländisch lässt die ganze Zeile stillschweigend wegfallen, nicht
  nur das Sprachfeld leer), `read_sealed_offers_for_card()`.
- **Services:** `SealedProductService` (CRUD, immer per Link — es gibt
  keinen Katalog für Sealed-Produkte), `SealedPriceService` (deutlich
  einfachere Leiter als bei Karten: **ein** ungefilterter Seitenaufruf,
  Sprachabgleich rein lokal in Python statt über einen ungeprüften
  `?language=`-URL-Parameter — der wurde für Sealed-Seiten nie live
  bestätigt, anders als bei Einzelkarten).
- **UI:** `SealedProductListPanel` (Name/Kategorie/Sprache-Flagge/Menge/
  Preis, eigener eingebetteter "+ Sealed-Produkt hinzufügen"-Knopf wie bei
  `CollectionPanel`s "+ Neue Sammlung" — es gibt keinen globalen
  Toolbar-Knopf dafür), `SealedProductDetailsDialog` (Name/Kategorie immer
  editierbar), `SealedProductController`/`SealedEntryController`/
  `SealedPriceController` (spiegeln die Karten-Pendants), neuer dritter
  Toolbar-Reiter "Sealed".
- **Geteilte Komponente ausgelagert:** `_CenteredIconDelegate` (bisher
  privat in `card_list_panel.py`) nach `app/ui/widgets/
  centered_icon_delegate.py` verschoben (`CenteredIconDelegate`, jetzt
  öffentlich) — wird von Kartenliste **und** Sealed-Liste für die
  zentrierten Sprachflaggen genutzt.
- `ManualEntryDialog` bekommt einen optionalen `title`-Parameter (Default
  weiterhin die Karten-Variante, zur Laufzeit aufgelöst statt als
  Default-Argument, sonst hätte sich die beim Import aktive Sprache für
  immer eingefroren) — wird für den Sealed-Link-Dialog wiederverwendet.

**Live-Check (echte Cardmarket-Seite, kein Mock):** `read_sealed_product_
info()` gegen die reale Base-Set-Booster-Box-Seite liefert
`SealedProductInfo(name='Base Set Booster Box', category='Booster
Boxes')`. `read_sealed_offers_for_card()` findet 2 echte Angebote (beide
Deutsch, 5.000 €/21.000 €) — ein drittes, niederländisches Angebot fällt
erwartungsgemäß weg (siehe oben). End-to-end (anlegen → Preis ermitteln)
funktionierte im ersten Versuch nicht (dieselbe, bereits bekannte
gelegentliche Fenster-Erkennungs-Flakigkeit wie bei Karten, siehe
"Bekannte Bugs" weiter oben — zwei Chrome-Tabs direkt hintereinander ohne
Pause), im zweiten Versuch (isolierter Aufruf) einwandfrei.

**Tests:** `tests/test_sealed_product_repository.py` (11, neu),
`tests/test_sealed_product_service.py` (10, neu),
`tests/test_sealed_price_service.py` (8, neu), Erweiterungen in
`tests/test_browser_price_reader.py` (6 neue), `tests/test_sealed_product_
details_dialog.py` (4, neu), `tests/test_sealed_product_controller.py`
(6, neu), `tests/test_sealed_product_info_worker.py` (3, neu),
`tests/test_sealed_price_lookup_worker.py` (5, neu),
`tests/test_sealed_entry_controller.py` (5, neu),
`tests/test_sealed_price_controller.py` (4, neu), `tests/test_database.py`
(Migrationszähler auf 5 aktualisiert).

**⚠️ Noch offen:** Ein Klick-Test über die echte GUI (Sealed-Reiter öffnen,
Link einfügen, Dialog bestätigen, Preis abrufen) steht noch aus.

---

## Verschieben zwischen Sammlungen + Export-Typ-Auswahl (2026-07-05)

Zwei vom Nutzer gewünschte Ergänzungen, direkt im Anschluss an die
Sealed-Produkte:

1. **Karte/Sealed-Produkt zwischen Sammlungen verschieben:** Neuer
   Kontextmenü-Punkt "Verschieben" in beiden Listen. Neues, gemeinsames
   `MoveDialog` (Zielsammlung-Dropdown, schließt die aktuelle Sammlung
   automatisch aus) — von `CardController`/`SealedProductController` genutzt,
   die dafür jetzt beide einen `CollectionService` brauchen (Konstruktor-
   Signatur geändert, alle Aufrufstellen inkl. Tests angepasst).
   `CardRepository.move()`/`SealedProductRepository.move()` +
   `CardService.move_card()`/`SealedProductService.move_product()` (jeweils
   ein simples `UPDATE ... SET collection_id = ...`).
2. **Export: Karten vs. Sealed-Produkte:** `ExportDialog` bekommt eine
   dritte Auswahl ("Was:" Karten/Sealed-Produkte) vor Format und Sammlung.
   `SealedExportRow`/`SEALED_COLUMNS` (neu, `app/export/models.py`) — eigene,
   kürzere Spalten (kein Set/Nr./Zustand/Extra, dafür Kategorie). Alle vier
   Writer (`csv_export`/`excel_export`/`json_export`/`pdf_export`) bekommen
   ein `write_sealed()` daneben; die bestehenden `write()`-Funktionen intern
   auf einen gemeinsamen, parametrisierten `_write()` umgestellt (Card-Export
   selbst unverändert, alle bestehenden Tests weiterhin grün).
   `ExportService.export()` bekommt einen neuen `target`-Parameter
   (`ExportTarget.CARDS`/`SEALED`, Default `CARDS` für Rückwärts-
   kompatibilität) und branched entsprechend.

**Recherchiert, aber (noch) nicht umgesetzt:** Nutzerfrage nach Graded-
Card-Preisen (z. B. via 130point.com, eBay-Verkäufe) und PSA Population
Report. Direkter Abruf beider Seiten liefert 403 (wie bei Cardmarket).
Ein schneller Testlauf mit der bestehenden Chrome-Fenster-Lesetechnik
(generisch, ohne Cardmarket-spezifische Titel-Prüfung) gegen 130point.com
fand das Fenster nicht rechtzeitig — nicht abschließend geklärt, ob das an
einer Bot-Prüfungsseite, langsamerem Laden oder stärkerem Schutz liegt.
Wäre ein eigenes, separates Recherche-/Bauprojekt (zwei neue Datenquellen:
Verkaufspreise + Grading-Populationszahlen), bewusst nicht in dieser Runde
begonnen.

**Tests:** `tests/test_card_repository.py`/`tests/test_sealed_product_
repository.py` (je 1 neu), `tests/test_card_service.py`/`tests/
test_sealed_product_service.py` (je 2 neu), `tests/test_move_dialog.py`
(neu, 3), `tests/test_card_controller.py`/`tests/test_sealed_product_
controller.py` (je 2 neu), `tests/test_csv_export.py`/`test_excel_export.py`/
`test_json_export.py`/`test_pdf_export.py` (je 1 neu),
`tests/test_export_service.py` (4 neu), `tests/test_export_dialog.py`
(2 neu), `tests/test_export_controller.py` (1 neu + bestehende angepasst).

---

## Reiter-Reihenfolge + Tab-Scoping + Sealed-Button-Verwirrung behoben (2026-07-05)

Drei vom Nutzer gemeldete Punkte direkt im Anschluss an Verschieben/Export:

1. **Suchfeld + "Karte manuell eintragen" nur bei "Karten":** beide waren
   bisher immer sichtbar, unabhängig vom aktiven Reiter. Jetzt genau wie
   der eingebettete "+ Sealed-Produkt hinzufügen"-Knopf tab-gebunden:
   `MainWindow._on_central_tab_changed()` blendet `_act_manual_entry`
   zusätzlich zu Suchfeld/Suchen-Knopf ein/aus.
2. **Reiter-Reihenfolge:** Karten → Sealed → Statistik (vorher Karten →
   Statistik → Sealed). Betroffen: Toolbar-Aktionsreihenfolge, `QTabWidget`-
   Registrierungsreihenfolge in `_build_central()`, alle index-basierten
   Stellen in `_switch_central_tab()`/`_on_central_tab_changed()`
   (Statistik-Refresh, Checked-Zustand der drei Nav-Buttons).
3. **"Add sealed product" wirkte kaputt:** Root Cause identisch zu einem
   bereits einmal aufgetretenen Fall bei "Karte manuell eintragen" — ohne
   ausgewählte Sammlung reagierte der Knopf nur mit einer leicht zu
   übersehenden Statusleisten-Meldung (5 Sekunden, kein Fokus-Wechsel), was
   auf einem größtenteils leeren Sealed-Reiter wie "nichts passiert"
   wirkt. Fix in beiden betroffenen Controllern
   (`SealedEntryController`/`ManualEntryController`): der Hinweis "Bitte
   zuerst eine Sammlung auswählen" erscheint jetzt als echter,
   blockierender `QMessageBox`-Dialog statt als Statusleisten-Toast — analog
   zu `SealedProductController.prompt_add()`s eigenem `show_error()`, der
   bereits einen Dialog verwendet.

**Tests:** `tests/test_ui_smoke.py` (Tab-Reihenfolge + Sichtbarkeits-
Assertions angepasst), `tests/test_manual_entry_controller.py`/`tests/
test_sealed_entry_controller.py` (Statusleisten- auf `QMessageBox`-Assertion
umgestellt).

---

## Sealed-Produkte ohne Sammlungsbezug + fixe Toolbar-Reiter-Positionen (2026-07-05)

Direktes Nutzer-Feedback zum vorigen Punkt (Live-Screenshot): das Suchfeld
blieb auf dem Sealed-Reiter sichtbar, und der Nutzer erklärte explizit,
dass Sealed-Produkte gar keine Sammlung haben sollten ("bei Karten macht es
Sinn, sind ja in Ordnern sortiert, aber Sealed ist unlogisch"). Per
`AskUserQuestion` bestätigt: sauberer Schnitt mit echter Migration statt
nur UI-seitigem Verstecken.

1. **Sealed-Produkte ohne Sammlung:** Migration 6 baut `sealed_products`
   ohne `collection_id` neu auf (SQLite kann eine Fremdschlüssel-Spalte
   nicht per `ALTER TABLE DROP COLUMN` entfernen — Standard-Rezept:
   Tabelle neu anlegen, Daten kopieren, alte Tabelle löschen, umbenennen).
   `SealedProduct`/`SealedProductFilter` ohne `collection_id`,
   `SealedProductRepository` ohne `list_by_collection()`/`move()`,
   `SealedProductService` ohne `list_products()`/`move_product()`,
   `SealedProductController` ohne `set_collection()`/`collection_id`-Property
   (Konstruktor braucht jetzt keinen `CollectionService` mehr) — `refresh()`
   lädt immer alle Produkte, einmalig beim Start aus `MainWindow._build_central()`
   aufgerufen statt reaktiv auf `CollectionController.selection_changed`.
   "Verschieben"-Kontextmenüpunkt + Signal aus `SealedProductListPanel`
   entfernt (ergibt ohne Sammlungen keinen Sinn; bleibt für Karten
   bestehen). `SealedEntryController.start()` braucht keinen
   Sammlungs-Guard mehr. Export "Sealed-Produkte": `ExportDialog` blendet
   die "Sammlung"-Zeile aus (`QFormLayout.setRowVisible`), wenn Sealed
   gewählt ist, und erzwingt `collection_id=None`; `SealedExportRow`/
   `SEALED_COLUMNS` verlieren die Spalte "Sammlung" (JSON/PDF-Spaltenbreiten
   entsprechend angepasst).
2. **Toolbar: fixe Reiter-Positionen:** Suchfeld, "Suchen" und "Karte
   manuell eintragen" stecken jetzt in einem gemeinsamen `QWidget`-
   Container (eigenes `QHBoxLayout`) mit fixer Mindestbreite, statt einzeln
   direkt auf der Toolbar zu sitzen — Ein-/Ausblenden verschiebt dadurch
   nicht mehr die Position der Reiter/Export/Infos danach. Nebenbei behoben:
   das Suchfeld blieb auf dem Sealed-Reiter fälschlich sichtbar, weil ein
   per `toolbar.addWidget()` direkt gesetztes Widget sein
   `setVisible(False)` nach einem Style-/Layout-Durchlauf wieder verlieren
   konnte — als echte Kinder eines eigenen Containers passiert das nicht
   mehr. "Karte manuell eintragen" bleibt eine echte `QAction` (für
   `.trigger()`/`.setVisible()` an bestehenden Stellen), gebunden an einen
   manuell erzeugten `QToolButton` per `setDefaultAction()`.

**Tests:** `tests/test_sealed_product_repository.py`/`test_sealed_product_
service.py`/`test_sealed_product_controller.py`/`test_sealed_entry_
controller.py`/`test_sealed_price_service.py`/`test_sealed_price_
controller.py`/`test_sealed_price_lookup_worker.py` (Sammlungsbezug
entfernt), `test_export_service.py`/`test_export_dialog.py`/`test_csv_
export.py`/`test_excel_export.py`/`test_json_export.py`/`test_pdf_
export.py` (keine "Sammlung"-Spalte mehr bei Sealed), `test_database.py`
(Migrationszähler 5 → 6, neuer Test für die fehlende Spalte),
`test_ui_smoke.py` (fixe Container-Breite ändert nichts an den bestehenden
Sichtbarkeits-Assertions). Alle 510 Tests grün (weniger als vorher, da die
Sammlungs-/Verschieben-Tests für Sealed-Produkte entfallen sind).

### Nachbesserung nach Live-Screenshot (noch am 2026-07-05)

Zwei Regressionen aus der obigen Änderung, vom Nutzer per Screenshot
gemeldet:

1. **"Suchen"-Button riesig:** `QPushButton`s Standard-`SizePolicy` ist
   `Minimum` (kann über den `sizeHint()` hinauswachsen) — ohne Deckelung war
   er der einzige Kandidat im neuen Container, der den Leerraum aufsaugen
   konnte, den die (auf Sealed/Statistik ausgeblendeten) Geschwister-Widgets
   hinterließen. Fix: `SizePolicy.Fixed` auf den Suchen-Button.
2. **"Karte manuell eintragen" blieb auf Sealed sichtbar:**
   `QToolButton.setDefaultAction()` synct Text/Icon/Enabled/Checked von der
   Action, **aber nicht die Sichtbarkeit** — ein Bug in meiner eigenen
   Annahme von der letzten Runde. Der echte `QToolButton` (`self.
   _manual_entry_button`) bekommt jetzt selbst ein explizites
   `setVisible()` in `_on_central_tab_changed()`, zusätzlich zur (weiterhin
   vorhandenen) `QAction`.
3. Nebenbei: die feste Mindestbreite des Suchgruppen-Containers wird jetzt
   erst **nach** `app.setStyleSheet(...)` eingefroren (vorher zu früh, mit
   noch ungestylten, kleineren Fonts/Paddings berechnet).

**Tests:** `test_ui_smoke.py` um zwei Assertions (`_manual_entry_button.
isHidden()`) und einen neuen Regressionstest
(`test_search_button_and_manual_entry_button_do_not_grow`) erweitert.

---

## Autonome Nacht-Session (2026-07-05, ohne Rückfragen)

Der Nutzer ist schlafen gegangen und hat mich ausdrücklich beauftragt, die
folgenden Punkte komplett und ohne weitere Rückfrage umzusetzen bzw. zu
recherchieren — Freigabe/Korrektur erfolgt danach:

### Graded-Karten (130point.com Verkaufspreise + PSA Population Report): recherchiert, bewusst NICHT umgesetzt

Live auf diesem Rechner mit der bestehenden Browser-Lese-Mechanik getestet
(derselbe echte-Chrome-Tab-Ansatz wie für Cardmarket):

- **130point.com hat — anders als Cardmarket — keine einfache, per URL
  filterbare Suchseite.** `?q=...`/`?query=...`-Parameter an `/search` bzw.
  `/sales` werden schlicht ignoriert (die Seite zeigt weiterhin nur die
  generischen "Featured Auctions"). Ein Live-Versuch mit `?q=...` löste
  sogar eine Cloudflare-Challenge aus (`__cf_chl_f_tk=...` in der
  resultierenden URL) — die Seite steht unter Bot-Schutz.
- Ein zweiter Test hat das Sucheingabefeld direkt über UI Automation
  angesteuert (Text eingetippt, Enter gedrückt) — **das funktioniert** und
  liefert echte Treffer (z. B. für "Umbreon VMAX 215" ein reales Angebot
  "Umbreon VMAX (Alternate Art Secret) 215/203 ... $1.750,00"). Das ist aber
  echtes Tippen/Klicken in eine fremde Webseite hinein — etwas, das dieses
  Projekt bei Cardmarket bewusst vermeidet (siehe Docstring in
  `browser_price_reader.py`: "This deliberately does not automate or drive
  a browser"). Diese Grenze jetzt für eine zweite Seite aufzuweichen, noch
  dazu eine mit aktivem Cloudflare-Schutz, halte ich für ein zu großes,
  unnötiges Risiko für einen Nice-to-have ("nur eine ungefähre
  Preisspanne").
- **PSA Population Report:** `psacard.com/pop/search` verlangt inzwischen
  eine Anmeldung ("Sign In to PSA"). Die offizielle, dokumentierte Public
  API (`psacard.com/publicapi/documentation`) deckt nur die Cert-Nummer-
  Verifikation ab (eine bestimmte, bereits bekannte Zertifikatsnummer prüfen),
  keine Namens-/Grade-basierte Populationssuche. Eine Anmeldung im Namen
  des Nutzers vorzunehmen, ist mir grundsätzlich untersagt (Kreditkarten/
  Login-Daten nie selbst eingeben) — damit ist dieser Teil ohne Weiteres
  nicht sauber umsetzbar.

**Entscheidung:** Kein Feature gebaut, weder für 130point.com noch für PSA.
Eine funktionslose "Öffne die Seite für dich"-Notlösung hätte kaum
Mehrwert gegenüber einem Lesezeichen geboten und wurde bewusst nicht
gebaut, um keine Pseudo-Funktion vorzutäuschen. Falls gewünscht, wäre der
nächstbeste Ansatz ein eigenständiges, separates Recherche-Tool mit
expliziter Nutzer-Freigabe für das Antippen fremder Suchfelder — das sollte
aber eine bewusste, eigene Entscheidung sein, keine, die ich stillschweigend
in der Haupt-App verankere.

### Sealed-Kategorien: feste Liste + Dropdown

Recherche (WebSearch, da direkter Fetch auf cardmarket.com/130point.com
weiterhin mit 403 blockt): Cardmarkets eigene Kategorie-URLs sind real
bestätigt `/Booster-Boxes`, `/Boosters`, `/Box-Sets`, `/Elite-Trainer-Boxes`,
`/Tins`, `/Blisters`. Daraus plus allgemein bekannten weiteren Pokemon-TCG-
Produkttypen ein neues, festes `SealedCategory`-Enum gebaut
(`app/models/enums.py`, gleiches Muster wie `Condition`/`Language`: `code`/
`label`, plus `guess_from_text()` für Best-Effort-Zuordnung von Freitext,
Fallback `OTHER`/"Sonstiges").

- `SealedProductDetailsDialog._category_edit` (QLineEdit) → `_category_combo`
  (editierbare QComboBox), vorbefüllt mit dem geratenen, kanonischen Label
  oder dem Original-Text, falls nichts erkannt wurde.
- `browser_price_reader._parse_sealed_product_info()` normalisiert die aus
  dem Cardmarket-Breadcrumb geparste Kategorie jetzt über `guess_from_text()`
  (z. B. "Booster Boxes" → "Booster Box").
- Bewusst **keine** SQL-Migration für bereits vorhandene Sealed-Produkte:
  es gibt noch keine echten Nutzerdaten in der Sealed-Tabelle (leerer
  Sealed-Reiter im letzten Screenshot), daher wäre eine Migration mit
  Substring-Matching-Logik in reinem SQL unverhältnismäßiger Aufwand für
  praktisch null Bestandsdaten. Freitext bleibt technisch weiterhin möglich
  (editierbare Combobox), falls ein Produkt in keine der festen Kategorien
  passt.

**Tests:** `tests/test_models.py` (`SealedCategory`-Lookup/Guess),
`tests/test_sealed_product_details_dialog.py` (Dropdown-Vorbefüllung/
-Optionen), `tests/test_browser_price_reader.py` (normalisierte Kategorie).

### Statistik: Sealed-Produkte einbezogen + optisch neu gegliedert

`StatisticsService` bekommt eine neue Pflicht-Abhängigkeit
`SealedProductService` und berechnet zusätzlich: `sealed_total_value`,
`sealed_item_count` (Mengen aufsummiert, nicht nur Anzahl Einträge),
`combined_total` (Karten + Sealed), `value_by_sealed_category`,
`most_expensive_sealed_products`, `sealed_stale_price_products` (neue
`StaleSealedPriceEntry`-Dataclass). Die bestehenden `is_price_stale()`/
`days_since_price_update()`-Hilfsfunktionen brauchten keine Änderung — sie
waren bereits duck-typed auf `.price_updated_at`/`.total_value` und wurden
schon vorher von `sealed_product_list_panel.py` mitbenutzt.

`StatisticsPanel` komplett neu aufgebaut: oben eine "Portfolio-Übersicht"
mit dem kombinierten Gesamtwert (großer, hervorgehobener Text) und zwei
Kennzahl-Kacheln (neues `QWidget#StatCard`-Styling in `theme.py` — dezent
abgehobener Hintergrund, große akzentfarbene Zahl, kleiner Untertext mit
Anzahl + Stand). Darunter zwei klar getrennte Ober-Abschnitte "Karten" und
"Sealed-Produkte" (neues `QLabel#SuperSectionHeader`-Styling — größer als
die bisherigen Abschnitts-Überschriften, mit Trennlinie darunter), jeweils
mit ihren eigenen Detail-Tabellen. Neues Signal
`sealed_price_lookup_requested` (mirror von `price_lookup_requested`) für
den Inline-Knopf in der Sealed-Tabelle mit veraltetem Preis.
`SealedPriceController` bekommt (wie `PriceController` schon vorher) einen
optionalen `statistics_controller`-Parameter, der nach einer erfolgreichen
Preisermittlung mit aktualisiert wird.

**Tests:** `tests/test_statistics_service.py`/`test_statistics_panel.py`
komplett um Sealed-Fälle erweitert, `tests/test_sealed_price_controller.py`
um einen Test für die neue Statistik-Refresh-Verdrahtung.

**Nicht selbst visuell geprüft:** Als CLI-Agent ohne Screenshot-Fähigkeit
für die native Qt-Anwendung konnte ich das neue Layout nur strukturell (über
Tests) prüfen, nicht tatsächlich ansehen. Bitte im laufenden Programm einmal
den Statistik-Reiter anschauen, bevor du das absegnest.

---

## Morgendliche Korrekturrunde: Toolbar-"Geisterbox" + kontextabhängiger linker Bereich (2026-07-05)

Der Nutzer war beim Aufwachen zurecht unzufrieden: die Toolbar sah auf
Sealed/Statistik schlimmer aus als vorher. Zwei echte Bugs gefunden und
behoben, live per Screenshot verifiziert (siehe unten):

1. **Dunkle "Geisterbox":** Der Container für Suchfeld/Suchen/"Karte manuell
   eintragen" (`self._cards_only_group`) hatte kein `objectName` und erbte
   dadurch die allgemeine `QWidget { background-color: ... }`-Regel — eine
   *dunklere* Farbe als die Toolbar selbst. Solange der Container voller
   Inhalte war, fiel das nicht auf; sobald die Kinder auf Sealed/Statistik
   ausgeblendet waren, blieb ein deutlich sichtbares dunkles Rechteck übrig.
   Erst fälschlich als Qt-Repaint-Bug vermutet (ein `.update()`-Aufruf
   brachte nichts) — der eigentliche Fund kam erst durchs tatsächliche
   Ansehen eines Screenshots. Fix: `objectName("ToolbarSearchGroup")` +
   `background: transparent` in `theme.py`.
2. **Linker Bereich sollte nie leer wirken (Nutzer-Feedback mit Photoshop-
   Annotation):** "+ Sealed-Produkt hinzufügen" ist kein eingebetteter
   Button im `SealedProductListPanel` mehr, sondern ein Toolbar-Button
   (`self._sealed_add_button`), der im selben Container wie Suchfeld/
   Suchen/"Karte manuell eintragen" sitzt und per neuem
   `MainWindow.sealed_add_requested`-Signal verdrahtet ist (da der
   Controller, der es letztlich braucht, erst in `_build_central()`
   entsteht — exakt das gleiche Verdrahtungsmuster wie `manual_entry_
   requested`). `_on_central_tab_changed()` blendet jetzt kontextabhängig
   um: Karten-Reiter → Suchfeld/Suchen/Karte-manuell; Sealed-Reiter → nur
   der Sealed-Add-Button; Statistik-Reiter → keins von beidem (dort gibt es
   keine sinnvolle Aktion für diesen Slot). Die Container-Breite bleibt
   weiterhin fix eingefroren, damit die Nav-Buttons rechts nie springen.

**Neue Fähigkeit diese Session:** echte Screenshots der laufenden Qt-App
selbst aufnehmen und ansehen (nicht nur Tests), über ein kleines PowerShell-
Skript mit `PrintWindow` (`PW_RENDERFULLCONTENT`) — bewusst *nicht* über
`CopyFromScreen` nach `SetForegroundWindow`, weil das einmal live
schiefging: `SetForegroundWindow` schlug still fehl (Windows' Fokus-
Diebstahl-Schutz, siehe auch die `AllowSetForegroundWindow`-Notiz in
`browser_price_reader.py`), und `CopyFromScreen` erfasste stattdessen ein
komplett unrelated Fenster, das gerade im Vordergrund war. `PrintWindow`
umgeht das, weil es das Fenster direkt zeichnen lässt, unabhängig vom
Fokus.

**Tests:** `tests/test_ui_smoke.py` um `test_sealed_add_button_emits_signal`
erweitert und die bestehende Sichtbarkeits-Assertion um den neuen Button
ergänzt.

### Nachbesserung 2: links zu breit, rechts nicht bündig

Per erneutem Screenshot-Vergleich aufgefallen: bei einer breiteren
Fensterbreite als der ursprünglich per `resize()` gesetzten öffnete sich
eine große Lücke zwischen der linken Gruppe und den Reitern, und die
Reiter selbst waren dadurch nicht wirklich rechtsbündig — nur "zufällig
nah dran", solange das Fenster ungefähr die Entwurfsbreite hatte.

- **Ursache 1:** `self._cards_only_group` (ein einfaches `QWidget`) hatte
  zwar eine per `setMinimumWidth()` eingefrorene Mindestbreite, aber keine
  explizite `SizePolicy` — Qt's Standard (`Preferred`) erlaubt weiterhin
  Wachstum über diese Mindestbreite hinaus. Da es das einzige *Widget*-
  Element in der Toolbar ist (alle Nav-/Export-/Infos-Punkte sind fixe
  `QAction`-Buttons), sog es jeden ungenutzten Fensterbreiten-Überschuss
  auf und schob den Trenner + die Reiter entsprechend weiter nach rechts —
  aber eben nicht bis zum echten rechten Rand, weil davor noch die
  addAction()-Elemente selbst kommen. Fix: `SizePolicy.Fixed` (horizontal).
- **Ursache 2:** Ohne dieses Wachstum braucht es stattdessen einen
  expliziten, dehnbaren Platzhalter zwischen Trenner und Reitern, damit
  die Reiter wirklich an den rechten Rand gedrückt werden (statt einfach
  direkt nach der jetzt fixen linken Gruppe zu stehen). Neues
  `toolbar_spacer`-Widget mit `SizePolicy.Expanding`, mit demselben
  `ToolbarSearchGroup`-`objectName` (transparent) wie die linke Gruppe —
  sonst hätte es dieselbe dunkle "Geisterbox" gezeigt wie die linke Gruppe
  vorher.
- **Ursache 3 (Nebenfund):** Die eingefrorene Breite selbst wurde bisher
  aus `self._cards_only_group.sizeHint()` berechnet — das unterschätzte
  die tatsächlich gewünschte Breite des Suchfelds (dessen `sizeHint()`
  nicht dessen `maximumWidth()` widerspiegelt), wodurch der jetzt *fixe*
  Container das Suchfeld sichtbar zusammenquetschte. Jetzt wird die Breite
  explizit aus den einzelnen Kind-Widgets berechnet (`search.
  maximumWidth()` + `sizeHint().width()` der drei Buttons + Abstände),
  unabhängig vom aktuellen Sichtbarkeits-Zustand einzelner Kinder.

Alle drei Reiter (Karten/Sealed/Statistik) nochmal per Screenshot
verifiziert: linke Gruppe kompakt und linksbündig, Reiter/Export/Infos
bündig am rechten Rand, Lücke dazwischen konstant unabhängig vom Reiter.

### Nachbesserung 3: Abstände links immer noch zu groß, Sealed-Button zu lang, Trenner weg

Der Nutzer bestätigte, dass die Reiter jetzt passen, meldete aber drei
weitere Detailprobleme:

1. **Suchfeld/Buttons auf Karten-Reiter zu weit auseinander:** Ursache war
   ein Denkfehler in der Breiten-Berechnung aus der vorigen Runde — die
   eingefrorene Container-Breite wurde als **Summe** aller vier möglichen
   Kinder (Suchfeld + Suchen + Karte-manuell + Sealed-Button) berechnet,
   obwohl Karten- und Sealed-Kombination nie gleichzeitig sichtbar sind
   (der eigene Kommentar im Code sagte sogar richtig "widest combination
   ... at once", umgesetzt wurde aber eine Summe statt eines Maximums).
   Der dadurch überbreite Container ließ das Suchfeld (`Expanding`-
   SizePolicy) zwar korrekt bis zu seiner `maximumWidth()` wachsen, aber
   der verbleibende Rest der überschüssigen Breite verteilte sich als
   sichtbare Lücken zwischen den Geschwister-Widgets. Fix: `max()` der
   beiden tatsächlichen Tab-Kombinationen statt ihrer Summe.
2. **"+ Sealed-Produkt hinzufügen" zu lang gezogen:** exakt derselbe Bug
   wie zuvor beim "Suchen"-Button (`QPushButton`s Default-`SizePolicy`
   erlaubt Wachstum) — dieses Mal war es mir schlicht entgangen, den
   gleichen Fix auch auf den neuen Button anzuwenden. Jetzt ebenfalls
   `SizePolicy.Fixed`.
3. **Schwarzer Trenner-Strich:** einfach ersatzlos entfernt
   (`toolbar.addSeparator()`-Aufruf gelöscht) — der dehnbare Platzhalter
   zwischen linker Gruppe und Reitern trennt beide Bereiche bereits
   optisch ausreichend.

Alle drei Reiter erneut per Screenshot verifiziert (jetzt inkl. Klick über
gezielte `CheckBox`-Kontrollen statt Text-Matching, nachdem sich das
Text-Matching einmal in der deutschen Oberfläche mit einem gleichnamigen
Statistik-Kachel-Titel "Karten" verwechselt hatte) — Ergebnis sieht jetzt
exakt so aus wie vom Nutzer gewünscht.

### Nachbesserung 4: Sealed-Add-Button zentriert statt linksbündig

Letzter Feinschliff: Karten- und Statistik-Reiter bestätigt korrekt, aber
"+ Sealed-Produkt hinzufügen" stand zentriert im (auf die breitere Karten-
Kombination eingefrorenen) Container statt linksbündig.

Erster Lösungsversuch (`group_layout.addStretch(1)` am Ende) führte zu
einer neuen Regression: das Suchfeld (`QLineEdit`s Standard-`SizePolicy`
ist `Expanding`) konkurrierte mit dem expliziten Stretch um denselben
Restplatz im (auf dem Karten-Reiter eigentlich exakt passend
eingefrorenen) Container und wurde dadurch auf einen Bruchteil seiner
Breite zusammengedrückt (live-confirmed via Screenshot: "Karten durchsu…"
statt der vollen Breite). Endgültiger Fix: das Suchfeld bekommt jetzt eine
echte feste Breite (`setFixedWidth(320)`) statt nur eine maximale
(`setMaximumWidth`) — ohne die `Expanding`-Policy gibt es keine Konkurrenz
mehr zwischen Suchfeld und Stretch, und der Stretch schiebt zuverlässig
nur echten Leerraum (auf dem Sealed-Reiter) nach rechts, ohne auf dem
Karten-Reiter irgendetwas zu beeinflussen (dort ist der Container ohnehin
exakt passend eingefroren, kein Leerraum vorhanden).

Beide Reiter erneut per Screenshot verifiziert: Suchfeld wieder in voller
Breite, Sealed-Add-Button jetzt linksbündig.

---

## Nächster Entwicklungsschritt

Schritt 10 ist umgesetzt und getestet (268 Tests grün) — Bestätigung im
laufenden Programm durch den Nutzer steht noch aus.

**Schritt 11 — Export (CSV/Excel/JSON/PDF).** Danach kurze Zusammenfassung
und Warten auf Freigabe.
