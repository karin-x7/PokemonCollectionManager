"""Background worker for a single "Sealed-Produkt eintragen" page lookup.

Mirrors :class:`~app.ui.workers.product_info_worker.ProductInfoWorker` --
runs in its own ``QThread`` so opening/reading/closing a browser tab doesn't
freeze the GUI. Scoped to exactly **one** URL per run, started by exactly
one user click.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, read_sealed_product_info

logger = get_logger(__name__)


class SealedProductInfoWorker(QThread):
    """Reads name/category off a single Cardmarket sealed-product page."""

    #: Emitted with the parsed SealedProductInfo on success.
    succeeded = Signal(object)
    #: Emitted with a friendly message when the page couldn't be read/parsed.
    failed = Signal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self._url = url

    def run(self) -> None:  # noqa: D102 — QThread override
        try:
            info = read_sealed_product_info(self._url, capture_image=True)
        except BrowserPriceReaderError as exc:
            logger.error("Sealed product lookup failed for %s: %s", self._url, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception("Unexpected error during sealed product lookup for %s", self._url)
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        self.succeeded.emit(info)
