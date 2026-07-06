"""Condition badge colours, matching Cardmarket's own colour-coding.

Approximate, not pixel-sampled from Cardmarket's CSS -- close enough to be
immediately recognisable to anyone used to browsing Cardmarket's own offer
tables (worst/best condition is "red" vs. "green" at a glance, matching a
user's own mental model from that site), not a byte-exact colour match.
"""

from __future__ import annotations

from app.models.enums import Condition

#: Text colour to use on top of each background -- dark text for the paler
#: yellow/gold tones, white everywhere else, for reliable contrast.
CONDITION_COLORS: dict[Condition, tuple[str, str]] = {
    Condition.MINT: ("#1f8a70", "#ffffff"),
    Condition.NEAR_MINT: ("#4a9e3f", "#ffffff"),
    Condition.EXCELLENT: ("#8a8a3a", "#ffffff"),
    Condition.GOOD: ("#e0b400", "#1a1200"),
    Condition.LIGHT_PLAYED: ("#e07b18", "#ffffff"),
    Condition.PLAYED: ("#9c2b3e", "#ffffff"),
    Condition.POOR: ("#7a1f1f", "#ffffff"),
}
