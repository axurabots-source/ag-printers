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
    QButtonGroup,
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


# ---------------------------------------------------------------------------

def paint_pad(
    painter: QPainter, page_kind: str, data: dict[str, Any], target_rect: QRectF
) -> None:
    """Render one A4 page (BILL or DELIVERY CHALLAN) into *target_rect*."""
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

    # Address right-aligned
    painter.setFont(QFont("Arial", 7.5))
    painter.setPen(QColor("#374151"))
    painter.drawText(
        QRectF(RM - 220, TM, 220, LOGO_SZ),
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
    BADGE_W = 200.0
    BADGE_H = 26.0
    BADGE_X = (A4_WIDTH - BADGE_W) / 2.0
    badge_rect = QRectF(BADGE_X, BADGE_Y, BADGE_W, BADGE_H)

    badge_path = QPainterPath()
    badge_path.addRoundedRect(badge_rect, 5.0, 5.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#000000"), 1.2))
    painter.drawPath(badge_path)

    badge_font = QFont("Georgia", 10.5, QFont.Weight.Bold)
    badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.8)
    painter.setFont(badge_font)
    painter.setPen(QColor("#000000"))
    is_bill = page_kind == "BILL"
    badge_label = "BILL" if is_bill else "DELIVERY CHALLAN"
    painter.drawText(
        badge_rect,
        Qt.AlignmentFlag.AlignCenter,
        badge_label,
    )

    # ── METADATA SECTION (Modern Integrated Info Cards) ───────────────────
    INFO_TOP = BADGE_Y + BADGE_H + 14
    INFO_H = 82.0
    BOX_BORDER_PEN = QPen(QColor("#E2E8F0"), 1.0)
    BOX_BG = QColor("#F8FAFC")

    raw_date = data.get("bill_date") or data.get("challan_date") or data.get("date") or data.get("created_at") or ""
    date_str = _format_pdf_date(str(raw_date)) if raw_date else "—"

    party_str = capitalize_words(str(data.get("party_name") or data.get("party") or data.get("customer_name") or ""))

    raw_po = data.get("po_number") or data.get("po_no") or ""
    po_str = capitalize_words(str(raw_po)) if raw_po else ""

    raw_job = data.get("job_number") or data.get("job_no") or ""
    job_str = capitalize_words(str(raw_job)) if raw_job else ""

    raw_bill = data.get("bill_number") or data.get("bill_no") or data.get("bill_ref") or ""
    bill_no_str = str(raw_bill) if raw_bill else "—"

    raw_dc = data.get("challan_no") or data.get("challan_number") or data.get("gate_pass_number") or data.get("dc_no") or ""
    dc_no_str = str(raw_dc) if raw_dc else "—"

    LEFT_BOX_W = 380.0
    RIGHT_BOX_X = LM + LEFT_BOX_W + 14.0
    RIGHT_BOX_W = CW - (LEFT_BOX_W + 14.0)

    # 1. Left Card: Customer / Billed To
    left_rect = QRectF(LM, INFO_TOP, LEFT_BOX_W, INFO_H)
    left_path = QPainterPath()
    left_path.addRoundedRect(left_rect, 6.0, 6.0)
    painter.fillPath(left_path, BOX_BG)
    painter.setPen(BOX_BORDER_PEN)
    painter.drawPath(left_path)

    # Billed To Label
    lbl_font = QFont("Arial", 8, QFont.Weight.Bold)
    lbl_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
    painter.setFont(lbl_font)
    painter.setPen(QColor("#64748B"))
    billed_tag = "BILLED TO:" if is_bill else "DELIVERED TO:"
    painter.drawText(
        QRectF(LM + 14, INFO_TOP + 10, LEFT_BOX_W - 28, 14),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        billed_tag,
    )

    # Customer Party Name
    party_font = QFont("Georgia", 13, QFont.Weight.Bold)
    painter.setFont(party_font)
    painter.setPen(QColor("#0F172A"))
    painter.drawText(
        QRectF(LM + 14, INFO_TOP + 26, LEFT_BOX_W - 28, 22),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        party_str if party_str else "Cash Customer",
    )

    # PO / Job Reference Badges (Distinct highlighted chips)
    badge_y = INFO_TOP + 52
    badge_h = 24.0
    badge_w = (LEFT_BOX_W - 28.0 - 10.0) / 2.0

    po_display = po_str if (po_str and po_str != "—") else "—"
    job_display = job_str if (job_str and job_str != "—") else "—"

    # P.O. Number Chip
    po_rect = QRectF(LM + 14, badge_y, badge_w, badge_h)
    po_path = QPainterPath()
    po_path.addRoundedRect(po_rect, 4.0, 4.0)
    painter.fillPath(po_path, QColor("#EFF6FF"))
    painter.setPen(QPen(QColor("#BFDBFE"), 1.0))
    painter.drawPath(po_path)

    painter.setFont(QFont("Arial", 7.5, QFont.Weight.Bold))
    painter.setPen(QColor("#1D4ED8"))
    painter.drawText(QRectF(LM + 22, badge_y, 48, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "P.O. NO:")

    painter.setFont(QFont("Arial", 9.5, QFont.Weight.Bold))
    painter.setPen(QColor("#0F172A"))
    painter.drawText(QRectF(LM + 70, badge_y, badge_w - 60, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, po_display)

    # Job Number Chip
    job_x = LM + 14 + badge_w + 10.0
    job_rect = QRectF(job_x, badge_y, badge_w, badge_h)
    job_path = QPainterPath()
    job_path.addRoundedRect(job_rect, 4.0, 4.0)
    painter.fillPath(job_path, QColor("#F8FAFC"))
    painter.setPen(QPen(QColor("#CBD5E1"), 1.0))
    painter.drawPath(job_path)

    painter.setFont(QFont("Arial", 7.5, QFont.Weight.Bold))
    painter.setPen(QColor("#475569"))
    painter.drawText(QRectF(job_x + 8, badge_y, 48, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "JOB NO:")

    painter.setFont(QFont("Arial", 9.5, QFont.Weight.Bold))
    painter.setPen(QColor("#0F172A"))
    painter.drawText(QRectF(job_x + 56, badge_y, badge_w - 60, badge_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, job_display)

    # 2. Right Card: Invoice Details
    right_rect = QRectF(RIGHT_BOX_X, INFO_TOP, RIGHT_BOX_W, INFO_H)
    right_path = QPainterPath()
    right_path.addRoundedRect(right_rect, 6.0, 6.0)
    painter.fillPath(right_path, BOX_BG)
    painter.setPen(BOX_BORDER_PEN)
    painter.drawPath(right_path)

    # Right Card Rows
    meta_rows = [
        ("BILL NO:" if is_bill else "CHALLAN NO:", bill_no_str if is_bill else dc_no_str),
        ("DATE:", date_str),
        ("CHALLAN NO:" if is_bill else "BILL REF:", dc_no_str if is_bill else bill_no_str),
    ]

    row_y_offset = INFO_TOP + 8
    row_height = 22.0

    meta_lbl_font = QFont("Arial", 8, QFont.Weight.Bold)
    meta_lbl_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
    meta_val_font = QFont("Arial", 9.5, QFont.Weight.Bold)

    for lbl_text, val_text in meta_rows:
        painter.setFont(meta_lbl_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(
            QRectF(RIGHT_BOX_X + 14, row_y_offset, 110, row_height),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            lbl_text,
        )

        painter.setFont(meta_val_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(RIGHT_BOX_X + 115, row_y_offset, RIGHT_BOX_W - 129, row_height),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            val_text,
        )

        row_y_offset += row_height

    # ── TABLE ─────────────────────────────────────────────────────────────
    TABLE_TOP = INFO_TOP + INFO_H + 16

    TH = 28.0       # table header height
    ROW_H = 32.0    # data row height
    TOT_H = 32.0    # totals row height

    max_space = (A4_HEIGHT - 165.0) - TABLE_TOP - TH - TOT_H
    num_rows = max(1, int(max_space / ROW_H))
    TABLE_H = TH + (num_rows * ROW_H) + TOT_H
    TABLE_BOTTOM = TABLE_TOP + TABLE_H

    is_bill = page_kind == "BILL"
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

    BORDER = QPen(QColor("#374151"), 1.2)
    GRID   = QPen(QColor("#d1d5db"), 0.7)

    # Header fill
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillRect(QRectF(LM, TABLE_TOP, CW, TH), QColor("#e8ecf0"))

    # Outer box + header line
    painter.setPen(BORDER)
    painter.drawRect(QRectF(LM, TABLE_TOP, CW, TABLE_H))
    painter.drawLine(QPointF(LM, TABLE_TOP + TH), QPointF(RM, TABLE_TOP + TH))

    # Column headers (all centered)
    hf = QFont("Arial", 8, QFont.Weight.Bold)
    hf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
    painter.setFont(hf)
    painter.setPen(QColor("#111827"))
    cur_x = LM
    for i, (title, width) in enumerate(cols):
        painter.drawText(
            QRectF(cur_x + 3, TABLE_TOP, width - 6, TH),
            Qt.AlignmentFlag.AlignCenter,
            title,
        )
        cur_x += width
        if i < len(cols) - 1:
            painter.setPen(BORDER)
            painter.drawLine(QPointF(cur_x, TABLE_TOP), QPointF(cur_x, TABLE_BOTTOM))
            painter.setPen(QColor("#111827"))

    # Row lines
    painter.setPen(GRID)
    for r in range(1, num_rows):
        y = TABLE_TOP + TH + r * ROW_H
        painter.drawLine(QPointF(LM + 1, y), QPointF(RM - 1, y))

    # Data rows — ALL CENTERED
    items = data.get("items", [])
    item_f = QFont("Arial", 10)
    total_qty = 0.0
    total_amt = 0.0

    for idx, item in enumerate(items[:num_rows]):
        row_y = TABLE_TOP + TH + idx * ROW_H
        if idx % 2 == 1:
            painter.fillRect(
                QRectF(LM + 1, row_y + 1, CW - 2, ROW_H - 1), QColor("#f8fafc")
            )

        sr   = str(idx + 1)
        desc = capitalize_words(str(item.get("description", "")))
        qty  = float(item.get("quantity", 0.0))
        rate = float(item.get("rate", 0.0))
        amt  = qty * rate
        total_qty += qty
        total_amt += amt

        painter.setFont(item_f)
        painter.setPen(QColor("#111827"))

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

    # Totals row
    TOT_Y = TABLE_TOP + TH + num_rows * ROW_H
    painter.setPen(BORDER)
    painter.drawLine(QPointF(LM, TOT_Y), QPointF(RM, TOT_Y))
    painter.fillRect(QRectF(LM + 1, TOT_Y + 1, CW - 2, TOT_H - 1), QColor("#f1f5f9"))

    tf = QFont("Arial", 10, QFont.Weight.Bold)
    painter.setFont(tf)
    painter.setPen(QColor("#0f172a"))

    if is_bill:
        painter.drawText(
            QRectF(LM + 3, TOT_Y, cw["sr"] + cw["desc"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "TOTAL:",
        )
        painter.drawText(
            QRectF(LM + cw["sr"] + cw["desc"] + 3, TOT_Y, cw["qty"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignCenter,
            f"{total_qty:g}",
        )
        painter.drawText(
            QRectF(RM - cw["amt"] + 3, TOT_Y, cw["amt"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignCenter,
            f"{total_amt:,.2f}",
        )
    else:
        painter.drawText(
            QRectF(LM + 3, TOT_Y, cw["sr"] + cw["desc"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "TOTAL QUANTITY:",
        )
        painter.drawText(
            QRectF(RM - cw["qty"] + 3, TOT_Y, cw["qty"] - 6, TOT_H),
            Qt.AlignmentFlag.AlignCenter,
            f"{total_qty:g}",
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

    painter.restore()



class A4PageCanvas(QWidget):
    """Visual rendering of one A4 paper sheet on screen."""

    def __init__(self, page_kind: str, data: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.page_kind = page_kind
        self.data = data
        self.setFixedSize(A4_WIDTH, A4_HEIGHT)

    def set_data(self, data: dict[str, Any], page_kind: str | None = None) -> None:
        self.data = data
        if page_kind:
            self.page_kind = page_kind
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_pad(painter, self.page_kind, self.data, QRectF(0, 0, self.width(), self.height()))
        painter.end()


class A4PrintPreviewDialog(QDialog):
    """Full print-preview modal displaying Page 1 (Bill) and Page 2 (Delivery Challan)."""

    def __init__(self, data: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.data = data
        self.setWindowTitle("A4 Print Preview — AG Printers")
        self.setMinimumSize(940, 780)
        self.setObjectName("A4PrintPreviewDialog")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top Control Bar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        title = QLabel("A4 Document Preview")
        title.setObjectName("DialogTitle")
        toolbar.addWidget(title)

        toolbar.addStretch(1)

        self._btn_group = QButtonGroup(self)
        self._btn_bill = QPushButton("Page 1: BILL")
        self._btn_bill.setCheckable(True)
        self._btn_bill.setChecked(True)
        self._btn_bill.setObjectName("OutlineButton")
        self._btn_bill.clicked.connect(lambda: self._switch_page("BILL"))
        self._btn_group.addButton(self._btn_bill)
        toolbar.addWidget(self._btn_bill)

        self._btn_challan = QPushButton("Page 2: DELIVERY CHALLAN")
        self._btn_challan.setCheckable(True)
        self._btn_challan.setObjectName("OutlineButton")
        self._btn_challan.clicked.connect(lambda: self._switch_page("CHALLAN"))
        self._btn_group.addButton(self._btn_challan)
        toolbar.addWidget(self._btn_challan)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        toolbar.addWidget(sep)

        print_btn = QPushButton("Print (Both Pages)...")
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

        self._canvas = A4PageCanvas("BILL", self.data)
        # Subtle drop shadow style for sheet
        self._canvas.setStyleSheet("border: 1px solid #9CA3AF;")
        c_layout.addWidget(self._canvas)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

    def _switch_page(self, page_kind: str) -> None:
        self._canvas.set_data(self.data, page_kind)

    def _print_documents(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setFullPage(True)

        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        painter = QPainter(printer)
        page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
        # Page 1: BILL
        paint_pad(painter, "BILL", self.data, QRectF(page_rect))
        # Page 2: DELIVERY CHALLAN
        printer.newPage()
        paint_pad(painter, "CHALLAN", self.data, QRectF(page_rect))
        painter.end()

        QMessageBox.information(self, "Printed", "Sent Bill and Delivery Challan to printer successfully.")

    def _export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Bill and Challan PDF",
            f"AG_Bill_{self.data.get('bill_number', 'Doc')}.pdf",
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
        paint_pad(painter, "BILL", self.data, QRectF(page_rect))
        printer.newPage()
        paint_pad(painter, "CHALLAN", self.data, QRectF(page_rect))
        painter.end()

        QMessageBox.information(self, "PDF Exported", f"Exported successfully to:\n{path}")
