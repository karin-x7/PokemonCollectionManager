"""Tests for the domain enums and dataclasses."""

from __future__ import annotations

from app.models import Card, Collection, Condition, Language, PriceQuality, PriceRecord
from app.models.enums import SealedCategory


def test_condition_ordering_and_distance() -> None:
    assert Condition.MINT.order < Condition.POOR.order
    assert Condition.NEAR_MINT.distance_to(Condition.GOOD) == 2
    assert Condition.from_code("NM") is Condition.NEAR_MINT
    assert Condition.from_code("unknown") is Condition.NEAR_MINT  # safe default


def test_language_lookup() -> None:
    assert Language.from_code("DE") is Language.GERMAN
    assert Language.from_code(None) is Language.ENGLISH


def test_price_quality_labels_and_lookup() -> None:
    assert PriceQuality.EXACT.label == "Exakter Treffer"
    assert PriceQuality.from_value("average") is PriceQuality.AVERAGE
    assert PriceQuality.from_value("bogus") is PriceQuality.NO_PRICE


def test_sealed_category_lookup() -> None:
    assert SealedCategory.from_code("tin") is SealedCategory.TIN
    assert SealedCategory.from_code("bogus") is SealedCategory.OTHER
    assert SealedCategory.from_code(None) is SealedCategory.OTHER


def test_sealed_category_guess_from_text() -> None:
    # Cardmarket's own plural breadcrumb wording.
    assert SealedCategory.guess_from_text("Booster Boxes") is SealedCategory.BOOSTER_BOX
    assert SealedCategory.guess_from_text("Elite Trainer Boxes") is SealedCategory.ELITE_TRAINER_BOX
    assert SealedCategory.guess_from_text("Tins") is SealedCategory.TIN
    assert SealedCategory.guess_from_text("Blisters") is SealedCategory.BLISTER
    # A more specific keyword must win over a shorter one it also contains.
    assert SealedCategory.guess_from_text("Booster Box") is SealedCategory.BOOSTER_BOX
    assert SealedCategory.guess_from_text("Boosters") is SealedCategory.BOOSTER_PACK
    # Unrecognised text falls back to OTHER rather than raising.
    assert SealedCategory.guess_from_text("Something Entirely New") is SealedCategory.OTHER
    assert SealedCategory.guess_from_text("") is SealedCategory.OTHER


def test_card_total_value() -> None:
    card = Card(id=None, collection_id=1, name="Xatu", quantity=3, current_price=4.5)
    assert card.total_value == 13.5


def test_card_total_value_without_price_is_none() -> None:
    card = Card(id=None, collection_id=1, name="Xatu")
    assert card.total_value is None


def test_collection_defaults() -> None:
    coll = Collection(id=None, name="Binder")
    assert coll.description == ""
    assert coll.position == 0


def test_price_record_defaults() -> None:
    record = PriceRecord(id=None, card_id=1, price=10.0)
    assert record.currency == "EUR"
    assert record.price_quality is PriceQuality.NO_PRICE
