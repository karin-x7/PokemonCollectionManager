"""Application theming: a single dark navy style sheet.

The GUI is styled centrally here so individual widgets stay free of colour
literals. :func:`build_stylesheet` renders the :data:`PALETTE` into a Qt
style sheet (QSS) that's applied to the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

#: A small white checkmark drawn with QPainter (see PROJECT_PROGRESS.md) --
#: shown on a checked QCheckBox, whose fully custom ::indicator styling
#: below otherwise replaces the native checkmark glyph with nothing.
_CHECK_ICON_PATH = (
    (Path(__file__).resolve().parent.parent / "resources" / "check.png")
    .as_posix()
)

#: A small muted-blue chevron replacing the native (visually clashing, see
#: QComboBox::down-arrow below) dropdown-arrow glyph.
_CHEVRON_ICON_PATH = (
    (Path(__file__).resolve().parent.parent / "resources" / "chevron.png")
    .as_posix()
)


@dataclass(frozen=True, slots=True)
class Palette:
    """A flat set of semantic colours used to build the style sheet."""

    window: str
    panel: str
    panel_raised: str
    input_bg: str
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
    #: Input fields/comboboxes -- a touch darker than the panel behind them
    #: so they read as "recessed" (user request), instead of panel_raised's
    #: lighter shade (still used for artwork stages/stat tiles, which are
    #: meant to look "raised" instead).
    input_bg="#161c29",
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


def _hex_to_rgba(hex_color: str, alpha: int) -> str:
    """Renders a "#rrggbb" palette colour as a QSS "rgba(r, g, b, a)" string
    -- lets subtle translucent overlays (row separators, hover tints) stay
    derived from the single palette instead of hand-picked separate colours.
    """
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


def enable_rounded_background(widget: QWidget) -> None:
    """Lets a ``Panel``/``StatCard`` QWidget *subclass* actually render its
    stylesheet background/border/border-radius.

    Every panel in this app is a subclass of ``QWidget`` (not a bare
    ``QWidget()``), and Qt only auto-applies a stylesheet's background/
    border/border-radius to bare QWidget instances -- a subclass silently
    renders a plain, unrounded rectangle (background/border colour still
    correct, radius just ignored) unless this attribute is set explicitly.
    Live-verified via a minimal repro: identical QSS, the only difference
    being a QWidget subclass vs a bare QWidget, reproduced the missing
    rounding every time.
    """
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


def apply_elevation(widget: QWidget) -> None:
    """Gives a panel/card widget a soft drop shadow for a sense of depth.

    A 1px QSS border alone reads flat against the window background --
    every top-level panel (Cards/Sealed/Wantlist lists, detail panels,
    Statistics tiles) calls this once after setting its ``Panel``/
    ``StatCard`` object name, so they read as raised surfaces instead of
    just outlined rectangles. Implies :func:`enable_rounded_background`.

    Kept deliberately small (short blur/offset): neighbouring panels sit
    only ~10px apart (the splitter handle's own width) -- a bigger shadow
    overflowed that gap and got hard-clipped by the next panel's opaque
    background, showing up as an ugly rectangular smudge in the corner
    (live-reported) instead of a smooth fade.
    """
    enable_rounded_background(widget)
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 3)
    shadow.setColor(QColor(0, 0, 0, 80))
    widget.setGraphicsEffect(shadow)


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
        border-radius: 14px;
    }}
    QLabel#PanelHeader {{
        font-size: 12pt;
        font-weight: 700;
        color: {p.accent_secondary};
        padding: 4px 2px 10px 2px;
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
        border-radius: 14px;
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
    /* Same fix, generalised: any plain QWidget used purely as a layout
       wrapper (grouping a few widgets that don't need their own visible
       box -- e.g. an icon+label row, a "label + action button" row)
       inherits the app-wide QWidget background-color rule above and shows
       up as an out-of-place dark rectangle wherever it sits on a lighter
       Panel/StatCard background (live-reported: the Set-icon row, the
       "All collections" checkbox row). Give such wrappers this object
       name to opt out. */
    QWidget#TransparentGroup {{
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
        outline: none;
    }}
    QToolBar QToolButton:hover {{
        background-color: {p.selection};
        color: {p.accent_secondary};
    }}
    QToolBar QToolButton:pressed {{
        background-color: {p.accent_soft};
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
    QToolBar QToolButton#ToolbarPrimaryAction:pressed {{
        background-color: {p.accent};
    }}
    QLineEdit, QPlainTextEdit, QSpinBox, QTextEdit, QTextBrowser {{
        background-color: {p.input_bg};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {p.accent};
        selection-color: #1a1408;
    }}
    QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover {{
        border: 1px solid {p.muted};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox {{
        background-color: {p.input_bg};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
    }}
    QComboBox:hover {{
        border: 1px solid {p.muted};
    }}
    QComboBox:focus, QComboBox:on {{
        border: 1px solid {p.accent};
    }}
    /* Default Qt draws a separate sunken box + native arrow glyph here,
       clashing with the flat/rounded field around it (user-reported: "the
       dropdown arrow looks bad"). A plain, borderless slot with a small
       custom-drawn chevron reads as one continuous control instead. */
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 24px;
        border: none;
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url({_CHEVRON_ICON_PATH});
        width: 10px;
        height: 10px;
    }}
    QComboBox QListView {{
        background-color: {p.input_bg};
        color: {p.text};
        border: 1px solid {p.accent};
        outline: none;
        padding: 2px;
    }}
    QComboBox QListView::item {{
        padding: 6px 10px;
    }}
    /* Without this, QCheckBox (itself a QWidget) paints the app-wide
       QWidget background-color rule as its own opaque rectangle -- a
       visible dark box tightly wrapping just the indicator+label,
       independent of whatever transparent/coloured parent it sits on
       (live-reported: "Alle Sammlungen" still had it after making its
       *parent* transparent -- the checkbox itself needed this too). */
    QCheckBox {{
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {p.border};
        border-radius: 4px;
        background-color: {p.panel_raised};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {p.accent};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p.accent};
        border: 1px solid {p.accent};
        image: url({_CHECK_ICON_PATH});
    }}
    QPushButton {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {p.accent_hover}, stop:1 {p.accent});
        color: #1a1408;
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 700;
        outline: none;
    }}
    QPushButton:hover {{
        background-color: {p.accent_hover};
    }}
    QPushButton:pressed {{
        background-color: {p.accent};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        background: {p.border};
        color: {p.muted};
    }}
    QPushButton#Secondary {{
        background: transparent;
        color: {p.accent};
        border: 1px solid {p.accent};
    }}
    QPushButton#Secondary:hover {{
        background-color: {p.accent_soft};
    }}
    QPushButton#Secondary:pressed {{
        background-color: {_hex_to_rgba(p.accent, 60)};
    }}
    QPushButton#Danger {{
        background: transparent;
        color: {p.negative};
        border: 1px solid {p.negative};
    }}
    QPushButton#Danger:hover {{
        background-color: #3a1f1f;
    }}
    QPushButton#Danger:pressed {{
        background-color: #4a2626;
    }}
    QListWidget, QTableWidget, QTableView {{
        background-color: {p.panel};
        border: 1px solid {p.border};
        border-radius: 10px;
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
        border-bottom: 1px solid {_hex_to_rgba(p.border, 130)};
    }}
    QHeaderView::section {{
        background-color: {p.window};
        color: {p.muted};
        padding: 10px 14px;
        border: none;
        border-bottom: 1px solid {p.accent};
        font-weight: 600;
    }}
    QTableWidget {{
        gridline-color: transparent;
    }}
    QSplitter::handle {{
        background: transparent;
    }}
    QSplitter::handle:hover {{
        background: {p.border};
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
