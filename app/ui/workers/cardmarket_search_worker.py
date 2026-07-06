"""Background worker for the "Cardmarket-Link suchen" flow's search step.

Runs in its own ``QThread`` so opening/reading/closing a browser tab (which
can take several seconds) doesn't freeze the GUI -- mirrors
:class:`~app.ui.workers.product_info_worker.ProductInfoWorker`. Deliberately
scoped to exactly **one** search per run, started by exactly one user click.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, search_cardmarket

logger = get_logger(__name__)


class CardmarketSearchWorker(QThread):
    """Searches Cardmarket's own site search for a card by name."""

    #: Emitted with the list[CardmarketSearchResult] found (possibly empty).
    succeeded = Signal(list)
    #: Emitted with a friendly message when the search itself failed.
    failed = Signal(str)

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(parent)
        self._name = name

    def run(self) -> None:  # noqa: D102 — QThread override
        try:
            results = search_cardmarket(self._name)
        except BrowserPriceReaderError as exc:
            logger.error("Cardmarket search failed for %r: %s", self._name, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception("Unexpected error during Cardmarket search for %r", self._name)
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        self.succeeded.emit(results)
