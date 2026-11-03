"""Statement / Ledger PDF export engine for AG Printers.

Renders high-quality multi-page A4 PDF statements showing:
Sr. | Date | Invoice # | Party Name | PO Number | Gate Pass # | Total Amount (PKR)

Strictly omits confidential profit, cost, and margin figures as requested.
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPageLayout,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtPrintSupport import QPrinter

from app.jobs.a4_view import _draw_fitting_text, _get_logo
from app.pdf_settings import get_pdf_export_dir, open_pdf_file

A4_WIDTH = 794.0
A4_HEIGHT = 1123.0
ITEMS_PAGE_1 = 28
ITEMS_SUBSEQUENT = 36


def _format_date(val: str | None) -> str:
    """Format date cleanly as '28-Sep-2026'."""
    if not val:
        return "—"
    try:
        clean = str(val).strip().replace("T", " ")
        if " " in clean:
            dt = datetime.fromisoformat(clean)
        else:
            dt = datetime.strptime(clean, "%Y-%m-%d")
        return dt.strftime("%d-%b-%Y")
    except Exception:
        return str(val)


def calculate_statement_page_count(total_items: int) -> int:
    """Calculate total pages required for the statement."""
    if total_items <= ITEMS_PAGE_1:
        return 1
    remaining = total_items - ITEMS_PAGE_1
    return 1 + math.ceil(remaining / ITEMS_SUBSEQUENT)


def get_items_for_page(items: Sequence[Any], page_number: int) -> tuple[int, list[Any]]:
    """Return (start_index_1_based, page_items) for the given page number."""
    if page_number == 1:
        return 1, list(items[:ITEMS_PAGE_1])
    start = ITEMS_PAGE_1 + (page_number - 2) * ITEMS_SUBSEQUENT
    end = start + ITEMS_SUBSEQUENT
    return start + 1, list(items[start:end])


def export_ledger_statement_pdf(
    bills: Sequence[Any],
    party_name: str = "All Parties (All Round)",
    party_details: str = "",
    date_range_label: str = "All Dates (All Round)",
    output_path: str | Path | None = None,
) -> Path:
    """Generate and save complete A4 PDF Statement for the selected bills.

    Confidential Net Profit & Cost figures are strictly excluded.
    """
    if output_path is None:
        target_dir = get_pdf_export_dir()
        clean_party = re.sub(r'[\\/*?:"<>|]', "", party_name or "All_Parties").strip()
        clean_party = re.sub(r"\s+", "_", clean_party)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Statement_{clean_party}_{timestamp}.pdf"
        out_file = target_dir / filename
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(out_file))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setFullPage(True)

    total_pages = calculate_statement_page_count(len(bills))
    total_amount = sum(float(getattr(b, "total_amount", 0.0) or 0.0) for b in bills)

    painter = QPainter(printer)
    page_rect = printer.pageLayout().paintRectPixels(printer.resolution())

    for page_num in range(1, total_pages + 1):
        if page_num > 1:
            printer.newPage()

        start_sr, page_bills = get_items_for_page(bills, page_num)
        is_last_page = (page_num == total_pages)

        _paint_statement_page(
            painter=painter,
            target_rect=QRectF(page_rect),
            page_number=page_num,
            total_pages=total_pages,
            start_sr=start_sr,
            page_bills=page_bills,
            total_invoices=len(bills),
            grand_total_amount=total_amount,
            party_name=party_name,
            party_details=party_details,
            date_range_label=date_range_label,
            is_last_page=is_last_page,
        )

    painter.end()
    return out_file


def _paint_statement_page(
    painter: QPainter,
    target_rect: QRectF,
    page_number: int,
    total_pages: int,
    start_sr: int,
    page_bills: list[Any],
    total_invoices: int,
    grand_total_amount: float,
    party_name: str,
    party_details: str,
    date_range_label: str,
    is_last_page: bool,
) -> None:
    """Render a single A4 page of the ledger statement."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale_x = target_rect.width() / A4_WIDTH
    scale_y = target_rect.height() / A4_HEIGHT
    painter.translate(target_rect.left(), target_rect.top())
    painter.scale(scale_x, scale_y)

    # Pure white background
    painter.fillRect(0, 0, int(A4_WIDTH), int(A4_HEIGHT), QColor("#FFFFFF"))

    LM = 48.0            # Left margin
    RM = A4_WIDTH - 48.0 # Right margin (746.0)
    CW = RM - LM         # 698.0 pt

    # Column Widths (Sum = 698.0)
    COL_SR = 35.0
    COL_DATE = 80.0
    COL_INV = 85.0
    COL_PARTY = 188.0
    COL_PO = 100.0
    COL_GP = 90.0
    COL_AMOUNT = 120.0

    X_SR = LM
    X_DATE = X_SR + COL_SR
    X_INV = X_DATE + COL_DATE
    X_PARTY = X_INV + COL_INV
    X_PO = X_PARTY + COL_PARTY
    X_GP = X_PO + COL_PO
    X_AMOUNT = X_GP + COL_GP

    if page_number == 1:
        # ── PAGE 1 FULL HEADER ──────────────────────────────────────────
        TM = 36.0
        LOGO_SZ = 64.0
        logo = _get_logo()
        if logo is not None:
            painter.drawPixmap(QRectF(LM, TM, LOGO_SZ, LOGO_SZ).toRect(), logo)
        else:
            painter.setFont(QFont("Georgia", 24, QFont.Weight.Bold))
            painter.setPen(QColor("#0F172A"))
            painter.drawText(QRectF(LM, TM, LOGO_SZ, LOGO_SZ), Qt.AlignmentFlag.AlignCenter, "AG")

        # Company Title
        co_font = QFont("Georgia", 20, QFont.Weight.Bold)
        co_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(co_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(LM + LOGO_SZ + 12, TM + 2, CW - LOGO_SZ - 12 - 240, 32),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "AG PRINTERS",
        )

        # Tagline
        tag_font = QFont("Georgia", 8.5)
        tag_font.setItalic(True)
        painter.setFont(tag_font)
        painter.setPen(QColor("#475569"))
        painter.drawText(
            QRectF(LM + LOGO_SZ + 12, TM + 36, CW - LOGO_SZ - 12 - 240, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Deals in All Kind of Offset Printing & Labels",
        )

        # Contact Info (Right Aligned)
        addr_font = QFont("Arial", 8.2)
        painter.setFont(addr_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(RM - 270, TM, 270, LOGO_SZ + 10),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            "Suite # 4, 1st Floor, Sultania Center\n"
            "St # 7, Munshi Mohallah, Aminpur Bazar, Faisalabad.\n"
            "Mob: +92 300 966 9060 | Email: agprinters33@gmail.com",
        )

        # Divider rule
        RULE_Y = TM + LOGO_SZ + 4
        painter.setPen(QPen(QColor("#0F172A"), 1.8))
        painter.drawLine(QPointF(LM, RULE_Y), QPointF(RM, RULE_Y))
        painter.setPen(QPen(QColor("#94A3B8"), 0.8))
        painter.drawLine(QPointF(LM, RULE_Y + 3), QPointF(RM, RULE_Y + 3))

        # Document Title Badge
        BADGE_Y = RULE_Y + 9
        BADGE_W = 280.0
        BADGE_H = 24.0
        BADGE_X = LM + (CW - BADGE_W) / 2.0
        badge_rect = QRectF(BADGE_X, BADGE_Y, BADGE_W, BADGE_H)

        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, 4.0, 4.0)
        painter.setBrush(QColor("#0F172A"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(badge_path)

        badge_font = QFont("Georgia", 10, QFont.Weight.Bold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        painter.setFont(badge_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "LEDGER STATEMENT")

        # ── METADATA CARD (Left: Party Info, Right: Period & Totals) ──
        META_Y = BADGE_Y + BADGE_H + 9
        META_H = 68.0
        meta_rect = QRectF(LM, META_Y, CW, META_H)

        meta_path = QPainterPath()
        meta_path.addRoundedRect(meta_rect, 5.0, 5.0)
        painter.setBrush(QColor("#F8FAFC"))
        painter.setPen(QPen(QColor("#CBD5E1"), 1.0))
        painter.drawPath(meta_path)

        # Middle dividing vertical line
        MID_X = LM + (CW * 0.52)
        painter.setPen(QPen(QColor("#E2E8F0"), 1.0))
        painter.drawLine(QPointF(MID_X, META_Y + 6), QPointF(MID_X, META_Y + META_H - 6))

        # Left: Party / Client
        lbl_font = QFont("Arial", 7.5, QFont.Weight.Bold)
        lbl_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        painter.setFont(lbl_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(
            QRectF(LM + 14, META_Y + 8, (MID_X - LM) - 24, 14),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "STATEMENT FOR:",
        )

        p_name_font = QFont("Georgia", 12, QFont.Weight.Bold)
        _draw_fitting_text(
            painter,
            QRectF(LM + 14, META_Y + 24, (MID_X - LM) - 24, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            party_name or "All Parties (All Round)",
            p_name_font,
            min_point_size=8.0,
        )

        p_det_font = QFont("Arial", 8.0)
        painter.setFont(p_det_font)
        painter.setPen(QColor("#475569"))
        detail_text = party_details if party_details else "Consolidated Billing Statement (All Active Accounts)"
        _draw_fitting_text(
            painter,
            QRectF(LM + 14, META_Y + 46, (MID_X - LM) - 24, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            detail_text,
            p_det_font,
            min_point_size=6.5,
        )

        # Right: Period, Date Generated, Totals
        r_box_w = RM - MID_X - 28
        painter.setFont(lbl_font)
        painter.setPen(QColor("#64748B"))

        # Line 1: Period
        painter.drawText(QRectF(MID_X + 14, META_Y + 8, 90, 15), Qt.AlignmentFlag.AlignLeft, "PERIOD:")
        p_val_font = QFont("Arial", 8.2, QFont.Weight.Bold)
        painter.setFont(p_val_font)
        painter.setPen(QColor("#0F172A"))
        _draw_fitting_text(
            painter,
            QRectF(MID_X + 90, META_Y + 8, r_box_w - 90, 15),
            Qt.AlignmentFlag.AlignLeft,
            date_range_label or "All Dates",
            p_val_font,
            min_point_size=7.0,
        )

        # Line 2: Date Printed
        painter.setFont(lbl_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(QRectF(MID_X + 14, META_Y + 26, 90, 15), Qt.AlignmentFlag.AlignLeft, "PRINTED ON:")
        now_str = datetime.now().strftime("%d-%b-%Y, %I:%M %p")
        painter.setFont(QFont("Arial", 8.0))
        painter.setPen(QColor("#0F172A"))
        painter.drawText(QRectF(MID_X + 90, META_Y + 26, r_box_w - 90, 15), Qt.AlignmentFlag.AlignLeft, now_str)

        # Line 3: Invoices & Amount Summary (NO PROFIT!)
        painter.setFont(lbl_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(QRectF(MID_X + 14, META_Y + 44, 90, 16), Qt.AlignmentFlag.AlignLeft, "TOTAL BILLED:")
        painter.setFont(QFont("Georgia", 9.5, QFont.Weight.Bold))
        painter.setPen(QColor("#0284C7"))
        summary_str = f"PKR {grand_total_amount:,.2f}  ({total_invoices} {'Bill' if total_invoices == 1 else 'Bills'})"
        painter.drawText(QRectF(MID_X + 90, META_Y + 44, r_box_w - 90, 16), Qt.AlignmentFlag.AlignLeft, summary_str)

        TABLE_Y = META_Y + META_H + 12
    else:
        # ── SUBSEQUENT PAGES COMPACT HEADER ─────────────────────────────
        TM = 30.0
        painter.setFont(QFont("Georgia", 11, QFont.Weight.Bold))
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(LM, TM, 320, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "AG PRINTERS — LEDGER STATEMENT",
        )

        painter.setFont(QFont("Arial", 8.2))
        painter.setPen(QColor("#64748B"))
        sub_info = f"{party_name} | {date_range_label}"
        _draw_fitting_text(
            painter,
            QRectF(RM - 340, TM, 340, 20),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            sub_info,
            QFont("Arial", 8.2),
            min_point_size=7.0,
        )

        painter.setPen(QPen(QColor("#CBD5E1"), 1.0))
        painter.drawLine(QPointF(LM, TM + 24), QPointF(RM, TM + 24))

        TABLE_Y = TM + 30

    # ── TABLE HEADER ────────────────────────────────────────────────────
    TH_H = 25.0
    th_rect = QRectF(LM, TABLE_Y, CW, TH_H)

    painter.fillRect(th_rect, QColor("#0F172A"))
    painter.setPen(QPen(QColor("#0F172A"), 1.0))
    painter.drawRect(th_rect)

    th_font = QFont("Arial", 7.8, QFont.Weight.Bold)
    th_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
    painter.setFont(th_font)
    painter.setPen(QColor("#FFFFFF"))

    painter.drawText(QRectF(X_SR, TABLE_Y, COL_SR, TH_H), Qt.AlignmentFlag.AlignCenter, "SR.")
    painter.drawText(QRectF(X_DATE, TABLE_Y, COL_DATE, TH_H), Qt.AlignmentFlag.AlignCenter, "DATE")
    painter.drawText(QRectF(X_INV, TABLE_Y, COL_INV, TH_H), Qt.AlignmentFlag.AlignCenter, "INVOICE #")
    painter.drawText(QRectF(X_PARTY + 8, TABLE_Y, COL_PARTY - 8, TH_H), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "PARTY NAME")
    painter.drawText(QRectF(X_PO, TABLE_Y, COL_PO, TH_H), Qt.AlignmentFlag.AlignCenter, "PO NUMBER")
    painter.drawText(QRectF(X_GP, TABLE_Y, COL_GP, TH_H), Qt.AlignmentFlag.AlignCenter, "GATE PASS")
    painter.drawText(QRectF(X_AMOUNT, TABLE_Y, COL_AMOUNT - 8, TH_H), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "TOTAL (PKR)")

    # ── TABLE DATA ROWS ─────────────────────────────────────────────────
    ROW_H = 24.0
    cur_y = TABLE_Y + TH_H

    data_font = QFont("Arial", 8.2)
    data_bold = QFont("Arial", 8.2, QFont.Weight.Bold)

    for idx, bill in enumerate(page_bills):
        sr_num = start_sr + idx
        row_rect = QRectF(LM, cur_y, CW, ROW_H)

        # Alternating background
        bg_col = QColor("#FFFFFF") if (sr_num % 2 == 1) else QColor("#F8FAFC")
        painter.fillRect(row_rect, bg_col)

        # Horizontal bottom gridline
        painter.setPen(QPen(QColor("#E2E8F0"), 0.8))
        painter.drawLine(QPointF(LM, cur_y + ROW_H), QPointF(RM, cur_y + ROW_H))

        # Vertical borders
        painter.setPen(QPen(QColor("#E2E8F0"), 0.6))
        for col_x in (X_DATE, X_INV, X_PARTY, X_PO, X_GP, X_AMOUNT):
            painter.drawLine(QPointF(col_x, cur_y), QPointF(col_x, cur_y + ROW_H))

        # Outer border
        painter.setPen(QPen(QColor("#CBD5E1"), 0.8))
        painter.drawLine(QPointF(LM, cur_y), QPointF(LM, cur_y + ROW_H))
        painter.drawLine(QPointF(RM, cur_y), QPointF(RM, cur_y + ROW_H))

        # Values
        inv_no = str(getattr(bill, "bill_number", "") or "")
        bill_date = _format_date(getattr(bill, "bill_date", ""))
        p_name = str(getattr(bill, "party_name", "") or "")
        po_num = str(getattr(bill, "po_number", "") or "—")
        gp_num = str(getattr(bill, "gate_pass_number", "") or getattr(bill, "gate_pass_number_value", "") or "—")
        amt = float(getattr(bill, "total_amount", 0.0) or 0.0)

        # 1. Sr.
        painter.setFont(data_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(QRectF(X_SR, cur_y, COL_SR, ROW_H), Qt.AlignmentFlag.AlignCenter, str(sr_num))

        # 2. Date
        painter.setFont(data_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(QRectF(X_DATE, cur_y, COL_DATE, ROW_H), Qt.AlignmentFlag.AlignCenter, bill_date)

        # 3. Invoice #
        painter.setFont(data_bold)
        painter.setPen(QColor("#0F172A"))
        _draw_fitting_text(
            painter,
            QRectF(X_INV + 4, cur_y, COL_INV - 8, ROW_H),
            Qt.AlignmentFlag.AlignCenter,
            inv_no,
            data_bold,
            min_point_size=7.0,
        )

        # 4. Party Name
        painter.setFont(data_font)
        painter.setPen(QColor("#0F172A"))
        _draw_fitting_text(
            painter,
            QRectF(X_PARTY + 8, cur_y, COL_PARTY - 14, ROW_H),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            p_name,
            data_font,
            min_point_size=6.5,
        )

        # 5. PO Number
        painter.setFont(data_font)
        painter.setPen(QColor("#475569"))
        _draw_fitting_text(
            painter,
            QRectF(X_PO + 4, cur_y, COL_PO - 8, ROW_H),
            Qt.AlignmentFlag.AlignCenter,
            po_num,
            data_font,
            min_point_size=6.5,
        )

        # 6. Gate Pass #
        painter.setFont(data_font)
        painter.setPen(QColor("#475569"))
        _draw_fitting_text(
            painter,
            QRectF(X_GP + 4, cur_y, COL_GP - 8, ROW_H),
            Qt.AlignmentFlag.AlignCenter,
            gp_num,
            data_font,
            min_point_size=6.5,
        )

        # 7. Total Amount
        painter.setFont(data_bold)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(X_AMOUNT, cur_y, COL_AMOUNT - 8, ROW_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"{amt:,.2f}",
        )

        cur_y += ROW_H

    # ── GRAND TOTAL ROW (Last Page Only) ────────────────────────────────
    if is_last_page:
        TOTAL_H = 26.0
        tot_rect = QRectF(LM, cur_y, CW, TOTAL_H)

        painter.fillRect(tot_rect, QColor("#F1F5F9"))

        # Double top border
        painter.setPen(QPen(QColor("#0F172A"), 1.4))
        painter.drawLine(QPointF(LM, cur_y), QPointF(RM, cur_y))
        painter.setPen(QPen(QColor("#0F172A"), 1.0))
        painter.drawLine(QPointF(LM, cur_y + TOTAL_H), QPointF(RM, cur_y + TOTAL_H))
        painter.drawLine(QPointF(LM, cur_y), QPointF(LM, cur_y + TOTAL_H))
        painter.drawLine(QPointF(RM, cur_y), QPointF(RM, cur_y + TOTAL_H))
        painter.drawLine(QPointF(X_AMOUNT, cur_y), QPointF(X_AMOUNT, cur_y + TOTAL_H))

        tot_lbl_font = QFont("Arial", 8.5, QFont.Weight.Bold)
        tot_lbl_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        painter.setFont(tot_lbl_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(LM + 14, cur_y, (X_AMOUNT - LM) - 24, TOTAL_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"GRAND TOTAL ({total_invoices} {'INVOICE' if total_invoices == 1 else 'INVOICES'}):",
        )

        tot_val_font = QFont("Georgia", 10.5, QFont.Weight.Bold)
        painter.setFont(tot_val_font)
        painter.setPen(QColor("#0F172A"))
        painter.drawText(
            QRectF(X_AMOUNT, cur_y, COL_AMOUNT - 8, TOTAL_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"PKR {grand_total_amount:,.2f}",
        )

    # ── FOOTER STRIP (Every Page) ───────────────────────────────────────
    FOOTER_Y = A4_HEIGHT - 38.0
    painter.setPen(QPen(QColor("#CBD5E1"), 0.8))
    painter.drawLine(QPointF(LM, FOOTER_Y), QPointF(RM, FOOTER_Y))

    painter.setFont(QFont("Arial", 7.5))
    painter.setPen(QColor("#64748B"))
    painter.drawText(
        QRectF(LM, FOOTER_Y + 4, CW - 120, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        "This is an official computer-generated statement from AG Printers. No signature required.",
    )

    page_str = f"Page {page_number} of {total_pages}"
    painter.setFont(QFont("Arial", 8.0, QFont.Weight.Bold))
    painter.setPen(QColor("#0F172A"))
    painter.drawText(
        QRectF(RM - 100, FOOTER_Y + 4, 100, 20),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        page_str,
    )

    painter.restore()

