"""A4 Document Preview and Print engine — AG Printers (V0.9).

Renders 2 pages:
  - Page 1: BILL   (Sr, Description, Quantity, Rate, Amount, Total)
  - Page 2: DELIVERY CHALLAN (Sr, Description, Quantity)

Design highlights (V0.9):
  - Real AG logo loaded from app/assets/ag_logo.jpg
  - Georgia serif font for company name / badge / party name
  - All table cells CENTERED
  - Dark filled badge for document type
  - Alternating row shading, footer contact strip
"""

from __future__ import annotations

import math as _math
import os as _os
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# Standard A4 size in logical points at 96 DPI: 794 x 1123
A4_WIDTH = 794
A4_HEIGHT = 1123
ITEMS_PER_PAGE = 18

from app.ui.capitalized_input import capitalize_words

_LOGO_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(__file__)), "assets", "ag_logo.jpg"
)

def _load_logo() -> "QPixmap | None":
    if _os.path.exists(_LOGO_PATH):
        px = QPixmap(_LOGO_PATH)
        if not px.isNull():
            return px
    return None

_LOGO_PIXMAP: "QPixmap | None" = None


def _get_logo() -> "QPixmap | None":
    global _LOGO_PIXMAP
    if _LOGO_PIXMAP is None or _LOGO_PIXMAP.isNull():
        _LOGO_PIXMAP = _load_logo()
    return _LOGO_PIXMAP


def _format_pdf_date(val: str | None) -> str:
    """Format date cleanly as '28 Sep, 2026'."""
    if not val:
        return "—"
    try:
        from datetime import datetime
        clean = str(val).strip().replace("T", " ")
        if " " in clean:
            dt = datetime.fromisoformat(clean)
        else:
            dt = datetime.strptime(clean, "%Y-%m-%d")
        return dt.strftime("%d %b, %Y")
    except Exception:
        return str(val)


def get_document_page_count(data: dict[str, Any]) -> int:
    """Calculate the number of pages required for the items in the document."""
    items = data.get("items", [])
    if not items:
        return 1
    return max(1, _math.ceil(len(items) / ITEMS_PER_PAGE))


# ---------------------------------------------------------------------------

def paint_pad(
    painter: QPainter,
    page_kind: str,
    data: dict[str, Any],
    target_rect: QRectF,
    page_number: int = 1,
    total_pages: int = 1,
) -> None:
    """Render one A4 page (INVOICE or GATE PASS) into *target_rect*."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale_x = target_rect.width() / A4_WIDTH
    scale_y = target_rect.height() / A4_HEIGHT
    painter.translate(target_rect.left(), target_rect.top())
    painter.scale(scale_x, scale_y)

    # White paper
    painter.fillRect(0, 0, A4_WIDTH, A4_HEIGHT, QColor("#FFFFFF"))

    LM = 45.0            # left margin
    RM = A4_WIDTH - 45.0 # right margin
    TM = 30.0            # top margin
    CW = RM - LM         # content width

    # ── HEADER ────────────────────────────────────────────────────────────
    LOGO_SZ = 80
    logo = _get_logo()
    if logo is not None:
        painter.drawPixmap(
            QRectF(LM, TM, LOGO_SZ, LOGO_SZ).toRect(), logo
        )
    else:
        # Fallback text badge
        painter.setFont(QFont("Georgia", 28, QFont.Weight.Bold))
        painter.setPen(QColor("#0f172a"))
        painter.drawText(
            QRectF(LM, TM, LOGO_SZ, LOGO_SZ),
            Qt.AlignmentFlag.AlignCenter,
            "AG"
        )

    # Company name
    name_font = QFont("Georgia", 22, QFont.Weight.Bold)
    name_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
    painter.setFont(name_font)
    painter.setPen(QColor("#0f172a"))
    painter.drawText(
        QRectF(LM + LOGO_SZ + 10, TM + 6, CW - LOGO_SZ - 10 - 220, 36),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        "AG PRINTERS",
    )

    # Tagline
    tag_font = QFont("Georgia", 9)
    tag_font.setItalic(True)
    painter.setFont(tag_font)
    painter.setPen(QColor("#475569"))
    painter.drawText(
        QRectF(LM + LOGO_SZ + 10, TM + 46, CW - LOGO_SZ - 10 - 220, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        "Deals in All Kind of Offset Printing & Labels",
    )

    # Address right-aligned (prominent, readable)
    addr_font = QFont("Arial", 9.5)
    painter.setFont(addr_font)
    painter.setPen(QColor("#0F172A"))
    painter.drawText(
        QRectF(RM - 280, TM - 2, 280, LOGO_SZ + 10),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        "Suite # 4, 1st Floor, Sultania Center\n"
        "St # 7, Munshi Mohallah,\n"
        "Aminpur Bazar, Faisalabad.\n"
        "Mob: +92 300 966 9060\n"
        "E-mail: agprinters33@gmail.com",
    )

    HEADER_BOTTOM = TM + LOGO_SZ + 6
    painter.setPen(QPen(QColor("#0f172a"), 2.0))
    painter.drawLine(QPointF(LM, HEADER_BOTTOM), QPointF(RM, HEADER_BOTTOM))
    painter.setPen(QPen(QColor("#94a3b8"), 0.8))
    painter.drawLine(QPointF(LM, HEADER_BOTTOM + 3), QPointF(RM, HEADER_BOTTOM + 3))

    # ── DOCUMENT TYPE BADGE (transparent pill with black border & black text) ──
    BADGE_Y = HEADER_BOTTOM + 12
    BADGE_H = 26.0
    is_bill = page_kind in ("BILL", "INVOICE")
    doc_title = "INVOICE" if is_bill else "GATE PASS"

    if total_pages > 1:
        badge_label = f"{doc_title}  (PAGE {page_number} OF {total_pages})"
        BADGE_W = 270.0
        badge_font = QFont("Georgia", 9.5, QFont.Weight.Bold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    else:
        badge_label = doc_title
        BADGE_W = 200.0
        badge_font = QFont("Georgia", 11, QFont.Weight.Bold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.8)

    BADGE_X = (A4_WIDTH - BADGE_W) / 2.0
    badge_rect = QRectF(BADGE_X, BADGE_Y, BADGE_W, BADGE_H)

    badge_path = QPainterPath()
    badge_path.addRoundedRect(badge_rect, 5.0, 5.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#000000"), 1.2))
    painter.drawPath(badge_path)

    painter.setFont(badge_font)
    painter.setPen(QColor("#000000"))
    painter.drawText(
        badge_rect,
        Qt.AlignmentFlag.AlignCenter,
        badge_label,
    )

    # ── METADATA SECTION (Transparent cards with crisp black borders) ───────
    INFO_TOP = BADGE_Y + BADGE_H + 14
    INFO_H = 82.0
    BOX_BORDER_PEN = QPen(QColor("#000000"), 1.2)

    raw_date = data.get("bill_date") or data.get("challan_date") or data.get("date") or data.get("created_at") or ""
    date_str = _format_pdf_date(str(raw_date)) if raw_date else "—"

    party_str = capitalize_words(str(data.get("party_name") or data.get("party") or data.get("customer_name") or ""))

    raw_po = data.get("po_number") or data.get("po_no") or ""
    po_str = capitalize_words(str(raw_po)) if raw_po else ""

    raw_job = data.get("job_number") or data.get("job_no") or ""
    job_str = capitalize_words(str(raw_job)) if raw_job else ""

    raw_cust_po = data.get("customer_po") or data.get("cust_po") or ""
    cust_po_str = capitalize_words(str(raw_cust_po)) if raw_cust_po else ""

    raw_bill = data.get("bill_number") or data.get("bill_no") or data.get("bill_ref") or ""
    bill_no_str = str(raw_bill) if raw_bill else "—"

    raw_dc = data.get("challan_no") or data.get("challan_number") or data.get("gate_pass_number") or data.get("dc_no") or ""
    dc_no_str = str(raw_dc) if raw_dc else "—"

    LEFT_BOX_W = 405.0
    RIGHT_BOX_X = LM + LEFT_BOX_W + 14.0
    RIGHT_BOX_W = CW - (LEFT_BOX_W + 14.0)

    # 1. Left Card: Customer / Invoiced To (Transparent inside, black border)
    left_rect = QRectF(LM, INFO_TOP, LEFT_BOX_W, INFO_H)
    left_path = QPainterPath()
    left_path.addRoundedRect(left_rect, 6.0, 6.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(BOX_BORDER_PEN)
    painter.drawPath(left_path)

    # Invoiced / Delivered To Label
    lbl_font = QFont("Arial", 8, QFont.Weight.Bold)
    lbl_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
    painter.setFont(lbl_font)
    painter.setPen(QColor("#000000"))
    billed_tag = "INVOICED TO:" if is_bill else "DELIVERED TO:"
    painter.drawText(
        QRectF(LM + 14, INFO_TOP + 10, LEFT_BOX_W - 28, 14),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        billed_tag,
    )

    # Customer Party Name
    party_font = QFont("Georgia", 13, QFont.Weight.Bold)
    painter.setFont(party_font)
    painter.setPen(QColor("#000000"))
    painter.drawText(
        QRectF(LM + 14, INFO_TOP + 26, LEFT_BOX_W - 28, 22),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        party_str if party_str else "Cash Customer",
    )

    # Reference Badges (3 Chips: P.O., Job, Customer P.O.)
    badge_y = INFO_TOP + 52
    badge_h = 24.0
    chip_gap = 7.0
    chip_w = (LEFT_BOX_W - 28.0 - (chip_gap * 2.0)) / 3.0

    po_display = po_str if (po_str and po_str != "—") else "—"
    job_display = job_str if (job_str and job_str != "—") else "—"
    cust_po_display = cust_po_str if (cust_po_str and cust_po_str != "—") else "—"

    # Chip 1: P.O. Number
    c1_x = LM + 14
    c1_rect = QRectF(c1_x, badge_y, chip_w, badge_h)
    c1_path = QPainterPath()
    c1_path.addRoundedRect(c1_rect, 4.0, 4.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#000000"), 1.0))
    painter.drawPath(c1_path)

    painter.setFont(QFont("Arial", 7.2, QFont.Weight.Bold))
    painter.setPen(QColor("#000000"))
    painter.drawText(QRectF(c1_x + 4, badge_y, 24, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "PO:")
    painter.setFont(QFont("Arial", 8.2, QFont.Weight.Bold))
    painter.drawText(QRectF(c1_x + 28, badge_y, chip_w - 30, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, po_display)

    # Chip 2: Job Number
    c2_x = c1_x + chip_w + chip_gap
    c2_rect = QRectF(c2_x, badge_y, chip_w, badge_h)
    c2_path = QPainterPath()
    c2_path.addRoundedRect(c2_rect, 4.0, 4.0)
    painter.drawPath(c2_path)

    painter.setFont(QFont("Arial", 7.2, QFont.Weight.Bold))
    painter.drawText(QRectF(c2_x + 4, badge_y, 28, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "JOB:")
    painter.setFont(QFont("Arial", 8.2, QFont.Weight.Bold))
    painter.drawText(QRectF(c2_x + 32, badge_y, chip_w - 34, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, job_display)

    # Chip 3: Customer P.O. Number
    c3_x = c2_x + chip_w + chip_gap
    c3_rect = QRectF(c3_x, badge_y, chip_w, badge_h)
    c3_path = QPainterPath()
    c3_path.addRoundedRect(c3_rect, 4.0, 4.0)
    painter.drawPath(c3_path)

    painter.setFont(QFont("Arial", 7.2, QFont.Weight.Bold))
    painter.drawText(QRectF(c3_x + 4, badge_y, 34, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "C.PO:")
    painter.setFont(QFont("Arial", 8.2, QFont.Weight.Bold))
    painter.drawText(QRectF(c3_x + 38, badge_y, chip_w - 40, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, cust_po_display)

    # 2. Right Card: Invoice Details (Transparent inside, black border)
    right_rect = QRectF(RIGHT_BOX_X, INFO_TOP, RIGHT_BOX_W, INFO_H)
    right_path = QPainterPath()
    right_path.addRoundedRect(right_rect, 6.0, 6.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(BOX_BORDER_PEN)
    painter.drawPath(right_path)

    # Right Card Rows (Updated terminology: INVOICE NO & GATE PASS NO)
    meta_rows = [
        ("INVOICE NO:" if is_bill else "GATE PASS NO:", bill_no_str if is_bill else dc_no_str),
        ("DATE:", date_str),
        ("GATE PASS NO:" if is_bill else "INVOICE REF:", dc_no_str if is_bill else bill_no_str),
    ]

    row_y_offset = INFO_TOP + 8
    row_height = 22.0

    meta_lbl_font = QFont("Arial", 8.5, QFont.Weight.Bold)
    meta_lbl_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
    meta_val_font = QFont("Arial", 10, QFont.Weight.Bold)

    for lbl_text, val_text in meta_rows:
        painter.setFont(meta_lbl_font)
        painter.setPen(QColor("#000000"))
        painter.drawText(
            QRectF(RIGHT_BOX_X + 14, row_y_offset, 115, row_height),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            lbl_text,
        )

        painter.setFont(meta_val_font)
        painter.setPen(QColor("#000000"))
        painter.drawText(
            QRectF(RIGHT_BOX_X + 120, row_y_offset, RIGHT_BOX_W - 134, row_height),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            val_text,
        )

        row_y_offset += row_height

    # ── TABLE ─────────────────────────────────────────────────────────────
    TABLE_TOP = INFO_TOP + INFO_H + 16

    TH = 28.0       # table header height
    ROW_H = 32.0    # data row height
    TOT_H = 32.0    # totals row height

    num_rows = ITEMS_PER_PAGE
    TABLE_H = TH + (num_rows * ROW_H) + TOT_H
    TABLE_BOTTOM = TABLE_TOP + TABLE_H

    if is_bill:
        cw = {
            "sr":   44.0,
            "desc": CW - (44.0 + 90.0 + 100.0 + 120.0),
            "qty":  90.0,
            "rate": 100.0,
            "amt":  120.0,
        }
        cols = [
            ("SR.", cw["sr"]),
            ("DESCRIPTION", cw["desc"]),
            ("QUANTITY", cw["qty"]),
            ("RATE (RS.)", cw["rate"]),
            ("TOTAL AMOUNT", cw["amt"]),
        ]
    else:
        cw = {
            "sr":   55.0,
            "desc": CW - (55.0 + 140.0),
            "qty":  140.0,
        }
        cols = [
            ("SR.", cw["sr"]),
            ("DESCRIPTION", cw["desc"]),
            ("QUANTITY", cw["qty"]),
        ]

    BORDER = QPen(QColor("#000000"), 1.2)
    GRID   = QPen(QColor("#000000"), 1.0)

    # 1. Header fill
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillRect(QRectF(LM, TABLE_TOP, CW, TH), QColor("#f1f5f9"))

    # 2. Alternating row background fills (DONE FIRST - BEFORE ANY LINES!)
    for idx in range(num_rows):
        row_y = TABLE_TOP + TH + idx * ROW_H
        if idx % 2 == 1:
            painter.fillRect(QRectF(LM, row_y, CW, ROW_H), QColor("#f8fafc"))

    # 3. Totals row fill
    TOT_Y = TABLE_TOP + TH + num_rows * ROW_H
    painter.fillRect(QRectF(LM, TOT_Y, CW, TOT_H), QColor("#f1f5f9"))

    # 4. Horizontal Grid Lines (Drawn ON TOP of all background fills!)
    painter.setPen(GRID)
    painter.drawLine(QPointF(LM, TABLE_TOP + TH), QPointF(RM, TABLE_TOP + TH))
    for r in range(1, num_rows):
        y = TABLE_TOP + TH + r * ROW_H
        painter.drawLine(QPointF(LM, y), QPointF(RM, y))
    painter.drawLine(QPointF(LM, TOT_Y), QPointF(RM, TOT_Y))

    # 5. Vertical Column Dividers (Drawn ON TOP of all fills from TABLE_TOP to TABLE_BOTTOM!)
    cur_x = LM
    for i, (title, width) in enumerate(cols):
        cur_x += width
        if i < len(cols) - 1:
            painter.setPen(GRID)
            painter.drawLine(QPointF(cur_x, TABLE_TOP), QPointF(cur_x, TABLE_BOTTOM))

    # 6. Outer table border & header border
    painter.setPen(BORDER)
    painter.drawRect(QRectF(LM, TABLE_TOP, CW, TABLE_H))
    painter.drawLine(QPointF(LM, TABLE_TOP + TH), QPointF(RM, TABLE_TOP + TH))
    painter.drawLine(QPointF(LM, TOT_Y), QPointF(RM, TOT_Y))

    # 7. Column headers text (all centered)
    hf = QFont("Arial", 8.5, QFont.Weight.Bold)
    hf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
    painter.setFont(hf)
    painter.setPen(QColor("#000000"))
    cur_x = LM
    for i, (title, width) in enumerate(cols):
        painter.drawText(
            QRectF(cur_x + 2, TABLE_TOP, width - 4, TH),
            Qt.AlignmentFlag.AlignCenter,
            title,
        )
        cur_x += width

    # 8. Data rows text — ALL CENTERED (No fills here, purely text!)
    items = data.get("items", [])
    start_idx = (page_number - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = items[start_idx:end_idx]

    item_f = QFont("Arial", 10)
    page_qty = 0.0
    page_amt = 0.0
    grand_qty = sum(float(it.get("quantity", 0.0)) for it in items)
    grand_amt = sum(float(it.get("quantity", 0.0)) * float(it.get("rate", 0.0)) for it in items)

    for idx in range(num_rows):
        if idx >= len(page_items):
            continue
        item = page_items[idx]
        row_y = TABLE_TOP + TH + idx * ROW_H
        sr   = str(start_idx + idx + 1)
        desc = capitalize_words(str(item.get("description", "")))
        qty  = float(item.get("quantity", 0.0))
        rate = float(item.get("rate", 0.0))
        amt  = qty * rate
        page_qty += qty
        page_amt += amt

        painter.setFont(item_f)
        painter.setPen(QColor("#000000"))

        cur_x = LM
        row_vals = (
            [(sr, cw["sr"]), (desc, cw["desc"]), (f"{qty:g}", cw["qty"]),
             (f"{rate:,.2f}", cw["rate"]), (f"{amt:,.2f}", cw["amt"])]
            if is_bill
            else [(sr, cw["sr"]), (desc, cw["desc"]), (f"{qty:g}", cw["qty"])]
        )
        for val, width in row_vals:
            painter.drawText(
                QRectF(cur_x + 3, row_y, width - 6, ROW_H),
                Qt.AlignmentFlag.AlignCenter,
                val,
            )
            cur_x += width

    # 9. Totals row text
    tf = QFont("Arial", 9.5, QFont.Weight.Bold)
    painter.setFont(tf)
    painter.setPen(QColor("#000000"))

    is_last_page = (page_number == total_pages)

    if is_bill:
        tot_label = "TOTAL:" if total_pages == 1 else ("GRAND TOTAL:" if is_last_page else f"SUBTOTAL (PG {page_number}):")
        display_qty = grand_qty if (total_pages == 1 or is_last_page) else page_qty
        display_amt = grand_amt if (total_pages == 1 or is_last_page) else page_amt

        painter.drawText(
            QRectF(LM + 3, TOT_Y, cw["sr"] + cw["desc"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            tot_label,
        )
        painter.drawText(
            QRectF(LM + cw["sr"] + cw["desc"] + 3, TOT_Y, cw["qty"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignCenter,
            f"{display_qty:g}",
        )
        painter.drawText(
            QRectF(RM - cw["amt"] + 3, TOT_Y, cw["amt"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignCenter,
            f"{display_amt:,.2f}",
        )
    else:
        tot_label = "TOTAL QUANTITY:" if total_pages == 1 else ("GRAND TOTAL QTY:" if is_last_page else f"SUBTOTAL QTY (PG {page_number}):")
        display_qty = grand_qty if (total_pages == 1 or is_last_page) else page_qty

        painter.drawText(
            QRectF(LM + 3, TOT_Y, cw["sr"] + cw["desc"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            tot_label,
        )
        painter.drawText(
            QRectF(RM - cw["qty"] + 3, TOT_Y, cw["qty"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignCenter,
            f"{display_qty:g}",
        )

    # ── SIGNATURE AREA ────────────────────────────────────────────────────
    SIG_W    = 210.0
    SIG_LN_Y = TABLE_BOTTOM + 55.0

    painter.setPen(QPen(QColor("#374151"), 1.0))
    painter.drawLine(QPointF(LM, SIG_LN_Y), QPointF(LM + SIG_W, SIG_LN_Y))
    painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
    painter.setPen(QColor("#6b7280"))
    painter.drawText(
        QRectF(LM, SIG_LN_Y + 5, SIG_W, 20), Qt.AlignmentFlag.AlignCenter, "Receiver Signature"
    )

    painter.setPen(QPen(QColor("#374151"), 1.0))
    painter.drawLine(QPointF(RM - SIG_W, SIG_LN_Y), QPointF(RM, SIG_LN_Y))
    painter.setPen(QColor("#6b7280"))
    painter.drawText(
        QRectF(RM - SIG_W, SIG_LN_Y + 5, SIG_W, 20),
        Qt.AlignmentFlag.AlignCenter,
        "Authorized Signature",
    )

    # ── FOOTER ────────────────────────────────────────────────────────────
    painter.setPen(QPen(QColor("#e2e8f0"), 1.0))
    painter.drawLine(QPointF(LM, A4_HEIGHT - 28), QPointF(RM, A4_HEIGHT - 28))
    painter.setFont(QFont("Arial", 7))
    painter.setPen(QColor("#9ca3af"))
    painter.drawText(
        QRectF(LM, A4_HEIGHT - 23, CW, 20),
        Qt.AlignmentFlag.AlignCenter,
        "AG Printers  *  agprinters33@gmail.com  *  +92 300 966 9060",
    )

    if total_pages > 1:
        painter.setFont(QFont("Arial", 7.5, QFont.Weight.Bold))
        painter.setPen(QColor("#64748b"))
        painter.drawText(
            QRectF(LM, A4_HEIGHT - 23, CW, 20),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"Page {page_number} of {total_pages}",
        )

    painter.restore()



class A4PageCanvas(QWidget):
    """Visual rendering of one A4 paper sheet on screen."""

    def __init__(
        self,
        page_kind: str,
        data: dict[str, Any],
        page_number: int = 1,
        total_pages: int = 1,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.page_kind = page_kind
        self.data = data
        self.page_number = page_number
        self.total_pages = total_pages
        self.setFixedSize(A4_WIDTH, A4_HEIGHT)

    def set_data(
        self,
        data: dict[str, Any],
        page_kind: str | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> None:
        self.data = data
        if page_kind:
            self.page_kind = page_kind
        self.page_number = page_number
        self.total_pages = total_pages
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_pad(
            painter,
            self.page_kind,
            self.data,
            QRectF(0, 0, self.width(), self.height()),
            page_number=self.page_number,
            total_pages=self.total_pages,
        )
        painter.end()


class A4PrintPreviewDialog(QDialog):
    """Full print-preview modal supporting multi-page pagination for Invoice and Gate Pass."""

    def __init__(self, data: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.data = data
        self.setWindowTitle("A4 Print Preview — AG Printers")
        self.setMinimumSize(940, 780)
        self.setObjectName("A4PrintPreviewDialog")

        self._doc_pages = get_document_page_count(self.data)
        self._pages_list: list[tuple[str, int, int]] = []
        for p in range(1, self._doc_pages + 1):
            self._pages_list.append(("BILL", p, self._doc_pages))
        for p in range(1, self._doc_pages + 1):
            self._pages_list.append(("CHALLAN", p, self._doc_pages))

        self._current_index = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top Control Bar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        title = QLabel("A4 Document Preview")
        title.setObjectName("DialogTitle")
        toolbar.addWidget(title)

        toolbar.addStretch(1)

        # Multi-page navigation
        self._prev_btn = QPushButton("◀ Prev Page")
        self._prev_btn.setObjectName("OutlineButton")
        self._prev_btn.clicked.connect(self._go_prev)
        toolbar.addWidget(self._prev_btn)

        self._page_combo = QComboBox()
        for idx, (kind, p_num, p_tot) in enumerate(self._pages_list):
            doc_name = "INVOICE" if kind == "BILL" else "GATE PASS"
            if p_tot > 1:
                label = f"{doc_name} — Page {p_num} of {p_tot}"
            else:
                label = f"{doc_name}"
            self._page_combo.addItem(label)
        self._page_combo.currentIndexChanged.connect(self._on_combo_changed)
        toolbar.addWidget(self._page_combo)

        self._next_btn = QPushButton("Next Page ▶")
        self._next_btn.setObjectName("OutlineButton")
        self._next_btn.clicked.connect(self._go_next)
        toolbar.addWidget(self._next_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        toolbar.addWidget(sep)

        print_label = (
            f"Print (All {len(self._pages_list)} Pages)..."
            if len(self._pages_list) > 2
            else "Print (Both Pages)..."
        )
        print_btn = QPushButton(print_label)
        print_btn.setObjectName("PrimaryButton")
        print_btn.clicked.connect(self._print_documents)
        toolbar.addWidget(print_btn)

        pdf_btn = QPushButton("Export PDF...")
        pdf_btn.setObjectName("OutlineButton")
        pdf_btn.clicked.connect(self._export_pdf)
        toolbar.addWidget(pdf_btn)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("OutlineButton")
        close_btn.clicked.connect(self.accept)
        toolbar.addWidget(close_btn)

        root.addLayout(toolbar)

        # Scroll Area holding the A4 paper sheet
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet("QScrollArea { background-color: #374151; border-radius: 8px; border: 1px solid #4B5563; }")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(24, 24, 24, 24)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        initial_kind, initial_p, initial_tot = self._pages_list[0]
        self._canvas = A4PageCanvas(initial_kind, self.data, page_number=initial_p, total_pages=initial_tot)
        self._canvas.setStyleSheet("border: 1px solid #9CA3AF;")
        c_layout.addWidget(self._canvas)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < len(self._pages_list) - 1)
        if self._page_combo.currentIndex() != self._current_index:
            self._page_combo.setCurrentIndex(self._current_index)

    def _go_prev(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._show_page_index(self._current_index)

    def _go_next(self) -> None:
        if self._current_index < len(self._pages_list) - 1:
            self._current_index += 1
            self._show_page_index(self._current_index)

    def _on_combo_changed(self, index: int) -> None:
        if index >= 0 and index != self._current_index:
            self._current_index = index
            self._show_page_index(self._current_index)

    def _show_page_index(self, index: int) -> None:
        kind, p_num, p_tot = self._pages_list[index]
        self._canvas.set_data(self.data, page_kind=kind, page_number=p_num, total_pages=p_tot)
        self._update_nav_buttons()

    def _print_documents(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setFullPage(True)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        painter = QPainter(printer)
        page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
        
        first = True
        for kind, p_num, p_tot in self._pages_list:
            if not first:
                printer.newPage()
            first = False
            paint_pad(painter, kind, self.data, QRectF(page_rect), page_number=p_num, total_pages=p_tot)
        painter.end()

        QMessageBox.information(self, "Printed", f"Sent {len(self._pages_list)} document pages to printer successfully.")

    def _export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Invoice and Gate Pass PDF",
            f"AG_Invoice_{self.data.get('bill_number', 'Doc')}.pdf",
            "PDF Files (*.pdf)",
        )
        if not path:
            return

        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setFullPage(True)

        painter = QPainter(printer)
        page_rect = printer.pageLayout().paintRectPixels(printer.resolution())

        first = True
        for kind, p_num, p_tot in self._pages_list:
            if not first:
                printer.newPage()
            first = False
            paint_pad(painter, kind, self.data, QRectF(page_rect), page_number=p_num, total_pages=p_tot)
        painter.end()

        QMessageBox.information(self, "PDF Exported", f"Exported successfully to:\n{path}")

