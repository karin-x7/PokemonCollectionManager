"""Data transfer objects for scraped Cardmarket marketplace data."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import Condition, Language


@dataclass(frozen=True, slots=True)
class CardmarketOffer:
    """A single seller offer read from a Cardmarket product page.

    ``condition``/``language`` are ``None`` when the row couldn't be mapped
    to a known value (e.g. an unrecognised flag) — such offers still count
    towards the ``AVERAGE`` price-quality fallback, just not towards an
    exact or partial match.
    """

    seller: str
    condition: Condition | None
    language: Language | None
    price: float
    comment: str = ""


@dataclass(frozen=True, slots=True)
class ProductInfo:
    """Name/set/card-number parsed off a Cardmarket product page's own title.

    ``card_number`` is blank for products with no printed number (e.g. some
    promos) — callers should treat it as a starting point to confirm/edit,
    not an infallible value.
    """

    name: str
    set_name: str
    card_number: str
    #: Path to a temporary file holding a best-effort screenshot capture of
    #: the card's photo, or ``None`` if the capture wasn't attempted or
    #: failed -- see ``app.pricing.sealed_image_capture`` (reused as-is: the
    #: capture logic itself has nothing sealed-product-specific about it).
    #: The caller is responsible for moving this temp file to its final
    #: location once the card's real id is known.
    photo_path: str | None = None
    #: pokemontcg.io ``set.id``, resolved best-effort from ``set_name`` via
    #: ``PokemonTcgClient.resolve_set_code`` (see its own docs) -- lets a
    #: manually-entered card show the same set icon a catalogue-matched one
    #: gets. Blank if not resolved (e.g. a network error, or no matching
    #: catalogue set at all) -- never blocks adding the card either way.
    set_code: str = ""
    #: Best-effort language guess -- the most common language among the
    #: product page's own already-visible offer rows (see
    #: ``cardmarket_parsing._detect_dominant_language``), or ``None`` if no
    #: offers could be parsed at all (e.g. currently out of stock). Only a
    #: starting point for the add-card dialog's language dropdown, never
    #: authoritative: a real user reported this defaulting to "English" no
    #: matter what was actually pasted (the field existed but was hardcoded),
    #: which then silently mis-filtered later price lookups for JP/KO/ZH/
    #: German cards added this way -- see ``price_service.py``.
    detected_language: Language | None = None


@dataclass(frozen=True, slots=True)
class CardmarketSearchResult:
    """A single candidate product from Cardmarket's own site search.

    No URL yet: Cardmarket's UI Automation tree only ever exposes a search
    result link's visible text, never its actual href -- ``raw_text`` is
    kept so the same link can be found again (matched by this exact text)
    and clicked through to recover its real URL, see
    ``resolve_cardmarket_search_result``.
    """

    name: str
    set_name: str
    card_number: str
    price_hint: str
    raw_text: str


@dataclass(frozen=True, slots=True)
class SealedOffer:
    """A single seller offer read from a Cardmarket sealed-product page.

    No ``condition`` field -- Cardmarket only ever sells sealed products
    sealed ("Opened products cannot be sold", confirmed live on a real
    product page), so there is no condition ladder to match on, unlike
    single cards.
    """

    seller: str
    language: Language | None
    price: float
    comment: str = ""


@dataclass(frozen=True, slots=True)
class SealedProductInfo:
    """Name/category parsed off a Cardmarket sealed-product page.

    ``category`` (e.g. "Booster Box", "Elite Trainer Box") comes from the
    page's own breadcrumb where it could be found; blank if not -- callers
    should treat it as a starting point to confirm/edit, not infallible.
    """

    name: str
    category: str
    #: Path to a temporary file holding a best-effort screenshot capture of
    #: the product's photo, or ``None`` if the capture wasn't attempted or
    #: failed -- see ``app.pricing.sealed_image_capture``. The caller is
    #: responsible for moving this temp file to its final location once the
    #: product's real id is known.
    photo_path: str | None = None
