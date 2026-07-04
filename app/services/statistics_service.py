"""Aggregates the owned collection into the numbers Schritt 10 asked for.

Every number here is derived purely from already-persisted data (no network
calls, no Cardmarket automation) — a straightforward Python-side aggregation
over the cards + price history already loaded via the existing
:class:`~app.services.card_service.CardService`/
:class:`~app.services.collection_service.CollectionService`/
:class:`~app.database.repositories.price_repository.PriceRepository`. This is
the only layer the GUI is allowed to call into for statistics.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from app.database.repositories.price_repository import PriceRepository
from app.models.card import Card, CardFilter
from app.models.collection import Collection
from app.services.card_service import CardService
from app.services.collection_service import CollectionService

#: How many cards to list under "Teuerste Karten".
_TOP_EXPENSIVE_CARDS = 10
#: A card whose price is older than this (or was never priced at all) shows
#: up under "Karten mit veraltetem Preis" -- the exact figure the user gave
#: as their own example ("seit 3 Monaten nicht aktualisiert").
STALE_PRICE_THRESHOLD_DAYS = 90


@dataclass(frozen=True, slots=True)
class CollectionValueSummary:
    """Total owned value of a single collection."""

    collection_id: int
    name: str
    card_count: int
    total_value: float


@dataclass(frozen=True, slots=True)
class ValueBreakdownEntry:
    """Total owned value grouped by one attribute (set/language/condition)."""

    label: str
    total_value: float


@dataclass(frozen=True, slots=True)
class PriceIncreaseHighlight:
    """The single card whose latest price update rose the most (in %)."""

    card: Card
    previous_price: float
    latest_price: float
    percent_change: float


@dataclass(frozen=True, slots=True)
class StalePriceEntry:
    """A card whose price is old (or was never determined at all).

    ``days_since_update`` is ``None`` for a card that has never had a price
    lookup run at all -- there's no date to show, just "never".
    """

    card: Card
    days_since_update: int | None


@dataclass(frozen=True, slots=True)
class StatisticsOverview:
    """Everything the statistics view shows, computed in one pass."""

    per_collection: list[CollectionValueSummary]
    grand_total: float
    #: Most recent ``price_updated_at`` across every priced card -- shown
    #: next to the grand total so it's clear *when* that number is from,
    #: not just what it is.
    as_of: str | None
    value_by_set: list[ValueBreakdownEntry]
    value_by_language: list[ValueBreakdownEntry]
    value_by_condition: list[ValueBreakdownEntry]
    most_expensive_cards: list[Card]
    biggest_price_increase: PriceIncreaseHighlight | None
    #: Cards whose price is older than STALE_PRICE_THRESHOLD_DAYS (or was
    #: never determined), most stale/never-priced first.
    stale_price_cards: list[StalePriceEntry]


def days_since_price_update(card: Card, now: datetime | None = None) -> int | None:
    """Days since ``card``'s price was last determined, or ``None`` if never."""
    if card.price_updated_at is None:
        return None
    now = now or datetime.now(timezone.utc)
    updated_at = datetime.fromisoformat(card.price_updated_at)
    return (now - updated_at).days


def is_price_stale(card: Card, now: datetime | None = None) -> bool:
    """Whether ``card``'s price is old enough to nudge the user to refresh it.

    Reused by :class:`~app.ui.widgets.card_list_panel.CardListPanel` (a "!"
    marker next to the price) so the threshold is only defined once.
    """
    days = days_since_price_update(card, now)
    return days is None or days >= STALE_PRICE_THRESHOLD_DAYS


def _value_of(card: Card) -> float:
    return card.total_value or 0.0


def _sorted_breakdown(totals: dict[str, float]) -> list[ValueBreakdownEntry]:
    return [
        ValueBreakdownEntry(label=label, total_value=total)
        for label, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


class StatisticsService:
    """Computes :class:`StatisticsOverview` from the current owned collection."""

    def __init__(
        self,
        card_service: CardService,
        collection_service: CollectionService,
        price_repository: PriceRepository,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._cards = card_service
        self._collections = collection_service
        self._prices = price_repository
        self._now = now

    def compute_overview(self) -> StatisticsOverview:
        """Aggregate every owned card, across every collection, into one overview."""
        all_cards = self._cards.search_cards(CardFilter(collection_id=None))
        collections = self._collections.list_collections()

        per_collection = self._per_collection_summary(all_cards, collections)
        grand_total = round(sum(summary.total_value for summary in per_collection), 2)

        return StatisticsOverview(
            per_collection=per_collection,
            grand_total=grand_total,
            as_of=self._most_recent_update(all_cards),
            value_by_set=self._breakdown_by(all_cards, lambda card: card.set_name or "—"),
            value_by_language=self._breakdown_by(all_cards, lambda card: card.language.label),
            value_by_condition=self._breakdown_by(all_cards, lambda card: card.condition.label),
            most_expensive_cards=self._most_expensive(all_cards),
            biggest_price_increase=self._biggest_price_increase(all_cards),
            stale_price_cards=self._stale_price_cards(all_cards),
        )

    def _per_collection_summary(
        self, all_cards: list[Card], collections: list[Collection]
    ) -> list[CollectionValueSummary]:
        totals: dict[int, float] = defaultdict(float)
        counts: dict[int, int] = defaultdict(int)
        for card in all_cards:
            totals[card.collection_id] += _value_of(card)
            counts[card.collection_id] += 1
        return [
            CollectionValueSummary(
                collection_id=collection.id,
                name=collection.name,
                card_count=counts.get(collection.id, 0),
                total_value=round(totals.get(collection.id, 0.0), 2),
            )
            for collection in collections
        ]

    def _breakdown_by(
        self, all_cards: list[Card], key: Callable[[Card], str]
    ) -> list[ValueBreakdownEntry]:
        totals: dict[str, float] = defaultdict(float)
        for card in all_cards:
            totals[key(card)] += _value_of(card)
        return _sorted_breakdown(totals)

    def _most_expensive(self, all_cards: list[Card]) -> list[Card]:
        priced = [card for card in all_cards if card.current_price is not None]
        priced.sort(key=_value_of, reverse=True)
        return priced[:_TOP_EXPENSIVE_CARDS]

    def _biggest_price_increase(self, all_cards: list[Card]) -> PriceIncreaseHighlight | None:
        best: PriceIncreaseHighlight | None = None
        for card in all_cards:
            if card.current_price is None:
                continue
            records = self._prices.list_for_card(card.id)
            if len(records) < 2:
                continue
            previous, latest = records[-2].price, records[-1].price
            if previous <= 0:
                continue
            percent_change = (latest - previous) / previous * 100
            if percent_change <= 0:
                continue
            if best is None or percent_change > best.percent_change:
                best = PriceIncreaseHighlight(
                    card=card,
                    previous_price=previous,
                    latest_price=latest,
                    percent_change=percent_change,
                )
        return best

    def _most_recent_update(self, all_cards: list[Card]) -> str | None:
        timestamps = [card.price_updated_at for card in all_cards if card.price_updated_at]
        return max(timestamps) if timestamps else None

    def _stale_price_cards(self, all_cards: list[Card]) -> list[StalePriceEntry]:
        now = self._now()
        entries = [
            StalePriceEntry(card=card, days_since_update=days_since_price_update(card, now))
            for card in all_cards
            if is_price_stale(card, now)
        ]
        # Never-priced cards first (days_since_update=None sorts as "infinite"),
        # then oldest/most-overdue first.
        entries.sort(
            key=lambda entry: (
                entry.days_since_update is not None,
                -(entry.days_since_update or 0),
            )
        )
        return entries
