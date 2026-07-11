"""Dialog with three tabs: FAQ, help/tutorial guide, and app info/credits.

Used to also have a UI language switcher tab, but the app is English-only
now -- that whole tab was replaced with the help guide, since neither needs
anything persisted across dialog opens.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.i18n import tr
from app.ui.dialogs.dimmed_dialog import DimmedDialog
from app.ui.theme import PALETTE

#: Third-party data sources/libraries this app relies on, shown as credits.
_CREDITS = (
    ("pokemontcg.io", "Catalog data (card names/sets/images) and Cardmarket linking"),
    ("Cardmarket", "Market prices (read from the browser window, see PROJECT_PROGRESS.md)"),
    ("PokeAPI", "Foreign-language Pokémon names for the bilingual search"),
    ("PySide6 (Qt for Python)", "GUI framework"),
    ("openpyxl", "Excel export"),
    ("reportlab", "PDF export"),
    ("pywinauto / pywin32", "Windows window reading for the Cardmarket price lookup"),
)

#: Base font size for both the Help and FAQ QTextBrowsers -- live-requested
#: to be noticeably bigger than the app's own default widget font, since
#: this dialog is read-heavy prose rather than compact UI chrome.
_HELP_FONT_POINT_SIZE = 15

#: Every clickable entry in Help's own "Contents" index at the top, and the
#: only place these anchor names are allowed to be listed loose like this --
#: every other appearance of one of these strings is either the ``<a
#: name="...">`` it points at (in ``_HELP_HTML``) or a ``href="help:#..."``
#: cross-link from ``_FAQ_HTML``. Kept as one flat tuple-of-tuples (category,
#: [(anchor, label), ...]) so the index and the section anchors can't drift
#: apart from each other silently -- a typo in either place would show up
#: immediately as a dead link when clicked.
_HELP_INDEX: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Collections", (("collections-organizing", "Organizing your cards"),)),
    (
        "Cards",
        (
            ("cards-getting-started", "Getting started"),
            ("cards-search-accuracy", "Search accuracy"),
            ("cards-duplicate-warning", "Possible-duplicate warning"),
            ("cards-foreign-language", "Foreign-language prints"),
            ("cards-base-set", "Base Set: Normal vs. Shadowless"),
            ("cards-filtering", "Filtering and searching your list"),
            ("cards-sorting-selecting", "Sorting and selecting"),
            ("cards-moving", "Moving cards between collections"),
            ("cards-correcting-price", "Correcting a price"),
            ("cards-fix-link", "Fixing a missing or wrong Cardmarket link"),
            ("cards-browsing", "Browsing a card's Cardmarket page yourself"),
        ),
    ),
    (
        "Sealed products",
        (
            ("sealed-adding", "Adding a sealed product"),
            ("sealed-editing", "Editing, deleting, and sorting"),
        ),
    ),
    (
        "Wantlist",
        (
            ("wantlist-tracking", "Tracking a target price"),
            ("wantlist-convert", "Turning a want into an owned card"),
        ),
    ),
    (
        "Statistics",
        (
            ("stats-value-over-time", "Value over time"),
            ("stats-overview", "Overview and breakdowns"),
            ("stats-most-expensive", "Most expensive and biggest movers"),
            ("stats-keeping-current", "Keeping prices current"),
        ),
    ),
    (
        "General",
        (
            ("general-updating-prices", "Updating prices"),
            ("general-price-history", "Price history"),
            ("general-export-import", "Export &amp; Import"),
            ("general-backups", "Backups"),
            ("general-update-notifications", "Update notifications"),
        ),
    ),
)


def _build_help_index_html() -> str:
    parts = ["<h3>Contents</h3>"]
    for category, entries in _HELP_INDEX:
        parts.append(f"<p><b>{category}</b></p><ul>")
        parts.extend(f'<li><a href="#{anchor}">{label}</a></li>' for anchor, label in entries)
        parts.append("</ul>")
    parts.append("<hr>")
    return "\n".join(parts)


#: The help/tutorial content, as HTML. English-only (no tr() wrapping) since
#: this is new content written after the app dropped its DE/EN toggle -- no
#: point running it through a translation table that only ever produces
#: English anyway. Short section headers with one or two full sentences
#: each: enough to read as proper documentation rather than shorthand notes,
#: while still staying scannable -- a wall of text is just as offputting as
#: no explanation at all. Anyone wanting more detail can still find it in
#: PROJECT_PROGRESS.md/CHANGELOG.md. Every ``<h2>``/``<h3>`` has a matching
#: ``<a name="...">`` right before it so the index above (and FAQ's own
#: cross-links) can jump straight to it.
#: Extra top margin on every Help category (h2) and feature entry (h3) --
#: live-requested, same reasoning as FAQ's own spacing: a long document of
#: back-to-back short entries reads as cramped without it. Categories get a
#: bigger gap than individual entries within one, so the hierarchy stays
#: visible at a glance.
_HELP_CATEGORY_STYLE = 'style="margin-top: 40px;"'
_HELP_SECTION_STYLE = 'style="margin-top: 22px;"'

_HELP_HTML = (
    _build_help_index_html()
    + f"""
<a name="collections-organizing"></a>
<h2 {_HELP_CATEGORY_STYLE}>Collections</h2>

<h3 {_HELP_SECTION_STYLE}>Organizing your cards</h3>
<p>The panel on the left of the Cards tab lists your collections. "+ New
collection" creates one; double-click a name (or right-click →
"Rename") to rename it; right-click → "Delete" removes it and every card
inside, with a warning first. Drag a collection up or down in the list to
reorder it.</p>

<a name="cards-getting-started"></a>
<h2 {_HELP_CATEGORY_STYLE}>Cards</h2>

<h3 {_HELP_SECTION_STYLE}>Getting started</h3>
<p>Use <b>Search</b> to add a card from the pokemontcg.io catalog. If a card
isn't found there (very new releases, some promos, or a Base Set variant),
use <b>"Add via Cardmarket link"</b> instead and paste the product's
Cardmarket URL directly — its name, set, and card number are read off the
page and can still be corrected by hand before saving.</p>

<a name="cards-search-accuracy"></a>
<h3 {_HELP_SECTION_STYLE}>Search accuracy</h3>
<p>Search also tolerates typos and card names in German, French, Spanish,
Italian, or Portuguese, but this multi-language matching is best-effort,
not guaranteed — an unusual name, a very new set, or an uncommon
abbreviation may still need to be searched in English, or added via
<b>"Add via Cardmarket link"</b> instead.</p>

<a name="cards-duplicate-warning"></a>
<h3 {_HELP_SECTION_STYLE}>Possible-duplicate warning</h3>
<p>Adding a card that already matches one you own (same set, number,
language, and condition) shows how many copies you already have and in
which collection, and asks whether to add another anyway — useful for
catching an accidental double-entry.</p>

<a name="cards-foreign-language"></a>
<h3 {_HELP_SECTION_STYLE}>Foreign-language prints</h3>
<p>Cardmarket filters every language — including Japanese, Korean, and
Traditional Chinese — directly on a card's product page, and the app
applies that filter automatically. A small number of older/reprint sets
list a language as an entirely separate product under an unrelated name
instead (e.g. a vintage set's Japanese print); if automatic pricing can't
find any matching offers at all, paste that language's own Cardmarket
product link via "Edit" instead.</p>

<a name="cards-base-set"></a>
<h3 {_HELP_SECTION_STYLE}>Base Set: Normal vs. Shadowless</h3>
<p>Base Set cards were printed in two Cardmarket-distinct variants, Normal
and Shadowless. Searching the catalog for a Base Set card shows both as
separate results, already linked to the correct Cardmarket product — pick
the one you actually own.</p>

<a name="cards-filtering"></a>
<h3 {_HELP_SECTION_STYLE}>Filtering and searching your list</h3>
<p>The filter bar above the card table narrows it by free text (name, set,
number, or notes), Set, Language, Condition, or a min/max price range.
"All collections" searches across every collection at once instead of just
the selected one; "Reset" clears every filter in one click.</p>

<a name="cards-sorting-selecting"></a>
<h3 {_HELP_SECTION_STYLE}>Sorting and selecting</h3>
<p>Click any column header to sort by it, and again to reverse the order.
Shift-click or Ctrl-click rows to select several at once for "Move" or
"Delete" — actions that only make sense for a single card (Edit, Edit price
manually, Open/Fix Cardmarket link) are hidden while more than one row is
selected.</p>

<a name="cards-moving"></a>
<h3 {_HELP_SECTION_STYLE}>Moving cards between collections</h3>
<p>Right-click one or more selected cards and choose "Move" to relocate
them to a different collection.</p>

<a name="cards-correcting-price"></a>
<h3 {_HELP_SECTION_STYLE}>Correcting a price</h3>
<p>If a seller mislabeled their listing on Cardmarket, right-click a card
and choose <b>"Edit price manually"</b> to set the price yourself.</p>

<a name="cards-fix-link"></a>
<h3 {_HELP_SECTION_STYLE}>Fixing a missing or wrong Cardmarket link</h3>
<p>If a card has no Cardmarket link (or the wrong one), click "Search
Cardmarket link" in its detail panel, or right-click it in the list and
choose "Fix Cardmarket link". This searches Cardmarket's own site for the
card's
name and shows a picker of candidates; picking one and confirming the
resolved link saves it. If nothing turns up automatically, an "Open
Cardmarket search in browser" button opens the same search in a normal
browser window so you can look yourself and, once found, paste the link in
via "Edit" instead.</p>

<a name="cards-browsing"></a>
<h3 {_HELP_SECTION_STYLE}>Browsing a card's Cardmarket page yourself</h3>
<p>"Update price" opens Cardmarket in the background, reads the price, and
closes the tab automatically — it never stays open for you to look at. To
browse the listing yourself (check seller comments, photos, other offers,
...), right-click a card and choose <b>"Open Cardmarket link"</b> instead:
this opens the same page in a normal, full-sized Chrome window and leaves
it open.</p>

<a name="sealed-adding"></a>
<h2 {_HELP_CATEGORY_STYLE}>Sealed products</h2>

<h3 {_HELP_SECTION_STYLE}>Adding a sealed product</h3>
<p>Add a sealed product from the Sealed tab by pasting its Cardmarket URL.
Sealed products aren't assigned to a collection, since they aren't
typically organized that way physically.</p>

<a name="sealed-editing"></a>
<h3 {_HELP_SECTION_STYLE}>Editing, deleting, and sorting</h3>
<p>Right-click a sealed product to edit its details (including its category
or a manual Cardmarket-link override) or delete it — Shift/Ctrl-click first
to act on several at once. Click any column header to sort, same as the
card table. The "Total" column shows unit price × quantity, so owning
several copies of the same product is visible at a glance.</p>

<a name="wantlist-tracking"></a>
<h2 {_HELP_CATEGORY_STYLE}>Wantlist</h2>

<h3 {_HELP_SECTION_STYLE}>Tracking a target price</h3>
<p>Track cards you don't own yet against a target price from the Wantlist
tab: "+ Add to wantlist" takes a Cardmarket link plus your language,
condition, target price, and notes, then fills in the name/set/number
automatically. "Check all prices" looks every entry up on Cardmarket (like
a card's own "Update price") and flags any that have reached your target
with a highlighted "Below target!" status; right-click a single entry to
check just that one, edit its details, or remove it.</p>

<a name="wantlist-convert"></a>
<h3 {_HELP_SECTION_STYLE}>Turning a want into an owned card</h3>
<p>Once you've actually bought a wanted card, right-click it and choose
"Add to collection" — pick a destination collection and it's added there as
an owned card and removed from the wantlist.</p>

<a name="stats-value-over-time"></a>
<h2 {_HELP_CATEGORY_STYLE}>Statistics</h2>

<h3 {_HELP_SECTION_STYLE}>Value over time</h3>
<p>The chart at the top of the Statistics tab shows the combined value of
your whole collection (cards + sealed products) over time, based on every
price update ever recorded — not just a single card's own history. Hover a
point to see its exact date and value.</p>

<a name="stats-overview"></a>
<h3 {_HELP_SECTION_STYLE}>Overview and breakdowns</h3>
<p>Summary tiles show your combined card and sealed-product counts and
values. Below that, tables break the total down per collection, and by Set,
Language, and Condition for cards (Category for sealed products) — click a
table's headers to sort it.</p>

<a name="stats-most-expensive"></a>
<h3 {_HELP_SECTION_STYLE}>Most expensive and biggest movers</h3>
<p>Separate tables list your most valuable cards and sealed products, and
highlight the single card with the biggest jump between its two most
recent price updates (with the before/after price and percent change).</p>

<a name="stats-keeping-current"></a>
<h3 {_HELP_SECTION_STYLE}>Keeping prices current</h3>
<p>The "Cards/Sealed products with an outdated price" lists show anything
stale or never priced; use a row's own update button for just that item, or
"Update all" to refresh everything in the list at once.</p>

<a name="general-updating-prices"></a>
<h2 {_HELP_CATEGORY_STYLE}>General</h2>

<h3 {_HELP_SECTION_STYLE}>Updating prices</h3>
<p>Click "Update price" on a card or sealed product to fetch its current
Cardmarket price. In the Statistics tab, "Update all" refreshes every price
that's more than a month old (or was never determined) in one go.</p>

<a name="general-price-history"></a>
<h3 {_HELP_SECTION_STYLE}>Price history</h3>
<p>Every price update is recorded, not just the latest value. Open "Price
history" in a card's or sealed product's detail panel to see how its value
has changed over time — hover a point on the chart for its exact date and
price, or use "Reset history" there to permanently erase all of it (this
cannot be undone).</p>

<a name="general-export-import"></a>
<h3 {_HELP_SECTION_STYLE}>Export &amp; Import</h3>
<p>"Export" saves your cards or sealed products to a CSV, Excel, JSON, or
PDF file, scoped to one collection or "All collections" (sealed products
aren't collection-scoped). "Import" reads them back from a CSV, Excel, or
JSON file in that same layout — handy for re-importing an edited export, or
a spreadsheet you already keep. Imported items start without a price, same
as adding one by hand; rows that can't be parsed (missing name,
unrecognized language, ...) are skipped and listed instead of stopping the
whole import.</p>

<a name="general-backups"></a>
<h3 {_HELP_SECTION_STYLE}>Backups</h3>
<p>The database is backed up automatically before each update, at most once
every 24 hours — no action required. Use "Restore from backup…" below to
pick from the list of past backups (by date and file size) and roll back to
one; the current database is itself backed up first, and the app needs to
be restarted afterward to show the restored data.</p>

<a name="general-update-notifications"></a>
<h3 {_HELP_SECTION_STYLE}>Update notifications</h3>
<p>On startup, the app checks GitHub in the background for a newer release.
If one exists, a link appears in the status bar — nothing is downloaded or
installed automatically.</p>
"""
)

#: FAQ content, in the same short-question/short-answer style as the Help
#: tab above -- live-requested to surface the "why doesn't this just work
#: automatically"-type questions a plain feature list tends to skip over.
#: Where a question maps onto a specific Help topic, a "See also" line links
#: straight to it via the ``help:#anchor`` scheme :meth:`SettingsDialog.
#: _on_anchor_clicked` intercepts -- switches to the Help tab and scrolls to
#: that anchor, rather than trying to open "help:" as a real URL.
#: Extra top margin on every FAQ question (beyond Help's own, tighter
#: default h3 spacing) -- live-requested: FAQ questions felt too cramped
#: together, since each entry already carries its own answer *and* a
#: "See also" line, unlike Help's shorter single-paragraph entries.
_FAQ_QUESTION_STYLE = 'style="margin-top: 32px;"'

_FAQ_HTML = f"""
<h3 {_FAQ_QUESTION_STYLE}>Why doesn't everything work automatically?</h3>
<p>Cardmarket has no public API, so prices are read by automating a real
browser window against the actual site — that's inherently slower and more
fragile than a direct API call, and it's why a search for the exact right
product, language, and condition sometimes needs a nudge from you (picking
a candidate, pasting a link) instead of just happening on its own.</p>
<p><i>See also: <a href="help:#general-updating-prices">Updating prices</a>
in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>How do I add a Japanese, Korean, or Traditional Chinese card?</h3>
<p>The same way as any other card — Cardmarket filters these languages
automatically, just like German or French. If automatic pricing still
finds nothing (a small number of older/reprint sets list these as an
entirely separate product), paste that language's own Cardmarket product
link via <b>"Add via Cardmarket link"</b> (or "Edit" → Cardmarket link for
a card you already own) instead.</p>
<p><i>See also: <a href="help:#cards-foreign-language">Foreign-language
prints</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>Why did search not find my card?</h3>
<p>Multi-language, typo-tolerant search is best-effort — an unusual name, a
very new set, or an uncommon abbreviation may not match. Try the plain
English name, or add the card via its Cardmarket link instead.</p>
<p><i>See also: <a href="help:#cards-search-accuracy">Search accuracy</a>
in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>Why is a price missing or marked as outdated?</h3>
<p>A price is "outdated" once it's more than a month old, or missing if it
was never looked up. Click "Update price" on the card or sealed product (or
"Update all" in Statistics) to refresh it.</p>
<p><i>See also: <a href="help:#general-updating-prices">Updating prices</a>
in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>The Cardmarket link is wrong or missing — how do I fix it?</h3>
<p>Click "Search Cardmarket link" in the card's detail panel, or right-click
it in the list and choose "Fix Cardmarket link", to search and confirm the
correct product. If nothing turns up, use the "Open Cardmarket search in
browser" fallback to search yourself, then paste the link in via "Edit".</p>
<p><i>See also: <a href="help:#cards-fix-link">Fixing a missing or wrong
Cardmarket link</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>How accurate are the prices really?</h3>
<p>Prices come straight from live Cardmarket listings, matched to your
card's exact language and condition where possible. When no listing exists
for that exact combination, the app estimates from the closest available
match and always shows what it was estimated from, rather than presenting
a guess as if it were exact.</p>
<p><i>See also: <a href="help:#cards-correcting-price">Correcting a
price</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>How do I move cards between collections?</h3>
<p>Select one or more cards (Shift/Ctrl-click for several), right-click,
and choose "Move".</p>
<p><i>See also: <a href="help:#cards-moving">Moving cards between
collections</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>Can I select and act on multiple cards at once?</h3>
<p>Yes — Shift-click or Ctrl-click rows in the card or sealed-product list
to select several, then "Move" or "Delete" all of them together.</p>
<p><i>See also: <a href="help:#cards-sorting-selecting">Sorting and
selecting</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>What's the Wantlist for?</h3>
<p>Track cards you don't own yet against a target price. "Check all prices"
looks every entry up on Cardmarket and flags any that have reached your
target; once you've bought one, "Add to collection" turns it into an owned
card.</p>
<p><i>See also: <a href="help:#wantlist-tracking">Tracking a target
price</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>What happens if something goes wrong — do I have a backup?</h3>
<p>Yes — the database is backed up automatically before every update, at
most once every 24 hours. Use "Restore from backup…" in the Info tab to
roll back to an earlier one.</p>
<p><i>See also: <a href="help:#general-backups">Backups</a> in Help.</i></p>

<h3 {_FAQ_QUESTION_STYLE}>Does the app run on Mac or Linux?</h3>
<p>Not currently — it's Windows-only for now.</p>
"""


class SettingsDialog(DimmedDialog):
    """Shows a FAQ, help/tutorial guide, and app info/credits."""

    #: Emitted when "Restore from backup..." is clicked; the actual dialog
    #: and restore logic live in :class:`~app.ui.controllers.
    #: backup_controller.BackupController`.
    restore_backup_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Infos und Einstellungen"))
        self.resize(820, 700)
        self._help_browser: QTextBrowser | None = None
        self._faq_browser: QTextBrowser | None = None
        self._tabs: QTabWidget | None = None
        self._help_tab_index = 0
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self._tabs = tabs
        tabs.addTab(self._build_faq_tab(), "FAQ")
        self._help_tab_index = tabs.addTab(self._build_help_tab(), "Help")
        tabs.addTab(self._build_info_tab(), tr("Info"))
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _build_info_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel(config.APP_NAME)
        title.setObjectName("PanelHeader")
        layout.addWidget(title)

        version = QLabel(f"{tr('Version')} {config.APP_VERSION}")
        layout.addWidget(version)

        author = QLabel("Created by Karin")
        layout.addWidget(author)

        credits_header = QLabel(tr("Quellen und Bibliotheken"))
        credits_header.setStyleSheet("font-weight: bold; margin-top: 12px;")
        layout.addWidget(credits_header)

        for name, description in _CREDITS:
            entry = QLabel(f"<b>{name}</b> — {description}")
            entry.setWordWrap(True)
            entry.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(entry)

        backups_header = QLabel("Backups")
        backups_header.setStyleSheet("font-weight: bold; margin-top: 12px;")
        layout.addWidget(backups_header)

        backups_description = QLabel(
            "The database is backed up automatically before each update. "
            "Restore an earlier backup if something went wrong."
        )
        backups_description.setWordWrap(True)
        layout.addWidget(backups_description)

        self._restore_backup_button = QPushButton("Restore from backup…")
        self._restore_backup_button.clicked.connect(self.restore_backup_requested)
        layout.addWidget(self._restore_backup_button)

        layout.addStretch(1)
        return widget

    def _make_browser(self, html: str) -> QTextBrowser:
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        # Internal anchor jumps (within-tab "#foo" and cross-tab "help:#foo")
        # are both handled by hand in ``_on_anchor_clicked`` instead of Qt's
        # own auto-navigation -- otherwise QTextBrowser tries to load
        # "help:#foo" as a brand new document source and fails, since it
        # isn't a real, loadable URL.
        browser.setOpenLinks(False)
        browser.anchorClicked.connect(lambda url, b=browser: self._on_anchor_clicked(b, url))
        font = QFont(browser.font())
        font.setPointSize(_HELP_FONT_POINT_SIZE)
        browser.setFont(font)
        # setFont() alone is silently overridden: theme.py's app-wide
        # "QMainWindow, QWidget { font-size: 10pt; }" QSS rule applies to
        # every QWidget including this one, and a stylesheet's font-size
        # always wins over a plain QWidget.setFont() call once *any*
        # stylesheet is set anywhere up the ancestor chain (here, on the
        # QApplication itself) -- live-reported: the font-size bump had no
        # visible effect until this per-widget override was added. A
        # widget's *own* stylesheet outranks an ancestor's for its own
        # properties, so this is what actually takes effect.
        browser.setStyleSheet(f"font-size: {_HELP_FONT_POINT_SIZE}pt;")
        # QWidget-level setStyleSheet() (Qt Style Sheets) doesn't reach the
        # anchor color inside the rendered HTML -- the document's own CSS
        # subset (setDefaultStyleSheet) is what actually colors ``<a>`` tags,
        # and must be set before setHtml() parses the content. Without this,
        # links render in the OS's own default link color (live-reported:
        # Windows' system green) instead of the app's own orange accent.
        browser.document().setDefaultStyleSheet(f"a {{ color: {PALETTE.accent}; }}")
        browser.setHtml(html)
        return browser

    def _build_help_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = self._make_browser(_HELP_HTML)
        self._help_browser = browser
        layout.addWidget(browser)

        return widget

    def _build_faq_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = self._make_browser(_FAQ_HTML)
        self._faq_browser = browser
        layout.addWidget(browser)

        return widget

    def _on_anchor_clicked(self, browser: QTextBrowser, url: QUrl) -> None:
        anchor = url.fragment()
        if not anchor:
            return
        if url.scheme() == "help":
            if self._tabs is not None and self._help_browser is not None:
                self._tabs.setCurrentIndex(self._help_tab_index)
                self._help_browser.scrollToAnchor(anchor)
            return
        browser.scrollToAnchor(anchor)
