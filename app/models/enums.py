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
    NO_PRICE = "no_price"

    @property
    def label(self) -> str:
        """Human-readable German label for display."""
        return {
            PriceQuality.EXACT: "Exakter Treffer",
            PriceQuality.ESTIMATED_FROM_CONDITION: "Geschätzt aus anderem Zustand",
            PriceQuality.ESTIMATED_FROM_LANGUAGE: "Geschätzt aus anderer Sprache",
            PriceQuality.AVERAGE: "Durchschnitt",
            PriceQuality.NO_PRICE: "Kein Preis gefunden",
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
