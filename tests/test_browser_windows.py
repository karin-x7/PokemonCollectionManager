"""Tests for the Windows-specific parts of the browser-reading backend.

Only ``_read_visible_text`` is tested here: every other function in
``app.pricing.browser._windows`` drives a real Chrome window (opening,
polling, resizing, focus-stealing workarounds), which has no deterministic,
sandboxable behaviour to test against -- those are verified manually
instead (see PROJECT_PROGRESS.md). ``_read_visible_text`` just walks a
``pywinauto``-style window's descendants, which a plain ``MagicMock`` can
stand in for.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.pricing.browser._windows import _read_visible_text


def _fake_descendant(text: str, visible: bool = True, raises: bool = False):
    node = MagicMock()
    node.is_visible.return_value = visible
    if raises:
        node.is_visible.side_effect = RuntimeError("control vanished mid-walk")
    node.window_text.return_value = text
    return node


def test_read_visible_text_skips_invisible_and_empty_and_errored_nodes() -> None:
    """Real bug this supports diagnosing: the window title can appear

    before the page's actual content has rendered, netting only a handful
    of lines (the browser's own chrome) instead of the usual several dozen
    -- see ``_open_and_capture_visible_text``'s one-retry-if-too-sparse
    logic, built after a live incident found exactly this.
    """
    window = MagicMock()
    window.descendants.return_value = [
        _fake_descendant("Available items"),
        _fake_descendant("", visible=True),  # empty text -- dropped
        _fake_descendant("hidden text", visible=False),  # invisible -- dropped
        _fake_descendant("irrelevant", raises=True),  # vanished mid-walk -- dropped
        _fake_descendant("13,90 €"),
    ]

    lines = _read_visible_text(window)

    assert lines == ["Available items", "13,90 €"]
