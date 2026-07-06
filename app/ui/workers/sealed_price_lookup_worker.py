"""Background worker for a single sealed-product Cardmarket price lookup.

Mirrors :class:`~app.ui.workers.price_lookup_worker.PriceLookupWorker` --
runs in its own ``QThread`` so opening/reading/closing a browser tab doesn't
freeze the GUI. Scoped to exactly **one** product per run, started by
exactly one user click -- no batch/loop over multiple products.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from app.database.connection import Database
from app.logging_config import get_logger
from app.services.exceptions import ServiceError
from app.services.sealed_price_service import SealedPriceService

logger = get_logger(__name__)

#: Returns a fresh ``SealedPriceService`` plus the ``Database`` connection
#: backing it -- called from *this* worker's own thread, never the caller's
#: (SQLite connections cannot be used from a thread other than the one that
#: created them), mirroring ``OpenPriceService``.
OpenSealedPriceService = Callable[[], tuple[SealedPriceService, Database | None]]


class SealedPriceLookupWorker(QThread):
    """Looks up and persists the Cardmarket price for exactly one sealed product."""

    #: Emitted with the updated SealedProduct on completion — including when
    #: no price could be determined (that's a normal, tolerant outcome).
    succeeded = Signal(object)
    #: Emitted with a friendly message when the product itself couldn't be found.
    failed = Signal(str)

    def __init__(self, open_service: OpenSealedPriceService, product_id: int, parent=None) -> None:
        super().__init__(parent)
        self._open_service = open_service
        self._product_id = product_id

    def run(self) -> None:  # noqa: D102 — QThread override
        service, database = self._open_service()
        try:
            product = service.update_price_for_product(self._product_id)
        except ServiceError as exc:
            logger.error(
                "Sealed price lookup failed for product id=%s: %s", self._product_id, exc
            )
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception(
                "Unexpected error during sealed price lookup for product id=%s", self._product_id
            )
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        finally:
            if database is not None:
                database.close()
        self.succeeded.emit(product)
