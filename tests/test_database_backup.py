"""Tests for the automatic database backup helper."""

from __future__ import annotations

import os
import time
from datetime import timedelta
from pathlib import Path

import pytest

from app.database.backup import backup_database, list_backups, restore_backup


def _make_db(path: Path, content: bytes = b"fake-sqlite-bytes") -> None:
    path.write_bytes(content)


def test_backs_up_an_existing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path)
    backups_dir = tmp_path / "backups"

    result = backup_database(db_path, backups_dir=backups_dir)

    assert result is not None
    assert result.parent == backups_dir
    assert result.read_bytes() == b"fake-sqlite-bytes"
    assert result.name.startswith("collection_")


def test_missing_database_returns_none_without_creating_a_backup(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    backups_dir = tmp_path / "backups"

    result = backup_database(db_path, backups_dir=backups_dir)

    assert result is None
    assert not backups_dir.exists() or list(backups_dir.iterdir()) == []


def test_second_call_within_the_interval_is_skipped(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path)
    backups_dir = tmp_path / "backups"

    first = backup_database(db_path, backups_dir=backups_dir)
    second = backup_database(db_path, backups_dir=backups_dir)

    assert first is not None
    assert second is None
    assert len(list(backups_dir.glob("collection_*.db"))) == 1


def test_backs_up_again_once_the_interval_has_passed(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path)
    backups_dir = tmp_path / "backups"

    first = backup_database(db_path, backups_dir=backups_dir, min_interval=timedelta(seconds=0))
    time.sleep(1.1)  # backups are timestamped to the second -- avoid a same-name collision
    second = backup_database(db_path, backups_dir=backups_dir, min_interval=timedelta(seconds=0))

    assert first is not None
    assert second is not None
    assert first != second
    assert len(list(backups_dir.glob("collection_*.db"))) == 2


def test_prunes_backups_beyond_the_retention_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    # 25 pre-existing "old" backups, all older than the interval.
    old_time = time.time() - 999999
    for i in range(25):
        stale = backups_dir / f"collection_{i:03d}_000000.db"
        stale.write_bytes(b"old")
        os.utime(stale, (old_time, old_time))

    backup_database(db_path, backups_dir=backups_dir, min_interval=timedelta(seconds=0))

    assert len(list(backups_dir.glob("collection_*.db"))) == 20


def test_never_raises_when_the_copy_fails(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path)
    backups_dir = tmp_path / "backups"

    def _raise(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("app.database.backup.shutil.copy2", _raise)

    result = backup_database(db_path, backups_dir=backups_dir)

    assert result is None


def test_list_backups_returns_them_newest_first(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    older = backups_dir / "collection_20260101_000000.db"
    newer = backups_dir / "collection_20260601_000000.db"
    older.write_bytes(b"old")
    newer.write_bytes(b"new")
    old_time = time.time() - 999999
    os.utime(older, (old_time, old_time))

    backups = list_backups(db_path, backups_dir=backups_dir)

    assert [b.path for b in backups] == [newer, older]
    assert backups[0].size_bytes == len(b"new")


def test_list_backups_returns_empty_list_when_none_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"

    assert list_backups(db_path, backups_dir=tmp_path / "backups") == []


def test_restore_backup_replaces_the_database_file(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path, content=b"current-data")
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    backup_path = backups_dir / "collection_20260101_000000.db"
    backup_path.write_bytes(b"older-data")

    restore_backup(backup_path, db_path, backups_dir=backups_dir)

    assert db_path.read_bytes() == b"older-data"


def test_restore_backup_backs_up_the_current_database_first(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path, content=b"current-data")
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    backup_path = backups_dir / "collection_20260101_000000.db"
    backup_path.write_bytes(b"older-data")

    restore_backup(backup_path, db_path, backups_dir=backups_dir)

    safety_backups = [
        p for p in backups_dir.glob("collection_*.db") if p.read_bytes() == b"current-data"
    ]
    assert len(safety_backups) == 1


def test_restore_backup_leaves_the_database_untouched_on_a_failed_copy(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "collection.db"
    _make_db(db_path, content=b"current-data")
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    backup_path = backups_dir / "collection_20260101_000000.db"
    backup_path.write_bytes(b"older-data")

    def _raise(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("app.database.backup.shutil.copy2", _raise)

    with pytest.raises(OSError):
        restore_backup(backup_path, db_path, backups_dir=backups_dir)

    assert db_path.read_bytes() == b"current-data"
    assert not (db_path.with_name(db_path.name + ".restoring")).exists()
