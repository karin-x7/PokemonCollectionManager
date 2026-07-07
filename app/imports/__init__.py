"""Importing owned cards/sealed products from CSV/Excel/JSON files.

The counterpart to ``app.export``: reads a file written in (or matching)
that same column layout and adds each row as a brand-new owned card/sealed
product -- mirrors the "add manually" flow (identity fields only), not a
price update. A freshly imported item has no price yet, same as a card
added by hand via a Cardmarket link; the existing "Preis aktualisieren"
button fetches a real one afterward. PDF has no importer -- it's a
rendered, one-way document, not a reasonable re-import source.
"""
