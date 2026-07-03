"""Background worker for a single Cardmarket price lookup.

Runs in its own ``QThread`` so opening/reading/closing a browser tab (which
can take several seconds) doesn't freeze the GUI. Deliberately scoped to
exactly **one** card per run, started by exactly one user click — no batch or
loop over multiple cards (see the "Architektur-Entscheidung" in
PROJECT_PROGRESS.md for why).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from app.database.connection import Database
from app.logging_config import get_logger
from app.services.exceptions import ServiceError
from app.services.price_service import PriceService

logger = get_logger(__name__)

#: Returns a fresh ``PriceService`` plus the ``Database`` connection backing
#: it (or ``None`` if the service doesn't own one, e.g. a test fake) — called
#: from *this* worker's own thread, never the caller's. SQLite connections
#: cannot be used from a thread other than the one that created them, so a
#: ``PriceService`` built on the GUI thread must never be reused here; each
#: run opens its own connection to the same database file and closes it when
#: done.
OpenPriceService = Callable[[], tuple[PriceService, Database | None]]


class PriceLookupWorker(QThread):
    """Looks up and persists the Cardmarket price for exactly one card."""

    #: Emitted with the updated Card on completion — including when no price
    #: could be determined (that's a normal, tolerant outcome, not a failure).
    succeeded = Signal(object)
    #: Emitted with a friendly message when the card itself couldn't be found.
    failed = Signal(str)

    def __init__(self, open_service: OpenPriceService, card_id: int, parent=None) -> None:
        super().__init__(parent)
        self._open_service = open_service
        self._card_id = card_id

    def run(self) -> None:  # noqa: D102 — QThread override
        service, database = self._open_service()
        try:
            card = service.update_price_for_card(self._card_id)
        except ServiceError as exc:
            logger.error("Price lookup failed for card id=%s: %s", self._card_id, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception("Unexpected error during price lookup for card id=%s", self._card_id)
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        finally:
            if database is not None:
                database.close()
        self.succeeded.emit(card)
