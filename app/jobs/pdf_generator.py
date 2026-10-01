"""Automated local PDF generation and retrieval for AG Printers bills & challans."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPageLayout, QPainter
from PySide6.QtPrintSupport import QPrinter

from app.jobs.a4_view import paint_pad
from app.pdf_settings import build_pdf_filename, get_pdf_export_dir


def export_bill_pdf(data: dict[str, Any], output_path: str | Path | None = None) -> Path:
    """Render and save a complete 2-page PDF (BILL + DELIVERY CHALLAN) to local machine."""
    if output_path is None:
        target_dir = get_pdf_export_dir()
        filename = build_pdf_filename(
            party_name=str(data.get("party_name", "")),
            bill_date=str(data.get("bill_date", "")),
            bill_number=str(data.get("bill_number", "")),
        )
        out_file = target_dir / filename
    else:
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

    printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(out_file))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setFullPage(True)

    painter = QPainter(printer)
    page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
    paint_pad(painter, "BILL", data, QRectF(page_rect))
    printer.newPage()
    paint_pad(painter, "CHALLAN", data, QRectF(page_rect))
    painter.end()

    return out_file


def get_or_create_bill_pdf(connection: sqlite3.Connection, bill_id: int) -> Path | None:
    """Fetch existing PDF path from disk, or dynamically regenerate into the configured local folder."""
    from app.db.bills import get_bill
    from app.db.parties import get_party

    bill = get_bill(connection, bill_id)
    if bill is None:
        return None

    # Check if recorded pdf_path exists on local machine
    if hasattr(bill, "pdf_path") and bill.pdf_path:
        p = Path(bill.pdf_path)
        if p.exists():
            return p

    # Also check if matching file exists in current export directory
    party = get_party(connection, bill.party_id) if bill.party_id else None
    party_name = party.name if party else bill.party_name
    expected_filename = build_pdf_filename(party_name, bill.bill_date, bill.bill_number)
    target_dir = get_pdf_export_dir()
    expected_path = target_dir / expected_filename
    if expected_path.exists():
        try:
            connection.execute("UPDATE bills SET pdf_path = ? WHERE id = ?", (str(expected_path), bill_id))
            connection.commit()
        except Exception:
            pass
        return expected_path

    # Regenerate fresh PDF
    items_data = []
    for item in bill.items:
        items_data.append({
            "description": item.description,
            "quantity": item.quantity,
            "rate": item.rate,
            "cost_price": item.cost_price,
        })

    doc_data = {
        "party_name": party_name,
        "bill_date": bill.bill_date,
        "po_number": bill.po_number,
        "job_number": bill.job_number,
        "bill_number": bill.bill_number,
        "gate_pass_number": bill.gate_pass_number,
        "items": items_data,
    }

    out_file = export_bill_pdf(doc_data)

    try:
        connection.execute("UPDATE bills SET pdf_path = ? WHERE id = ?", (str(out_file), bill_id))
        connection.commit()
    except Exception:
        pass

    return out_file
