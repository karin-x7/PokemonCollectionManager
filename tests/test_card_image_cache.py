"""Tests for the card artwork download/cache helper."""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from app.catalog.card_image_cache import ensure_card_image
from app.catalog.models import CatalogCard

_CARD = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url="https://images.pokemontcg.io/ecard3/H32_small.png",
    image_large_url="https://images.pokemontcg.io/ecard3/H32.png",
)

_NO_IMAGE_CARD = CatalogCard(
    external_id="skg-h32",
    name="Xatu",
    set_name="Skyridge",
    set_code="skg",
    card_number="H32",
    rarity="Rare Holo",
    image_small_url=None,
    image_large_url=None,
)


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


def test_downloads_and_writes_image_to_photos_dir(tmp_path) -> None:
    session = _session_returning(b"fake-png-bytes")

    path = ensure_card_image(_CARD, photos_dir=tmp_path, session=session)

    assert path == str(tmp_path / "skg-h32.png")
    assert (tmp_path / "skg-h32.png").read_bytes() == b"fake-png-bytes"
    session.get.assert_called_once_with(
        _CARD.image_large_url, timeout=10.0
    )


def test_second_call_reuses_cached_file_without_network_call(tmp_path) -> None:
    session = _session_returning(b"fake-png-bytes")

    first = ensure_card_image(_CARD, photos_dir=tmp_path, session=session)
    second = ensure_card_image(_CARD, photos_dir=tmp_path, session=session)

    assert first == second
    session.get.assert_called_once()


def test_network_error_returns_none_instead_of_raising(tmp_path) -> None:
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")

    assert ensure_card_image(_CARD, photos_dir=tmp_path, session=session) is None
    assert list(tmp_path.iterdir()) == []


def test_http_error_status_returns_none(tmp_path) -> None:
    session = _session_returning(b"", status_code=500)

    assert ensure_card_image(_CARD, photos_dir=tmp_path, session=session) is None


def test_no_image_url_returns_none_without_network_call(tmp_path) -> None:
    session = MagicMock()

    assert ensure_card_image(_NO_IMAGE_CARD, photos_dir=tmp_path, session=session) is None
    session.get.assert_not_called()
