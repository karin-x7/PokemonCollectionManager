"""Automatic, best-effort backups of the SQLite database file.

Protects against a corrupted database or a bad schema migration wiping out
someone's whole collection -- there was previously no backup of any kind.
Read-only with respect to the live database (a plain file copy, taken
*before* :func:`app.database.migrations.run_migrations` touches anything),
and never raises: a failed backup must never block the app from starting.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app import config
from app.logging_config import get_logger

logger = get_logger(__name__)

_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
#: Kept low enough that a personal collection's backups stay a trivial
#: amount of disk space, high enough to survive several app updates (each
#: bringing new migrations) without losing the oldest safety net too soon.
_MAX_BACKUPS = 20
#: Skipped if the most recent existing backup is younger than this -- during
#: active use/testing the app can restart many times in a single day (a
#: real, observed pattern), which would otherwise exhaust _MAX_BACKUPS
#: within hours instead of covering a much longer real timespan.
_MIN_INTERVAL = timedelta(hours=24)


def backup_database(
    db_path: Path,
    backups_dir: Path | None = None,
    min_interval: timedelta = _MIN_INTERVAL,
) -> Path | None:
    """Copy ``db_path`` into ``backups_dir`` with a timestamped name.

    Skipped (returns ``None``) if ``db_path`` doesn't exist yet (a brand-new
    install has nothing to back up), or the most recent existing backup for
    this database is younger than ``min_interval``. Prunes backups beyond
    :data:`_MAX_BACKUPS` (oldest first) after a successful copy.

    Never raises: a failed backup (permissions, disk full, ...) is logged
    and swallowed rather than blocking the app from starting.
    """
    if not db_path.exists():
        return None

    directory = backups_dir if backups_dir is not None else config.BACKUPS_DIR
    directory.mkdir(parents=True, exist_ok=True)

    existing = _existing_backups(directory, db_path.stem)
    if existing and _age(existing[0]) < min_interval:
        logger.debug(
            "Skipping database backup -- most recent one (%s) is still recent enough.",
            existing[0].name,
        )
        return None

    timestamp = datetime.now().strftime(_TIMESTAMP_FORMAT)
    dest = directory / f"{db_path.stem}_{timestamp}.db"
    try:
        shutil.copy2(db_path, dest)
    except OSError as exc:
        logger.warning("Database backup failed (%s -> %s): %s", db_path, dest, exc)
        return None

    logger.info("Database backed up to %s", dest)
    _prune_old_backups(directory, db_path.stem)
    return dest


@dataclass(frozen=True, slots=True)
class BackupInfo:
    """One backup file, as shown in the restore-from-backup UI."""

    path: Path
    created_at: datetime
    size_bytes: int


def list_backups(db_path: Path, backups_dir: Path | None = None) -> list[BackupInfo]:
    """Existing backups for ``db_path``, newest first."""
    directory = backups_dir if backups_dir is not None else config.BACKUPS_DIR
    infos = []
    for backup in _existing_backups(directory, db_path.stem):
        try:
            stat = backup.stat()
        except OSError:
            continue  # vanished between listing and stat()-ing -- skip it
        infos.append(
            BackupInfo(
                path=backup, created_at=datetime.fromtimestamp(stat.st_mtime), size_bytes=stat.st_size
            )
        )
    return infos


def restore_backup(backup_path: Path, db_path: Path, backups_dir: Path | None = None) -> None:
    """Replace ``db_path`` with ``backup_path``'s contents.

    Takes a fresh safety backup of the *current* ``db_path`` first
    (ignoring the normal 24h throttle -- this is a deliberate, one-off
    action, not the routine pre-migration backup), so a restore is itself
    reversible via another restore. The caller is responsible for closing
    any open connection to ``db_path`` first -- SQLite's WAL sidecar files
    are only guaranteed flushed/removed once the last connection closes.

    Unlike :func:`backup_database`, this raises ``OSError`` on failure
    rather than swallowing it: restoring is a deliberate user action, so a
    failure should surface as an error, not silently do nothing.

    Copies to a temporary file first and only then swaps it into place via
    an atomic rename, so a failure partway through the copy (disk full,
    permissions, ...) can never leave ``db_path`` half-overwritten.
    """
    if db_path.exists():
        backup_database(db_path, backups_dir, min_interval=timedelta(0))
    tmp_path = db_path.with_name(db_path.name + ".restoring")
    try:
        shutil.copy2(backup_path, tmp_path)
        tmp_path.replace(db_path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
    logger.info("Database restored from %s", backup_path)


def _existing_backups(directory: Path, stem: str) -> list[Path]:
    """Existing backups for ``stem``, newest first."""
    return sorted(directory.glob(f"{stem}_*.db"), reverse=True)


def _age(backup: Path) -> timedelta:
    try:
        modified = datetime.fromtimestamp(backup.stat().st_mtime)
    except OSError:
        return timedelta.max
    return datetime.now() - modified


def _prune_old_backups(directory: Path, stem: str) -> None:
    for stale in _existing_backups(directory, stem)[_MAX_BACKUPS:]:
        try:
            stale.unlink()
        except OSError as exc:
            logger.warning("Could not remove stale backup %s: %s", stale, exc)
