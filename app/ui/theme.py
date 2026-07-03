"""Application theming: light and dark mode expressed as Qt style sheets.

The GUI is styled centrally here so individual widgets stay free of colour
literals. A :class:`Theme` value maps to a colour palette, which is rendered
into a Qt style sheet (QSS) and applied to the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Theme(str, Enum):
    """Available colour themes."""

    LIGHT = "light"
    DARK = "dark"

    def toggled(self) -> "Theme":
        """Return the opposite theme."""
        return Theme.DARK if self is Theme.LIGHT else Theme.LIGHT


@dataclass(frozen=True, slots=True)
class Palette:
    """A flat set of semantic colours used to build the style sheet."""

    window: str
    panel: str
    text: str
    muted: str
    border: str
    accent: str
    accent_hover: str
    selection: str
    selection_text: str


_LIGHT = Palette(
    window="#f4f5f8",
    panel="#ffffff",
    text="#1f2430",
    muted="#6b7280",
    border="#e2e5ea",
    accent="#2f6fed",
    accent_hover="#2559c9",
    selection="#e6efff",
    selection_text="#12203a",
)

_DARK = Palette(
    window="#1e2027",
    panel="#262a33",
    text="#e6e8ee",
    muted="#9aa2b1",
    border="#333a46",
    accent="#4c8dff",
    accent_hover="#3f78e0",
    selection="#2f3b52",
    selection_text="#eaf1ff",
)

_PALETTES: dict[Theme, Palette] = {Theme.LIGHT: _LIGHT, Theme.DARK: _DARK}


def palette_for(theme: Theme) -> Palette:
    """Return the colour palette backing a theme."""
    return _PALETTES[theme]


def build_stylesheet(theme: Theme) -> str:
    """Render the full application style sheet for a theme."""
    p = palette_for(theme)
    return f"""
    QMainWindow, QWidget {{
        background-color: {p.window};
        color: {p.text};
        font-family: "Segoe UI", "Noto Sans", sans-serif;
        font-size: 10pt;
    }}
    QWidget#Panel {{
        background-color: {p.panel};
        border: 1px solid {p.border};
        border-radius: 10px;
    }}
    QLabel#PanelHeader {{
        font-size: 12pt;
        font-weight: 600;
        padding: 4px 2px 8px 2px;
        border: none;
        background: transparent;
    }}
    QLabel#FieldLabel {{
        color: {p.muted};
        border: none;
        background: transparent;
    }}
    QLabel#FieldValue {{
        font-weight: 600;
        border: none;
        background: transparent;
    }}
    QLabel#EmptyState {{
        color: {p.muted};
        border: none;
        background: transparent;
    }}
    QToolBar {{
        background-color: {p.panel};
        border-bottom: 1px solid {p.border};
        padding: 6px 8px;
        spacing: 8px;
    }}
    QToolBar QToolButton {{
        background: transparent;
        color: {p.text};
        padding: 6px 10px;
        border-radius: 8px;
    }}
    QToolBar QToolButton:hover {{
        background-color: {p.selection};
    }}
    QLineEdit {{
        background-color: {p.window};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {p.accent};
        selection-color: #ffffff;
    }}
    QLineEdit:focus {{
        border: 1px solid {p.accent};
    }}
    QPushButton {{
        background-color: {p.accent};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {p.accent_hover};
    }}
    QPushButton:disabled {{
        background-color: {p.border};
        color: {p.muted};
    }}
    QPushButton#Secondary {{
        background-color: transparent;
        color: {p.accent};
        border: 1px solid {p.accent};
    }}
    QPushButton#Secondary:hover {{
        background-color: {p.selection};
    }}
    QListWidget, QTableWidget, QTableView {{
        background-color: {p.panel};
        border: 1px solid {p.border};
        border-radius: 8px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 6px;
    }}
    QListWidget::item:selected, QTableView::item:selected {{
        background-color: {p.selection};
        color: {p.selection_text};
    }}
    QListWidget::item:hover {{
        background-color: {p.selection};
    }}
    QHeaderView::section {{
        background-color: {p.window};
        color: {p.muted};
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {p.border};
        font-weight: 600;
    }}
    QTableWidget {{
        gridline-color: {p.border};
    }}
    QSplitter::handle {{
        background: transparent;
    }}
    QStatusBar {{
        background-color: {p.panel};
        border-top: 1px solid {p.border};
        color: {p.muted};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    """
