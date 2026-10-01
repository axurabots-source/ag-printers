"""Vector icons for the sidebar, painted with Qt (no extra dependencies).

Icons are drawn on a 20x20 logical grid and rendered at 2x (40px) so they
stay crisp. Colours are parameters so the same glyph can be tinted for
normal / hover / active states.
"""

from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

#: Sidebar label -> icon kind for every navigation item.
NAV_ICONS: dict[str, str] = {
    "Dashboard": "dashboard",
    "Parties": "parties",
    "Purchase Orders": "purchase_orders",
    "New Job": "new_job",
    "Gate Pass": "gate_pass",
    "Bills": "bills",
    "Invoices": "bills",
    "Costing": "costing",
    "Sales": "sales",
    "Ledger": "ledger",
    "Reports": "reports",
    "Items": "items",
    "Inventory": "items",
    "Settings": "settings",
}

_DESIGN = 20  # logical design grid


def _pen(color: str, width: float = 1.6) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _dashboard(p: QPainter, color: str) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(2.5, 2.5, 6.4, 6.4), 1.6, 1.6)
    p.drawRoundedRect(QRectF(11.1, 2.5, 6.4, 6.4), 1.6, 1.6)
    p.drawRoundedRect(QRectF(2.5, 11.1, 6.4, 6.4), 1.6, 1.6)
    p.drawRoundedRect(QRectF(11.1, 11.1, 6.4, 6.4), 1.6, 1.6)


def _parties(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(2.8, 3.2, 6.2, 6.2))
    left = QPainterPath()
    left.moveTo(1.8, 16.6)
    left.cubicTo(1.8, 11.4, 10.0, 11.4, 10.0, 16.6)
    p.drawPath(left)
    p.drawEllipse(QRectF(11.6, 5.0, 5.2, 5.2))
    right = QPainterPath()
    right.moveTo(11.2, 16.6)
    right.cubicTo(11.2, 12.4, 18.6, 12.4, 18.6, 16.6)
    p.drawPath(right)


def _purchase_orders(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    doc = QPainterPath()
    doc.moveTo(4.6, 2.6)
    doc.lineTo(12.2, 2.6)
    doc.lineTo(15.4, 5.8)
    doc.lineTo(15.4, 17.4)
    doc.lineTo(4.6, 17.4)
    doc.closeSubpath()
    p.drawPath(doc)
    fold = QPainterPath()
    fold.moveTo(12.2, 2.6)
    fold.lineTo(12.2, 5.8)
    fold.lineTo(15.4, 5.8)
    p.drawPath(fold)
    p.drawLine(QLineF(7.0, 9.4, 13.0, 9.4))
    p.drawLine(QLineF(7.0, 12.4, 13.0, 12.4))


def _new_job(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    doc = QPainterPath()
    doc.moveTo(4.6, 2.6)
    doc.lineTo(11.4, 2.6)
    doc.lineTo(15.4, 6.6)
    doc.lineTo(15.4, 17.4)
    doc.lineTo(4.6, 17.4)
    doc.closeSubpath()
    p.drawPath(doc)
    fold = QPainterPath()
    fold.moveTo(11.4, 2.6)
    fold.lineTo(11.4, 6.6)
    fold.lineTo(15.4, 6.6)
    p.drawPath(fold)
    p.drawLine(QLineF(10.0, 9.5, 10.0, 14.5))
    p.drawLine(QLineF(7.5, 12.0, 12.5, 12.0))


def _gate_pass(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(2.4, 4.6, 15.2, 10.8), 2.2, 2.2)
    p.drawEllipse(QRectF(4.8, 6.9, 3.4, 3.4))
    shoulders = QPainterPath()
    shoulders.moveTo(4.0, 13.4)
    shoulders.cubicTo(4.0, 10.8, 9.0, 10.8, 9.0, 13.4)
    p.drawPath(shoulders)
    p.drawLine(QLineF(11.4, 8.4, 15.0, 8.4))
    p.drawLine(QLineF(11.4, 11.6, 15.0, 11.6))


def _bills(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    receipt = QPainterPath()
    receipt.moveTo(4.6, 2.6)
    receipt.lineTo(15.4, 2.6)
    receipt.lineTo(15.4, 17.4)
    receipt.lineTo(12.7, 15.7)
    receipt.lineTo(10.0, 17.4)
    receipt.lineTo(7.3, 15.7)
    receipt.lineTo(4.6, 17.4)
    receipt.closeSubpath()
    p.drawPath(receipt)
    p.drawLine(QLineF(7.2, 7.0, 12.8, 7.0))
    p.drawLine(QLineF(7.2, 10.2, 12.8, 10.2))


def _costing(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(4.2, 2.6, 11.6, 14.8), 2.0, 2.0)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(6.2, 4.8, 7.6, 2.8), 0.8, 0.8)
    for y in (10.4, 13.8):
        for x in (6.6, 9.6, 12.6):
            p.drawEllipse(QRectF(x, y, 1.7, 1.7))


def _sales(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    tag = QPainterPath()
    tag.moveTo(3.2, 10.6)
    tag.lineTo(10.6, 3.2)
    tag.lineTo(16.8, 3.2)
    tag.lineTo(16.8, 9.4)
    tag.lineTo(9.4, 16.8)
    tag.closeSubpath()
    p.drawPath(tag)
    p.drawEllipse(QRectF(13.2, 5.6, 2.0, 2.0))


def _ledger(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(4.2, 2.6, 11.6, 14.8), 1.6, 1.6)
    p.drawLine(QLineF(7.2, 2.6, 7.2, 17.4))
    p.drawLine(QLineF(9.6, 7.2, 13.4, 7.2))
    p.drawLine(QLineF(9.6, 10.4, 13.4, 10.4))

def _reports(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(3.4, 3.2, 3.4, 16.6))
    p.drawLine(QLineF(3.4, 16.6, 17.0, 16.6))
    trend = QPainterPath()
    trend.moveTo(6.0, 13.6)
    trend.lineTo(9.4, 10.2)
    trend.lineTo(12.4, 12.2)
    trend.lineTo(16.0, 6.8)
    p.drawPath(trend)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QRectF(15.1, 5.9, 1.8, 1.8))


def _items(p: QPainter, color: str) -> None:
    p.setPen(_pen(color))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(3.4, 6.4, 13.2, 10.6), 1.6, 1.6)
    p.drawLine(QLineF(3.4, 10.2, 16.6, 10.2))
    p.drawLine(QLineF(10.0, 10.2, 10.0, 17.0))
    handle = QPainterPath()
    handle.moveTo(8.0, 6.4)
    handle.lineTo(8.0, 4.8)
    handle.lineTo(12.0, 4.8)
    handle.lineTo(12.0, 6.4)
    p.drawPath(handle)


def _settings(p: QPainter, color: str) -> None:
    p.setPen(_pen(color, 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(8):
        angle = math.radians(i * 45.0)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        p.drawLine(
            QLineF(
                10 + 4.7 * cos_a,
                10 + 4.7 * sin_a,
                10 + 7.4 * cos_a,
                10 + 7.4 * sin_a,
            )
        )
    p.drawEllipse(QRectF(6.3, 6.3, 7.4, 7.4))
    p.drawEllipse(QRectF(8.8, 8.8, 2.4, 2.4))


def _chevron_left(p: QPainter, color: str) -> None:
    p.setPen(_pen(color, 1.9))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(12.4, 5.2)
    path.lineTo(7.6, 10.0)
    path.lineTo(12.4, 14.8)
    p.drawPath(path)


def _chevron_right(p: QPainter, color: str) -> None:
    p.setPen(_pen(color, 1.9))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(7.6, 5.2)
    path.lineTo(12.4, 10.0)
    path.lineTo(7.6, 14.8)
    p.drawPath(path)


_PAINTERS = {
    "dashboard": _dashboard,
    "parties": _parties,
    "purchase_orders": _purchase_orders,
    "new_job": _new_job,
    "gate_pass": _gate_pass,
    "bills": _bills,
    "costing": _costing,
    "sales": _sales,
    "ledger": _ledger,
    "reports": _reports,
    "items": _items,
    "settings": _settings,
    "chevron_left": _chevron_left,
    "chevron_right": _chevron_right,
}


@lru_cache(maxsize=256)
def icon(kind: str, color: str, px: int = 40) -> QIcon:
    """Return a cached :class:`QIcon` for *kind* painted in *color*."""
    return QIcon(pixmap(kind, color, px))


@lru_cache(maxsize=256)
def pixmap(kind: str, color: str, px: int = 20) -> QPixmap:
    """Return a cached :class:`QPixmap` for *kind* painted in *color*."""
    pix = QPixmap(px, px)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(px / _DESIGN, px / _DESIGN)
    _PAINTERS[kind](painter, color)
    painter.end()
    return pix


