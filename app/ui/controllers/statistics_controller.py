"""Connects :class:`StatisticsPanel` to :class:`StatisticsService`.

Recomputed on demand via :meth:`refresh` rather than kept continuously in
sync -- statistics aren't a real-time feature, so :class:`~app.ui.main_window.
MainWindow` only calls this when the Statistiken tab actually becomes active.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from app.services.statistics_service import StatisticsService
from app.ui.widgets.statistics_panel import StatisticsPanel


class StatisticsController(QObject):
    """Wires a :class:`StatisticsPanel` to a :class:`StatisticsService`."""

    def __init__(
        self,
        panel: StatisticsPanel,
        service: StatisticsService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._service = service

    def refresh(self) -> None:
        """Recompute the overview and render it into the panel."""
        self._panel.show_overview(self._service.compute_overview())

    def set_bulk_card_update_running(self, running: bool) -> None:
        """Forwards to the panel -- lets ``PriceController`` toggle the

        "Alle aktualisieren" button's state without needing a direct
        ``StatisticsPanel`` reference of its own.
        """
        self._panel.set_bulk_update_running(running)

    def set_bulk_sealed_update_running(self, running: bool) -> None:
        """Mirrors ``set_bulk_card_update_running`` for sealed products."""
        self._panel.set_sealed_bulk_update_running(running)
