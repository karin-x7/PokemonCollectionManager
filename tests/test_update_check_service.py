"""Tests for check_for_update: version comparison + best-effort failure handling."""

from __future__ import annotations

import requests

from app.services.update_check_service import UpdateInfo, check_for_update

_URL = "https://api.github.com/repos/codeonEXE/PokemonCollectionManager/releases/latest"


class _FakeResponse:
    def __init__(self, payload=None, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


def _release(tag: str) -> dict:
    return {"tag_name": tag, "html_url": f"https://github.com/x/x/releases/tag/{tag}"}


def test_returns_update_info_when_a_newer_release_exists(monkeypatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse(_release("v0.9.1")))

    info = check_for_update("0.9.0-alpha.1")

    assert info == UpdateInfo(version="0.9.1", url="https://github.com/x/x/releases/tag/v0.9.1")


def test_returns_none_when_already_up_to_date(monkeypatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse(_release("v0.9.0-alpha.1")))

    assert check_for_update("0.9.0-alpha.1") is None


def test_returns_none_when_current_is_newer_than_latest_release(monkeypatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse(_release("v0.8.0")))

    assert check_for_update("0.9.0") is None


def test_a_release_is_newer_than_its_own_prerelease(monkeypatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse(_release("v0.9.0")))

    info = check_for_update("0.9.0-alpha.1")

    assert info is not None
    assert info.version == "0.9.0"


def test_network_error_returns_none_instead_of_raising(monkeypatch) -> None:
    def raise_connection_error(*a, **kw):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", raise_connection_error)

    assert check_for_update("0.9.0-alpha.1") is None


def test_non_2xx_response_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse(status_code=403))

    assert check_for_update("0.9.0-alpha.1") is None


def test_malformed_payload_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse({"unexpected": "shape"}))

    assert check_for_update("0.9.0-alpha.1") is None
