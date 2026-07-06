"""Tests for the set-symbol icon download/cache helper."""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from app.catalog.set_icon_cache import ensure_set_icon


def _session_returning(content: bytes, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    response.raise_for_status.side_effect = (
        None if status_code < 400 else requests.HTTPError(response=response)
    )
    session = MagicMock()
    session.get.return_value = response
    return session


def test_downloads_and_writes_icon_to_icons_dir(tmp_path) -> None:
    session = _session_returning(b"fake-png-bytes")

    path = ensure_set_icon("swsh7", icons_dir=tmp_path, session=session)

    assert path == str(tmp_path / "swsh7.png")
    assert (tmp_path / "swsh7.png").read_bytes() == b"fake-png-bytes"
    session.get.assert_called_once_with(
        "https://images.pokemontcg.io/swsh7/symbol.png", timeout=10.0
    )


def test_second_call_reuses_cached_file_without_network_call(tmp_path) -> None:
    session = _session_returning(b"fake-png-bytes")

    first = ensure_set_icon("swsh7", icons_dir=tmp_path, session=session)
    second = ensure_set_icon("swsh7", icons_dir=tmp_path, session=session)

    assert first == second
    session.get.assert_called_once()


def test_network_error_returns_none_instead_of_raising(tmp_path) -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")

    assert ensure_set_icon("swsh7", icons_dir=tmp_path, session=session) is None
    assert list(tmp_path.iterdir()) == []


def test_http_error_status_returns_none(tmp_path) -> None:
    session = _session_returning(b"", status_code=500)

    assert ensure_set_icon("swsh7", icons_dir=tmp_path, session=session) is None


def test_empty_set_code_returns_none_without_network_call(tmp_path) -> None:
    session = MagicMock()

    assert ensure_set_icon("", icons_dir=tmp_path, session=session) is None
    session.get.assert_not_called()


def test_falls_back_to_tcgdex_when_pokemontcgio_fails_and_set_name_given(
    tmp_path, monkeypatch
) -> None:
    # Real, live-confirmed case: pokemontcg.io can lag behind for a newly
    # released set ("Perfect Order", 2026-03-27) and 404 on its own icon
    # request, while tcgdex.dev already has one -- see
    # app.catalog.tcgdex_set_icon's own docs.
    session = _session_returning(b"", status_code=404)
    calls = []
    monkeypatch.setattr(
        "app.catalog.set_icon_cache.ensure_tcgdex_set_icon",
        lambda set_name, icons_dir, http: calls.append((set_name, icons_dir, http))
        or str(tmp_path / "tcgdex_perfect_order.png"),
    )

    path = ensure_set_icon("me3", "Perfect Order", icons_dir=tmp_path, session=session)

    assert path == str(tmp_path / "tcgdex_perfect_order.png")
    assert calls == [("Perfect Order", tmp_path, session)]


def test_does_not_fall_back_to_tcgdex_without_a_set_name(tmp_path) -> None:
    session = _session_returning(b"", status_code=404)

    assert ensure_set_icon("me3", icons_dir=tmp_path, session=session) is None
