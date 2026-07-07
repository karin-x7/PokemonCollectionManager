"""Domain-level exceptions raised by the services layer.

The UI catches these to show friendly messages (translated per the current
UI language, see :mod:`app.i18n`) instead of raw SQL errors.
"""

from __future__ import annotations

from app.i18n import tr


class ServiceError(Exception):
    """Base class for all service-layer errors."""


class ValidationError(ServiceError):
    """Raised when user-supplied input fails a business rule."""


class DuplicateCollectionError(ServiceError):
    """Raised when a collection name already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(tr("Eine Sammlung mit dem Namen „{name}“ existiert bereits.").format(name=name))


class CollectionNotFoundError(ServiceError):
    """Raised when a collection id does not exist."""

    def __init__(self, collection_id: int) -> None:
        self.collection_id = collection_id
        super().__init__(
            tr("Sammlung mit ID {id} wurde nicht gefunden.").format(id=collection_id)
        )


class CatalogSearchError(ServiceError):
    """Raised when the catalogue search backend(s) cannot be reached."""


class CardNotFoundError(ServiceError):
    """Raised when a card id does not exist."""

    def __init__(self, card_id: int) -> None:
        self.card_id = card_id
        super().__init__(tr("Karte mit ID {id} wurde nicht gefunden.").format(id=card_id))


class SealedProductNotFoundError(ServiceError):
    """Raised when a sealed product id does not exist."""

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(
            tr("Sealed-Produkt mit ID {id} wurde nicht gefunden.").format(id=product_id)
        )


class WantlistItemNotFoundError(ServiceError):
    """Raised when a wantlist item id does not exist."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__(f"Wantlist item with id {item_id} was not found.")
