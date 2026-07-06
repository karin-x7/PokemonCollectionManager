"""Tests for the live tcgdex.dev foreign-card-name translation fallback.

Uses a fake session keyed by URL (mirrors test_tcgdex_designation_lookup.py)
so each test can script the exact sequence of locale-search/English-lookup
requests without any real network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.catalog.tcgdex_name_translation import translate_foreign_card_name


class FakeSession:
    def __init__(self, responses: dict[str, list | dict | None]) -> None:
        self._responses = responses
        self.requested_paths: list[str] = []

    def get(self, url: str, timeout: float):
        path = url.split("api.tcgdex.net/v2", 1)[1]
        self.requested_paths.append(path)
        response = MagicMock()
        if path not in self._responses or self._responses[path] is None:
            response.status_code = 404
            response.raise_for_status.side_effect = None
            return response
        response.status_code = 200
        response.json.return_value = self._responses[path]
        response.raise_for_status.return_value = None
        return response


_DE_CANDIDATES = [
    {"id": "me01-119", "name": "Lillys Entschlossenheit"},
    {"id": "me01-184", "name": "Lillys Entschlossenheit"},
]
_EN_CARD = {"id": "me01-119", "name": "Lillie's Determination"}


def test_finds_english_name_via_german_locale() -> None:
    session = FakeSession(
        {
            "/de/cards?name=Lillys%20Entschlossenheit": _DE_CANDIDATES,
            "/en/cards/me01-119": _EN_CARD,
        }
    )

    result = translate_foreign_card_name("Lillys Entschlossenheit", session=session)

    assert result == "Lillie's Determination"


def test_no_candidates_in_any_locale_returns_none() -> None:
    session = FakeSession({})

    result = translate_foreign_card_name("Nichtvorhandene Karte", session=session)

    assert result is None
    # Every configured Western locale was tried.
    assert any("/de/cards" in p for p in session.requested_paths)
    assert any("/fr/cards" in p for p in session.requested_paths)
    assert any("/it/cards" in p for p in session.requested_paths)


def test_falls_through_to_next_locale_when_first_has_no_match() -> None:
    session = FakeSession(
        {
            "/de/cards?name=Determination%20de%20Lilie": [],
            "/fr/cards?name=Determination%20de%20Lilie": [
                {"id": "me01-119", "name": "Détermination de Lilie"}
            ],
            "/en/cards/me01-119": _EN_CARD,
        }
    )

    result = translate_foreign_card_name("Determination de Lilie", session=session)

    assert result == "Lillie's Determination"


def test_candidate_whose_english_lookup_404s_is_skipped() -> None:
    session = FakeSession(
        {
            "/de/cards?name=Lillys%20Entschlossenheit": [
                {"id": "missing-1", "name": "Lillys Entschlossenheit"},
                {"id": "me01-119", "name": "Lillys Entschlossenheit"},
            ],
            "/en/cards/missing-1": None,
            "/en/cards/me01-119": _EN_CARD,
        }
    )

    result = translate_foreign_card_name("Lillys Entschlossenheit", session=session)

    assert result == "Lillie's Determination"


def test_blank_query_returns_none_without_any_request() -> None:
    session = FakeSession({})

    result = translate_foreign_card_name("   ", session=session)

    assert result is None
    assert session.requested_paths == []


def test_ranks_exact_normalised_match_before_loose_substring_match() -> None:
    session = FakeSession(
        {
            "/de/cards?name=Entschlossenheit": [
                {"id": "other-1", "name": "Lillys Entschlossenheit Deluxe"},
                {"id": "me01-119", "name": "Entschlossenheit"},
            ],
            "/en/cards/me01-119": _EN_CARD,
        }
    )

    result = translate_foreign_card_name("Entschlossenheit", session=session)

    assert result == "Lillie's Determination"
    # The exact match's English lookup must have been requested first.
    assert session.requested_paths[-1] == "/en/cards/me01-119"
