"""Repositories: thin SQL access objects mapping rows to domain dataclasses.

Repositories contain no validation or orchestration — that lives in the
``services`` layer. They only translate between SQL and domain objects.
"""

from app.database.repositories.collection_repository import CollectionRepository

__all__ = ["CollectionRepository"]
