"""Background worker for the toolbar catalogue search.

Runs in its own ``QThread`` so the pokemontcg.io network call (which can
take a few seconds) doesn't freeze the GUI -- previously a synchronous,
blocking call, which made the whole app look frozen/crashed for however
long it took (live-reported point of confusion). Mirrors
:class:`~app.ui.workers.cardmarket_search_worker.CardmarketSearchWorker`.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.logging_config import get_logger
from app.services.catalog_search_service import CatalogSearchService
from app.services.exceptions import CatalogSearchError

logger = get_logger(__name__)


class CatalogSearchWorker(QThread):
    """Searches the pokemontcg.io catalogue for a query string."""

    #: Emitted with the list[CatalogCard] found (possibly empty).
    succeeded = Signal(list)
    #: Emitted with a friendly message when the search itself failed.
    failed = Signal(str)

    def __init__(self, service: CatalogSearchService, query: str, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._query = query

    def run(self) -> None:  # noqa: D102 — QThread override
        try:
            matches = self._service.search(self._query)
        except CatalogSearchError as exc:
            logger.error("Catalogue search failed for %r: %s", self._query, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception("Unexpected error during catalogue search for %r", self._query)
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        self.succeeded.emit(matches)
