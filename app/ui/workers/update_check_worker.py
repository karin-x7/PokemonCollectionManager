"""Background worker for the startup "is a newer version available?" check.

Runs in its own ``QThread`` so a slow/unreachable GitHub API can't delay
startup. Unlike the other workers in this package, there's no ``failed``
signal: ``check_for_update`` already treats any failure as "nothing found"
(see its own docstring), so there's nothing distinct to report back.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.services.update_check_service import UpdateInfo, check_for_update


class UpdateCheckWorker(QThread):
    """Checks GitHub Releases once for a newer version than ``current_version``."""

    #: Emitted with the found UpdateInfo, or ``None`` if already up to date
    #: (or the check failed -- treated the same, see module docstring).
    succeeded = Signal(object)

    def __init__(self, current_version: str, parent=None) -> None:
        super().__init__(parent)
        self._current_version = current_version

    def run(self) -> None:  # noqa: D102 — QThread override
        info: UpdateInfo | None = check_for_update(self._current_version)
        self.succeeded.emit(info)
