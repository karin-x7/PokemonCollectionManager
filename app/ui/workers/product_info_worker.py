"""Background worker for a single "Karte manuell eintragen" page lookup.

Runs in its own ``QThread`` so opening/reading/closing a browser tab (which
can take several seconds) doesn't freeze the GUI -- mirrors
:class:`~app.ui.workers.price_lookup_worker.PriceLookupWorker`. Deliberately
scoped to exactly **one** URL per run, started by exactly one user click.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QThread, Signal

from app.catalog.pokemontcg_client import PokemonTcgClient, PokemonTcgClientError
from app.logging_config import get_logger
from app.pricing.browser_price_reader import BrowserPriceReaderError, read_product_info

logger = get_logger(__name__)


class ProductInfoWorker(QThread):
    """Reads name/set/card-number off a single Cardmarket product page."""

    #: Emitted with the parsed ProductInfo on success.
    succeeded = Signal(object)
    #: Emitted with a friendly message when the page couldn't be read/parsed.
    failed = Signal(str)

    def __init__(
        self, url: str, pokemontcg_client: PokemonTcgClient | None = None, parent=None
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._pokemontcg = pokemontcg_client

    def run(self) -> None:  # noqa: D102 — QThread override
        try:
            info = read_product_info(self._url, capture_image=True)
        except BrowserPriceReaderError as exc:
            logger.error("Manual product lookup failed for %s: %s", self._url, exc)
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — this runs in pythonw with no
            # console, so an uncaught exception here would otherwise vanish
            # silently instead of ever reaching the log file.
            logger.exception("Unexpected error during manual product lookup for %s", self._url)
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
            return
        if self._pokemontcg is not None:
            # Best-effort: a card manually entered via Cardmarket link has
            # no catalogue match of its own, so it would otherwise show no
            # set icon at all (unlike a catalogue-matched card) -- resolving
            # set_code here, still in the background thread, keeps the GUI
            # responsive even though pokemontcg.io can be slow (a live
            # request has taken 20+ seconds during a slow period). Never
            # lets a network error here fail the whole lookup.
            try:
                set_code = self._pokemontcg.resolve_set_code(info.set_name)
                if set_code:
                    info = replace(info, set_code=set_code)
            except PokemonTcgClientError as exc:
                logger.warning("Could not resolve set_code for %r: %s", info.set_name, exc)
        self.succeeded.emit(info)
