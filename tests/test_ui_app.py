"""Tests for the Windows taskbar-identity fix in app/ui/app.py."""

from __future__ import annotations

import ctypes

from app.ui.app import _set_windows_app_user_model_id


def test_sets_the_windows_app_user_model_id(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        ctypes.windll.shell32,
        "SetCurrentProcessExplicitAppUserModelID",
        lambda app_id: calls.append(app_id),
    )

    _set_windows_app_user_model_id()

    assert calls == ["Codeon.PokemonCollectionManager.Desktop.1"]


def test_never_raises_when_the_call_fails(monkeypatch) -> None:
    def _raise(app_id):
        raise OSError("no shell32")

    monkeypatch.setattr(ctypes.windll.shell32, "SetCurrentProcessExplicitAppUserModelID", _raise)

    _set_windows_app_user_model_id()  # must not raise
