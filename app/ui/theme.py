"""Application theming: a single dark navy style sheet.

The GUI is styled centrally here so individual widgets stay free of colour
literals. :func:`build_stylesheet` renders the :data:`PALETTE` into a Qt
style sheet (QSS) that's applied to the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: A small white checkmark drawn with QPainter (see PROJECT_PROGRESS.md) --
#: shown on a checked QCheckBox, whose fully custom ::indicator styling
#: below otherwise replaces the native checkmark glyph with nothing.
_CHECK_ICON_PATH = (
    (Path(__file__).resolve().parent.parent / "resources" / "check.png")
    .as_posix()
)


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
    /* Search-results dialogs' "Suche läuft…" loading state. */
    QLabel#SearchLoadingLabel {{
        color: {p.accent};
        font-weight: 600;
        border: none;
        background: transparent;
    }}
    QProgressBar#SearchLoadingBar {{
        max-height: 6px;
        border: none;
        border-radius: 3px;
        background-color: {p.panel_raised};
    }}
    QProgressBar#SearchLoadingBar::chunk {{
        border-radius: 3px;
        background-color: {p.accent};
    }}
    QLabel#SectionHeader {{
        font-size: 12pt;
        font-weight: 700;
        color: {p.text};
        padding: 10px 0 2px 0;
        border: none;
        background: transparent;
    }}
    /* Statistics tab: "Karten"/"Sealed-Produkte" top-level dividers -- a
       bigger, accent-underlined header so the two portfolios read as
       clearly separate parts of the page, not just another SectionHeader
       among many. */
    QLabel#SuperSectionHeader {{
        font-size: 14pt;
        font-weight: 700;
        color: {p.accent_secondary};
        padding: 4px 0 6px 0;
        border-bottom: 2px solid {p.border};
        margin-top: 8px;
        background: transparent;
    }}
    /* Statistics tab: small "Karten"/"Sealed-Produkte" summary tiles at the
       top -- a raised card, distinct from the page's own background, so
       the headline numbers stand out before the detail tables below. */
    QWidget#StatCard {{
        background-color: {p.panel_raised};
        border: 1px solid {p.border};
        border-radius: 10px;
    }}
    QLabel#StatCardTitle {{
        color: {p.muted};
        font-weight: 600;
        border: none;
        background: transparent;
    }}
    QLabel#StatCardValue {{
        color: {p.accent_secondary};
        font-size: 16pt;
        font-weight: 700;
        border: none;
        background: transparent;
    }}
    /* Toolbar: the fixed-width container holding search field/button/
       "Karte manuell eintragen" (see main_window.py). Plain QWidgets
       otherwise inherit the app-wide QWidget background-color rule above,
       which is a *darker* shade than QToolBar's own -- invisible while
       full of children, but a jarring dark rectangle once they're hidden
       on non-"Karten" tabs (live-confirmed via screenshot). Transparent
       lets the toolbar's own background show through instead. */
    QWidget#ToolbarSearchGroup {{
        background: transparent;
        border: none;
    }}
    QLabel#StatCardSubtext {{
        color: {p.muted};
        font-size: 9pt;
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
    /* Active "Karten"/"Statistik" tab -- a subtle text colour + underline,
       not a solid fill, so it still reads as a plain tab-style toggle
       rather than a real action button like "Suchen"/"Karte manuell
       eintragen" (see ToolbarPrimaryAction below). */
    QToolBar QToolButton:checked {{
        background: transparent;
        color: {p.accent_secondary};
        font-weight: 700;
        border-bottom: 2px solid {p.accent};
    }}
    QToolBar QToolButton:checked:hover {{
        background-color: {p.selection};
    }}
    /* "Karte manuell eintragen" -- styled as a solid button like "Suchen",
       not a plain toolbar action (user request). */
    QToolBar QToolButton#ToolbarPrimaryAction {{
        background-color: {p.accent};
        color: #1a1408;
        font-weight: 700;
    }}
    QToolBar QToolButton#ToolbarPrimaryAction:hover {{
        background-color: {p.accent_hover};
    }}
    QLineEdit, QPlainTextEdit, QSpinBox, QTextEdit, QTextBrowser {{
        background-color: {p.panel_raised};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {p.accent};
        selection-color: #1a1408;
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox {{
        background-color: {p.panel_raised};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
    }}
    QComboBox:focus, QComboBox:on {{
        border: 1px solid {p.accent};
    }}
    QComboBox QListView {{
        background-color: {p.panel_raised};
        color: {p.text};
        border: 1px solid {p.accent};
        outline: none;
        padding: 2px;
    }}
    QComboBox QListView::item {{
        padding: 6px 10px;
    }}
    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {p.border};
        border-radius: 4px;
        background-color: {p.panel_raised};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p.accent};
        border: 1px solid {p.accent};
        image: url({_CHECK_ICON_PATH});
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
    QTableWidget::item {{
        padding: 8px 14px;
    }}
    QHeaderView::section {{
        background-color: {p.window};
        color: {p.muted};
        padding: 8px 14px;
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
