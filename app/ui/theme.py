"""Application theming: a single dark navy style sheet.

The GUI is styled centrally here so individual widgets stay free of colour
literals. :func:`build_stylesheet` renders the :data:`PALETTE` into a Qt
style sheet (QSS) that's applied to the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    """A flat set of semantic colours used to build the style sheet."""

    window: str
    panel: str
    panel_raised: str
    text: str
    muted: str
    border: str
    accent: str
    accent_hover: str
    accent_soft: str
    accent_secondary: str
    selection: str
    selection_text: str
    positive: str
    negative: str


#: Dark navy background, warm orange/yellow accents — the app's only theme.
PALETTE = Palette(
    window="#10141c",
    panel="#1a2233",
    panel_raised="#212a3d",
    text="#e8ecf5",
    muted="#8b95ac",
    border="#2b3550",
    accent="#ff9d45",
    accent_hover="#ffb066",
    accent_soft="#3a2e22",
    accent_secondary="#ffd166",
    selection="#3a3320",
    selection_text="#ffe8c2",
    positive="#5bd88a",
    negative="#ff6b6b",
)


def build_stylesheet() -> str:
    """Render the application's single dark style sheet."""
    p = PALETTE
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
        border-radius: 12px;
    }}
    QWidget#ArtworkStage {{
        background-color: {p.panel_raised};
        border: 1px solid {p.accent};
        border-radius: 14px;
    }}
    QLabel#PanelHeader {{
        font-size: 12pt;
        font-weight: 700;
        color: {p.accent_secondary};
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
    QLabel#PercentPositive {{
        color: {p.positive};
        font-weight: 700;
        font-size: 12pt;
        border: none;
        background: transparent;
    }}
    QLabel#PercentNegative {{
        color: {p.negative};
        font-weight: 700;
        font-size: 12pt;
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
        color: {p.accent_secondary};
    }}
    QLineEdit {{
        background-color: {p.window};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {p.accent};
        selection-color: #1a1408;
    }}
    QLineEdit:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox {{
        background-color: {p.window};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
    }}
    QComboBox:focus, QComboBox:on {{
        border: 1px solid {p.accent};
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QPushButton {{
        background-color: {p.accent};
        color: #1a1408;
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 700;
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
        background-color: {p.accent_soft};
    }}
    QPushButton#Danger {{
        background-color: transparent;
        color: {p.negative};
        border: 1px solid {p.negative};
    }}
    QPushButton#Danger:hover {{
        background-color: #3a1f1f;
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
        border-bottom: 1px solid {p.accent};
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
    QScrollBar::handle:vertical:hover {{
        background: {p.accent};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QDockWidget {{
        color: {p.text};
        titlebar-close-icon: none;
    }}
    QDockWidget::title {{
        background-color: {p.panel};
        padding: 8px 10px;
        font-weight: 700;
        color: {p.accent_secondary};
        border-bottom: 1px solid {p.border};
    }}
    """
