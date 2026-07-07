"""Background worker for a single wantlist-item Cardmarket price lookup.

Mirrors :class:`~app.ui.workers.sealed_price_lookup_worker.
SealedPriceLookupWorker` -- runs in its own ``QThread`` so opening/reading/
closing a browser tab doesn't freeze the GUI. Scoped to exactly **one** item
per run, started by exactly one user click -- no batch/loop over multiple
items (the "Check all prices" button drives this one-at-a-time, same as
``PriceController.start_bulk_update``).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from app.database.connection import Database
from app.logging_config import get_logger
from app.services.exceptions import ServiceError
from app.services.wantlist_price_service import WantlistPriceService

logger = get_logger(__name__)

#: Returns a fresh ``WantlistPriceService`` plus the ``Database`` connection
#: backing it -- called from *this* worker's own thread, never the caller's
#: (SQLite connections cannot be used from a thread other than the one that
#: created them), mirroring ``OpenSealedPriceService``.
OpenWantlistPriceService = Callable[[], tuple[WantlistPriceService, Database | None]]


class WantlistPriceLookupWorker(QThread):
    """Looks up and persists the Cardmarket price for exactly one wantlist item."""

    #: Emitted with the updated WantlistItem on completion — including when
    #: no price could be determined (that's a normal, tolerant outcome).
    succeeded = Signal(object)
    #: Emitted with a friendly message when the item itself couldn't be found.
    failed = Signal(str)

    def __init__(self, open_service: OpenWantlistPriceService, item_id: int, parent=None) -> None:
        super().__init__(parent)
        self._open_service = open_service
        self._item_id = item_id

    def run(self) -> None:  # noqa: D102 — QThread override
        service, database = self._open_service()
        try:
            item = service.update_price_for_item(self._item_id)
        except ServiceError as exc:
            logger.error("Wantlist price lookup failed for item id=%s: %s", self._item_id, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception(
                "Unexpected error during wantlist price lookup for item id=%s", self._item_id
            )
            self.failed.emit(f"Unexpected error: {exc}")
            return
        finally:
            if database is not None:
                database.close()
        self.succeeded.emit(item)
