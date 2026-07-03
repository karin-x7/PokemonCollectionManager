"""Domain-level exceptions raised by the services layer.

The UI catches these to show friendly, German-language messages instead of
raw SQL errors.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for all service-layer errors."""


class ValidationError(ServiceError):
    """Raised when user-supplied input fails a business rule."""


class DuplicateCollectionError(ServiceError):
    """Raised when a collection name already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Eine Sammlung mit dem Namen „{name}“ existiert bereits.")


class CollectionNotFoundError(ServiceError):
    """Raised when a collection id does not exist."""

    def __init__(self, collection_id: int) -> None:
        self.collection_id = collection_id
        super().__init__(f"Sammlung mit ID {collection_id} wurde nicht gefunden.")
