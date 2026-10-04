"""Searchable list of bills and their matching challans (V0.6)."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
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

BILLS_TABLE_STYLE = """
QTableWidget#BillsTable {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    color: #0F172A;
    font-size: 13px;
    outline: none;
}
QTableWidget#BillsTable::item {
    padding: 4px 6px;
    border: none;
    outline: none;
}
QTableWidget#BillsTable::item:focus {
    border: none;
    outline: none;
}
QTableWidget#BillsTable::item:selected {
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
    padding: 9px 6px;
}
"""

DANGER_BTN_STYLE = """
QPushButton#DangerButton {
    background-color: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 8px;
    color: #DC2626;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
}
QPushButton#DangerButton:hover {
    background-color: #FEE2E2;
    border: 1px solid #F87171;
    color: #B91C1C;
}
QPushButton#DangerButton:disabled {
    background-color: #F9FAFB;
    color: #9CA3AF;
    border: 1px solid #E5E7EB;
}
"""


class BillsListView(QWidget):
    """Toolbar (search + date filter + actions) above a view-only table of bills."""

    #: Emitted when the user clicks "+ New Bill".
    new_requested = Signal()
    #: Emitted with the bill id when Delete is clicked.
    delete_requested = Signal(int)
    #: Emitted with the bill id when a row is double clicked or opened.
    open_requested = Signal(int)

    _COLUMNS = (
        "Invoice Number",
        "Date",
        "Party",
        "PO Number",
        "Items",
        "Total",
        "Profit",
        "Gate Pass",
        "PDF",
    )

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._rows: list[Bill] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Toolbar Row 1: Search + Actions ---------------------------------
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText("Search by invoice #, party, PO, or gate pass #...")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(240)
        self._search.textChanged.connect(self.refresh)

        self._delete_button = QPushButton("Delete Invoice")
        self._delete_button.setObjectName("DangerButton")
        self._delete_button.setStyleSheet(DANGER_BTN_STYLE)
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._emit_delete)

        row1.addWidget(self._search, 1)
        row1.addWidget(self._delete_button)
        layout.addLayout(row1)

        # Toolbar Row 2: Date filter strip (dedicated row prevents text collapse) --
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

        # Table -----------------------------------------------------------
        self._table = QTableWidget(0, len(self._COLUMNS))
        self._table.setObjectName("BillsTable")
        self._table.setStyleSheet(BILLS_TABLE_STYLE)
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

        header = self._table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumSectionSize(50)

        for col_idx in range(len(self._COLUMNS)):
            header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Interactive)

        # Party column stretches so it adapts dynamically to wide windows
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Optimized widths: slightly trimmed other columns so Date is 100% visible and unhidden
        self._table.setColumnWidth(0, 115)  # Invoice Number
        self._table.setColumnWidth(1, 130)  # Date (ample room, completely unhidden)
        self._table.setColumnWidth(2, 175)  # Party Name (stretches wider)
        self._table.setColumnWidth(3, 95)   # PO Number
        self._table.setColumnWidth(4, 55)   # Items
        self._table.setColumnWidth(5, 115)  # Total Amount
        self._table.setColumnWidth(6, 105)  # Profit
        self._table.setColumnWidth(7, 130)  # Gate Pass No
        self._table.setColumnWidth(8, 90)   # PDF button

        self._table.itemSelectionChanged.connect(self._sync_selection)
        self._table.cellDoubleClicked.connect(lambda _r, _c: self._open_selected())

        self._empty = QLabel(
            "No invoices found for the selected filter."
        )
        self._empty.setObjectName("EmptyState")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)

        layout.addWidget(self._table, 1)
        layout.addWidget(self._empty, 1)

        self.refresh()

    # -- data ----------------------------------------------------------

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
        """Reload bills using current search text and date filter."""
        selected_id = self.selected_bill_id()
        date_from, date_to = self._get_active_date_range()
        self._rows = list_bills(
            self._connection,
            search=self._search.text(),
            date_from=date_from,
            date_to=date_to,
        )
        self._table.setRowCount(0)

        bold = QFont(self.font())
        bold.setBold(True)
        for bill in self._rows:
            row = self._table.rowCount()
            self._table.insertRow(row)

            number_item = QTableWidgetItem(bill.bill_number)
            number_item.setData(Qt.ItemDataRole.UserRole, bill.id)
            number_item.setFont(bold)
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            number_item.setToolTip(bill.bill_number)
            self._table.setItem(row, 0, number_item)

            d_item = QTableWidgetItem(bill.bill_date)
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            d_item.setToolTip(bill.bill_date)
            self._table.setItem(row, 1, d_item)

            p_item = QTableWidgetItem(bill.party_name)
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            p_item.setToolTip(bill.party_name)
            self._table.setItem(row, 2, p_item)

            po_item = QTableWidgetItem(bill.po_number or "—")
            po_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            po_item.setToolTip(bill.po_number or "No PO Number")
            self._table.setItem(row, 3, po_item)

            c_item = QTableWidgetItem(str(bill.item_count))
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, c_item)

            total_item = QTableWidgetItem(f"{bill.total_amount:,.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 5, total_item)

            profit_val = f"{bill.profit:,.2f}" if bill.profit > 0 else "—"
            profit_item = QTableWidgetItem(profit_val)
            if bill.profit > 0:
                profit_item.setForeground(QColor("#047857"))
                profit_item.setFont(bold)
            profit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 6, profit_item)

            gp_val = bill.gate_pass_number or "—"
            gp_item = QTableWidgetItem(gp_val)
            gp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            gp_item.setToolTip(bill.gate_pass_number or "No Gate Pass")
            self._table.setItem(row, 7, gp_item)

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
            self._table.setCellWidget(row, 8, btn_container)

        has_rows = bool(self._rows)
        self._table.setVisible(has_rows)
        self._empty.setVisible(not has_rows)

        if selected_id is not None:
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self._table.selectRow(row)
                    break
        self._sync_selection()

    def selected_bill_id(self) -> int | None:
        """Id of the highlighted bill row (None when nothing is selected)."""
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # -- internals -----------------------------------------------------

    def _sync_selection(self) -> None:
        self._delete_button.setEnabled(self.selected_bill_id() is not None)

    def _open_selected(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is not None:
            self.open_requested.emit(bill_id)

    def _emit_delete(self) -> None:
        bill_id = self.selected_bill_id()
        if bill_id is not None:
            self.delete_requested.emit(bill_id)

    def _open_bill_pdf(self, bill_id: int) -> None:
        try:
            pdf_path = get_or_create_bill_pdf(self._connection, bill_id)
            if pdf_path and pdf_path.exists():
                open_pdf_file(pdf_path)
            else:
                QMessageBox.warning(self, "PDF Not Found", "Could not generate or find the PDF file.")
        except Exception as exc:
            QMessageBox.critical(self, "Error Opening PDF", str(exc))
