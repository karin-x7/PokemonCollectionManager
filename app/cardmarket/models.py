"""Data transfer objects for CardTrader read-only lookups."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CardTraderExpansion:
    """A single CardTrader expansion (card set)."""

    id: int
    game_id: int
    code: str
    name: str
