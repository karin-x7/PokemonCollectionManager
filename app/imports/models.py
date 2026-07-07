"""Data shapes shared by every import format.

Mirrors ``app.export.models``: a flat, still-raw-text snapshot of one row --
each reader (CSV/Excel/JSON) only ever produces these, so
:class:`~app.services.import_service.ImportService` has exactly one place
that parses/validates language, condition, quantity, etc., regardless of
which file format they came from.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportedCardRow:
    """One prospective owned card, still as raw text -- unvalidated."""

    collection_name: str
    name: str
    set_name: str
    card_number: str
    language: str
    condition: str
    extras: str
    quantity: str
    notes: str
    cardmarket_url: str


@dataclass(frozen=True, slots=True)
class ImportedSealedRow:
    """One prospective owned sealed product, still as raw text -- unvalidated."""

    name: str
    category: str
    language: str
    quantity: str
    notes: str
    cardmarket_url: str


@dataclass(frozen=True, slots=True)
class ImportRowError:
    """A single row that couldn't be imported, with a human-readable reason.

    ``row_number`` is 1-based counting the header as row 1 (matches what a
    user sees when opening the file in a spreadsheet program).
    """

    row_number: int
    message: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Outcome of one import run: how many rows made it in, and why any didn't."""

    imported_count: int
    errors: list[ImportRowError]


class ImportFileError(Exception):
    """Raised when the file itself can't be read/parsed (wrong format, corrupt, ...)."""
