"""Stock In / Out Movement History Dialog.

Displays complete audit log of:
- IN: Inward stock additions (initial stock, manual additions, supplier receipts)
- OUT: Outward stock deductions (bills, invoice numbers, customer names)
"""

from __future__ import annotations

from datetime import datetime
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.barcode_inventory import (
    BarcodeInventoryItem,
    get_in_history,
    get_out_history,
)


def _format_datetime(val: str | None) -> str:
    """Format ISO or SQLite timestamp into human readable date and time."""
    if not val:
        return "—"
    clean = str(val).strip().replace("T", " ")
    try:
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%d-%b-%Y  %I:%M %p")
    except Exception:
        try:
            parts = clean.split(" ")[0].split("-")
            if len(parts) == 3:
                from datetime import date

                d = date(int(parts[0]), int(parts[1]), int(parts[2]))
                time_part = clean.split(" ")[1] if " " in clean else ""
                if time_part:
                    return f"{d.strftime('%d-%b-%Y')}  {time_part[:5]}"
                return d.strftime("%d-%b-%Y")
        except Exception:
            pass
        return clean


class StockHistoryDialog(QDialog):
    """Modal dialog displaying Inward or Outward stock movement history."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        item: BarcodeInventoryItem,
        mode: str = "IN",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._item = item
        self._mode = mode.upper()
        self.setModal(True)
        self.resize(680, 480)

        is_in = self._mode == "IN"
        self.setWindowTitle(
            f"📥 Stock IN History — {item.detail}"
            if is_in
            else f"📤 Stock OUT History — {item.detail}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # 1. Header Card
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px 14px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.setSpacing(12)

        info_box = QVBoxLayout()
        info_box.setSpacing(4)

        tag_lbl = QLabel("INWARD STOCK LOG" if is_in else "OUTWARD DEDUCTION LOG")
        tag_lbl.setStyleSheet(
            """
            QLabel {
                font-size: 10px;
                font-weight: 800;
                color: #047857;
                background-color: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 2px 6px;
                letter-spacing: 0.5px;
            }
            """
            if is_in
            else """
            QLabel {
                font-size: 10px;
                font-weight: 800;
                color: #DC2626;
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 4px;
                padding: 2px 6px;
                letter-spacing: 0.5px;
            }
            """
        )
        tag_row = QHBoxLayout()
        tag_row.addWidget(tag_lbl)
        tag_row.addStretch(1)
        info_box.addLayout(tag_row)

        item_title = QLabel(item.detail)
        item_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A; border: none; background: transparent;")
        info_box.addWidget(item_title)

        curr_stock_str = f"{item.quantity:,.0f}" if item.quantity.is_integer() else f"{item.quantity:,.2f}"
        sub_lbl = QLabel(f"Current Available Stock: {curr_stock_str} Units  |  Unit Rate: Rs. {item.rate:,.2f}")
        sub_lbl.setStyleSheet("font-size: 11.5px; color: #64748B; border: none; background: transparent;")
        info_box.addWidget(sub_lbl)

        h_layout.addLayout(info_box, 1)

        # Right Summary Box
        self._summary_box = QVBoxLayout()
        self._summary_box.setSpacing(2)
        self._summary_box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._stat_title = QLabel("TOTAL LOGGED" if is_in else "TOTAL DEDUCTED")
        self._stat_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; border: none; background: transparent;")
        self._stat_val = QLabel("0 Units")
        self._stat_val.setStyleSheet(
            f"font-size: 17px; font-weight: 800; color: {'#047857' if is_in else '#DC2626'}; border: none; background: transparent;"
        )
        self._summary_box.addWidget(self._stat_title)
        self._summary_box.addWidget(self._stat_val)

        h_layout.addLayout(self._summary_box)
        layout.addWidget(header_card)

        # 2. History Table
        self._table = QTableWidget()
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setShowGrid(False)
        self._table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
                gridline-color: #F1F5F9;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #475569;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-bottom: 2px solid #E2E8F0;
                padding: 8px 6px;
            }
        """)

        if is_in:
            self._table.setColumnCount(4)
            self._table.setHorizontalHeaderLabels([
                "Sr.",
                "Date & Time",
                "Quantity In",
                "Log Type / Remarks",
            ])
            h = self._table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            self._table.setColumnWidth(0, 45)
            self._table.setColumnWidth(1, 170)
            self._table.setColumnWidth(2, 130)
        else:
            self._table.setColumnCount(5)
            self._table.setHorizontalHeaderLabels([
                "Sr.",
                "Date & Time",
                "Quantity Out",
                "Bill / Invoice #",
                "Party / Customer",
            ])
            h = self._table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            self._table.setColumnWidth(0, 45)
            self._table.setColumnWidth(1, 160)
            self._table.setColumnWidth(2, 120)
            self._table.setColumnWidth(3, 115)

        layout.addWidget(self._table, 1)

        # 3. Bottom Row (Summary count + Close Button)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("font-size: 11.5px; color: #64748B; font-weight: 600;")
        bottom_row.addWidget(self._count_lbl)
        bottom_row.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("OutlineButton")
        close_btn.setFixedSize(84, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                color: #334155;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
            }
        """)
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        layout.addLayout(bottom_row)

        self._load_data()

    def _load_data(self) -> None:
        """Fetch and populate history rows."""
        is_in = self._mode == "IN"
        if is_in:
            records = get_in_history(self._connection, self._item.id)
        else:
            records = get_out_history(self._connection, self._item.id)

        self._table.setRowCount(len(records))
        total_qty = 0.0

        for row, rec in enumerate(records):
            self._table.setRowHeight(row, 36)
            qty = float(rec["quantity"] or 0.0)
            total_qty += qty

            # 0. Sr
            sr_lbl = QLabel(str(row + 1))
            sr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sr_lbl.setStyleSheet("color: #64748B; font-size: 11.5px; font-weight: 600;")
            self._table.setCellWidget(row, 0, sr_lbl)

            # 1. Date & Time
            dt_lbl = QLabel(_format_datetime(rec.get("created_at")))
            dt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dt_lbl.setStyleSheet("color: #334155; font-size: 11.5px; font-weight: 500;")
            self._table.setCellWidget(row, 1, dt_lbl)

            # 2. Quantity
            qty_fmt = f"{qty:,.0f}" if qty.is_integer() else f"{qty:,.2f}"
            if is_in:
                qty_lbl = QLabel(f"+{qty_fmt} Units")
                qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qty_lbl.setStyleSheet("color: #047857; font-size: 12px; font-weight: 700;")
                self._table.setCellWidget(row, 2, qty_lbl)

                # 3. Notes
                notes_lbl = QLabel(str(rec.get("notes") or "Stock Added"))
                notes_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 500; padding-left: 8px;")
                self._table.setCellWidget(row, 3, notes_lbl)
            else:
                qty_lbl = QLabel(f"-{qty_fmt} Units")
                qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                qty_lbl.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 700;")
                self._table.setCellWidget(row, 2, qty_lbl)

                # 3. Bill / Invoice #
                bill_lbl = QLabel(str(rec.get("bill_number") or "—"))
                bill_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                bill_lbl.setStyleSheet("color: #2563EB; font-size: 12px; font-weight: 700;")
                self._table.setCellWidget(row, 3, bill_lbl)

                # 4. Party / Customer
                party_lbl = QLabel(str(rec.get("party_name") or "Direct Sale"))
                party_lbl.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 600; padding-left: 8px;")
                self._table.setCellWidget(row, 4, party_lbl)

        # Update stats
        tot_fmt = f"{total_qty:,.0f}" if total_qty.is_integer() else f"{total_qty:,.2f}"
        if is_in:
            self._stat_val.setText(f"+{tot_fmt} Units")
        else:
            self._stat_val.setText(f"-{tot_fmt} Units")

        self._count_lbl.setText(f"Showing {len(records)} movement record{'s' if len(records) != 1 else ''}")
