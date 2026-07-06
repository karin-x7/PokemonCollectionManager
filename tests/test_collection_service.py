"""Tests for collection business logic: validation and friendly errors."""

from __future__ import annotations

import pytest

from app.database.connection import Database
from app.database.repositories.collection_repository import CollectionRepository
from app.services.collection_service import CollectionService
from app.services.exceptions import (
    CollectionNotFoundError,
    DuplicateCollectionError,
    ValidationError,
)


@pytest.fixture
def service(temp_db: Database) -> CollectionService:
    return CollectionService(CollectionRepository(temp_db))


def test_create_collection_trims_whitespace(service: CollectionService) -> None:
    created = service.create_collection("  Binder  ")
    assert created.name == "Binder"


@pytest.mark.parametrize("bad_name", ["", "   ", "\t\n"])
def test_create_collection_rejects_empty_name(service: CollectionService, bad_name: str) -> None:
    with pytest.raises(ValidationError):
        service.create_collection(bad_name)


def test_create_collection_rejects_too_long_name(service: CollectionService) -> None:
    with pytest.raises(ValidationError):
        service.create_collection("x" * 101)


def test_create_duplicate_collection_raises_friendly_error(service: CollectionService) -> None:
    service.create_collection("Binder")
    with pytest.raises(DuplicateCollectionError, match="Binder"):
        service.create_collection("Binder")


def test_rename_missing_collection_raises_not_found(service: CollectionService) -> None:
    with pytest.raises(CollectionNotFoundError):
        service.rename_collection(999, "Neu")


def test_rename_to_duplicate_name_raises_friendly_error(service: CollectionService) -> None:
    service.create_collection("Binder")
    vintage = service.create_collection("Vintage")
    with pytest.raises(DuplicateCollectionError):
        service.rename_collection(vintage.id, "Binder")


def test_rename_trims_and_validates(service: CollectionService) -> None:
    created = service.create_collection("Binder")
    service.rename_collection(created.id, "  Ordner  ")
    assert service.get_collection(created.id).name == "Ordner"

    with pytest.raises(ValidationError):
        service.rename_collection(created.id, "   ")


def test_delete_missing_collection_raises_not_found(service: CollectionService) -> None:
    with pytest.raises(CollectionNotFoundError):
        service.delete_collection(999)


def test_delete_removes_collection(service: CollectionService) -> None:
    created = service.create_collection("Binder")
    service.delete_collection(created.id)
    with pytest.raises(CollectionNotFoundError):
        service.get_collection(created.id)


def test_list_collections_returns_creation_order(service: CollectionService) -> None:
    service.create_collection("Binder")
    service.create_collection("Vintage")
    assert [c.name for c in service.list_collections()] == ["Binder", "Vintage"]


def test_reorder_collections(service: CollectionService) -> None:
    a = service.create_collection("A")
    b = service.create_collection("B")
    service.reorder_collections([b.id, a.id])
    assert [c.name for c in service.list_collections()] == ["B", "A"]


