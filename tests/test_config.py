"""Tests for app.config's frozen-vs-source BASE_DIR resolution.

PyInstaller sets ``sys.frozen = True`` and points ``sys.executable`` at the
built .exe; python.exe/pythonw.exe never set that attribute. The module
computes BASE_DIR at import time, so each case is exercised via
importlib.reload() with sys.frozen/sys.executable patched beforehand.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import app.config as config_module


def _reload_with(monkeypatch, *, frozen: bool, executable: str | None = None):
    if frozen:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", executable)
    else:
        monkeypatch.delattr(sys, "frozen", raising=False)
    return importlib.reload(config_module)


def test_base_dir_is_project_root_when_not_frozen(monkeypatch) -> None:
    reloaded = _reload_with(monkeypatch, frozen=False)
    try:
        assert reloaded.BASE_DIR == Path(__file__).resolve().parent.parent
    finally:
        importlib.reload(config_module)


def test_base_dir_is_exe_directory_when_frozen(monkeypatch, tmp_path) -> None:
    fake_exe = tmp_path / "PokemonCollectionManager.exe"
    reloaded = _reload_with(monkeypatch, frozen=True, executable=str(fake_exe))
    try:
        assert reloaded.BASE_DIR == tmp_path
    finally:
        importlib.reload(config_module)


def test_data_and_logs_dirs_stay_at_the_project_root_when_not_frozen(monkeypatch) -> None:
    reloaded = _reload_with(monkeypatch, frozen=False)
    try:
        project_root = Path(__file__).resolve().parent.parent
        assert reloaded.DATA_DIR == project_root / "data"
        assert reloaded.LOGS_DIR == project_root / "logs"
    finally:
        importlib.reload(config_module)


def test_data_and_logs_dirs_are_nested_under_a_named_folder_when_frozen(
    monkeypatch, tmp_path
) -> None:
    fake_exe = tmp_path / "PokemonCollectionManager.exe"
    reloaded = _reload_with(monkeypatch, frozen=True, executable=str(fake_exe))
    try:
        app_root = tmp_path / "PokemonCollectionManager"
        assert reloaded.DATA_DIR == app_root / "data"
        assert reloaded.LOGS_DIR == app_root / "logs"
    finally:
        importlib.reload(config_module)
