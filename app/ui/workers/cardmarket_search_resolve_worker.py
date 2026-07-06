"""Background worker for the "Cardmarket-Link suchen" flow's confirm step.

Runs in its own ``QThread`` -- mirrors
:class:`~app.ui.workers.cardmarket_search_worker.CardmarketSearchWorker`.
Separate from the search step itself since it only runs once the user has
picked a candidate from the search results dialog, well after the search
tab has already been closed.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, resolve_cardmarket_search_result
from app.pricing.models import CardmarketSearchResult

logger = get_logger(__name__)


class CardmarketSearchResolveWorker(QThread):
    """Clicks through to a chosen search result's real Cardmarket URL."""

    #: Emitted with the resolved URL on success.
    succeeded = Signal(str)
    #: Emitted with a friendly message when resolving failed.
    failed = Signal(str)

    def __init__(self, name: str, chosen: CardmarketSearchResult, parent=None) -> None:
        super().__init__(parent)
        self._name = name
        self._chosen = chosen

    def run(self) -> None:  # noqa: D102 — QThread override
        try:
            url = resolve_cardmarket_search_result(self._name, self._chosen)
        except BrowserPriceReaderError as exc:
            logger.error(
                "Cardmarket search result resolution failed for %r: %s", self._chosen, exc
            )
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception(
                "Unexpected error resolving Cardmarket search result for %r", self._chosen
            )
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        self.succeeded.emit(url)
