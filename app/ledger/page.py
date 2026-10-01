"""Ledger page – profit summary of all saved bills (view-only).

Columns shown: Bill No. | Date | Party | PO Number | Challan | Total Amount | Net Profit | PDF
All data comes from the bills table; no editing is allowed.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.bills import Bill, list_bills
from app.jobs.pdf_generator import get_or_create_bill_pdf
from app.pdf_settings import open_pdf_file
from app.ui.calendar import (
    CLEAR_BTN_STYLE,
    DATE_EDIT_STYLE,
    FILTER_COMBO_STYLE,
    PremiumCalendarWidget,
)

LEDGER_TABLE_STYLE = """
QTableWidget#LedgerTable {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    color: #0F172A;
    font-size: 13px;
    outline: none;
}
QTableWidget#LedgerTable::item {
    padding: 5px 8px;
    border: none;
    outline: none;
}
QTableWidget#LedgerTable::item:focus {
    border: none;
    outline: none;
}
QTableWidget#LedgerTable::item:selected {
    background-color: #E6EEFB;
    color: #0F172A;
    border: none;
    outline: none;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #64748B;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 8px;
}
"""


class LedgerPage(QWidget):
    """Read-only ledger showing net profit per bill with date filtering and KPI cards."""

    _COLUMNS = (
        "Invoice No.",
        "Date",
        "Party",
        "PO Number",
        "Gate Pass",
        "Total Amount",
        "Net Profit",
        "PDF",
    )

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header strip ---------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title = QLabel("Profit Ledger")
        title.setObjectName("ProfileName")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")

        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText("Search by invoice #, party, PO, or gate pass #...")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(260)
        self._search.textChanged.connect(self.refresh)

        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self._search)
        layout.addLayout(header_row)

        # Date Filter Row -------------------------------------------------
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        date_lbl = QLabel("Date Filter:")
        date_lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 13px;")

        self._date_mode = QComboBox()
        self._date_mode.setObjectName("DateFilterCombo")
        self._date_mode.setStyleSheet(FILTER_COMBO_STYLE)
        self._date_mode.addItems([
            "All Dates",
            "Today",
            "This Month",
            "Specific Date",
            "Date Range",
        ])
        self._date_mode.currentIndexChanged.connect(self._on_date_mode_changed)

        self._single_date = QDateEdit(QDate.currentDate())
        self._single_date.setCalendarPopup(True)
        self._single_date.setCalendarWidget(PremiumCalendarWidget(self))
        self._single_date.setDisplayFormat("dd MMM yyyy")
        self._single_date.setStyleSheet(DATE_EDIT_STYLE)
        self._single_date.setVisible(False)
        self._single_date.dateChanged.connect(lambda _d: self.refresh())

        self._range_from_label = QLabel("From:")
        self._range_from_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        self._range_from_label.setVisible(False)

        self._date_from = QDateEdit(QDate.currentDate().addDays(-7))
        self._date_from.setCalendarPopup(True)
        self._date_from.setCalendarWidget(PremiumCalendarWidget(self))
        self._date_from.setDisplayFormat("dd MMM yyyy")
        self._date_from.setStyleSheet(DATE_EDIT_STYLE)
        self._date_from.setVisible(False)
        self._date_from.dateChanged.connect(lambda _d: self.refresh())

        self._range_to_label = QLabel("To:")
        self._range_to_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        self._range_to_label.setVisible(False)

        self._date_to = QDateEdit(QDate.currentDate())
        self._date_to.setCalendarPopup(True)
        self._date_to.setCalendarWidget(PremiumCalendarWidget(self))
        self._date_to.setDisplayFormat("dd MMM yyyy")
        self._date_to.setStyleSheet(DATE_EDIT_STYLE)
        self._date_to.setVisible(False)
        self._date_to.dateChanged.connect(lambda _d: self.refresh())

        self._clear_date_btn = QPushButton("✕ Clear Date")
        self._clear_date_btn.setStyleSheet(CLEAR_BTN_STYLE)
        self._clear_date_btn.setVisible(False)
        self._clear_date_btn.clicked.connect(self._reset_date_filter)

        filter_row.addWidget(date_lbl)
        filter_row.addWidget(self._date_mode)
        filter_row.addWidget(self._single_date)
        filter_row.addWidget(self._range_from_label)
        filter_row.addWidget(self._date_from)
        filter_row.addWidget(self._range_to_label)
        filter_row.addWidget(self._date_to)
        filter_row.addWidget(self._clear_date_btn)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        # Bary Boxes (Big KPI Summary Cards) ------------------------------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        card1, self._kpi_bills_val, self._kpi_bills_sub = self._make_kpi_card("TOTAL INVOICES", "#0F172A")
        card2, self._kpi_revenue_val, self._kpi_revenue_sub = self._make_kpi_card("TOTAL REVENUE", "#2563EB")
        card3, self._kpi_profit_val, self._kpi_profit_sub = self._make_kpi_card("TOTAL NET PROFIT", "#059669")

        kpi_row.addWidget(card1)
        kpi_row.addWidget(card2)
        kpi_row.addWidget(card3)
        layout.addLayout(kpi_row)

        # Table -----------------------------------------------------------
        self._table = QTableWidget(0, len(self._COLUMNS))
        self._table.setObjectName("LedgerTable")
        self._table.setStyleSheet(LEDGER_TABLE_STYLE)
        self._table.setHorizontalHeaderLabels(self._COLUMNS)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(46)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        hdr = self._table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setMinimumSectionSize(50)

        for col_idx in range(len(self._COLUMNS)):
            hdr.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Interactive)

        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Comfortable column sizing
        self._table.setColumnWidth(0, 105)  # Bill No.
        self._table.setColumnWidth(1, 130)  # Date (fully unhidden)
        self._table.setColumnWidth(2, 175)  # Party Name (stretches wider)
        self._table.setColumnWidth(3, 100)  # PO Number
        self._table.setColumnWidth(4, 140)  # Challan
        self._table.setColumnWidth(5, 120)  # Total Amount
        self._table.setColumnWidth(6, 110)  # Net Profit
        self._table.setColumnWidth(7, 90)   # PDF button

        self._empty = QLabel("No bills found for the selected date filter.")
        self._empty.setObjectName("EmptyState")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)

        layout.addWidget(self._table, 1)
        layout.addWidget(self._empty, 1)

        self.refresh()

    def _make_kpi_card(self, title: str, value_color: str) -> tuple[QFrame, QLabel, QLabel]:
        """Create a big, premium KPI summary box."""
        card = QFrame()
        card.setObjectName("KPICard")
        card.setStyleSheet("""
            QFrame#KPICard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QFrame#KPICard:hover {
                border-color: #CBD5E1;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")

        val_lbl = QLabel("0")
        val_lbl.setStyleSheet(f"color: {value_color}; font-size: 22px; font-weight: 700;")

        sub_lbl = QLabel("")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")

        card_layout.addWidget(title_lbl)
        card_layout.addWidget(val_lbl)
        card_layout.addWidget(sub_lbl)
        return card, val_lbl, sub_lbl

    # public
    def reset_to_list(self) -> None:
        """Called by MainWindow when this page is (re-)shown."""
        self.refresh()

    def _get_active_date_range(self) -> tuple[str, str]:
        mode = self._date_mode.currentText()
        if mode == "Today":
            today_str = QDate.currentDate().toString("yyyy-MM-dd")
            return today_str, today_str
        elif mode == "This Month":
            today = QDate.currentDate()
            first_day = QDate(today.year(), today.month(), 1).toString("yyyy-MM-dd")
            last_day = QDate(today.year(), today.month(), today.daysInMonth()).toString("yyyy-MM-dd")
            return first_day, last_day
        elif mode == "Specific Date":
            dt_str = self._single_date.date().toString("yyyy-MM-dd")
            return dt_str, dt_str
        elif mode == "Date Range":
            from_str = self._date_from.date().toString("yyyy-MM-dd")
            to_str = self._date_to.date().toString("yyyy-MM-dd")
            return from_str, to_str
        return "", ""

    def _on_date_mode_changed(self, index: int) -> None:
        mode = self._date_mode.currentText()
        is_all = (mode == "All Dates")
        is_single = (mode == "Specific Date")
        is_range = (mode == "Date Range")

        self._single_date.setVisible(is_single)
        self._range_from_label.setVisible(is_range)
        self._date_from.setVisible(is_range)
        self._range_to_label.setVisible(is_range)
        self._date_to.setVisible(is_range)
        self._clear_date_btn.setVisible(not is_all)

        self.refresh()

    def _reset_date_filter(self) -> None:
        self._date_mode.setCurrentIndex(0)

    def refresh(self, *_args) -> None:
        """Reload bills from DB using current search and date filter, and update KPI boxes."""
        date_from, date_to = self._get_active_date_range()
        bills: list[Bill] = list_bills(
            self._connection,
            search=self._search.text(),
            date_from=date_from,
            date_to=date_to,
        )

        bold = QFont()
        bold.setBold(True)

        self._table.setRowCount(0)
        total_profit = 0.0
        total_amount = 0.0

        for bill in bills:
            row = self._table.rowCount()
            self._table.insertRow(row)

            def _cell(text: str) -> QTableWidgetItem:
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return it

            # Bill No.
            bn = _cell(bill.bill_number)
            bn.setFont(bold)
            bn.setToolTip(bill.bill_number)
            self._table.setItem(row, 0, bn)

            # Date
            d_it = _cell(bill.bill_date)
            d_it.setToolTip(bill.bill_date)
            self._table.setItem(row, 1, d_it)

            # Party
            p_it = _cell(bill.party_name)
            p_it.setToolTip(bill.party_name)
            self._table.setItem(row, 2, p_it)

            # PO Number
            po_it = _cell(bill.po_number or "—")
            po_it.setToolTip(bill.po_number or "No PO Number")
            self._table.setItem(row, 3, po_it)

            # Challan
            ch_it = _cell(bill.gate_pass_number or "—")
            ch_it.setToolTip(bill.gate_pass_number or "No Challan")
            self._table.setItem(row, 4, ch_it)

            # Total Amount
            self._table.setItem(row, 5, _cell(f"{bill.total_amount:,.2f}"))

            # Net Profit
            profit_text = f"{bill.profit:,.2f}" if bill.profit else "—"
            profit_item = _cell(profit_text)
            if bill.profit > 0:
                profit_item.setForeground(QColor("#047857"))
                profit_item.setFont(bold)
            elif bill.profit < 0:
                profit_item.setForeground(QColor("#dc2626"))
                profit_item.setFont(bold)
            self._table.setItem(row, 6, profit_item)

            # PDF Button
            pdf_btn = QPushButton("Open PDF")
            pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background: #0284c7;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 12px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #0369a1;
                }
                QPushButton:pressed {
                    background: #075985;
                }
            """)
            pdf_btn.clicked.connect(lambda _checked=False, bid=bill.id: self._open_bill_pdf(bid))
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.addWidget(pdf_btn)
            self._table.setCellWidget(row, 7, btn_container)

            total_profit += bill.profit
            total_amount += bill.total_amount

        has_rows = bool(bills)
        self._table.setVisible(has_rows)
        self._empty.setVisible(not has_rows)

        # Update KPI Cards (bary boxes) -----------------------------------
        count = len(bills)
        self._kpi_bills_val.setText(f"{count} {'Invoice' if count == 1 else 'Invoices'}")

        mode = self._date_mode.currentText()
        if mode == "All Dates":
            period_text = "All time records"
        elif mode == "Today":
            period_text = f"Today ({QDate.currentDate().toString('dd MMM yyyy')})"
        elif mode == "This Month":
            period_text = f"Month of {QDate.currentDate().toString('MMMM yyyy')}"
        elif mode == "Specific Date":
            period_text = f"On {self._single_date.date().toString('dd MMM yyyy')}"
        elif mode == "Date Range":
            period_text = f"{self._date_from.date().toString('dd MMM')} – {self._date_to.date().toString('dd MMM yyyy')}"
        else:
            period_text = "Selected period"

        self._kpi_bills_sub.setText(period_text)

        self._kpi_revenue_val.setText(f"PKR {total_amount:,.2f}")
        self._kpi_revenue_sub.setText(f"Gross billed ({period_text})")

        profit_color = "#059669" if total_profit >= 0 else "#DC2626"
        self._kpi_profit_val.setText(f"PKR {total_profit:,.2f}")
        self._kpi_profit_val.setStyleSheet(f"color: {profit_color}; font-size: 22px; font-weight: 700;")

        margin_pct = (total_profit / total_amount * 100) if total_amount > 0 else 0.0
        self._kpi_profit_sub.setText(f"Net Margin: {margin_pct:.1f}%")

    def _open_bill_pdf(self, bill_id: int) -> None:
        try:
            pdf_path = get_or_create_bill_pdf(self._connection, bill_id)
            if pdf_path and pdf_path.exists():
                open_pdf_file(pdf_path)
            else:
                QMessageBox.warning(self, "PDF Not Found", "Could not generate or find the PDF file.")
        except Exception as exc:
            QMessageBox.critical(self, "Error Opening PDF", str(exc))
