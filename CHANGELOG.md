# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier chronologisch
dokumentiert. Format angelehnt an [Keep a Changelog](https://keepachangelog.com);
Versionierung nach [SemVer](https://semver.org).

## [Unreleased]

## [1.0.0-beta.1] — 2026-07-11

Erste Beta: die App ist feature-komplett für ihr Kernversprechen (Karten,
Sealed-Produkte, Wantlist, Statistik, Export/Import, Backups) und lief durch
etliche Runden echten Testens mit einer umfangreichen automatisierten
Test-Suite im Rücken. Zwei bekannte Rückstands-Punkte sind bewusst nicht
Teil dieses Standes: ein Grading-Lohnt-sich-Rechner und ein automatisches
Backup an einen zweiten Ort -- beides spätere Erweiterungen, keine
Blocker für diese Beta.

### Behoben — Kartenbild wechselte sichtbar die Größe je nach Karte
- Live-reported (Beta-Test): dasselbe Artwork-Feld zeigte je nach Karte
  unterschiedlich große Bilder, obwohl das Panel selbst nicht in der Größe
  verändert wurde. Ursache: `CardArtworkView`/`SealedArtworkView` hatten nur
  eine Min/Max-Höhen-Spanne (260-420px) und waren zugleich das einzige
  Element mit `stretch=1` im Detail-Panel-Layout -- ein längeres
  "Price quality"-Feld (zweizeilige Schätz-Begründung statt einer kurzen
  "Exact match"-Zeile) stahl dadurch sichtbar Platz vom Artwork. Fix: feste
  statt variable Höhe für beide Artwork-Widgets, unabhängig vom Inhalt der
  übrigen Felder. Ein erster Versuch (360px) war selbst wieder zu groß und
  überlappte die Formularfelder darunter -- auf 260px korrigiert (derselbe
  Wert, den die alte Min-Höhe schon sicher nutzte).

### Hinzugefügt — Manuell per Link eingetragene Karten bekommen den englischen Namen
- Der Name einer manuell per Cardmarket-Link hinzugefügten Karte kam bisher
  1:1 vom Seitentitel -- auf einer nicht-englischen Cardmarket-Domain (z. B.
  cardmarket.com/de/...) also in der jeweiligen Sprache ("Despotar V" statt
  "Tyranitar V"), obwohl jede andere Karte in der Sammlung unter ihrem
  englischen Namen geführt wird. Nutzt jetzt dieselbe Übersetzungstabelle,
  die schon die Katalogsuche für fremdsprachige Namen verwendet (inkl.
  Karten mit Endungen wie "V"/"GX"/"VMAX") -- ein unbekannter oder bereits
  englischer Name bleibt unverändert.

### Behoben — Kartenfoto blieb leer, obwohl der Preis korrekt gefunden wurde
- Live-reported: "Blitza" (Split Earth) zeigte konsequent kein Bild, auch
  nach mehrfachem erneutem Hinzufügen -- obwohl die Preissuche auf derselben
  Cardmarket-Seite einwandfrei funktionierte. Live an der echten Cardmarket-
  Seite nachvollzogen: das Produktfoto liegt dort in einem Bilder-Karussell
  mit mehreren `<img>`-Elementen, die exakt denselben zugänglichen Namen
  tragen -- z. B. eine benachbarte Karussell-Folie, die für die
  Slide-Animation an einer negativen Bildschirmposition (aber in voller
  Originalgröße!) sitzt, daneben eine unsichtbare 0×0-Pixel-Dublette für
  die mobile Ansicht. Die Bild-Erkennung nahm bisher einfach den *ersten*
  Namenstreffer -- traf sie zuerst auf einen dieser Duplikate statt auf das
  tatsächlich sichtbare Foto, war das Ergebnis bei jedem einzelnen Versuch
  identisch falsch (kein Zufallstreffer, sondern ein deterministischer
  Fehlgriff). Jetzt werden Namenstreffer zuerst auf tatsächlich im Fenster
  sichtbare Kandidaten eingegrenzt, und unter denen der größte gewählt --
  wie es bei fehlendem Namenstreffer schon immer der Fall war.

### Behoben — Bearbeiten einer Karte löschte ihren eigenen Cardmarket-Link
- Live-reported (Beta-Test): nach dem Bearbeiten einer manuell per Link
  hinzugefügten Karte fand die Preissuche plötzlich gar nichts mehr, obwohl
  sie direkt nach dem Hinzufügen noch einen exakten Preis gefunden hatte.
  Ursache: der "Karte bearbeiten"-Dialog übernahm den eigenen Cardmarket-
  Link der Karte (`manual_cardmarket_url`) beim Öffnen nicht -- das Feld
  erschien leer, und beim Speichern wurde dieser leere Wert zurück in die
  Karte geschrieben, wodurch der zuvor gesetzte Link verschwand. Jetzt wird
  er beim Öffnen des Dialogs korrekt vorausgefüllt und bleibt bei jeder
  Bearbeitung erhalten, die ihn nicht bewusst ändert.

### Behoben — Kartenbild "sprang" in der Position, nicht der Größe
- Live-reported (Beta-Test, nach dem Größen-Fix oben): auf einem Fenster,
  das größer war als der eigentliche Panel-Inhalt brauchte, verschob sich
  die vertikale Position des Artworks zwischen Karten -- z. B. saß es bei
  einer Karte mit zweizeiliger Preis-Begründung höher als bei einer mit
  einzeiliger, obwohl das Artwork selbst (dank des Fixes oben) längst eine
  feste Größe hatte. Ursache: ohne einen expliziten Stretch-Faktor am Ende
  des Layouts verteilt Qt übrig gebliebenen vertikalen Platz auf alle
  nicht-fixierten Elemente -- hier die Überschrift oberhalb des Artworks --
  und wie viel Platz überblieb, hing genau davon ab, wie viele Zeilen die
  variable Preisqualitäts-Begründung darunter brauchte. Fix: ein
  abschließender Stretch am Ende des Panels beansprucht jetzt den gesamten
  übrigen Platz selbst, sodass alle Elemente darüber ihre natürliche
  Position behalten -- unabhängig von der Fensterhöhe oder der Textlänge
  darunter.

### Behoben — "Preisqualität"-Text zu lang, überlappte das Panel
- Die Begründungstexte für geschätzte Preise wiederholten unnötig
  "Geschätzt aus"/"Estimated from" -- das steht bereits in der
  Qualitäts-Bezeichnung direkt davor ("Estimated from a different
  condition — Estimated from Japanese, condition..."). Gekürzt auf die
  reinen Details (Sprache/Zustand), ohne die eigentliche Information zu
  verlieren.

### Behoben — Manuell erfasstes Kartenfoto war ein reiner Zweifarben-Split
- Live-reported (mit Screenshot): das automatisch erfasste Foto einer
  manuell per Cardmarket-Link hinzugefügten Karte zeigte gar kein echtes
  Bild, nur eine saubere vertikale Zweifarben-Fläche (schwarz/dunkelgrau).
  Die "sieht das leer aus?"-Prüfung vor dem Speichern hat das nicht
  erkannt: sie verglich nur 9 feste Stichprobenpunkte auf exakte
  Übereinstimmung, und bei einem Zweifarben-Split fielen manche Punkte auf
  die eine, manche auf die andere Seite -- "nicht alle neun identisch"
  wurde fälschlich als "kein Problem" gewertet. Jetzt: mehr Stichproben
  plus eine Mindestanzahl unterschiedlicher Farben statt nur "mehr als
  eine" -- ein echtes Kartenfoto hat immer deutlich mehr Farbvielfalt als
  eine handvoll flacher Blöcke.

### Behoben — Cardmarket-Sprachfilter für Japanisch/Koreanisch/Chinesisch bei Einzelkarten
- Live-reported (mit Screenshot): eine besessene japanische EX-Karte in
  Zustand Excellent hatte auf Cardmarket ein exaktes Angebot (149,99 €) --
  die App zeigte stattdessen einen geschätzten Near-Mint-Preis (230,00 €)
  an. Ursache: eine falsche Annahme im Code, dass Cardmarket für
  Einzelkarten (anders als Sealed-Produkte) generell keinen `?language=`-
  Filter für Japanisch/Koreanisch/Chinesisch anbietet -- der Nutzer bewies
  live per Screenshot, dass `?language=7&minCondition=3` auf einer normalen
  Kartenseite korrekt filtert. Die echte, engere Ausnahme (manche
  ältere Sets/Nachdrucke führen die Sprache als eigenständiges Produkt,
  z. B. Neo Revelations Ho-Oh als "Awakening Legends") bleibt über den
  bestehenden Alternate-Version-Versuch und "Eigener Cardmarket-Link"
  abgedeckt. Automatische Preisermittlung funktioniert jetzt für diese drei
  Sprachen genau wie für jede andere -- die bisher nötige Umgehung über
  einen manuell eingetragenen Cardmarket-Link entfällt im Regelfall.
  Weiterhin unverändert: ein Preis wird nie über Sprachgrenzen hinweg für
  Japanisch/Koreanisch/Chinesisch geschätzt (deren Marktpreise können stark
  abweichen) -- das gilt jetzt als eigener, klar benannter Grundsatz statt
  zufällig an derselben Prüfung wie der (jetzt korrigierte) Filter-Bug zu
  hängen.

### Neu — Welcome-Fenster + FAQ-Reiter, Help-Text stark erweitert
- Neues Welcome-Fenster beim Programmstart (Text vom Nutzer vorab
  abgesegnet): kurzer Überblick über die App + Hinweis auf "Help". Erscheint
  standardmäßig bei jedem Start; "Don't show this again" merkt sich die
  Entscheidung dauerhaft (einfache Marker-Datei in `data/`, kein
  Windows-Registry-Zugriff, passend zum bestehenden "alles liegt in
  Klartext-Dateien"-Prinzip der App).
- Neuer dritter Reiter **FAQ** im Info-Dialog (zwischen Help und Info):
  beantwortet konkrete Nutzerfragen wie "Warum funktioniert das nicht alles
  automatisch?", "Wie trage ich japanische/koreanische/chinesische Karten
  ein?" oder "Was passiert, wenn etwas kaputtgeht?".
- Help-Tab nach vollständigem Audit aller UI-Funktionen deutlich erweitert:
  neuer Abschnitt "Collections" (bisher komplett unerwähnt), plus bisher
  fehlende Punkte bei Cards (Verschieben zwischen Sammlungen, Duplikat-
  Warnung, Mehrfachauswahl, Sortierung, Filterleiste, Cardmarket-Link-Fix-
  Flow), Sealed products (Bearbeiten/Löschen/Sortierung/Gesamtpreis),
  Wantlist ("Add to collection"-Konvertierung, Status-Anzeige), Statistics
  (Übersichts-Kacheln, Aufschlüsselungen, "Most expensive", "Biggest price
  increase") und General (Export-Bereichsauswahl, Backup-Wiederherstellungs-
  Mechanik im Detail).

### Nachbesserung: Reihenfolge, Größe, Navigation, Textkorrektur
- Reiter-Reihenfolge getauscht: FAQ jetzt vor Help.
- Info-Dialog deutlich größer (820×700) und Schrift in Help/FAQ spürbar
  größer (15pt) -- mehrfach nachgebessert, nachdem ein `setFont()` allein
  von der App-weiten QSS-Regel (`font-size: 10pt` auf jedem `QWidget`)
  überschrieben wurde; Fix ist ein widget-eigenes Stylesheet, das gegen
  jede Vorfahren-Regel gewinnt. Gleicher Fix + gleiche Schriftgröße auch
  im Welcome-Fenster, das dafür ebenfalls vergrößert wurde (zuletzt
  640×520, in zwei Nachbesserungsrunden).
- Neuer "Contents"-Index oben im Help-Tab: pro Kategorie eine klickbare
  Liste aller Funktionen, springt direkt zur passenden Stelle. FAQ-Fragen
  verlinken jetzt ebenfalls auf die passende Help-Stelle ("See also"), inkl.
  automatischem Tab-Wechsel beim Klick.
- Verlinkungen erscheinen jetzt im App-eigenen Orange-Akzent statt in
  Windows' Standard-Linkfarbe (grün) -- selbes Problem wie beim Font-Fix:
  Farbe muss über das `QTextDocument`-eigene `setDefaultStyleSheet` gesetzt
  werden, ein reines Widget-Stylesheet erreicht die Links innerhalb des
  gerenderten HTML nicht.
- Mehr Abstand zwischen den einzelnen FAQ-Fragen.
- Textkorrektur: Help/FAQ nannten den Cardmarket-Such-Button fälschlich
  "Cardmarket link suchen" (der interne deutsche `tr()`-Quelltext) statt
  seiner tatsächlichen englischen Beschriftung "Search Cardmarket link".

### Neu — Cardmarket-Link-Button: 3 UX-Verbesserungen
- Inline-Fallback "Open Cardmarket search in browser" im Ergebnis-Dialog,
  wenn die automatische Suche selbst nichts findet -- öffnet Cardmarkts
  eigene Suche in einem normalen, offen bleibenden Browserfenster.
- Neue Kontextmenü-Aktion "Fix Cardmarket link" in der Kartenliste (vorher
  nur über den Button im Detailpanel erreichbar, jetzt auch direkt aus der
  Liste heraus, ohne die Karte erst öffnen zu müssen).
- Zusätzliche Bestätigung mit dem konkret aufgelösten Link, bevor er
  tatsächlich gespeichert wird -- vorher wurde nach Auswahl eines
  Suchtreffers automatisch und ohne weitere Rückfrage gespeichert.

### Geändert — Help/Info-Dialog
- Help-Tab kommt jetzt vor Info.
- Credits im Info-Tab: "Created by Karin" statt "Created by Codeon" mit
  GitHub-Link.
- Neuer Hinweis im Help-Text: die mehrsprachige Suche ist best-effort,
  nicht garantiert -- ungewöhnliche Namen ggf. auf Englisch suchen oder
  per Cardmarket-Link manuell eintragen.

### Behoben — Restliches Deutsch in der Massenpreisabfrage + weiteren Stellen
- Die Statusmeldungen der Massenpreisabfrage ("Preis X/Y wird von
  Cardmarket abgerufen…", "Alle veralteten Preise wurden aktualisiert.")
  waren für Karten und Sealed-Produkte noch auf Deutsch. Nebenbei per
  Audit gefunden und ebenfalls behoben: mehrere weitere untranslatierte
  Einzelstellen (Sealed-Produktdetails, Sealed-Tabellenspalten, JP/KO/ZH-
  Schätzpreis-Hinweis, Preisverlauf-Löschbestätigung, Cardmarket-
  Sucheautomatisierung).

### Behoben — Set-Icon im Card-Details-Panel noch mit dunklem Kasten
- Der erste Skalierungs-Fix reichte nicht: die eigentliche Ursache war eine
  globale Stylesheet-Regel, die jedem `QWidget` (auch einem `QLabel`) einen
  opaken Hintergrund gibt, sofern nicht explizit `background: transparent`
  gesetzt ist — derselbe Bug, der früher schon die "Alle Sammlungen"-
  Checkbox betraf. Neue allgemeine Regel behebt es für jedes Label.

### Behoben — "Sprache"-Feldlabel fälschlich noch Deutsch
- Das "Sprache:"-Feld im Card-Details-Panel (und, derselbe Bug, im Sealed-
  Detailpanel, der Sealed-Liste und der Statistik-Tabelle) zeigte noch den
  deutschen Text statt "Language" — fehlender Übersetzungseintrag.

### Behoben — UI-Politur (Suchfeld, Spinner-Pfeile, Sortierung, Set-Icons)
- Suchfeld in der Toolbar verbreitert, Platzhaltertext-Beispiel aktualisiert.
- Quantity-Spinner-Pfeile sind jetzt sichtbar (vorher kaum erkennbar gegen
  das dunkle Theme).
- Standard-Sortierung der Kartenliste: alt→neu statt neu→alt.
- Set-Icons in der Kartenliste zeigten einen sichtbaren Kasten um sich herum
  (roh heruntergeladene Icons in teils sehr großer Original-Auflösung ohne
  Skalierung) — jetzt auf eine feste, transparente Canvas-Größe skaliert,
  wie die anderen Icon-Spalten.

### Behoben — Manuelles Hinzufügen: Busy-Overlay + Sprachfilter + Bild-Bug
- Beim Lesen einer manuell eingefügten Cardmarket-Seite erscheint jetzt ein
  Busy-Overlay (vorher nur eine leicht übersehene Statusleisten-Meldung).
- Die Sprache im Add-Dialog wird nicht mehr immer hart auf Englisch
  vorbelegt, sondern aus den bereits gelesenen Angeboten der Seite erkannt
  (häufigste Sprache) — wichtig gerade für JP/KO/ZH/Vintage-Drucke, dem
  eigentlichen Zweck dieses Flows. Weiterhin voll editierbar.
- Manuell aufgenommene Kartenfotos konnten als komplett schwarzes Bild
  gespeichert werden, wenn der Cardmarket-Tab das Foto im Aufnahmemoment
  noch nicht fertig gerendert hatte. Eine verdächtig einfarbige Aufnahme
  wird jetzt einmal automatisch wiederholt, statt dauerhaft ein nutzloses
  schwarzes Bild zu speichern.

### Behoben — Katalogsuche grundlegend überarbeitet
- Bindestrich-Bug behoben: pokemontcg.io speichert GX/EX-Suffixe wörtlich
  mit Bindestrich ("Umbreon-GX"), mehrwortige Namen werden jetzt als
  UND-verknüpfte Einzelwort-Wildcards gesucht statt als eine exakte
  Leerzeichen-Phrase — behebt u. a. "Nachtara GX", "Mewtu GX",
  "Mega-Zobiris & Despotar-GX".
- Neue Symbol-Synonymtabelle: "Delta"/"Gold Star"/"Star" werden auf die
  literalen Zeichen (δ/★) abgebildet, die pokemontcg.io tatsächlich
  speichert.
- Kaskaden-Fix: eine bereits übersetzte Namenskandidatur bekommt jetzt auch
  die schrumpfende Präfix-Lockerung, statt nach einem einzigen gescheiterten
  Versuch aufzugeben.
- Preisschätz-Logik neu geordnet: exakte Sprache/exakter Zustand → exakte
  Sprache mit Zustand ±1 Stufe (neuer harter Deckel) → Englisch/exakt →
  Englisch ±1 Stufe. Kein unbegrenzter "Durchschnitt über alles"-Fallback
  mehr — ohne einen ausreichend nahen Treffer gibt es jetzt ehrlich keinen
  Preis statt einer irreführenden Schätzung.
- Laufende Katalogsuche wird jetzt tatsächlich abgebrochen, wenn der
  Ergebnis-Dialog geschlossen wird, statt im Hintergrund weiterzulaufen und
  jede neue Suche bis zu ihrem Abschluss stillschweigend zu blockieren.

### Neu (WIP) — Cross-Platform-Vorbereitung: macOS-Backend
- `browser_price_reader.py` (1319 Zeilen) aufgeteilt in
  `app/pricing/cardmarket_parsing.py` (reine, plattformunabhängige URL-Bau-
  und Text-Parsing-Logik, von jeder Plattform gemeinsam genutzt) und
  `app/pricing/browser/` (Plattform-Dispatch nach `sys.platform`:
  `_windows.py`, neu `_macos.py`, Platzhalter `_unsupported.py` für Linux).
  `browser_price_reader.py` selbst ist jetzt nur noch eine reine
  Re-Export-Fassade -- kein anderer Aufrufer musste sich ändern. Volle
  Testsuite bleibt grün, reine Umstrukturierung ohne Verhaltensänderung
  unter Windows.
- Erster Entwurf für `app/pricing/browser/_macos.py`: spiegelt die
  Windows-Variante Funktion für Funktion, aber auf Basis der macOS
  Bedienungshilfen-API (`AXUIElement`, PyObjC) statt Windows UI Automation.
  **Wichtig: bisher ungetestet** -- kann in dieser Windows-Umgebung nicht
  ausgeführt werden, muss auf echter Mac-Hardware live geprüft/korrigiert
  werden (genau wie die Windows-Variante selbst nur durch mehrfaches
  Live-Testen ihren jetzigen Stand erreicht hat).
- Neue bedingte Abhängigkeiten in `requirements.txt`: `pywinauto` jetzt nur
  noch für `sys_platform == "win32"`, neu `pyobjc-framework-{Cocoa,
  ApplicationServices,Quartz}` für `sys_platform == "darwin"`.

### Geändert — Chrome-Fenster: mehrere Anläufe bis zur finalen Lösung
- Ursprüngliches Problem: `--window-size` beim Chrome-Start wird
  stillschweigend ignoriert, wenn Chrome bereits (auch nur unsichtbar) im
  Hintergrund läuft (Windows' "Hintergrund-Apps weiterlaufen lassen", oft
  Standard) -- der Aufruf wird dann per IPC an den laufenden Prozess
  weitergereicht, der ein neues Fenster in Standardgröße (meist maximiert)
  öffnet.
- Erster Versuch (kleines 700x850-Fenster per pywinauto's `window.restore()`
  erzwungen): hat einen echten Folgefehler verursacht -- `restore()` ruft
  intern `ShowWindow(hwnd, SW_RESTORE)` auf, was laut Win32-Doku das Fenster
  *immer* aktiviert, auch wenn es gar nicht maximiert war. Chrome sprang
  wieder in den Vordergrund UND die automatische Preiserkennung brach
  dadurch komplett ab.
- Zweiter Versuch (1280x720 statt 700x850, per rohem `win32gui`/`win32con`
  ohne `ShowWindow`): immer noch zu klein zum bequemen Lesen, und die App
  blieb weiterhin nicht zuverlässig im Vordergrund.
- Finale Lösung: Chrome wird jetzt komplett maximiert (voller Bildschirm,
  aber hinter der App) statt auf eine feste Größe verkleinert -- per
  `SetWindowPlacement` (setzt Maximiert-Zustand direkt, ohne jeden
  `ShowWindow`-Aufruf, der sonst den Fokus stehlen würde).
- Zusätzlich behoben: `SetForegroundWindow` wird von Windows generell
  stillschweigend *ignoriert*, wenn der aufrufende Prozess gerade nicht
  selbst im Vordergrund ist (Anti-Fokus-Klau-Schutz) -- das hat verhindert,
  dass die App sich den Vordergrund von Chrome zurückholen konnte. Jetzt per
  `AttachThreadInput`-Workaround gelöst (Standard-Win32-Technik dafür).

### Neu — "Estimated from"-Info jetzt direkt sichtbar
- Bei einem geschätzten Preis (anderes Zustand/Sprache als gewünscht) stand
  bisher nur die generische Preisqualität ("Estimated from a different
  condition") sichtbar da, die konkrete Begründung (welche Sprache/welcher
  Zustand tatsächlich verwendet wurde) nur als Tooltip beim Hovern. Steht
  jetzt direkt im Kartendetail, Sealed-Detail und Preisverlauf.
- Dabei nebenbei behoben: die Begründungstexte in `price_service.py` waren
  noch hartcodiert Deutsch, obwohl die UI seit Schritt 15 komplett
  Englisch ist -- jetzt wie überall sonst über `tr()` übersetzt.
- Bei einem exakten Treffer stand die Preisqualität doppelt da ("Exact
  match — Exact match: English, Near Mint.", live-reported) -- die
  Begründung wiederholte den Namen der Preisqualität selbst. Jetzt ohne
  das redundante Präfix, nur noch die konkreten Details.

### Neu — "Cardmarket-Link öffnen" (Rechtsklick auf eine Karte)
- Rechtsklick auf eine Karte → "Open Cardmarket link" öffnet die Cardmarket-
  Seite in einem normalen, vollgroßen Chrome-Fenster und lässt es offen --
  im Gegensatz zu "Preis aktualisieren", das die Seite automatisch liest und
  den Tab wieder schließt. Gedacht dafür, sich Angebote/Fotos/Kommentare in
  Ruhe selbst anzuschauen.

## [0.10.0-alpha.2] — 2026-07-07

### Neu — Abgedunkelte App mit Ladebalken während des Preis-Abrufs
- Während ein Cardmarket-Preis geholt wird (Karten, Sealed-Produkte,
  Wantlist, einzeln oder als Sammelaktualisierung), wird das ganze
  Fenster spürbar abgedunkelt und zeigt einen kleinen, mittig
  eingeblendeten Ladebalken samt Statustext -- macht deutlich sichtbar,
  dass gerade etwas läuft, statt sich allein auf die kleine
  Statusleisten-Meldung zu verlassen (Nutzerwunsch).
- Dabei denselben Subklassen-Stolperstein wie beim Panel-Schatten erneut
  gefunden: das Abdunkeln (`rgba(...)`-Hintergrund) rendert bei einer
  QWidget-Subklasse nur mit explizitem `WA_StyledBackground` -- ohne das
  blieb es unsichtbar, obwohl Ladetext und -balken schon korrekt
  erschienen. Per echtem (nicht PrintWindow-basiertem) Screenshot
  pixelgenau nachgewiesen und behoben.
- Statustext und Ladebalken stecken in einer gemeinsamen, abgerundeten
  Box (gleicher Panel-Look wie der Rest der App) statt lose auf dem
  abgedunkelten Hintergrund zu schweben.

### Geändert — Chrome bleibt beim Preis-Abruf im Hintergrund
- Beim Abrufen eines Cardmarket-Preises (Karten, Sealed-Produkte, Wantlist)
  bleibt die App jetzt durchgehend im Vordergrund -- Chrome öffnet sich
  dahinter, statt kurz nach vorne zu springen. Live per Fokus-Log über den
  gesamten Ablauf (Chrome-Start, Seite lesen, Tab schließen) bestätigt.
- Ist Chrome noch nicht offen, startet es in einem deutlich kleineren
  Fenster (700×850) statt in voller Größe -- betrifft nur diesen Kaltstart-
  Fall, da ein bereits laufendes Chrome die Fenstergröße für einen neuen
  Tab im bestehenden Fenster ignoriert.
- Die Fenstererkennung verglich bisher, welches Fenster gerade im
  *Vordergrund* stand -- das ist mit der neuen Hintergrund-Öffnung nicht
  mehr möglich. Ersetzt durch einen Titel-Vorher/Nachher-Vergleich über
  alle offenen Chrome-Fenster: erkannt wird, welches Fenster jetzt
  "Cardmarket" im Titel zeigt, aber vorher noch nicht -- damit werden
  weiterhin zuverlässig nur neu geöffnete/aktivierte Tabs erkannt, keine
  bereits offenen, unveränderten Cardmarket-Tabs aus einem früheren Abruf.

### Behoben — Checkbox zeigte weiterhin einen dunklen Kasten
- Die QCheckBox selbst (nicht nur ihr Eltern-Container) zeichnete einen
  eigenen, opaken Fensterhintergrund -- betraf nach dem ersten Fix immer
  noch "Alle Sammlungen". Jetzt global transparent gestellt.

### Neu — Preisdiagramme: Tooltip mit Datum/Preis beim Hovern
- Karten-Preisverlauf, Sealed-Preisverlauf und der kombinierte
  Gesamtwert-Verlauf im Statistik-Tab zeigen jetzt beim Überfahren eines
  Punktes ein Tooltip mit exaktem Datum und Wert -- vorher musste der Wert
  an der Y-Achse abgelesen/geschätzt werden (Nutzerwunsch).

### Behoben — UI-Feinkorrekturen nach Live-Review
- Schlagschatten der Panels verkleinert (Blur/Versatz reduziert): bei
  ~10px Abstand zwischen benachbarten Panels lief der vorherige, größere
  Schatten über den Spalt hinaus und wurde vom Nachbar-Panel hart
  abgeschnitten -- sichtbar als hässlicher Fleck in der Ecke.
- Ein unauffälliger `QWidget`-Wrapper (z. B. die Set-Icon-Zeile im
  Kartendetail, die "Alle Sammlungen"-Checkbox-Zeile) erbte die
  app-weite Fensterhintergrundfarbe und wirkte dadurch wie ein
  deplatzierter dunkler Kasten auf dem helleren Panel-Hintergrund.
  Betroffene Wrapper bekommen jetzt einen transparenten Hintergrund.
- ComboBox-Dropdown-Pfeil neu gestaltet: der native Pfeil samt eigenem
  Kasten wirkte unpassend neben dem restlichen, abgerundeten Design --
  jetzt ein schlichtes, selbst gezeichnetes Chevron ohne Rahmen.
- Eingabefelder/Comboboxen etwas dunkler als der Panel-Hintergrund
  (neue `input_bg`-Palettenfarbe) für einen "eingelassenen" statt
  gleichfarbigen Look.

### Geändert — UI-Feinschliff für einen hochwertigeren Eindruck (Farbschema unverändert)
- Alle Panels (Sammlungen, Karten-/Sealed-/Wantlist-Listen, Detailpanels,
  Statistik-Kacheln) bekommen jetzt einen weichen Schlagschatten (Elevation)
  -- vorher rein flach mit 1px-Rand, jetzt sichtbar vom Fensterhintergrund
  abgehoben. Dabei ein echter Qt-Stolperstein gefunden und behoben: eine
  QWidget-*Subklasse* (wie hier überall verwendet) rendert `border-radius`
  aus dem Stylesheet nur mit explizit gesetztem `WA_StyledBackground` --
  ohne das blieb der Rahmen unsichtbar eckig, obwohl Hintergrund-/Randfarbe
  schon korrekt kamen. Live mit einem minimalen Repro nachgewiesen (einzige
  Variable: Subklasse vs. reines `QWidget()`) und zentral in
  `theme.apply_elevation()`/`enable_rounded_background()` gefixt.
- Eckenradius vereinheitlicht (Panels/Kacheln 14px, Listen/Tabellen 10px,
  Buttons/Eingabefelder 8px) statt vorher uneinheitlicher 4–14px-Mischung.
- Tabellen zeigen keine Excel-artigen Gitterlinien mehr, nur noch eine
  dezente Trennlinie pro Zeile -- ruhiger, "listenartiger" statt
  tabellenartig wirkend.
- Buttons: dezenter Verlauf (statt reiner Flatcolor) + Press-Zustand
  (Button "sackt" beim Klicken minimal ab) für ein taktileres Gefühl;
  Eingabefelder/Comboboxen/Checkboxen bekommen einen sichtbaren Hover-Rand.
  Splitter-Griffe zeigen beim Hovern eine dezente Linie (Resize-Hinweis,
  vorher komplett unsichtbar).
- Wantlist-Tab bekam denselben 10px-Seitenrand wie Karten/Sealed, damit
  sein Panel (Ecken + Schatten) nicht mehr direkt an den Reiterrand
  anstößt.

## [0.10.0-alpha.1] — 2026-07-07

### Neu — Wantlist-Eintrag in eine Sammlung übernehmen
- Rechtsklick auf einen Wantlist-Eintrag → "Add to collection": fragt nach
  der Zielsammlung und legt die Karte dort als normal besessene Karte an
  (gleicher Weg wie eine manuell per Cardmarket-Link eingetragene Karte,
  inkl. übernommenem Link/Sprache/Zustand/Notizen) -- der Wantlist-Eintrag
  verschwindet danach, ohne dass er von Hand gelöscht und die Karte separat
  neu eingetragen werden muss.

### Neu — Warnung beim Hinzufügen einer möglichen Doppel-Karte
- Beim Hinzufügen einer Karte (per Katalogsuche oder manuell per
  Cardmarket-Link) wird geprüft, ob bereits eine Karte mit exakt
  gleichem Name/Set/Kartennummer/Sprache/Zustand/Extras existiert — egal
  in welcher Sammlung. Falls ja, fragt ein Bestätigungsdialog nach, statt
  stillschweigend eine zweite, identische Zeile anzulegen (für echte
  Mehrfachexemplare bleibt "trotzdem hinzufügen" natürlich möglich).
- Neue `CardService.find_duplicates()` -- reine Warnung, blockiert
  nichts; die eigentliche Entscheidung bleibt beim Nutzer.

### Neu — CSV/Excel/JSON-Import (Gegenstück zum Export)
- Neue "Import"-Schaltfläche in der Toolbar, direkt neben "Export": liest
  Karten oder Sealed-Produkte aus einer CSV-, Excel- oder JSON-Datei im
  selben Spaltenlayout, das der eigene Export erzeugt — praktisch für ein
  bearbeitetes Re-Import einer Export-Datei oder eine bereits gepflegte
  eigene Tabelle. Kein PDF-Import: eine PDF ist ein gerenderter, nur in
  eine Richtung sinnvoller Bericht, keine plausible Import-Quelle.
- Importierte Einträge starten ohne Preis (wie beim manuellen Eintragen) —
  Preis/Preisqualität/Datum aus einer Export-Datei würden sonst
  fälschlich als "vom eigenen Programm ermittelt" erscheinen, obwohl der
  Import selbst keine echte Preisermittlung ist.
- Eine fehlerhafte einzelne Zeile (fehlender Name, unbekannte Sprache/
  Zustand, ungültige Menge, fehlende Sammlung) wird übersprungen und in
  der Ergebnis-Zusammenfassung aufgelistet, statt den ganzen Import
  abzubrechen — eine echte Tabelle ist selten perfekt sauber.
- Fehlende Sammlungen werden automatisch angelegt (Namensabgleich ohne
  Groß-/Kleinschreibung), damit ein voller "Export, bearbeiten,
  Re-Import"-Kreislauf funktioniert, ohne Sammlungen von Hand
  wiederherzustellen.

### Neu — Wantlist mit Preisalarm
- Neuer "Wantlist"-Tab: Karten, die man noch nicht besitzt, mit Zielpreis,
  Sprache und Zustand eintragen (per Cardmarket-Link, wie beim manuellen
  Karten-Eintrag) -- Name/Set/Kartennummer werden automatisch aus der
  Cardmarket-Seite gelesen, kein Katalog-Abgleich in dieser ersten Version.
- "Check all prices"-Button prüft alle Einträge nacheinander (kein
  Hintergrund-Polling, gleiches Ein-Klick-Muster wie das bestehende "Alle
  aktualisieren") und markiert Einträge, deren aktueller Preis den
  Zielpreis erreicht hat ("Below target!").
- Preisermittlung nutzt intern dieselbe Cardmarket-Matching-Ladder wie
  bereits besessene Karten (`PriceService.determine_price`, jetzt public) --
  über eine nur-temporäre `Card`-Instanz, keine doppelt gepflegte Logik.
- Migration 9: neue `wantlist_items`-Tabelle (globale Liste, nicht
  sammlungsgebunden, wie Sealed-Produkte) -- ohne eigene Preisverlauf-
  Tabelle, da es für noch nicht Besessenes keinen "Wert über Zeit" gibt.

### Neu — Gesamtwert-Verlauf über Zeit (Statistik-Tab)
- Neuer Graph im Statistik-Tab: Gesamtwert der ganzen Sammlung (Karten +
  Sealed-Produkte) über Zeit, aggregiert aus den bereits vorhandenen
  Preisverlauf-Tabellen (`price_history`/`sealed_price_history`) — reine
  Auswertung bestehender Daten, keine neue Datenquelle.
- Technisch eine Stufenfunktion: bei jedem Zeitpunkt, an dem sich
  irgendeine Karte/Sealed-Produkt-Preis geändert hat, ist der Gesamtwert
  die Summe aus dem jeweils zuletzt bekannten Preis jedes Items (nicht nur
  der gerade aktualisierten) — multipliziert mit der *aktuellen* Menge, da
  Mengenänderungen selbst nicht historisch nachverfolgt werden.
- Neue `PriceRepository.list_all()`/`SealedPriceRepository.list_all()`
  (bisher gab's nur Preisverlauf pro einzelner Karte/Produkt) für die
  effiziente Ein-Abfrage-Aggregation über die ganze Sammlung.
- Wird ausgeblendet (Platzhaltertext statt Graph), solange weniger als
  zwei Preis-Datenpunkte insgesamt vorliegen.

### Neu — Backup wiederherstellen über die UI
- Neuer "Restore from backup…"-Button unter "Infos und Einstellungen":
  listet vorhandene automatische Backups (Zeitpunkt, Dateigröße) und
  stellt ein ausgewähltes wieder her.
- Sicherheitsnetz: vor dem eigentlichen Restore wird der aktuelle Stand
  selbst nochmal gesichert (unabhängig vom üblichen 24h-Minimalabstand),
  damit ein versehentlicher Restore selbst wieder rückgängig gemacht
  werden kann.
- Kopiert erst in eine temporäre Datei und tauscht dann atomar um, statt
  die echte Datenbankdatei direkt zu überschreiben -- ein Fehler mitten im
  Kopiervorgang (Speicherplatz, Rechte, …) kann die Datenbank so nicht
  halb überschrieben zurücklassen.
- Da die laufende Datenbankverbindung (und alles, was darauf aufbaut) den
  Dateitausch nicht "live" mitbekommt, schließt die App sich nach einem
  erfolgreichen Restore selbst -- ein manueller Neustart zeigt dann den
  wiederhergestellten Stand.

### Geändert — Schwelle für veraltete Preise: 2 Monate -> 1 Monat
- `STALE_PRICE_THRESHOLD_DAYS` (zentrale Definition in
  `statistics_service.py`, von dort für Karten und Sealed-Produkte
  gleichermaßen wiederverwendet — Statistik-Tab, "!"-Hinweis in den
  Listen, Help-Text) auf 30 Tage gesenkt.

### Neu — Hinweis auf neue Version verfügbar
- Beim Start wird (nur im echten Programmstart, nicht in Tests) im
  Hintergrund geprüft, ob auf GitHub ein neueres Release existiert als
  die laufende Version. Falls ja, erscheint ein klickbarer Link dauerhaft
  rechts in der Statusleiste — kein automatischer Download/Install, nur
  ein Hinweis.
- Best-effort: kein Internet, GitHub-Rate-Limit o. Ä. wird wie "kein
  Update gefunden" behandelt, nie als Fehler angezeigt.

### Geändert — data/ und logs/ liegen bei der .exe in einem eigenen Unterordner
- Bisher legte die `.exe` `data/` und `logs/` direkt neben sich selbst an
  — bei einer `.exe` z. B. direkt auf dem Desktop wären das zwei lose
  Ordner mitten dazwischen gewesen. Beide liegen jetzt stattdessen in
  einem gemeinsamen `PokemonCollectionManager/`-Unterordner neben der
  `.exe`. Betrifft nur den gepackten `.exe`-Fall; ein Quellcode-Checkout
  bleibt unverändert (`data/`/`logs/` weiterhin direkt im Projektordner).

### Behoben — Uneinheitliche Zeilenhöhen in der Kartentabelle
- Live-reportiert: die Zeilen in der Kartentabelle waren unterschiedlich
  hoch. Ursache: `resizeRowsToContents()` bemaß jede Zeile nach ihrem
  jeweils größten Zellinhalt — Set-Icons kommen aber je nach Quelle
  (pokemontcg.io/tcgdex-Fallback) in unterschiedlicher Auflösung, was pro
  Zeile eine andere Höhe ergab.
- Feste, einheitliche Zeilenhöhe (36px) statt automatischer Bemessung —
  live geprüft: alle 20 Zeilen einer echten Sammlung jetzt exakt gleich
  hoch, unabhängig vom jeweiligen Set-Icon.

## [0.9.0-alpha.1] — 2026-07-06

Erster Alpha-Release: der komplette Funktionsumfang aus den Schritten 2-11
plus alle seither gesammelten Bugfixes/Feinschliffe, davor nur einzeln als
Fortschrittsnotizen in `PROJECT_PROGRESS.md` festgehalten.

### Neu — Eigenständige .exe (PyInstaller)
- Neues `PokemonCollectionManager.spec` (onefile, ohne Konsolenfenster,
  bündelt Icon/Set-Icon-Cache-Assets/Namensübersetzungstabelle) — Anleitung
  in der README unter "Eigenständige .exe bauen".
- `app/config.py`s `BASE_DIR` erkennt jetzt den PyInstaller-gefrorenen
  Zustand (`sys.frozen`) und zeigt dann auf das Verzeichnis der `.exe`
  selbst statt auf das temporäre Extraktionsverzeichnis
  (`sys._MEIPASS`) — sonst wären Datenbank/Fotos/Logs bei jedem Neustart
  verloren gegangen. Live getestet: `.exe` in ein leeres Verzeichnis
  kopiert und gestartet — Datenbank, Backup und Log landen korrekt daneben.
- `.gitignore` überarbeitet: `data/` jetzt komplett ausgeschlossen (vorher
  fehlten `backups/`, `sealed_photos/`, `set_icons/` in der engeren, alten
  Regel), `build/`/`dist/` für PyInstaller-Ausgaben ergänzt.

### Neu — Erste Sammlung wird beim Start automatisch ausgewählt
- Bisher zeigte die App beim Start eine leere Kartenliste, bis man von Hand
  eine Sammlung anklickte.
- Die in der Sammlungsliste zuoberst stehende Sammlung wird jetzt beim
  App-Start automatisch ausgewählt (kein Effekt, wenn noch keine Sammlung
  existiert).
- Kurzzeitig war stattdessen eine automatisch angelegte, nicht löschbare
  Sammlung "All Cards" geplant und auch schon eingebaut — auf Nutzerwunsch
  wieder vollständig entfernt (inkl. Migration/Datenbankspalte), da eine
  simple "erste Sammlung auswählen"-Lösung bevorzugt wurde.

### Neu — Katalogsuche findet Trainer-/Item-Karten auch unter ihrem fremdsprachigen Namen
- Die bestehende Namensübersetzung kannte nur Pokémon-Spezies (aus PokeAPI
  generiert) — eine Suche nach "Lillys Entschlossenheit" (deutsch für
  "Lillie's Determination") fand nichts, da Trainer-/Item-/Stadium-Karten
  bei PokeAPI gar nicht vorkommen.
- Neue Suchstufe direkt nach der Spezies-Übersetzung (vor dem schrumpfenden
  Präfix, der bei einem fremdsprachigen Namen ohnehin nie etwas fände):
  live bei tcgdex.dev in Deutsch/Französisch/Spanisch/Italienisch/
  Portugiesisch nachschauen und den englischen Namen derselben Karte
  auflösen — live bestätigt für "Lillys Entschlossenheit" ->
  "Lillie's Determination". Die fünf Sprachabfragen laufen parallel statt
  nacheinander.
- Nachbesserung (Nutzerfeedback: Suche dauerte "sehr lange"): Ursache war,
  dass die neue Stufe ursprünglich ganz am Ende stand — bei einer
  fremdsprachigen Trainer-Karte lief davor immer erst der komplette (dabei
  nutzlose) schrumpfende-Präfix-Durchlauf gegen die englische
  pokemontcg.io-API, was bei einer gerade langsamen pokemontcg.io-Anbindung
  mehrere überflüssige 20s-Wartezeiten verursachte. Live nachgemessen:
  dieselbe Suche ("Cynthias Ehrgeiz" -> "Cynthia's Ambition") lief danach
  in ca. 5s statt über eine Minute.

### Verworfener Versuch — Shadowless-Bild per Cardmarket-Screenshot
- Die Base-Set-Normal/Shadowless-Aufteilung in der Katalogsuche (siehe unten)
  zeigt für die Shadowless-Variante weiterhin das normale pokemontcg.io-Bild
  (pokemontcg.io führt pro Karte nur ein einziges Foto, das der
  Normal-Version) — das ist rein optisch, der gespeicherte Cardmarket-Link
  ist bereits korrekt der Shadowless-Version zugeordnet.
- Ein automatischer Screenshot-Capture von der Cardmarket-Produktseite
  wurde gebaut und wieder verworfen: die automatische Fenster-/
  Bild-Erkennung erwies sich in der Praxis als nicht robust genug
  (Nutzerfeedback). Da der Link auf die richtige Version zeigt und damit
  Preisermittlung/Zuordnung korrekt bleiben, wurde das als "gut genug"
  akzeptiert statt die unzuverlässige Automatik zu behalten.

### Neu — Neues App-Icon (Kartenfächer freigestellt)
- Das App-Icon zeigte den Kartenfächer bisher innerhalb eines umschließenden
  Kastens; jetzt freigestellt (echte Transparenz), sodass nur der
  Kartenfächer selbst als Icon erscheint — in Taskleiste, Titelleiste und
  Fenster-Icon.

### Fix — Taskleisten-Icon zeigte Python-Symbol statt eigenem App-Icon
- Windows gruppierte die App unter `pythonw.exe`s eigenem Symbol statt dem
  eigens gesetzten `icon.ico`.
- Setzt jetzt vor der `QApplication`-Erstellung eine eigene
  `AppUserModelID` (Windows-only, best-effort).

### Neu — Kontextmenü: Preis manuell bearbeiten
- Cardmarket-Verkäufer beschriften Angebote gelegentlich falsch (z. B. eine
  PSA-1-Karte als "Near Mint" gelistet) — das verfälscht die automatische
  Preisermittlung, ohne dass es aus der App heraus korrigierbar war.
- Neue Option im Rechtsklick-Kontextmenü einer einzelnen Karte: "Preis
  manuell bearbeiten" — setzt den Preis auf einen fest eingetragenen Wert
  (neue `PriceQuality.MANUAL`), unabhängig von der nächsten automatischen
  Preisermittlung.

### Neu — Hintergrundfenster wird bei Popups abgedunkelt
- Ein offener Dialog sah optisch identisch zum Hauptfenster im Ruhezustand
  aus — bei einer länger laufenden Suche wirkte die App dadurch wie
  eingefroren/abgestürzt statt "arbeitet noch".
- Neue gemeinsame Basisklasse `DimmedDialog` (`app/ui/dialogs/dimmed_dialog.py`):
  überlagert das Hauptfenster mit einem halbtransparenten Overlay, solange
  der Dialog offen ist. Alle eigenen Dialogklassen der App nutzen sie jetzt
  statt direkt `QDialog`.

### Neu — Sofortiger Ladeindikator bei Kartensuche/Cardmarket-Suche
- Beide Such-Ergebnis-Dialoge (Katalogsuche über die Toolbar, "Cardmarket-
  Link suchen") öffnen sich jetzt sofort mit "Suche läuft…" + Ladebalken,
  statt erst nach Abschluss der (teils mehrere Sekunden dauernden) Suche zu
  erscheinen — bis dahin sah die App aus, als würde sie nichts tun.
- Die Katalogsuche lief bisher synchron im GUI-Thread (nur ein Wartecursor
  als Rückmeldung) und lief deswegen komplett blockierend; sie läuft jetzt
  wie die Cardmarket-Suche in einem Hintergrund-Worker
  (`CatalogSearchWorker`).

### Fix — Base Set: Normal/Shadowless-Mehrdeutigkeit
- Live-reportiert: eine manuell über die Katalogsuche hinzugefügte Base-Set-
  Karte (z. B. Charizard) bekam automatisch den Cardmarket-Link der
  Shadowless-Variante zugeordnet, obwohl der Nutzer die normale (Unlimited)
  Version besaß bzw. eine nicht-englische Karte gar keine Shadowless-Variante
  hat (Shadowless existiert ausschließlich auf Englisch).
- Ursache: pokemontcg.io führt pro Base-Set-Karte nur einen einzigen
  Cardmarket-Link, der immer auf die Shadowless-Variante zeigt.
- Die Katalogsuche zeigt für Base-Set-Treffer jetzt zwei Einträge an ("Base"
  und "Base (Shadowless)"), jeweils mit dem korrekt aufgelösten Cardmarket-
  Link (Normal bzw. Shadowless) — der Nutzer wählt beim Hinzufügen die
  richtige Version direkt aus, statt hinterher von Hand nachbessern zu
  müssen. Für bereits bestehende Karten (oder falls die Auflösung mal
  fehlschlägt) zeigt die Preisermittlung weiterhin eine spezifische
  Meldung, die auf "Eigener Cardmarket-Link" verweist, statt automatisch
  die falsche Variante zu verwenden.

### Geändert — Schwelle für "veraltete Preise" auf 2 Monate
- `STALE_PRICE_THRESHOLD_DAYS` von 90 auf 60 Tage gesenkt (Nutzerwunsch).

### Neu — Mehrfachauswahl in Karten- und Sealed-Tabelle
- Bisher konnte immer nur eine Zeile ausgewählt werden — Verschieben/Löschen
  mehrerer Karten oder Sealed-Produkte am Stück war nicht möglich.
- Beide Tabellen erlauben jetzt Shift-/Strg-Klick wie in einem normalen
  Dateimanager. "Verschieben" und "Löschen" wirken auf die gesamte
  Markierung; "Bearbeiten" (und bei Sealed-Produkten: "Preis
  aktualisieren") bleiben auf genau eine Zeile beschränkt und verschwinden
  aus dem Kontextmenü, sobald mehrere Zeilen markiert sind.

### Geändert — UI nur noch auf Englisch
- Der DE/EN-Sprachumschalter in "Infos und Einstellungen" wurde entfernt —
  die Programmoberfläche ist jetzt ausschließlich Englisch.
- Betrifft ausschließlich die UI-Sprache. Die Sprache einzelner Karten/
  Sealed-Produkte (Englisch, Deutsch, Japanisch, Koreanisch, ...) bleibt
  unverändert vollständig unterstützt — das ist Karteninhalt, kein
  UI-Zustand.
- Der dadurch frei gewordene zweite Tab in "Infos und Einstellungen" zeigt
  jetzt eine kurze Hilfe/Anleitung: manuelles Eintragen per
  Cardmarket-Link, warum Japanisch/Koreanisch/Traditionelles-Chinesisch
  keinen automatischen Sprachfilter bekommen (im Gegensatz zu
  Englisch/Deutsch/Französisch/Spanisch/Italienisch/Portugiesisch),
  Preisverlauf, veraltete Preise, und der Unterschied zwischen Sammlungen
  (nur Karten) und Sealed-Produkten (nicht sammlungsgebunden).

### Neu — Sammel-Button "Alle aktualisieren" für veraltete Preise
- Die Statistik-Ansicht listet Karten/Sealed-Produkte mit veraltetem Preis
  einzeln auf, jede mit einem eigenen "Preis aktualisieren"-Button — bei
  vielen veralteten Preisen musste bisher jede Zeile einzeln angeklickt
  werden.
- Neuer Button "Alle aktualisieren" über jeder der beiden Listen: aktualisiert
  alle dort aufgeführten Preise nacheinander (mit Fortschrittsanzeige in der
  Statusleiste), deaktiviert sich während des Laufs selbst und ist
  ausgegraut, wenn die Liste leer ist.

### Neu — Automatische Datenbank-Backups
- Bisher gab es keinerlei Sicherung der `collection.db` — ein korrupter
  Zustand oder eine fehlerhafte Migration hätte die ganze Sammlung kosten
  können.
- Neues Modul `app/database/backup.py`: kopiert die Datenbankdatei
  automatisch mit Zeitstempel nach `data/backups/`, bevor
  `Database.initialize()` Migrationen laufen lässt. Läuft nur, wenn die
  Datei schon existiert (frische Installation hat nichts zu sichern), und
  überspringt sich selbst, wenn die letzte Sicherung jünger als 24h ist
  (verhindert eine Flut bei häufigen Neustarts). Behält maximal die
  letzten 20 Sicherungen, ältere werden automatisch entfernt. Nie
  blockierend: ein fehlgeschlagenes Backup verhindert nie den App-Start.

### Neu — Cardmarket-Sucheautomatisierung mit Bestätigungsdialog
- Für Karten ohne bekannte Cardmarket-Verknüpfung (z. B. "Poké Pad" aus
  "Perfect Order", wo pokemontcg.io keinen Link hinterlegt hat) musste der
  Link bisher von Hand recherchiert und über "Eigener Cardmarket-Link"
  eingetragen werden.
- Neuer Button "Cardmarket-Link suchen" im Kartendetail-Panel: durchsucht
  Cardmarkets eigene Website-Suche automatisch und zeigt die Treffer zur
  Bestätigung an (Name/Set/Nummer/Preis) — erst nach Bestätigung durch den
  Nutzer wird ein Link übernommen, es wird nie automatisch geraten.
- Technisch: Cardmarkets UI-Automatisierungs-Baum liefert nie die echte
  URL eines Suchtreffers, nur sichtbaren Text. Live bestätigt: das UI-
  Automation-*Invoke*-Pattern (nicht ein simulierter Klick) navigiert
  zuverlässig zum echten Produkt, dessen Adresszeile danach ganz normal
  ausgelesen werden kann — darüber wird die korrekte URL rekonstruiert.
- Live end-to-end verifiziert: Suche nach "Poke Pad" findet u. a. das
  echte "Perfect Order (POR 113)"-Ergebnis, dessen aufgelöste URL exakt
  mit dem vom Nutzer bereitgestellten Cardmarket-Link übereinstimmt.

### Neu — Set-Icon-Fallback über tcgdex.dev, wenn pokemontcg.io hinterherhinkt
- Nutzer-Sorge: pokemontcg.io könnte für neue Sets vernachlässigt werden
  (Beleg: "Perfect Order", erschienen 27.03.2026, hat dort Monate später
  immer noch kein Set-Icon).
- Recherche: live gegen tcgdex.dev geprüft (im Projekt schon für JP/KO/ZH-
  Namenssuche genutzt) — "Perfect Order" ist dort bereits vollständig
  vorhanden, inklusive eines funktionierenden Icons. Eine Idee, die
  fehlende Cardmarket-Verknüpfung über tcgdex's Cardmarket-Produkt-ID
  automatisch aufzulösen, wurde verworfen: drei plausible URL-Muster live
  getestet, keins führt zur echten Produktseite bei Cardmarket.
- Fix: `ensure_set_icon()` (`app/catalog/set_icon_cache.py`) fällt jetzt,
  wenn pokemontcg.io kein Icon liefert, automatisch auf tcgdex.dev zurück
  (neues Modul `app/catalog/tcgdex_set_icon.py`, Zuordnung über den
  Set-Namen, da tcgdex eigene, unabhängige Set-IDs verwendet). Live
  end-to-end verifiziert: "Perfect Order" lädt jetzt ein Icon.

### Geändert — Karten-Tab: Spaltenüberschriften abgekürzt, Detailpanel schmaler
- Nutzer-Fund: die schmal gehaltenen Sprache/Zustand/Menge-Spalten
  schnitten die vollen Spaltenüberschriften ab ("...nguag", "...nditio").
- Fix: neue abgekürzte Überschriften "Spr."/"Zust."/"Anz." (EN:
  "Lang."/"Cond."/"Qty"), passend zur bewusst schmalen Spaltenbreite.
- Zusätzlich auf Nutzerwunsch: Kartendetail-Panel (rechts) schmaler
  gemacht (Mindestbreite 320→260px, Splitter-Anfangsbreite 360→290px) —
  ein Karten-Artwork ist ohnehin schmal (2,5:3,5-Hochformat), im
  Gegensatz zum breiteren Sealed-Produkt-Panel. Die frei werdende Breite
  geht an die Kartentabelle (Splitter-Anfangsbreite 730→800px).

### Behoben — Katalogsuche fand "Poké Pad" ohne Akzent nicht ("poke pad")
- Nutzer-Fund: die Suche fand "Poké Pad" nur bei exakter Schreibweise mit
  é, nicht bei "poke pad" oder "pokepad".
- Ursache: pokemontcg.io foldet Akzente grundsätzlich nicht — auch nicht
  bei einer Präfix-Wildcard-Suche gegen den zusammengeschriebenen
  Gesamtnamen ("poke*", "pokepad*" finden nichts). Live bestätigt: eine
  Suche nach "pad*" (dem zweiten, akzentfreien Wort) findet die Karte
  aber, weil pokemontcg.io eine Präfix-Wildcard gegen jedes Wort im
  Namensfeld prüft, nicht nur das erste.
- Fix: der schrumpfende Präfix-Fallback in `catalog_search_service.py`
  probiert jetzt zusätzlich jedes einzelne Wort der Anfrage einzeln
  (längstes zuerst), nicht mehr nur Präfixe des gesamten
  zusammengeschriebenen Namens.

### Behoben — EX-Serie: falscher Set-Name durch pokemontcg.io (fehlendes "EX ")
- Nutzer-Fund (mit Beleg: offizielle Übersicht der EX-Serie): pokemontcg.io
  lässt bei der kompletten EX-Serie (EX Ruby & Sapphire bis EX Power
  Keepers, 16 Sets) das führende "EX " in seinen eigenen Set-Namen weg
  (z. B. nur "Sandstorm" statt "EX Sandstorm") — live gegen alle 16 Sets
  bestätigt (IDs `ex1` bis `ex16`, exakt sequentiell, wie vom Nutzer
  geliefert).
- Fix: neue `_EX_SERIES_SET_NAMES`-Zuordnung in
  `app/catalog/pokemontcg_client.py`, angewendet in `list_sets()` und beim
  Parsen von Kartensuchergebnissen — Katalog-Treffer aus dieser Serie
  zeigen jetzt korrekt "EX ..." statt des abgeschnittenen Namens, passend
  zu Cardmarkets eigener Bezeichnung (und zu `resolve_set_code()`, das
  diese Korrektur jetzt automatisch mitnutzt).
- Migration 8 (`app/database/schema.py`) korrigiert zusätzlich bereits
  bestehende Karten dieser 16 Sets rückwirkend in der Datenbank.

### Neu — Set-Icon auch für manuell per Cardmarket-Link eingetragene Karten
- Nutzer-Fund: eine per Katalogsuche hinzugefügte Karte ("Aerodactyl ex")
  zeigt ein Set-Icon, eine manuell per Link eingetragene Karte aus
  demselben Set ("Cacturne", EX Sandstorm) nicht — obwohl beide zum
  gleichen Set gehören, wirkten sie in der Tabelle wie unterschiedliche
  Sets.
- Ursache: das Set-Icon wird über `card.set_code` geladen, das für manuell
  eingetragene Karten nie gesetzt wurde (nur `set_name`, aus Cardmarkets
  Titel/Breadcrumb geparst). Live bestätigt: pokemontcg.io kennt dieses Set
  als `Sandstorm` (Code `ex2`), Cardmarket nennt es `EX Sandstorm` — beide
  meinen dasselbe Set, nur mit leicht anderer Namensgebung.
- Fix: neue `PokemonTcgClient.resolve_set_code()`-Methode löst den
  Katalog-Code best-effort aus dem freien Set-Namen auf (exakter Treffer
  zuerst, sonst „gegebener Name endet mit Katalog-Name“ als Fallback für
  den abgeschnittenen „EX “-Präfix). Läuft im selben Hintergrund-Thread wie
  der übrige "Karte manuell eintragen"-Ablauf (pokemontcg.io kann mehrere
  Sekunden brauchen), blockiert die Karte nie, falls die Auflösung
  fehlschlägt.

### Behoben — Signed/1st-Edition/Altered-Filter waren serverseitig wirkungslos
- Nutzer-Fund: manuell eingetragene Karte (Cacturne/Noktuska, EX Sandstorm)
  als "nicht Reverse Holo" eingestellt, Preis-Abruf lieferte trotzdem
  16€ — das ist der Preis der Reverse-Variante, die günstigste normale
  Holo liegt bei 28€. Erste Einschätzung (falsch): das sei eine
  Datenqualitäts-Eigenheit bei Cardmarket (Verkäufer kennzeichnet sein
  Angebot nicht korrekt), kein eigener Bug.
- Korrektur durch den Nutzer: er hat die echten URLs gepostet, die
  Cardmarkets eigene Filter-Sidebar erzeugt, wenn man die Haken direkt
  anklickt — `isSigned`, `isFirstEd`, `isAltered` und `isReverseHolo` sind
  dort **alle vier** flache Top-Level-Parameter. Unser Code hatte
  `isSigned`/`isFirstEd`/`isAltered` fälschlich als `extra[isSigned]` usw.
  verschachtelt (Ergebnis einer früheren, falsch verifizierten
  Recherche) — nur `isReverseHolo` war schon richtig bar. Die
  unbekannten `extra[...]`-Parameter haben vermutlich das serverseitige
  Filtern insgesamt lahmgelegt, statt nur ignoriert zu werden, wodurch am
  Ende die komplette, ungefilterte Angebotsliste zurückkam.
- Fix: `build_filtered_url()` in `browser_price_reader.py` nutzt jetzt für
  alle vier Extras bare Parameter (`isSigned`/`isFirstEd`/`isAltered`/
  `isReverseHolo`), keine mehr verschachtelt unter `extra[...]`.

### Behoben — "Karte manuell eintragen" scheiterte lautlos bei Karten ohne Nummer
- Nutzer-Fund (während des Tests eines neuen Features, siehe unten): beim
  Anlegen von "Shining Mew" (Cardmarket-Kategorie "Unnumbered Promos") über
  den Cardmarket-Link öffnete sich der Tab zwar mit der richtigen Seite,
  aber es wurde kein Eintrag angelegt — ohne sichtbare Fehlermeldung im
  Dialog (nur im Log).
- Ursache: Cardmarkets Seitentitel hat für Karten ohne gedruckte Nummer
  nicht "<Name> () - <Set> | Cardmarket" (leere Klammern), sondern lässt die
  komplette "(Nummer) - Set"-Klausel weg — live bestätigt: nur "Shining
  Mew | Cardmarket". Das bisherige Erkennungsmuster verlangte diese Klausel
  zwingend, fand also nie einen Treffer und brach die Suche ohne Karte ab.
- Fix: Fällt jetzt auf dasselbe schlichte "<Name> | Cardmarket"-Muster
  zurück, das Sealed-Produkte schon nutzen, falls das ausführlichere Muster
  nirgends passt — Set bleibt dann leer (wie die Kartennummer für solche
  Promos ohnehin schon), beides im Dialog editierbar.

### Neu — Bild-Erfassung auch für manuell per Cardmarket-Link eingetragene Karten
- Nutzer-Fund: eine manuell eingetragene Karte (kein Katalog-Treffer) hatte
  Preis und alles andere korrekt, aber kein Bild, obwohl Cardmarket eins
  anzeigt.
- Ursache: bislang bewusste Design-Entscheidung ("es gibt kein
  Katalog-Bild für eine manuell eingetragene Karte") von vor dem
  Sealed-Bild-Feature dieser Session.
- Fix: derselbe Screenshot-Erfassungs-Mechanismus wie bei Sealed-Produkten
  (`app.pricing.sealed_image_capture`, unverändert wiederverwendet) läuft
  jetzt auch beim "Karte manuell eintragen"-Ablauf mit, im selben bereits
  offenen Chrome-Tab. Best-effort wie bei Sealed: ein Fehlschlag beim
  Bild-Fund blockiert das Anlegen der Karte nie.

### Behoben — Sealed-Preis nahm bei Japanisch/Koreanisch/Chinesisch falsche Sprache
- Nutzer-Fund: Sealed-Produkt mit Sprache "Japanisch" (Beispiel: "Abyss Eye
  Booster Box", ein rein asiatisches Set ohne westliche Auflage) zeigte einen
  Preis an, der tatsächlich nur von **koreanischen** Angeboten auf derselben
  Seite stammte.
- Erste Annahme (falsch, per Screenshot vom Nutzer widerlegt): Japanisch/
  Koreanisch/Chinesisch seien bei Cardmarket eigene Produkte mit eigenem
  Link, wie es für Einzelkarten tatsächlich zutrifft. Der Nutzer zeigte
  jedoch Cardmarkets eigene Sprachfilter-Sidebar auf genau dieser
  Sealed-Produktseite und bestätigte live per eigenem Klick auf die
  Filter-Checkboxen: `?language=7` (Japanisch), `?language=10` (Koreanisch)
  und `?language=11` (Traditionelles Chinesisch) filtern alle dieselbe
  Seite — bei Sealed-Produkten ist das also, anders als bei Einzelkarten,
  eine reine Sprachvariante derselben Seite.
- Eigentliche Ursache: Der beim Anlegen/Bearbeiten gespeicherte Cardmarket-
  Link bekam für Japanisch/Koreanisch/Chinesisch nie einen `?language=N`-
  Filter angehängt (die dafür genutzte, Karten-spezifische Prüfung schließt
  diese drei bewusst aus). Ohne Filter las die App die komplette,
  ungefilterte Angebotsliste — und die Angebote der gesuchten Sprache lagen
  in diesem Fall weiter unten auf der Seite, als das automatisierte Auslesen
  erreichte, sodass am Ende nur koreanische Angebote ankamen.
- Fix: Neue, Sealed-spezifische Sprach-ID-Zuordnung (ergänzt die bisherige,
  weiterhin für Einzelkarten gültige um Japanisch=7/Koreanisch=10/
  Traditionelles Chinesisch=11), damit der gespeicherte Link für Sealed-
  Produkte auch bei diesen drei Sprachen korrekt gefiltert wird. Der
  bestehende Schutz "kein Ausweich-Preis aus einer anderen Sprache" bleibt
  für diese drei zusätzlich bestehen (jetzt korrekt begründet: es bedeutet
  "aktuell keine Angebote in dieser Sprache", nicht mehr "falsches Produkt
  verlinkt").
- Nachtrag (Live-Test durch den Nutzer zeigte, dass der Preis-Abruf trotzdem
  noch die volle Angebotsliste durchsuchte): Der Filter wurde bislang nur
  beim Anlegen/Bearbeiten in den gespeicherten Link geschrieben — bereits
  bestehende Produkte (z. B. das Test-Produkt "Abyss Eye Booster Box", vor
  diesem Fix angelegt) behalten dadurch dauerhaft einen ungefilterten Link,
  egal wie oft der Preis aktualisiert wird. Der Preis-Abruf berechnet den
  `?language=N`-Filter jetzt bei **jedem** Aufruf frisch aus der
  gespeicherten Produktsprache (wie bei Einzelkarten schon üblich), statt
  sich auf den gespeicherten Link zu verlassen — behebt damit auch bereits
  bestehende Produkte ohne erneutes Bearbeiten. `build_sealed_filtered_url`
  ersetzt einen vorhandenen `?language=`-Parameter jetzt, statt ihn ein
  zweites Mal anzuhängen (sonst hätte das erneute Anwenden bei bereits
  gefilterten, neueren Links zu `?language=X&language=Y` geführt).

### Geändert — Sealed-Produkt hinzufügen: ein Dialog statt zwei
- Bisher: Link eingeben → (Chrome-Tab flackert kurz auf) → zweiter Dialog
  zum Bestätigen von Name/Kategorie/Sprache/Menge. Nutzer-Feedback: der
  Chrome-Tab dazwischen wirkte wie unerklärte, störende Aktivität.
- Jetzt: **ein** Dialog (Link + Sprache + Menge + Notizen). Name **und**
  Kategorie werden nach Bestätigen automatisch von Cardmarket übernommen
  (Kategorie wie gehabt per Texterkennung geraten) — kein zweiter
  Bestätigungsdialog mehr, explizit auf Nutzerwunsch ("nicht viel selbst
  eintragen wollen"). Ein falsch erkannter Name/Kategorie lässt sich wie
  gehabt über "Bearbeiten" korrigieren.
- Neue `SealedProductAddDialog`-Klasse; `SealedEntryController` erstellt das
  Produkt jetzt direkt nach erfolgreichem Cardmarket-Abruf, ohne Umweg über
  einen zweiten, vom Panel gezeigten Dialog (die alte
  `add_confirmed`-Signalkette und `SealedProductListPanel.prompt_add()`
  sind entfernt, da nicht mehr gebraucht).

### Hinzugefügt — Gesamtpreis-Spalte in der Sealed-Tabelle
- Neben "Einzelpreis" (bisher nur "Preis" genannt) jetzt auch "Gesamtpreis"
  (Einzelpreis × Menge) direkt in der Tabelle sichtbar — Nutzer-Feedback:
  bei mehreren Exemplaren desselben Produkts (z. B. Booster in größerer
  Stückzahl) war der Gesamtwert bisher nicht auf einen Blick ersichtlich.
  Sortierbar wie alle anderen Spalten, mit demselben ⚠️-Hinweis bei
  veraltetem Preis.

### Behoben — Detailpanel-Preis-Button war nicht verdrahtet
- Der neue "Preis von Cardmarket abrufen"-Button im Sealed-Detailpanel
  (aus dem Detailpanel-Ausbau) hatte keine Verbindung zum eigentlichen
  Preis-Controller — Klick tat schlicht nichts. `SealedPriceController`
  bekommt jetzt (mirrors `PriceController` bei Karten) optional das
  Detailpanel übergeben, verbindet dessen `price_lookup_requested`-Signal
  und deaktiviert den Button für die Dauer der Preisabfrage.

### Behoben — Sealed-Preisabruf fand nie einen Preis
- Nach dem Detailpanel-Ausbau meldete "Preis von Cardmarket abrufen" für
  Sealed-Produkte immer "kein Preis gefunden" — obwohl die Seite sichtbar
  richtig geöffnet wurde. Ursache: Cardmarket zeigt die Sprache pro Angebot
  in der Sprache der aufgerufenen Seite an (z. B. "Deutsch"/"Englisch" auf
  `/de/`-URLs) — der Code kannte aber nur die englischen Wörter
  ("German"/"English"). Bei Karten fällt das nicht auf (die erkennen
  Angebote am sprachunabhängigen Zustands-Kürzel wie "NM"), bei
  Sealed-Produkten (kein Zustand) ist die Sprache aber der einzige Anker.
- **Sauberer Fix statt Flickenteppich pro Sprache:** Der eigentliche
  Preis-Abruf (nicht das Anzeigen/Erfassen von Name & Kategorie!) läuft
  jetzt immer über eine intern auf Englisch umgeschriebene Kopie der URL
  (`with_canonical_locale()`), unabhängig davon, in welcher Sprache der
  Nutzer seinen Cardmarket-Link eingefügt hat. Der **gespeicherte** Link
  bleibt unverändert in der Original-Sprache. Damit funktioniert der
  Preis-Abruf robust für jede Cardmarket-Locale (Deutsch, Französisch,
  Spanisch, ...) ohne dass für jede Sprache eine eigene Wortliste gepflegt
  werden müsste — wichtig, da die App perspektivisch für Nutzer in vielen
  Ländern gedacht ist. Die zuvor ergänzte deutsche Wortliste bleibt als
  zusätzliches Sicherheitsnetz bestehen.
- **Zusätzlich entdeckt und behoben:** Cardmarkets eigener
  Cookie-Consent-Banner kann beim allerersten Besuch einer Locale (z. B.
  jeder neue Nutzer bei seinem allerersten Preis-Abruf überhaupt) die
  eigentliche Seite kurz blockieren. Wird jetzt automatisch erkannt und
  weggeklickt ("Nur erforderliche Cookies", nicht "Alle akzeptieren" —
  entspricht der datensparsamen Voreinstellung).

### Hinzugefügt — Sealed-Tab: Detailpanel, Produktbild, Preisverlauf
- Der Sealed-Reiter ist jetzt strukturell wie der Karten-Reiter aufgebaut
  (nur ohne Sammlungsspalte, da Sealed-Produkte weiterhin nicht sammlungs-
  gebunden sind): neben der Liste zeigt ein neues Detailpanel
  (`SealedProductDetailPanel`) das ausgewählte Produkt mit Bild,
  Preis-Feldern und einem "Preis von Cardmarket abrufen"-Button.
- Neues Produktbild: da es für Sealed-Produkte (anders als Karten via
  pokemontcg.io) keine offizielle Bild-API gibt, wird das Foto beim
  manuellen Eintragen per Screenshot direkt aus dem ohnehin schon für
  Name/Kategorie geöffneten Cardmarket-Tab erfasst (`SealedArtworkView` +
  `app/pricing/sealed_image_capture.py`): das zum Produktnamen passende
  Bild-Element wird über Windows UI-Automation gefunden und per
  `PrintWindow`-Screenshot zugeschnitten. Best-effort — schlägt die
  Erfassung fehl, bleibt das Produkt einfach ohne Bild (wie bisher schon
  bei manuell eingetragenen Karten ohne Katalog-Treffer).
- Neuer Preisverlauf: eine neue `sealed_price_history`-Tabelle (Migration 7,
  spiegelt `price_history`) speichert jetzt jede Preisermittlung als
  Zeitreihe statt nur den letzten Wert. Ein neues, ausklappbares
  `SealedPriceHistoryDock` (spiegelt `PriceHistoryDock`) zeigt den
  Preisverlauf als Diagramm, exakt wie bei Karten.
- Migration 7 ergänzt außerdem `sealed_products.photo_path`.

### Behoben — Sealed-Cardmarket-Link berücksichtigte Sprache nicht
- Beim manuellen Eintragen/Bearbeiten eines Sealed-Produkts wurde der
  gespeicherte Cardmarket-Link nicht um Cardmarkets eigenen
  `?language=N`-Filter ergänzt, obwohl genau dieser Filter für Einzelkarten
  bereits funktioniert (live bestätigt) — der Nutzer hat per eigenem Test
  bestätigt, dass er auch auf Sealed-Produktseiten identisch funktioniert
  (Deutsch = `?language=3`). Der Link wird jetzt beim Anlegen und Bearbeiten
  konsistent um den passenden Filter ergänzt (Englisch/Französisch/Deutsch/
  Spanisch/Italienisch/Portugiesisch); Japanisch/Koreanisch/Chinesisch
  bleiben unverändert, da das dort separate Cardmarket-Produkte sind, kein
  Filter auf derselben Seite.

### Hinzugefügt — Alle Tabellenspalten überall sortierbar
- Kartenliste: bisher waren nur Name/Set/Sprache/Zustand sortierbar, jetzt
  alle 8 Spalten inkl. Menge und Preis. Menge/Preis sortieren numerisch
  (nicht alphabetisch) über eine neue `_NumericItem`-Klasse, die einen
  separat gespeicherten Zahlenwert statt des angezeigten Texts vergleicht
  ("10" würde alphabetisch vor "2" einsortiert werden). Unbepreiste Karten
  sortieren als "billigste" (Sentinel-Wert, willkürliche aber konsistente
  Konvention).
- Sealed-Tab: Menge/Preis ebenso numerisch sortierbar gemacht (spiegelt
  dieselbe `_NumericItem`-Klasse).
- Statistik-Tab: alle Übersichtstabellen (Sammlungen, Wert nach Set/Sprache/
  Zustand/Kategorie, teuerste Karten/Sealed-Produkte) jetzt sortierbar über
  Qt-Bordmittel plus dieselben numerisch-/alphabetisch-bewussten Item-Typen.
  Die beiden Tabellen mit veraltetem Preis (die einen "Preis aktualisieren"-
  Button pro Zeile als Cell-Widget einbetten) sortieren stattdessen manuell:
  Qt's eingebautes Sortieren verschiebt Zellen, lässt aber Cell-Widgets an
  ihrer alten Zeilenposition zurück, was den Button vom falschen Eintrag
  aus auslösen würde. Ein Klick auf die Kopfzeile sortiert stattdessen die
  gespeicherten Einträge und rendert die Tabelle komplett neu (Buttons
  werden dabei frisch erzeugt, bleiben also korrekt zugeordnet).

### Geändert — Suchfeld etwas breiter
- Feste Breite von 320px auf 420px erhöht (Nutzer-Feedback).

### Behoben — Sealed-Add-Button war zentriert statt linksbündig
- Nach Runde 2 stand "+ Sealed-Produkt hinzufügen" auf dem Sealed-Reiter
  zentriert im Container statt linksbündig, da der Container auf die
  breitere Karten-Kombination eingefroren ist. Ein `addStretch()` als
  Fix führte zu einem neuen Problem: das Suchfeld (Standard-`SizePolicy
  Expanding`) konkurrierte mit dem Stretch um denselben Restplatz und
  wurde auf einen Bruchteil seiner Breite zusammengedrückt. Endgültiger
  Fix: Suchfeld bekommt jetzt eine echte feste Breite (`setFixedWidth`)
  statt nur eine maximale — dadurch gibt es keine Konkurrenz mehr, und
  der abschließende Stretch schiebt zuverlässig nur echten Leerraum nach
  rechts.

### Behoben — Toolbar-Feinschliff Runde 2: Abstände links, Sealed-Button-Breite, Trenner
- Suchfeld/"Suchen"/"Karte manuell eintragen" standen auf dem Karten-Reiter
  unnötig weit auseinander: die eingefrorene Container-Breite wurde als
  **Summe** aller vier möglichen Kinder berechnet (auch der nie gleichzeitig
  sichtbaren Sealed- und Karten-Kombination), statt als **Maximum** der
  beiden tatsächlich vorkommenden Kombinationen — der Container war dadurch
  auf allen Reitern deutlich breiter als nötig, was sich als Lücken
  zwischen den sichtbaren Elementen zeigte.
- "+ Sealed-Produkt hinzufügen" war unnötig in die Breite gezogen (gleicher
  Bug wie zuvor beim "Suchen"-Button: `QPushButton`-Standardgröße erlaubt
  Wachstum) — jetzt ebenfalls fest auf Textgröße gedeckelt.
- Der schwarze Trenner-Strich zwischen linker Gruppe und Reitern komplett
  entfernt (unnötig, da beide Bereiche jetzt eindeutig durch den
  dehnbaren Platzhalter dazwischen getrennt sind).

### Behoben — Toolbar-Feinschliff: links wieder zu breit, rechts nicht bündig
- Nach dem ersten Fix-Versuch per Screenshot aufgefallen: die linke
  Such-/Aktions-Gruppe konnte sich noch über ihre eigentlich fixe Breite
  hinaus strecken (ein einfaches `QWidget` behält Qt's "Grow"-Flag, auch
  mit gesetzter Mindestbreite), wodurch bei einem breiteren Fenster eine
  große Lücke vor den Reitern entstand. Jetzt echte `SizePolicy.Fixed` auf
  dem Container plus ein eigener, transparenter Platzhalter-Widget
  (`Expanding`) zwischen Trenner und Reitern, der genau diese Lücke
  aufnimmt — Reiter/Export/Infos sitzen dadurch jetzt wirklich bündig am
  rechten Rand, unabhängig von der Fensterbreite. Nebenbei: die fixe
  Breite wird jetzt direkt aus den einzelnen Kind-Widgets berechnet statt
  aus der (unzuverlässigen) `sizeHint()` des Containers selbst — die
  unterschätzte, wie breit sich das Suchfeld eigentlich strecken darf, und
  quetschte es sichtbar zusammen.

### Geändert — Toolbar: linker Bereich zeigt jetzt tab-eigene Aktionen statt leer zu bleiben
- Nutzer-Feedback (mit Photoshop-Annotation der Screenshots): der linke
  Toolbar-Bereich sollte nie leer wirken. "+ Sealed-Produkt hinzufügen" ist
  jetzt kein eingebetteter Button mehr im Sealed-Panel selbst, sondern sitzt
  in der Toolbar an genau der Stelle, an der auf dem Karten-Reiter
  Suchfeld/Suchen/"Karte manuell eintragen" stehen. Cards/Sealed/Statistik/
  Export/Infos bleiben weiterhin fix auf der rechten Seite.

### Behoben — Dunkle "Geisterbox" im Toolbar auf Sealed-/Statistik-Reiter
- Nach dem morgendlichen Live-Check per Screenshot gefunden: der Container
  für Suchfeld/Suchen/"Karte manuell eintragen" hatte kein `objectName` und
  erbte dadurch die allgemeine `QWidget`-Regel (`background-color:
  {Fenster-Hintergrund}`) — dunkler als die Toolbar selbst. Solange der
  Container voller Inhalte war (Karten-Reiter), fiel das nicht auf; sobald
  die Kinder auf Sealed/Statistik ausgeblendet waren, blieb ein deutlich
  sichtbares dunkles Rechteck übrig. Fix: `objectName` + eine transparente
  QSS-Regel dafür.

### Hinzugefügt — Feste Sealed-Kategorien + Statistik für Sealed-Produkte
- Sealed-Produkte hatten bisher eine reine Freitext-Kategorie (aus dem
  Cardmarket-Seitentitel geraten) — jetzt gibt es eine recherchierte, feste
  Liste (Booster Box, Elite Trainer Box, Booster Bundle, Booster Pack, Box
  Set, Tin, Blister, Premium Collection, Build & Battle Box, Theme Deck,
  Pin Collection, Sonstiges) als editierbares Dropdown im Hinzufügen-/
  Bearbeiten-Dialog. Beim automatischen Eintragen per Cardmarket-Link wird
  die geratene Kategorie jetzt auf diese feste Liste normalisiert (z. B.
  Cardmarkets "Booster Boxes" → "Booster Box"), damit die Kategorie-Spalte
  sinnvoll sortier-/gruppierbar ist.
- Statistik-Tab bezieht jetzt auch Sealed-Produkte mit ein: eine neue
  Portfolio-Übersicht ganz oben zeigt den kombinierten Gesamtwert (Karten +
  Sealed) sowie zwei Kennzahl-Kacheln ("Karten"/"Sealed-Produkte"). Darunter
  ein eigener "Sealed-Produkte"-Abschnitt mit Wert nach Kategorie, teuersten
  Sealed-Produkten und Sealed-Produkten mit veraltetem Preis (inkl. Inline-
  "Preis aktualisieren"-Knopf, wie bei Karten).
- Der bisherige, sehr lange Statistik-Tab wurde optisch klarer gegliedert:
  "Karten" und "Sealed-Produkte" sind jetzt zwei deutlich abgesetzte
  Ober-Abschnitte (größere, unterstrichene Überschrift), die Portfolio-
  Kennzahlen oben stehen in eigenen, abgehobenen Kacheln statt als reiner
  Fließtext.

### Recherchiert, nicht umgesetzt (erneut) — Graded-Karten-Preise
- Live-Test bestätigt: 130point.com hat keine URL-basierte Suche und steht
  unter Cloudflare-Schutz; interaktives Antippen des Suchfelds funktioniert
  zwar technisch, würde aber die bewusste "keine Browser-Automation"-Grenze
  dieses Projekts aufweichen. PSAs Population Report verlangt eine
  Anmeldung. Bewusst kein Feature gebaut — Details in PROJECT_PROGRESS.md.

### Behoben — Toolbar-Nachbesserung: riesiger Suchen-Button + Sealed-Sichtbarkeit
- "Suchen"-Button wuchs fälschlich in den Leerraum ausgeblendeter Toolbar-
  Elemente hinein (QPushButton-Standard-SizePolicy) — jetzt fest gedeckelt.
  "Karte manuell eintragen" blieb auf dem Sealed-Reiter sichtbar, da
  `QToolButton.setDefaultAction()` keine Sichtbarkeit synct — jetzt
  explizit über den echten Button-Widget gesteuert.

### Recherchiert, nicht umgesetzt — Graded-Karten-Preise (130point.com/PSA)
- Live getestet: 130point.com hat keine per URL filterbare Suche (anders
  als Cardmarket) und steht unter Cloudflare-Schutz; PSAs Population Report
  verlangt inzwischen eine Anmeldung, die offizielle API deckt nur Cert-
  Nummer-Verifikation ab. Bewusst kein Feature gebaut, um weder die
  projekteigene "keine Browser-Automation"-Grenze aufzuweichen noch eine
  Login-Umgehung vorzunehmen. Details in PROJECT_PROGRESS.md.

### Geändert — Sealed-Produkte sind keiner Sammlung mehr zugeordnet
- Anders als Karten (in physischen Ordnern/Ordnern sortiert) werden Sealed-
  Produkte nicht so organisiert — der Sammlungsbezug wurde komplett entfernt
  (neue Migration 6: `collection_id` aus `sealed_products` entfernt, da
  SQLite eine Fremdschlüssel-Spalte nicht per `ALTER TABLE DROP COLUMN`
  löschen kann — die Tabelle wird stattdessen neu aufgebaut). Der Sealed-
  Reiter zeigt jetzt immer alle Sealed-Produkte, unabhängig von der links
  ausgewählten Sammlung. Die "Verschieben"-Aktion entfällt dadurch für
  Sealed-Produkte (ergibt ohne Sammlungen keinen Sinn mehr, bleibt aber für
  Karten bestehen). Export "Sealed-Produkte" hat keine Sammlungsauswahl mehr
  (immer "alle") — die Spalte "Sammlung" entfällt entsprechend in allen vier
  Export-Formaten.

### Geändert — Toolbar: fixe Reiter-Positionen, kein "Springen" mehr
- Suchfeld, "Suchen" und "Karte manuell eintragen" stecken jetzt in einem
  gemeinsamen Container mit fixer Mindestbreite, statt einzeln direkt auf
  der Toolbar zu sitzen. Vorher verschob sich die Position der Reiter/
  Export/Infos, je nachdem welche dieser drei Elemente gerade ein-/
  ausgeblendet waren — jetzt bleiben sie an fester Position. Behebt dabei
  auch einen Qt-Eigenheit-Bug: das Suchfeld blieb auf dem Sealed-Reiter
  fälschlich sichtbar, weil ein direkt auf die Toolbar per `addWidget()`
  gesetztes Widget sein eigenes `setVisible(False)` nach einem Style-/
  Layout-Durchlauf wieder verlieren konnte.

### Geändert — Reiter-Reihenfolge + Suchfeld/manuell eintragen nur bei "Karten"
- Reiter-Reihenfolge jetzt Karten → Sealed → Statistik (vorher Karten →
  Statistik → Sealed). Suchfeld, "Suchen" und "Karte manuell eintragen"
  sind jetzt nur sichtbar, während der Karten-Reiter aktiv ist — genauso
  wie der "+ Sealed-Produkt hinzufügen"-Knopf bereits ausschließlich im
  Sealed-Reiter eingebettet ist.

### Behoben — "Sealed-Produkt hinzufügen" wirkte wie "funktioniert nicht"
- Ursache: ohne ausgewählte Sammlung zeigte der Knopf nur eine leicht zu
  übersehende Statusleisten-Meldung an, statt sichtbar zu reagieren — exakt
  das gleiche Muster, das schon einmal bei "Karte manuell eintragen" für
  Verwirrung gesorgt hatte. Beide zeigen den Hinweis "Bitte zuerst eine
  Sammlung auswählen" jetzt als echten, nicht zu übersehenden Dialog an.

### Hinzugefügt — Karte/Sealed-Produkt zwischen Sammlungen verschieben
- Neuer Kontextmenü-Punkt "Verschieben" in Kartenliste und Sealed-Liste:
  Zielsammlung auswählen, fertig.

### Hinzugefügt — Export: Typ-Auswahl Karten vs. Sealed-Produkte
- Der Export-Dialog fragt jetzt zuerst, was exportiert werden soll (Karten
  oder Sealed-Produkte), zusätzlich zu Format und Sammlung. Sealed-Produkte
  bekommen eigene Spalten (Name/Kategorie/Sprache/Menge/Preis/...) in allen
  vier Formaten.

### Hinzugefügt — Sealed-Produkte (Booster-Boxen, Displays, ETBs, ...)
- Neuer eigener Reiter "Sealed" neben "Karten"/"Statistik". Eintragen nur
  per Cardmarket-Link (es gibt keinen Katalog für Sealed-Produkte wie bei
  Karten) — Name/Kategorie werden aus dem Seitentitel/der Breadcrumb
  gelesen. Eigene, vereinfachte Preisermittlung ohne Zustands-Leiter
  (Cardmarket verkauft Sealed-Produkte ausschließlich versiegelt): nur
  passende Sprache vs. jede Sprache.

### Hinzugefügt — Sprachflaggen + farbige Zustands-Badges in der Kartenliste
- Sprachcode-Text (DE/EN/…) durch ein kleines, selbst gezeichnetes,
  zentriertes Flaggen-Icon ersetzt. Zustands-Zelle (MT/NM/EX/GD/LP/PL/PO)
  zeigt jetzt ein farbiges Badge-Icon mit dem Kürzel (wie auf Cardmarket),
  statt die ganze Zelle einzufärben.

### Geändert — Toolbar-Reihenfolge + aktiver Reiter hervorgehoben + Fenstergröße
- "Karte manuell eintragen" steht jetzt direkt neben "Suchen", gefolgt von
  einem einzelnen Trenner und allen übrigen Punkten (Karten/Statistik/
  Export/Infos und Einstellungen) als eine Gruppe. Dabei einen Bug
  gefunden und behoben: der Knopf war versehentlich doppelt in der
  Toolbar. "Karte manuell eintragen" ist jetzt wie "Suchen" ein solider
  Button; der aktive Reiter ("Karten"/"Statistik") bekommt stattdessen nur
  einen dezenten farbigen Unterstrich statt vollflächiger Farbe. Start-
  Fenstergröße vergrößert (1650×900), damit die komplette Toolbar ohne
  Überlauf-Pfeil sichtbar ist.

### Behoben — Datum/Uhrzeit zu eng zusammen
- Mehr Abstand zwischen Datum und Uhrzeit in Statistik/Preisverlauf/
  Kartendetails. "Letzte Aktualisierung" in den Kartendetails zeigte
  bisher einen unformatierten rohen Zeitstempel an.

### Hinzugefügt — "Infos und Einstellungen" + zweisprachige Oberfläche (DE/EN)
- Neuer Toolbar-Knopf mit App-Infos/Quellen und einer Sprachauswahl
  Deutsch/Englisch (wirksam nach Neustart). Die komplette Oberfläche ist
  jetzt übersetzt.

### Hinzugefügt — Karte manuell per Cardmarket-Link eintragen
- Neuer Toolbar-Knopf "Karte manuell eintragen": Cardmarket-Produktlink
  einfügen, die App öffnet einen Chrome-Tab, liest Name/Set/Kartennummer aus
  dem Seitentitel und öffnet den gewohnten Hinzufügen-Dialog (Felder dabei
  editierbar) — der Link wird direkt als eigener Cardmarket-Link
  hinterlegt, ganz ohne Katalog-Suche/Zuordnungs-Heuristik.

### Geändert — Toolbar aufgeräumt
- Scanner- und "Cardmarket-Preise aktualisieren"-Knopf entfernt (Scanner
  vorerst verworfen; der Sammel-Update-Knopf tat ohnehin nie mehr als eine
  Erklärung anzuzeigen — Preise werden weiterhin pro Karte einzeln über den
  Knopf in den Kartendetails abgerufen). Alle verbleibenden Toolbar-Knöpfe
  sind jetzt reine Textbuttons ohne Icon.

### Behoben — Reverse Holo hatte fälschlich keinen Cardmarket-Preisfilter
- Frühere Recherche hatte angenommen, Cardmarket biete keinen Reverse-Holo-
  Filter — vom Nutzer per echtem Link widerlegt und live nachgeprüft
  (`?isReverseHolo=Y`, ein Yes/No-Filter direkt im Produktseiten-Formular).
  Reverse-Holo-Karten werden jetzt genauso wie Signiert/1st Edition/Altered
  auf jeder Preis-Leiter-Stufe verbindlich gefiltert.

### Behoben — Vintage-Sets mit mehreren Cardmarket-Produktversionen
- Base Set & ähnliche Sets können eine Sprache als eigenständiges
  Cardmarket-Produkt unter einer Nachbar-Versionsnummer führen (statt
  eines Filters auf derselben Seite) — die App probiert jetzt genau eine
  Alternativ-Version (nie mehr), nach einer bewussten Pause, bevor sie
  aufgibt.

### Hinzugefügt — Export (CSV/Excel/JSON/PDF)
- Sammlung (eine oder alle) über den Toolbar-„Export"-Knopf in eines von
  vier Formaten exportieren, mit nativem „Speichern unter"-Dialog.

### Behoben — Tolerante Suche scheiterte an Varianten-Wörtern wie "holo"
- "xatu skyridge holo" fand 0 Treffer, obwohl "xatu skyridge" funktionierte
  — "holo" wird jetzt als Druckvariante erkannt und aus der Namenssuche
  entfernt, statt fälschlich als Teil des Kartennamens behandelt zu werden.

### Hinzugefügt — Sortierbare Spalten in der Kartenliste
- Klick auf Name/Set/Sprache/Zustand sortiert die Kartenliste alphabetisch
  (nochmaliger Klick kehrt die Richtung um). Die Sortierung bleibt auch
  nach dem nächsten Aktualisieren der Liste erhalten.

### Behoben — Preis-Lookup las die Cardmarket-Seite manchmal zu früh aus
- Die Seite hatte sich schon umbenannt (Fenstertitel korrekt), aber der
  eigentliche Inhalt (Angebotstabelle) war noch nicht fertig gerendert —
  die App erfasste dann nur die Chrome-Oberfläche und meldete "keine
  Angebote gefunden". Wartet jetzt automatisch länger, wenn die erste
  Erfassung auffällig dünn ausfällt.

### Verbessert — Cardmarket-Link-Auflösung robuster gegen Timeouts
- Ein Timeout beim Auflösen von pokemontcg.ios Tracking-Kurzlink zur
  echten Cardmarket-Seite ließ den Browser den unaufgelösten Kurzlink
  öffnen (keine echte Produktseite). Wird jetzt einmal wiederholt.

### Verbessert — Katalogsuche robuster gegen kurzzeitige pokemontcg.io-Aussetzer
- Eine einzelne Zeitüberschreitung ließ die ganze Suche mit "Kartenkatalog
  nicht erreichbar" scheitern. Wird jetzt einmal automatisch wiederholt,
  bevor aufgegeben wird.

### Behoben — Zweisprachige Suche mit Karten-Suffix ("Blitza VMAX")
- Fremdsprachige Namen mit einem Karten-Typ-Suffix (VMAX/EX/GX/V/ex)
  fanden bisher gar nichts, obwohl der reine Artname allein funktionierte
  ("Blitza" ja, "Blitza VMAX" nein) — betraf praktisch jede moderne Karte.
  Übersetzt jetzt den Artnamen-Teil und hängt den Suffix wieder an.

### Behoben — Preise auf englisch formatierten Cardmarket-Seiten erkannt
- Die Preis-Erkennung erwartete nur deutsches Zahlenformat ("1.550,00 €")
  und meldete auf `/en/`-Seiten ("1,550.00 €") fälschlich "keine Angebote
  gefunden". Erkennt jetzt beide Formate unabhängig von der Locale.

### Hinzugefügt — Bezeichnungsvorschlag für JP/KO/ZH-Karten (nie Preise)
- Wenn die automatische Preisermittlung für Japanisch/Koreanisch/
  Chinesisch abbricht, schlägt die App jetzt zusätzlich (über tcgdex.dev,
  ausschließlich Namen/Sets, nie Preise) die wahrscheinliche Cardmarket-
  Bezeichnung vor, damit sie schneller von Hand gesucht werden kann.
  Kandidaten mit unplausiblem zeitlichem Abstand (z. B. moderne Karten
  ohne echte tcgdex-Abdeckung wie Umbreon VMAX) werden verworfen statt
  geraten.

### Behoben/Hinzugefügt — JP/KO/ZH-Preisermittlung (Zwischenlösung)
- Preis-Lookup berechnet für Japanisch/Koreanisch/Chinesisch nicht mehr
  stillschweigend einen falschen Preis vom (falschen) westlichen
  Cardmarket-Produkt, sondern bricht mit klarer Begründung ab.
- Neues Feld „Eigener Cardmarket-Link“ im Karten-Dialog: eigenen,
  korrekten Link hinterlegen, um die Preisermittlung für diese Karte zu
  aktivieren (funktioniert auch als genereller Override für jede andere
  Karte).

### Hinzugefügt — Set-Symbole überall, wo ein Set-Name steht
- Offizielle pokemontcg.io-Set-Icons in Kartenliste, Kartendetails,
  Katalog-Suchergebnissen und allen Statistik-Tabellen (Kartenliste,
  veraltete Preise, teuerste Karten, Wert nach Set).

### Behoben — Preis-Lookup aktualisierte den Preis nicht trotz korrekt geöffnetem Tab
- `AllowSetForegroundWindow(ASFW_ANY)` vor dem Chrome-Start behebt eine
  Windows-Fokus-Diebstahl-Sperre: der Preis-Lookup lief in ein Timeout
  ("Cardmarket-Tab ... nicht rechtzeitig gefunden"), obwohl die richtige
  Seite bereits sichtbar geöffnet war, weil die Fensteraktivierung aus
  einem Hintergrund-Thread kam.

### Hinzugefügt — Toleranteres Suchen: Sonderzeichen + zweisprachige Namen
- Suche (Katalog **und** eigene Sammlung) ist jetzt Akzent-/Bindestrich-/
  Leerzeichen-unempfindlich: "pokepad"/"poke pad" findet "Poképad",
  "hooh"/"ho oh" findet "Ho-Oh".
- Kartennamen sind jetzt auch in ihrer Übersetzung suchbar (statische, aus
  der PokeAPI generierte Übersetzungstabelle für 1025 Spezies): "Turtok"
  findet "Blastoise", "Bisaflor" findet "Venusaur" — sowohl im Katalog als
  auch in der eigenen Sammlung.

### Hinzugefügt/Behoben — Dritte Nachbesserung zu Schritt 10: Statistiken
- "Preis aktualisieren"-Button in der Statistik-Tabelle war abgeschnitten:
  Spaltenbreite und (der eigentliche Grund) Zeilenhöhe waren zu klein, da
  `resizeColumnToContents()`/`resizeRowsToContents()` Cell-*Widgets* nicht
  zuverlässig einbeziehen — jetzt feste Breite/Höhe direkt aus dem Button.
- Name/Set-Spalten in "Karten mit veraltetem Preis"/"Teuerste Karten" jetzt
  50:50 statt Set gequetscht.
- Kartenliste breiter, Sammlungen-Panel schmaler, Fenster insgesamt breiter
  — kein horizontales Scrollen mehr nötig.
- Lade-Feedback ("Suche läuft …" + Wartecursor) bei der Katalogsuche.
- Eingabefelder im Bearbeiten-Dialog heben sich jetzt farblich vom
  Hintergrund ab; Checkbox zeigt ein Häkchen-Icon, wenn angehakt.
- Hover-Effekte auf Tabellenzeilen/Dropdown-Einträgen nach mehreren
  erfolglosen Versuchen wieder entfernt (Button-Hover bleibt) — spätere
  Wiederaufnahme geplant.

### Hinzugefügt — Zweite Nachbesserung zu Schritt 10: Statistiken
- Suchleiste + Suchen-Button sind jetzt nur noch im "Karten"-Tab sichtbar.
- Toolbar-Navigation "Karten"/"Statistik" zeigt nur noch Text, keine Icons.
- "!"-Preis-Reminder neben dem Preis in der Kartenliste bei veraltetem Preis.
- Inline "Preis aktualisieren"-Button direkt in der "Karten mit veraltetem
  Preis"-Tabelle — löst denselben echten Cardmarket-Lookup aus wie der große
  Button im Kartendetail-Panel.
- Fußnote nennt jetzt explizit den 90-Tage-Zeitraum.
- `PriceController.start_lookup()` ist jetzt public und aktualisiert optional
  auch die Statistik-Ansicht nach einem erfolgreichen Lookup.

### Hinzugefügt — Nachbesserung zu Schritt 10: Statistiken
- Größere, deutlich abgesetzte Abschnitts-Überschriften im Statistiken-Tab.
- Gesamtwert zeigt jetzt ein Stand-Datum (jüngstes Preis-Update über alle
  Karten) plus einen Hinweis, dass der Wert veraltet sein kann.
- Neue Übersicht "Karten mit veraltetem Preis": listet Karten, deren Preis
  seit ≥90 Tagen nicht aktualisiert wurde oder noch nie ermittelt wurde.
- Navigation zwischen "Karten" und "Statistik" läuft jetzt über zwei
  Toolbar-Buttons statt der (jetzt versteckten) Tab-Leiste.

### Hinzugefügt — Schritt 10: Statistiken
- Neuer "Statistiken"-Tab (Zentral-Widget ist jetzt ein `QTabWidget`):
  Gesamtpreis-Übersicht mit Wert + Kartenzahl pro Sammlung **und**
  Gesamtsumme über alle Sammlungen gleichzeitig sichtbar.
- Wert nach Set/Sprache/Zustand (absteigend sortiert), teuerste Karten
  (Top 10), größte Preissteigerung (Vergleich der letzten zwei
  Preis-Updates einer Karte, größte positive Änderung gewinnt).
- Wird nur bei Tab-Wechsel neu berechnet, keine Hintergrundaktualisierung.
- Neu: `app/services/statistics_service.py`, `app/ui/widgets/statistics_panel.py`,
  `app/ui/controllers/statistics_controller.py`. 15 neue Tests.

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
