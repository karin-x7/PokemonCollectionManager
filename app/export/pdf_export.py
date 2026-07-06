"""PDF export: a simple, printable tabular report."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.export.models import COLUMNS, SEALED_COLUMNS, ExportRow, SealedExportRow
from app.utils.time import utc_now_iso

_TITLE = "Pokémon-Kartensammlung"
_SEALED_TITLE = "Pokémon Sealed-Produkte"
#: Long text columns (Name/Set/Notizen/Cardmarket-Link) get more room than
#: short fixed-format ones (Nr./Sprache/Zustand/Menge/...) -- a single even
#: split left those unreadably narrow on a 14-column landscape page.
_COLUMN_WIDTH_WEIGHTS = (1.2, 1.4, 1.4, 0.6, 0.7, 0.7, 1.0, 0.6, 0.7, 0.6, 1.1, 1.1, 1.4, 1.6)
#: Same idea, for the sealed-product's shorter column set (no Set/Nr./
#: Zustand/Extra/Sammlung; "Kategorie" instead).
_SEALED_COLUMN_WIDTH_WEIGHTS = (1.6, 1.2, 0.7, 0.6, 0.7, 0.6, 1.1, 1.1, 1.6, 1.8)


def write(rows: list[ExportRow], path: Path) -> None:
    """Write ``rows`` to ``path`` as a landscape A4 PDF table."""
    _write(rows, COLUMNS, _COLUMN_WIDTH_WEIGHTS, _TITLE, "Karte(n)", path)


def write_sealed(rows: list[SealedExportRow], path: Path) -> None:
    """Write sealed-product ``rows`` to ``path`` as a landscape A4 PDF table."""
    _write(rows, SEALED_COLUMNS, _SEALED_COLUMN_WIDTH_WEIGHTS, _SEALED_TITLE, "Produkt(e)", path)


def _write(
    rows: list[ExportRow] | list[SealedExportRow],
    columns: tuple[str, ...],
    column_width_weights: tuple[float, ...],
    title: str,
    unit_label: str,
    path: Path,
) -> None:
    document = SimpleDocTemplate(
        str(path), pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24
    )
    styles = getSampleStyleSheet()
    cell_style = styles["BodyText"]
    cell_style.fontSize = 7
    cell_style.leading = 9

    def _cell(value: object) -> Paragraph:
        # Paragraph parses its text as a small XML-like markup language --
        # a card name/note is free text the user controls and could contain
        # a bare "<"/"&"/">" (e.g. a note like "Zustand < NM"), which
        # crashes the parser unescaped. Card data is display text here,
        # never markup, so it must always be escaped.
        return Paragraph(escape(str(value)), cell_style)

    table_data = [list(columns)] + [[_cell(v) for v in row.as_tuple()] for row in rows]

    available_width = landscape(A4)[0] - 48
    total_weight = sum(column_width_weights)
    col_widths = [available_width * weight / total_weight for weight in column_width_weights]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#212a3d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    elements = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Stand: {utc_now_iso()} · {len(rows)} {unit_label}", styles["Normal"]),
        Spacer(1, 12),
        table,
    ]
    document.build(elements)
