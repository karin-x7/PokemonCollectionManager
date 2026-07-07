"""Background worker for the "Open Cardmarket link" context-menu action.

Mirrors :class:`~app.ui.workers.price_lookup_worker.PriceLookupWorker`'s
own threading setup (resolving the URL can involve a network round-trip to
follow pokemontcg.io's tracking shortlink, and a fresh ``Database``
connection per run since SQLite connections can't cross threads) -- but
unlike that worker, opening the resolved URL in Chrome is fire-and-forget:
there is no window to wait for, read, or close, so this finishes almost
immediately once the URL is known.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from app.database.connection import Database
from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, open_cardmarket_link
from app.services.exceptions import ServiceError
from app.services.price_service import PriceService

logger = get_logger(__name__)

#: Mirrors ``price_lookup_worker.OpenPriceService`` -- see its own docstring
#: for why a fresh service/connection is built per run rather than reused.
OpenPriceService = Callable[[], tuple[PriceService, Database | None]]


class OpenCardmarketLinkWorker(QThread):
    """Resolves a card's Cardmarket URL and opens it in Chrome, left open."""

    #: Emitted with the opened URL, or ``None`` if no Cardmarket link is known.
    succeeded = Signal(object)
    #: Emitted with a friendly message on failure (card not found, Chrome missing).
    failed = Signal(str)

    def __init__(self, open_service: OpenPriceService, card_id: int, parent=None) -> None:
        super().__init__(parent)
        self._open_service = open_service
        self._card_id = card_id

    def run(self) -> None:  # noqa: D102 — QThread override
        service, database = self._open_service()
        try:
            url = service.resolve_display_url(self._card_id)
            if url is not None:
                open_cardmarket_link(url)
        except (ServiceError, BrowserPriceReaderError) as exc:
            logger.error("Could not open Cardmarket link for card id=%s: %s", self._card_id, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception(
                "Unexpected error opening Cardmarket link for card id=%s", self._card_id
            )
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        finally:
            if database is not None:
                database.close()
        self.succeeded.emit(url)
