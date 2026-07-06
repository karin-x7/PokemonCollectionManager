"""Tests for the tcgdex.dev set-icon fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

import app.catalog.tcgdex_set_icon as tcgdex_set_icon
from app.catalog.tcgdex_set_icon import ensure_tcgdex_set_icon

_SETS_PAYLOAD = [
    {"id": "me03", "name": "Perfect Order", "symbol": "https://assets.tcgdex.net/univ/me/me03/symbol"},
    {"id": "base1", "name": "Base", "symbol": "https://assets.tcgdex.net/univ/base/base1/symbol"},
]


def _session_returning(sets_payload, icon_content: bytes = b"fake-png-bytes") -> MagicMock:
    sets_response = MagicMock()
    sets_response.status_code = 200
    sets_response.json.return_value = sets_payload
    sets_response.raise_for_status.side_effect = None

    icon_response = MagicMock()
    icon_response.status_code = 200
    icon_response.content = icon_content
    icon_response.raise_for_status.side_effect = None

    session = MagicMock()
    session.get.side_effect = [sets_response, icon_response]
    return session


def setup_function() -> None:
    # The module-level sets cache must not leak between tests.
    tcgdex_set_icon._sets_cache = None


def test_downloads_and_caches_icon_by_matching_set_name(tmp_path) -> None:
    session = _session_returning(_SETS_PAYLOAD)

    path = ensure_tcgdex_set_icon("Perfect Order", icons_dir=tmp_path, session=session)

    assert path == str(tmp_path / "tcgdex_perfect_order.png")
    assert (tmp_path / "tcgdex_perfect_order.png").read_bytes() == b"fake-png-bytes"
    session.get.assert_any_call("https://assets.tcgdex.net/univ/me/me03/symbol.png", timeout=10.0)


def test_matches_case_insensitively(tmp_path) -> None:
    session = _session_returning(_SETS_PAYLOAD)

    path = ensure_tcgdex_set_icon("perfect order", icons_dir=tmp_path, session=session)

    assert path is not None


def test_second_call_reuses_cached_file_without_network_call(tmp_path) -> None:
    session = _session_returning(_SETS_PAYLOAD)

    first = ensure_tcgdex_set_icon("Perfect Order", icons_dir=tmp_path, session=session)
    second = ensure_tcgdex_set_icon("Perfect Order", icons_dir=tmp_path, session=session)

    assert first == second
    assert session.get.call_count == 2  # sets list + icon, never repeated


def test_blank_set_name_returns_none_without_network_call(tmp_path) -> None:
    session = MagicMock()

    assert ensure_tcgdex_set_icon("", icons_dir=tmp_path, session=session) is None
    session.get.assert_not_called()


def test_no_matching_set_returns_none(tmp_path) -> None:
    session = _session_returning(_SETS_PAYLOAD)

    assert ensure_tcgdex_set_icon("Totally Unknown Set", icons_dir=tmp_path, session=session) is None


def test_sets_list_request_failure_returns_none(tmp_path) -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")

    assert ensure_tcgdex_set_icon("Perfect Order", icons_dir=tmp_path, session=session) is None


def test_icon_download_failure_returns_none(tmp_path) -> None:
    sets_response = MagicMock()
    sets_response.status_code = 200
    sets_response.json.return_value = _SETS_PAYLOAD
    sets_response.raise_for_status.side_effect = None

    session = MagicMock()
    session.get.side_effect = [sets_response, requests.ConnectionError("boom")]

    assert ensure_tcgdex_set_icon("Perfect Order", icons_dir=tmp_path, session=session) is None
