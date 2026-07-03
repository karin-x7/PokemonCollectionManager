"""Tests for the SQL-level collection repository."""

from __future__ import annotations

import sqlite3

import pytest

from app.database.connection import Database
from app.database.repositories.collection_repository import CollectionRepository


@pytest.fixture
def repo(temp_db: Database) -> CollectionRepository:
    return CollectionRepository(temp_db)


def test_create_assigns_incrementing_position(repo: CollectionRepository) -> None:
    first = repo.create("Binder")
    second = repo.create("Vintage")
    assert first.position == 0
    assert second.position == 1
    assert first.id is not None and second.id is not None


def test_list_all_orders_by_position(repo: CollectionRepository) -> None:
    repo.create("Binder")
    repo.create("Vintage")
    repo.create("Verkauf")
    names = [c.name for c in repo.list_all()]
    assert names == ["Binder", "Vintage", "Verkauf"]


def test_create_duplicate_name_raises_integrity_error(repo: CollectionRepository) -> None:
    repo.create("Binder")
    with pytest.raises(sqlite3.IntegrityError):
        repo.create("Binder")


def test_get_returns_none_for_missing_id(repo: CollectionRepository) -> None:
    assert repo.get(999) is None


def test_rename_updates_name(repo: CollectionRepository) -> None:
    created = repo.create("Binder")
    repo.rename(created.id, "Ordner")
    assert repo.get(created.id).name == "Ordner"


def test_delete_removes_collection(repo: CollectionRepository) -> None:
    created = repo.create("Binder")
    repo.delete(created.id)
    assert repo.get(created.id) is None


def test_delete_cascades_to_cards(temp_db: Database, repo: CollectionRepository) -> None:
    created = repo.create("Binder")
    conn = temp_db.connection
    with conn:
        conn.execute(
            "INSERT INTO cards (collection_id, name, created_at, updated_at) "
            "VALUES (?, 'Xatu', '2026-01-01', '2026-01-01')",
            (created.id,),
        )
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 1

    repo.delete(created.id)

    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 0


def test_reorder_persists_new_positions(repo: CollectionRepository) -> None:
    a = repo.create("A")
    b = repo.create("B")
    c = repo.create("C")

    repo.reorder([c.id, a.id, b.id])

    names = [col.name for col in repo.list_all()]
    assert names == ["C", "A", "B"]
