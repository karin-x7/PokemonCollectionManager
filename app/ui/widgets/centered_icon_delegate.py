"""Shared item delegate that draws an item's icon centred in the cell.

Used wherever a table column shows an icon (flag, condition badge) with no
visible text (the text stays, invisible, purely so the existing
alphabetical sort still has something to compare) -- the default item
delegate would otherwise draw that icon hugging the cell's left edge (its
normal decoration-then-text layout), not centred, since the icon and text
are still two separate layout slots even when the text itself is painted
transparent.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class CenteredIconDelegate(QStyledItemDelegate):
    """Draws an item's icon centred in the cell, with no visible text."""

    def paint(self, painter, option, index) -> None:  # noqa: D102 — Qt override
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QIcon) or icon.isNull():
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.icon = QIcon()
        opt.text = ""
        style = opt.widget.style() if opt.widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        pixmap = icon.pixmap(icon.actualSize(option.rect.size()))
        x = option.rect.x() + (option.rect.width() - pixmap.width()) / 2
        y = option.rect.y() + (option.rect.height() - pixmap.height()) / 2
        painter.drawPixmap(int(x), int(y), pixmap)
