"""Background worker for Sealed's "Open Cardmarket link" context-menu action.

Mirrors :class:`~app.ui.workers.open_cardmarket_link_worker.
OpenCardmarketLinkWorker` exactly, scaled down to sealed products (no
shortlink resolution -- see :class:`~app.services.sealed_price_service.
SealedPriceService`'s own docstring): opening the resolved URL in Chrome is
fire-and-forget, so this finishes almost immediately.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, open_cardmarket_link
from app.services.exceptions import ServiceError
from app.ui.workers.sealed_price_lookup_worker import OpenSealedPriceService

logger = get_logger(__name__)


class OpenSealedCardmarketLinkWorker(QThread):
    """Resolves a sealed product's Cardmarket URL and opens it in Chrome, left open."""

    #: Emitted with the opened URL, or ``None`` if no Cardmarket link is known.
    succeeded = Signal(object)
    #: Emitted with a friendly message on failure (product not found, Chrome missing).
    failed = Signal(str)

    def __init__(
        self, open_service: OpenSealedPriceService, product_id: int, parent=None
    ) -> None:
        super().__init__(parent)
        self._open_service = open_service
        self._product_id = product_id

    def run(self) -> None:  # noqa: D102 — QThread override
        service, database = self._open_service()
        try:
            url = service.resolve_display_url(self._product_id)
            if url is not None:
                open_cardmarket_link(url)
        except (ServiceError, BrowserPriceReaderError) as exc:
            logger.error(
                "Could not open Cardmarket link for sealed product id=%s: %s",
                self._product_id, exc,
            )
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception(
                "Unexpected error opening Cardmarket link for sealed product id=%s",
                self._product_id,
            )
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        finally:
            if database is not None:
                database.close()
        self.succeeded.emit(url)
