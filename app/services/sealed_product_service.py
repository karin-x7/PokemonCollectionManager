"""Business logic for managing owned sealed products.

Validates user input (quantity) and translates missing-product lookups into
a typed exception. Mirrors ``card_service.py``, minus the catalogue-based add
path (there is no pokemontcg.io-style catalogue for sealed products, so
"manuell eintragen" -- a pasted Cardmarket link -- is the only way to add
one) and minus any notion of a collection: unlike cards, sealed products
aren't kept in physical folders/binders, so they aren't collection-scoped.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app import config
from app.database.repositories.sealed_product_repository import SealedProductRepository
from app.i18n import tr
from app.logging_config import get_logger
from app.models.enums import Language
from app.models.sealed_product import SealedProduct, SealedProductDetailsValues, SealedProductFilter
from app.pricing.browser_price_reader import (
    build_sealed_filtered_url,
    sealed_supports_language_filter,
)
from app.services.exceptions import SealedProductNotFoundError, ValidationError

logger = get_logger(__name__)

_MIN_QUANTITY = 1


def _validate_quantity(quantity: int) -> None:
    if quantity < _MIN_QUANTITY:
        raise ValidationError(
            tr("Die Menge muss mindestens {min_quantity} betragen.").format(
                min_quantity=_MIN_QUANTITY
            )
        )


def _with_language_filter(url: str | None, language: Language) -> str | None:
    """Rewrite ``url`` to include Cardmarket's own ``?language=N`` filter for

    ``language``, if it supports one. Uses the sealed-specific
    ``sealed_supports_language_filter``/``build_sealed_filtered_url`` rather
    than the single-card ones: unlike single cards, a sealed product's
    Cardmarket page genuinely does expose Japanese/Korean/Traditional
    Chinese as a filter on the *same* page (live-confirmed against a real
    Asian-exclusive set, see their own docstrings), so those get filtered
    here too. Left untouched only when there's no URL yet."""
    if url is None or not sealed_supports_language_filter(language):
        return url
    return build_sealed_filtered_url(url, language)


def _finalize_photo(product_id: int, temp_photo_path: str | None) -> str | None:
    """Move a temp screenshot capture into its final, id-based filename.

    Best-effort: the product's id is only known after ``repository.create()``
    returns, so the capture (which ran before that) had to land in a temp
    file first -- this renames it now that the real id exists. Returns the
    final path, or ``None`` if there was no temp file to begin with, or the
    move fails (never blocks adding the product over a photo problem)."""
    if temp_photo_path is None:
        return None
    temp_path = Path(temp_photo_path)
    if not temp_path.exists():
        return None
    dest = config.SEALED_PHOTOS_DIR / f"sealed_{product_id}{temp_path.suffix}"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp_path.replace(dest)
    except OSError as exc:
        logger.warning("Could not finalize sealed product photo for id=%s: %s", product_id, exc)
        return None
    return str(dest)


class SealedProductService:
    """Orchestrates sealed product CRUD with validation and friendly errors."""

    def __init__(self, repository: SealedProductRepository) -> None:
        self._repo = repository

    def search_products(self, product_filter: SealedProductFilter) -> list[SealedProduct]:
        """Return sealed products matching every set criterion in ``product_filter``."""
        return self._repo.search(product_filter)

    def get_product(self, product_id: int) -> SealedProduct:
        """Return a sealed product by id.

        Raises:
            SealedProductNotFoundError: If no such product exists.
        """
        product = self._repo.get(product_id)
        if product is None:
            raise SealedProductNotFoundError(product_id)
        return product

    def add_product_manual(
        self,
        name: str,
        category: str,
        values: SealedProductDetailsValues,
        temp_photo_path: str | None = None,
    ) -> SealedProduct:
        """Add a new owned sealed product, identified by a Cardmarket link.

        ``temp_photo_path`` (if given, from a best-effort screenshot capture
        taken during the lookup -- see ``app.pricing.sealed_image_capture``)
        is moved into its final, id-based location once the new product's
        real id is known.

        Raises:
            ValidationError: If ``values.quantity`` is less than 1.
        """
        _validate_quantity(values.quantity)
        new_product = SealedProduct(
            id=None,
            name=name,
            category=category,
            language=values.language,
            quantity=values.quantity,
            notes=values.notes,
            cardmarket_url=_with_language_filter(values.cardmarket_url, values.language),
        )
        product = self._repo.create(new_product)
        photo_path = _finalize_photo(product.id, temp_photo_path)
        if photo_path is not None:
            self._repo.update_photo_path(product.id, photo_path)
            product = replace(product, photo_path=photo_path)
        logger.info("Sealed product added: %s (id=%s)", product.name, product.id)
        return product

    def update_product_details(self, product_id: int, values: SealedProductDetailsValues) -> None:
        """Update the owned-copy attributes of an existing sealed product.

        Raises:
            ValidationError: If ``values.quantity`` is less than 1.
            SealedProductNotFoundError: If the product does not exist.
        """
        self.get_product(product_id)  # raises SealedProductNotFoundError
        _validate_quantity(values.quantity)
        values = replace(
            values, cardmarket_url=_with_language_filter(values.cardmarket_url, values.language)
        )
        self._repo.update_details(product_id, values)
        logger.info("Sealed product details updated: id=%s", product_id)

    def remove_product(self, product_id: int) -> None:
        """Delete a sealed product.

        Raises:
            SealedProductNotFoundError: If the product does not exist.
        """
        self.get_product(product_id)  # raises SealedProductNotFoundError
        self._repo.delete(product_id)
        logger.info("Sealed product removed: id=%s", product_id)
