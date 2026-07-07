"""Dialog with two tabs: app info/credits, and a help/tutorial guide.

Used to also have a UI language switcher tab, but the app is English-only
now -- that whole tab was replaced with the help guide, since neither needs
anything persisted across dialog opens.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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

#: The help/tutorial content, as HTML. English-only (no tr() wrapping) since
#: this is new content written after the app dropped its DE/EN toggle -- no
#: point running it through a translation table that only ever produces
#: English anyway. Short section headers with one or two full sentences
#: each: enough to read as proper documentation rather than shorthand notes,
#: while still staying scannable -- a wall of text is just as offputting as
#: no explanation at all. Anyone wanting more detail can still find it in
#: PROJECT_PROGRESS.md/CHANGELOG.md.
_HELP_HTML = """
<h2>Cards</h2>

<h3>Getting started</h3>
<p>Use <b>Search</b> to add a card from the pokemontcg.io catalog. If a card
isn't found there (very new releases, some promos, or a Base Set variant),
use <b>"Add via Cardmarket link"</b> instead and paste the product's
Cardmarket URL directly.</p>

<h3>Foreign-language prints</h3>
<p>Cardmarket filters most languages (English, German, French, Spanish,
Italian, Portuguese) directly on a card's product page, and the app applies
that filter automatically. Japanese, Korean, and Traditional Chinese prints
are listed as entirely separate Cardmarket products with no such filter —
for these, copy the link from that language's own Cardmarket page.</p>

<h3>Base Set: Normal vs. Shadowless</h3>
<p>Base Set cards were printed in two Cardmarket-distinct variants, Normal
and Shadowless. Searching the catalog for a Base Set card shows both as
separate results, already linked to the correct Cardmarket product — pick
the one you actually own.</p>

<h3>Correcting a price</h3>
<p>If a seller mislabeled their listing on Cardmarket, right-click a card
and choose <b>"Edit price manually"</b> to set the price yourself.</p>

<h2>Sealed products</h2>

<h3>Adding a sealed product</h3>
<p>Add a sealed product from the Sealed tab by pasting its Cardmarket URL.
Sealed products aren't assigned to a collection, since they aren't
typically organized that way physically.</p>

<h2>Wantlist</h2>

<h3>Tracking a target price</h3>
<p>Track cards you don't own yet against a target price from the Wantlist
tab. "Check all prices" looks each one up on Cardmarket (like a card's own
"Update price"), and flags any that have reached your target.</p>

<h2>Statistics</h2>

<h3>Value over time</h3>
<p>The chart at the top of the Statistics tab shows the combined value of
your whole collection (cards + sealed products) over time, based on every
price update ever recorded — not just a single card's own history.</p>

<h2>General</h2>

<h3>Updating prices</h3>
<p>Click "Update price" on a card or sealed product to fetch its current
Cardmarket price. In the Statistics tab, "Update all" refreshes every price
that's more than a month old (or was never determined) in one go.</p>

<h3>Price history</h3>
<p>Every price update is recorded, not just the latest value. Open "Price
history" in a card's or sealed product's detail panel to see how its value
has changed over time.</p>

<h3>Export &amp; Import</h3>
<p>"Export" saves your cards or sealed products to a CSV, Excel, JSON, or
PDF file. "Import" reads them back from a CSV, Excel, or JSON file in that
same layout — handy for re-importing an edited export, or a spreadsheet you
already keep. Imported items start without a price, same as adding one by
hand; rows that can't be parsed (missing name, unrecognized language, ...)
are skipped and listed instead of stopping the whole import.</p>

<h3>Backups</h3>
<p>The database is backed up automatically before each update, at most once
every 24 hours — no action required. Use "Restore from backup…" below to
roll back to an earlier one if something goes wrong.</p>

<h3>Update notifications</h3>
<p>On startup, the app checks GitHub in the background for a newer release.
If one exists, a link appears in the status bar — nothing is downloaded or
installed automatically.</p>
"""


class SettingsDialog(DimmedDialog):
    """Shows app info/credits and a help/tutorial guide."""

    #: Emitted when "Restore from backup..." is clicked; the actual dialog
    #: and restore logic live in :class:`~app.ui.controllers.
    #: backup_controller.BackupController`.
    restore_backup_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Infos und Einstellungen"))
        self.resize(560, 480)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_info_tab(), tr("Info"))
        tabs.addTab(self._build_help_tab(), "Help")
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

        author = QLabel(
            'Created by Codeon — <a href="https://github.com/codeonexe">GitHub</a>'
        )
        author.setTextFormat(Qt.TextFormat.RichText)
        author.setOpenExternalLinks(True)
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

    def _build_help_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(_HELP_HTML)
        layout.addWidget(browser)

        return widget
