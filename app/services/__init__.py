"""Application/business services orchestrating the domain layers.

This is the only layer the GUI is permitted to call for business operations;
it validates input and translates raw persistence errors into the typed
exceptions in :mod:`app.services.exceptions`.
"""

from app.services.collection_service import CollectionService
from app.services.exceptions import (
    CollectionNotFoundError,
    DuplicateCollectionError,
    ServiceError,
    ValidationError,
)

__all__ = [
    "CollectionNotFoundError",
    "CollectionService",
    "DuplicateCollectionError",
    "ServiceError",
    "ValidationError",
]
