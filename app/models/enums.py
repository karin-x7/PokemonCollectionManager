"""Fixed vocabularies used throughout the domain.

``Condition`` and ``Language`` carry explicit ordering / codes because the
pricing engine walks a fallback ladder over them ("next better / next worse
condition", "same vs. other language"). Values are stored in the database as
short, stable string codes so that reordering the Python enum never corrupts
existing rows.
"""

from __future__ import annotations

from enum import Enum


class Condition(Enum):
    """Card grading condition, ordered from best (0) to worst.

    ``order`` drives the pricing fallback ("nearest better / worse condition").
    ``code`` is the value persisted in the database (Cardmarket abbreviation).
    """

    MINT = ("M", "Mint", 0)
    NEAR_MINT = ("NM", "Near Mint", 1)
    EXCELLENT = ("EX", "Excellent", 2)
    GOOD = ("GD", "Good", 3)
    LIGHT_PLAYED = ("LP", "Light Played", 4)
    PLAYED = ("PL", "Played", 5)
    POOR = ("PO", "Poor", 6)

    def __init__(self, code: str, label: str, order: int) -> None:
        self.code = code
        self.label = label
        self.order = order

    @classmethod
    def from_code(cls, code: str | None) -> "Condition":
        """Resolve a stored code (e.g. ``"NM"``) to a member."""
        if code is None:
            return cls.NEAR_MINT
        for member in cls:
            if member.code.casefold() == str(code).casefold():
                return member
        return cls.NEAR_MINT

    def distance_to(self, other: "Condition") -> int:
        """Absolute number of grading steps between two conditions."""
        return abs(self.order - other.order)


class Language(Enum):
    """Card language. ``code`` (ISO-ish) is the persisted value."""

    ENGLISH = ("EN", "English")
    GERMAN = ("DE", "German")
    FRENCH = ("FR", "French")
    ITALIAN = ("IT", "Italian")
    SPANISH = ("ES", "Spanish")
    PORTUGUESE = ("PT", "Portuguese")
    JAPANESE = ("JP", "Japanese")
    KOREAN = ("KO", "Korean")
    CHINESE = ("ZH", "Chinese")

    def __init__(self, code: str, label: str) -> None:
        self.code = code
        self.label = label

    @classmethod
    def from_code(cls, code: str | None) -> "Language":
        """Resolve a stored code (e.g. ``"DE"``) to a member."""
        if code is None:
            return cls.ENGLISH
        for member in cls:
            if member.code.casefold() == str(code).casefold():
                return member
        return cls.ENGLISH


class PriceQuality(str, Enum):
    """Provenance / confidence of a determined price.

    Mirrors the required "Preisqualität" states so the UI can explain exactly
    why a given price was used.
    """

    EXACT = "exact"
    ESTIMATED_FROM_CONDITION = "estimated_from_condition"
    ESTIMATED_FROM_LANGUAGE = "estimated_from_language"
    AVERAGE = "average"
    #: Legacy value: a quick market-trend price from tcgdex.dev's bundled
    #: Cardmarket data. No longer produced (tcgdex's pricing turned out
    #: unreliable, e.g. a real Xatu worth ~200 EUR was reported as 3.09 EUR)
    #: -- kept only so already-persisted rows still resolve correctly.
    MARKET_TREND = "market_trend"
    NO_PRICE = "no_price"
    #: Set directly by the user via "Preis manuell bearbeiten" -- for cases
    #: where the automatic Cardmarket matching picked a mislabeled listing
    #: (e.g. a seller listing a PSA 1 graded card as "Near Mint" condition,
    #: live-reported), so the user overrides it with the price they know is
    #: actually right instead of waiting for a better auto-match.
    MANUAL = "manual"

    @property
    def label(self) -> str:
        """Human-readable German label for display."""
        return {
            PriceQuality.EXACT: "Exakter Treffer",
            PriceQuality.ESTIMATED_FROM_CONDITION: "Geschätzt aus anderem Zustand",
            PriceQuality.ESTIMATED_FROM_LANGUAGE: "Geschätzt aus anderer Sprache",
            PriceQuality.AVERAGE: "Durchschnitt",
            PriceQuality.MARKET_TREND: "Marktpreis (tcgdex)",
            PriceQuality.NO_PRICE: "Kein Preis gefunden",
            PriceQuality.MANUAL: "Manuell eingetragen",
        }[self]

    @classmethod
    def from_value(cls, value: str | None) -> "PriceQuality":
        """Resolve a stored value to a member, defaulting to NO_PRICE."""
        if value is None:
            return cls.NO_PRICE
        try:
            return cls(value)
        except ValueError:
            return cls.NO_PRICE


class SealedCategory(Enum):
    """Fixed vocabulary of sealed-product types (booster box, ETB, ...).

    Sealed products used to store their category as arbitrary free text
    parsed off Cardmarket's own breadcrumb -- fine for display, but useless
    for sorting/grouping, since near-identical products worded their
    breadcrumb slightly differently. This fixed list (researched against
    Cardmarket's own category taxonomy -- ``/Products/Booster-Boxes``,
    ``/Boosters``, ``/Box-Sets``, ``/Elite-Trainer-Boxes``, ``/Tins``,
    ``/Blisters`` are real, confirmed category URLs -- plus other common
    Pokemon TCG product types) makes the category column meaningfully
    sortable/groupable. ``OTHER`` is the deliberate catch-all for whatever
    doesn't fit -- new product lines get invented constantly, and forcing
    every one into a wrong bucket would be worse than an honest "Sonstiges".
    """

    BOOSTER_BOX = ("booster_box", "Booster Box")
    BOOSTER_BUNDLE = ("booster_bundle", "Booster Bundle")
    BOOSTER_PACK = ("booster_pack", "Booster Pack")
    ELITE_TRAINER_BOX = ("elite_trainer_box", "Elite Trainer Box")
    BOX_SET = ("box_set", "Box Set")
    TIN = ("tin", "Tin")
    BLISTER = ("blister", "Blister")
    PREMIUM_COLLECTION = ("premium_collection", "Premium Collection")
    BUILD_AND_BATTLE = ("build_and_battle", "Build & Battle Box")
    THEME_DECK = ("theme_deck", "Theme Deck")
    PIN_COLLECTION = ("pin_collection", "Pin Collection")
    OTHER = ("other", "Sonstiges")

    def __init__(self, code: str, label: str) -> None:
        self.code = code
        self.label = label

    @classmethod
    def from_code(cls, code: str | None) -> "SealedCategory":
        """Resolve a stored code (e.g. ``"tin"``) to a member, defaulting to OTHER."""
        if code is None:
            return cls.OTHER
        for member in cls:
            if member.code.casefold() == str(code).casefold():
                return member
        return cls.OTHER

    @classmethod
    def guess_from_text(cls, text: str) -> "SealedCategory":
        """Best-effort match of free text (e.g. a Cardmarket breadcrumb like

        "Booster Boxes") to a fixed category -- never raises, falls back to
        OTHER. Only a starting suggestion: the add/edit dialog always shows
        this as an overridable dropdown, since the guess can be wrong.
        """
        normalized = text.strip().casefold()
        if not normalized:
            return cls.OTHER
        for keyword, member in sorted(
            _CATEGORY_KEYWORDS.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if keyword in normalized:
                return member
        return cls.OTHER


#: Keywords matched (as substrings) against free text -- longest keyword
#: wins first, so e.g. "Booster Box" is checked before the bare "Booster"
#: that would otherwise also match it. Covers both Cardmarket's own plural
#: breadcrumb wording ("Booster Boxes") and common singular/alternate
#: phrasing a user might type by hand.
_CATEGORY_KEYWORDS: dict[str, SealedCategory] = {
    "booster box": SealedCategory.BOOSTER_BOX,
    "booster boxes": SealedCategory.BOOSTER_BOX,
    "display": SealedCategory.BOOSTER_BOX,
    "booster bundle": SealedCategory.BOOSTER_BUNDLE,
    "booster bundles": SealedCategory.BOOSTER_BUNDLE,
    "elite trainer box": SealedCategory.ELITE_TRAINER_BOX,
    "elite trainer boxes": SealedCategory.ELITE_TRAINER_BOX,
    "etb": SealedCategory.ELITE_TRAINER_BOX,
    "box set": SealedCategory.BOX_SET,
    "box sets": SealedCategory.BOX_SET,
    "starter": SealedCategory.BOX_SET,
    "tin": SealedCategory.TIN,
    "tins": SealedCategory.TIN,
    "blister": SealedCategory.BLISTER,
    "blisters": SealedCategory.BLISTER,
    "premium collection": SealedCategory.PREMIUM_COLLECTION,
    "special collection": SealedCategory.PREMIUM_COLLECTION,
    "build & battle": SealedCategory.BUILD_AND_BATTLE,
    "build and battle": SealedCategory.BUILD_AND_BATTLE,
    "theme deck": SealedCategory.THEME_DECK,
    "battle deck": SealedCategory.THEME_DECK,
    "pin collection": SealedCategory.PIN_COLLECTION,
    "booster": SealedCategory.BOOSTER_PACK,
    "boosters": SealedCategory.BOOSTER_PACK,
}


class ExportFormat(Enum):
    """A file format the collection can be exported to."""

    CSV = ("csv", "CSV")
    EXCEL = ("xlsx", "Excel")
    JSON = ("json", "JSON")
    PDF = ("pdf", "PDF")

    def __init__(self, extension: str, label: str) -> None:
        self.extension = extension
        self.label = label


class ExportTarget(Enum):
    """What to export: owned cards, or owned sealed products.

    Two entirely different row shapes (see ``app/export/models.py``) --
    always exported as separate files, never merged into one.
    """

    CARDS = "cards"
    SEALED = "sealed"

    @property
    def label(self) -> str:
        """Human-readable label for display (German, translated via app.i18n)."""
        return {self.CARDS: "Karten", self.SEALED: "Sealed-Produkte"}[self]
