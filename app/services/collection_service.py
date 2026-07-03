"""Business logic for managing collections.

Validates user input (non-empty, trimmed, unique names) and translates raw
SQL errors from the repository into friendly, typed exceptions the UI can
display. This is the only layer the GUI is allowed to call into for
collection operations.
"""

from __future__ import annotations

import sqlite3

from app.database.repositories.collection_repository import CollectionRepository
from app.logging_config import get_logger
from app.models.collection import Collection
from app.services.exceptions import (
    CollectionNotFoundError,
    DuplicateCollectionError,
    ValidationError,
)

logger = get_logger(__name__)

_MAX_NAME_LENGTH = 100


def _clean_name(name: str) -> str:
    """Validate and normalise a collection name.

    Raises:
        ValidationError: If the name is empty/whitespace-only or too long.
    """
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError("Der Name einer Sammlung darf nicht leer sein.")
    if len(cleaned) > _MAX_NAME_LENGTH:
        raise ValidationError(
            f"Der Name darf höchstens {_MAX_NAME_LENGTH} Zeichen lang sein."
        )
    return cleaned


class CollectionService:
    """Orchestrates collection CRUD with validation and friendly errors."""

    def __init__(self, repository: CollectionRepository) -> None:
        self._repo = repository

    def list_collections(self) -> list[Collection]:
        """Return all collections in sidebar order."""
        return self._repo.list_all()

    def get_collection(self, collection_id: int) -> Collection:
        """Return a collection by id.

        Raises:
            CollectionNotFoundError: If no such collection exists.
        """
        collection = self._repo.get(collection_id)
        if collection is None:
            raise CollectionNotFoundError(collection_id)
        return collection

    def create_collection(self, name: str, description: str = "") -> Collection:
        """Create a new collection.

        Raises:
            ValidationError: If the name is empty or too long.
            DuplicateCollectionError: If the name already exists.
        """
        cleaned = _clean_name(name)
        try:
            collection = self._repo.create(cleaned, description)
        except sqlite3.IntegrityError as exc:
            raise DuplicateCollectionError(cleaned) from exc
        logger.info("Collection created: %s (id=%s)", collection.name, collection.id)
        return collection

    def rename_collection(self, collection_id: int, new_name: str) -> None:
        """Rename a collection.

        Raises:
            ValidationError: If the new name is empty or too long.
            DuplicateCollectionError: If the new name already exists.
            CollectionNotFoundError: If the collection does not exist.
        """
        self.get_collection(collection_id)  # raises CollectionNotFoundError
        cleaned = _clean_name(new_name)
        try:
            self._repo.rename(collection_id, cleaned)
        except sqlite3.IntegrityError as exc:
            raise DuplicateCollectionError(cleaned) from exc
        logger.info("Collection renamed: id=%s -> %s", collection_id, cleaned)

    def delete_collection(self, collection_id: int) -> None:
        """Delete a collection and (via cascade) all of its cards.

        Raises:
            CollectionNotFoundError: If the collection does not exist.
        """
        self.get_collection(collection_id)  # raises CollectionNotFoundError
        self._repo.delete(collection_id)
        logger.info("Collection deleted: id=%s", collection_id)

    def reorder_collections(self, ordered_ids: list[int]) -> None:
        """Persist a new sidebar order."""
        self._repo.reorder(ordered_ids)
        logger.debug("Collections reordered: %s", ordered_ids)
