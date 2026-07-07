"""English-only UI translation layer.

The app is entirely hand-built PySide6 widgets (no Qt Linguist/``.ui``
files), so this is a simple lookup-table approach instead: every
user-facing string is written in German at its call site (as it always was,
from before the UI was made English-only) and wrapped in :func:`tr`, which
looks it up in a static English catalogue. A German string missing from the
catalogue is returned unchanged -- new call sites should just pass an
English literal instead of adding to the catalogue.

The UI used to be switchable between German and English (a persisted
``SettingsRepository`` setting); that toggle was removed and the app is
English-only now. This is unrelated to a *card's own printed language*
(``app.models.enums.Language``), which stays fully multilingual -- the
catalogue/database/Cardmarket integration never cared about UI language.
"""

from __future__ import annotations

#: German source string -> English translation. Keys are exactly the German
#: text used at the call site (not symbolic ids) -- this keeps every call
#: site a plain, readable ``tr("...")`` around the string that was already
#: there, and a missing entry is instantly visible in the source diff.
_EN: dict[str, str] = {
    # main_window.py
    "Karten durchsuchen  (z. B. „xatu skyridge holo“)": (
        'Search cards  (e.g. "xatu skyridge holo")'
    ),
    "Suchen": "Search",
    "Statistik": "Statistics",
    "Statistiken": "Statistics",
    "Sealed": "Sealed",
    "Infos und Einstellungen": "Info and help",
    "bereit": "ready",
    # settings_dialog.py
    "Info": "Info",
    "Version": "Version",
    "Quellen und Bibliotheken": "Sources and libraries",
    # card_details_dialog.py
    "Name:": "Name:",
    "Set:": "Set:",
    "Kartennummer:": "Card number:",
    "Kategorie:": "Category:",
    "Rarität:": "Rarity:",
    "Sprache:": "Language:",
    "Zustand:": "Condition:",
    "Reverse Holo": "Reverse Holo",
    "Signiert": "Signed",
    "Altered": "Altered",
    "Extra:": "Extra:",
    "Menge:": "Quantity:",
    "Notizen:": "Notes:",
    "Eigener Cardmarket-Link:": "Custom Cardmarket link:",
    (
        "Nur nötig bei Japanisch/Koreanisch/Chinesisch: eigener Link zum "
        "richtigen Cardmarket-Produkt"
    ): "Only needed for Japanese/Korean/Chinese: custom link to the correct Cardmarket product",
    (
        "Für Japanisch/Koreanisch/Chinesisch führt Cardmarket den Druck als "
        "eigenständiges Produkt unter einem anderen Set-Namen -- die "
        "automatische Zuordnung zeigt dort das falsche (westliche) Produkt. "
        "Hier den korrekten Cardmarket-Link einfügen, um das zu beheben."
    ): (
        "For Japanese/Korean/Chinese, Cardmarket lists the print as a separate "
        "product under a different set name -- automatic matching shows the "
        "wrong (Western) product there. Paste the correct Cardmarket link "
        "here to fix that."
    ),
    # export_dialog.py
    "Exportieren": "Export",
    "Was:": "What:",
    "Format:": "Format:",
    "Alle Sammlungen": "All collections",
    "Sammlung:": "Collection:",
    # manual_entry_dialog.py
    "Cardmarket-Link:": "Cardmarket link:",
    "Weiter": "Next",
    # catalog_search_results_dialog.py
    "Rarität": "Rarity",
    "Suchergebnisse": "Search results",
    "Keine Treffer.": "No matches.",
    "Hinzufügen": "Add",
    # cardmarket_search_results_dialog.py / cardmarket_search_controller.py
    "Cardmarket-Suchergebnisse": "Cardmarket search results",
    "Suche läuft…": "Searching…",
    "Übernehmen": "Use this",
    "Cardmarket-Link suchen": "Search Cardmarket link",
    "Cardmarket wird durchsucht…": "Searching Cardmarket…",
    "Link wird übernommen…": "Applying link…",
    "Cardmarket-Link gespeichert.": "Cardmarket link saved.",
    # card_list_panel.py
    "Extra": "Extra",
    "Zustand": "Condition",
    "Menge": "Quantity",
    "Preis": "Price",
    # card_list_panel.py -- abbreviated column headers (user request: the
    # narrow Sprache/Zustand/Menge columns truncated the full words).
    "Spr.": "Lang.",
    "Zust.": "Cond.",
    "Anz.": "Qty",
    "Rev. Holo": "Rev. Holo",
    "Sign.": "Signed",
    "Alt.": "Alt.",
    "Karten": "Cards",
    "Karte hinzufügen": "Add card",
    "Karte manuell eintragen": "Add card manually",
    "Karte bearbeiten": "Edit card",
    "Speichern": "Save",
    "Karte löschen": "Delete card",
    "Soll die Karte „{name}“ wirklich aus der Sammlung gelöscht werden?": (
        'Should the card "{name}" really be deleted from the collection?'
    ),
    "Sollen die {count} ausgewählten Karten wirklich aus der Sammlung gelöscht werden?": (
        "Should the {count} selected cards really be deleted from the collection?"
    ),
    "Bearbeiten": "Edit",
    "Löschen": "Delete",
    "Verschieben": "Move",
    "Preis manuell bearbeiten": "Edit price manually",
    "Cardmarket-Link öffnen": "Open Cardmarket link",
    "Keine Cardmarket-Zuordnung für diese Karte bekannt -- Link kann nicht geöffnet werden.": (
        "No Cardmarket link known for this card -- nothing to open."
    ),
    "Cardmarket-Seite geöffnet.": "Cardmarket page opened.",
    "Ein anderer Cardmarket-Vorgang läuft gerade -- bitte kurz warten.": (
        "Another Cardmarket operation is already running -- please wait a moment."
    ),
    "Preis:": "Price:",
    "Der Preis muss größer als 0 sein.": "The price must be greater than 0.",
    "Zielsammlung:": "Target collection:",
    "Es gibt keine andere Sammlung, in die verschoben werden könnte.": (
        "There is no other collection to move this to."
    ),
    # card_detail_panel.py -- field labels (identifiers, also used as dict
    # keys; "Set" is identical in both languages)
    "Kartennummer": "Card number",
    "Preisqualität": "Price quality",
    "Letzte Aktualisierung": "Last updated",
    "Notizen": "Notes",
    "Preis von Cardmarket abrufen": "Fetch price from Cardmarket",
    "Preisverlauf anzeigen": "Show price history",
    "Preisverlauf ausblenden": "Hide price history",
    "Kartendetails": "Card details",
    # models/enums.py -- PriceQuality.label (the only enum whose .label is
    # German prose, not an English technical term like Language/Condition)
    "Exakter Treffer": "Exact match",
    "Geschätzt aus anderem Zustand": "Estimated from a different condition",
    "Geschätzt aus anderer Sprache": "Estimated from a different language",
    "Durchschnitt": "Average",
    "Marktpreis (tcgdex)": "Market price (tcgdex)",
    "Kein Preis gefunden": "No price found",
    "Manuell eingetragen": "Manually set",
    # collection_panel.py
    "Sammlungen": "Collections",
    "+ Neue Sammlung": "+ New collection",
    "Neue Sammlung": "New collection",
    "Name der Sammlung:": "Collection name:",
    "Sammlung umbenennen": "Rename collection",
    "Neuer Name:": "New name:",
    "Sammlung löschen": "Delete collection",
    (
        "Soll die Sammlung „{name}“ wirklich gelöscht werden?\n"
        "Alle enthaltenen Karten werden dabei ebenfalls gelöscht."
    ): (
        'Should the collection "{name}" really be deleted?\n'
        "All cards it contains will be deleted as well."
    ),
    "Umbenennen": "Rename",
    # card_filter_bar.py
    "Alle": "All",
    "Suche (Name, Set, Nummer, Notizen) …": "Search (name, set, number, notes) …",
    "Preis von": "Price from",
    "bis": "to",
    "Zurücksetzen": "Reset",
    # statistics_panel.py
    "noch nie aktualisiert": "never updated",
    "vor {days} Tagen": "{days} days ago",
    "Gesamtpreis-Übersicht": "Total value overview",
    "Sammlung": "Collection",
    "Wert": "Value",
    "Karten mit veraltetem Preis": "Cards with outdated price",
    "Zuletzt aktualisiert": "Last updated",
    "Aktion": "Action",
    "Karten, deren Preis seit mehr als {days} Tagen nicht aktualisiert wurde oder noch nie ermittelt wurde.": (
        "Cards whose price hasn't been updated in more than {days} days, or "
        "was never determined at all."
    ),
    "Wert nach Set": "Value by set",
    "Wert nach Sprache": "Value by language",
    "Wert nach Zustand": "Value by condition",
    "Teuerste Karten": "Most valuable cards",
    "Größte Preissteigerung": "Biggest price increase",
    "Gesamtwert Karten (alle Sammlungen): {value}": "Total card value (all collections): {value}",
    "Gesamtwert (Karten + Sealed-Produkte): {value}": "Total value (cards + sealed products): {value}",
    "{count} Karte(n) · Stand: {as_of}": "{count} card(s) · as of: {as_of}",
    "{count} Stück · Stand: {as_of}": "{count} item(s) · as of: {as_of}",
    "Stand: {as_of} — basiert auf dem zuletzt bekannten Preis je Karte und kann veraltet sein.": (
        "As of: {as_of} — based on the most recently known price per card, "
        "may be outdated."
    ),
    "Preis aktualisieren": "Update price",
    "Alle aktualisieren": "Update all",
    "Keine Karte mit einer Preissteigerung in der Historie gefunden.": (
        "No card with a price increase found in the history."
    ),
    # statistics_panel.py -- sealed products
    "Wert nach Kategorie": "Value by category",
    "Teuerste Sealed-Produkte": "Most valuable sealed products",
    "Sealed-Produkte mit veraltetem Preis": "Sealed products with outdated price",
    "Sealed-Produkte, deren Preis seit mehr als {days} Tagen nicht aktualisiert wurde oder noch nie ermittelt wurde.": (
        "Sealed products whose price hasn't been updated in more than {days} "
        "days, or was never determined at all."
    ),
    # price_history_dock.py
    "Preisverlauf": "Price history",
    "Noch kein Preisverlauf vorhanden.": "No price history yet.",
    "Letzte Aktualisierungen:": "Recent updates:",
    "Historie zurücksetzen": "Reset history",
    "Nur ein Preis bisher: {price} {currency}": "Only one price so far: {price} {currency}",
    "Datum": "Date",
    "Preis (€)": "Price (€)",
    "{sign}{value} % ggü. letzter Aktualisierung": "{sign}{value} % vs. last update",
    "Wirklich den gesamten Preisverlauf dieser Karte löschen? Das kann nicht rückgängig gemacht werden.": (
        "Really delete this card's entire price history? This cannot be undone."
    ),
    # catalog_search_controller.py
    "Bitte Suchbegriff eingeben.": "Please enter a search term.",
    "Suche läuft für „{query}“ …": 'Searching for "{query}" …',
    "{count} Treffer für „{query}“.": '{count} matches for "{query}".',
    "Keine Treffer für „{query}“.": 'No matches for "{query}".',
    "Kartensuche": "Card search",
    # export_controller.py
    "CSV-Datei (*.csv)": "CSV file (*.csv)",
    "Excel-Datei (*.xlsx)": "Excel file (*.xlsx)",
    "JSON-Datei (*.json)": "JSON file (*.json)",
    "PDF-Datei (*.pdf)": "PDF file (*.pdf)",
    "Export fehlgeschlagen": "Export failed",
    "Die Datei konnte nicht geschrieben werden:\n{error}": (
        "The file could not be written:\n{error}"
    ),
    "{count} {unit} nach „{name}“ exportiert.": '{count} {unit} exported to "{name}".',
    "Karte(n)": "card(s)",
    "Sealed-Produkt(e)": "sealed product(s)",
    # price_controller.py
    "Preis wird von Cardmarket abgerufen…": "Fetching price from Cardmarket…",
    "Preis für „{name}“ aktualisiert: {price} {currency}": (
        'Price for "{name}" updated: {price} {currency}'
    ),
    "Kein Preis für „{name}“ gefunden.": 'No price found for "{name}".',
    # manual_entry_controller.py
    "Bitte zuerst eine Sammlung auswählen.": "Please select a collection first.",
    "Cardmarket-Seite wird gelesen…": "Reading Cardmarket page…",
    # exceptions.py
    "Eine Sammlung mit dem Namen „{name}“ existiert bereits.": (
        'A collection named "{name}" already exists.'
    ),
    "Sammlung mit ID {id} wurde nicht gefunden.": "Collection with id {id} was not found.",
    "Karte mit ID {id} wurde nicht gefunden.": "Card with id {id} was not found.",
    "Sealed-Produkt mit ID {id} wurde nicht gefunden.": (
        "Sealed product with id {id} was not found."
    ),
    # collection_service.py
    "Der Name einer Sammlung darf nicht leer sein.": "A collection name cannot be empty.",
    "Der Name darf höchstens {max_length} Zeichen lang sein.": (
        "The name may be at most {max_length} characters long."
    ),
    # card_service.py
    "Die Menge muss mindestens {min_quantity} betragen.": (
        "The quantity must be at least {min_quantity}."
    ),
    # browser_price_reader.py
    (
        "Google Chrome wurde nicht gefunden. Bitte installiere Chrome "
        r"(erwarteter Pfad: ...\Google\Chrome\Application\chrome.exe)."
    ): (
        "Google Chrome was not found. Please install Chrome "
        r"(expected path: ...\Google\Chrome\Application\chrome.exe)."
    ),
    "Cardmarket-Tab für „{hint}“ wurde nicht rechtzeitig gefunden.": (
        'Cardmarket tab for "{hint}" was not found in time.'
    ),
    "Die Seite wurde nicht als Cardmarket-Produktseite erkannt. Bitte prüfe den Link.": (
        "The page was not recognised as a Cardmarket product page. Please check the link."
    ),
    "Keine Angebote auf der Cardmarket-Seite für „{hint}“ erkannt.": (
        'No offers detected on the Cardmarket page for "{hint}".'
    ),
    "Sealed-Produkt eintragen": "Add sealed product",
    # card_artwork_view.py
    "Kein Foto": "No photo",
    # price_service.py
    "Geschätzt aus {language}, Zustand {found_condition} statt {expected_condition}.": (
        "Estimated from {language}, condition {found_condition} instead of "
        "{expected_condition}."
    ),
    "Geschätzt aus {found_language} statt {expected_language}, gleicher Zustand ({condition}).": (
        "Estimated from {found_language} instead of {expected_language}, "
        "same condition ({condition})."
    ),
    "Durchschnitt über alle gefundenen Angebote, unabhängig von Zustand und Sprache.": (
        "Average over all offers found, regardless of condition and language."
    ),
    (
        "Automatische Preisermittlung für {language} wird nicht unterstützt "
        "(Cardmarket führt diesen Druck als eigenständiges Produkt). Trage "
        "unter „Eigener Cardmarket-Link“ den korrekten Link ein, um die "
        "Preisermittlung für diese Karte zu aktivieren."
    ): (
        "Automatic price lookup for {language} is not supported (Cardmarket "
        "lists this print as a separate product). Enter the correct link "
        'under "Custom Cardmarket link" to enable price lookups for this card.'
    ),
    (
        "{set_name} führt mehrere Druckvarianten (z. B. Normal/Shadowless) "
        "als getrennte Cardmarket-Produkte, die pokemontcg.io nicht "
        "auseinanderhält. Trage unter „Eigener Cardmarket-Link“ den "
        "korrekten Link für die Version ein, die du besitzt."
    ): (
        "{set_name} lists multiple print variants (e.g. Normal/Shadowless) "
        "as separate Cardmarket products that pokemontcg.io can't tell "
        'apart. Enter the correct link for the version you own under '
        '"Custom Cardmarket link".'
    ),
    "Keine Cardmarket-Zuordnung für diese Karte bekannt.": (
        "No Cardmarket link known for this card."
    ),
    "Mögliche Bezeichnung auf Cardmarket (via tcgdex.dev): „{card_name}“, Set „{set_name}“, Nr. {local_id}.": (
        'Possible Cardmarket designation (via tcgdex.dev): "{card_name}", '
        'set "{set_name}", no. {local_id}.'
    ),
    # sealed_price_service.py
    "Keine Cardmarket-Zuordnung für dieses Produkt bekannt.": (
        "No Cardmarket link known for this product."
    ),
    "unbekannter Sprache": "unknown language",
    "Geschätzt aus {found}, gewünscht war {expected}.": (
        "Estimated from {found}, {expected} was wanted."
    ),
    "Keine Angebote auf Cardmarket gefunden.": "No offers found on Cardmarket.",
    # sealed_product_list_panel.py
    "Name": "Name",
    "Kategorie": "Category",
    "Sealed-Produkte": "Sealed products",
    "+ Sealed-Produkt hinzufügen": "+ Add sealed product",
    "Sealed-Produkt bearbeiten": "Edit sealed product",
    "Sealed-Produkt löschen": "Delete sealed product",
    "Soll das Sealed-Produkt „{name}“ wirklich gelöscht werden?": (
        'Should the sealed product "{name}" really be deleted?'
    ),
    "Sollen die {count} ausgewählten Sealed-Produkte wirklich gelöscht werden?": (
        "Should the {count} selected sealed products really be deleted?"
    ),
}


def tr(text: str) -> str:
    """Translate ``text`` (written in German) to English."""
    return _EN.get(text, text)
