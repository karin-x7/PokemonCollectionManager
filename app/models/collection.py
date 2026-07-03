"""The :class:`Collection` domain object.

A collection is a named container for cards (e.g. "Binder", "PSA Submission",
"Vintage"). It holds no business logic — persistence lives in the repository
layer and orchestration in the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Collection:
    """A named group of cards.

    Attributes:
        id: Primary key; ``None`` for an unsaved collection.
        name: Unique, human-facing name.
        description: Optional free-text description.
        position: Sort order in the sidebar (ascending).
        created_at: ISO-8601 UTC creation timestamp.
        updated_at: ISO-8601 UTC last-modification timestamp.
    """

    id: int | None
    name: str
    description: str = ""
    position: int = 0
    created_at: str | None = None
    updated_at: str | None = None
