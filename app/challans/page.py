"""Gate Pass / Challan page (V0.6).

Challans are never created here: each one is generated automatically with its
bill (spec Step 6), so this module only lists them and opens the CHALLAN /
GATE PASS document together with the bill it belongs to.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.bills.document_view import DocumentView
from app.db.bills import (
    GatePass,
    delete_gate_pass,
    get_bill,
    get_gate_pass,
    list_gate_passes,
)
from app.jobs.pdf_generator import get_or_create_bill_pdf
from app.pdf_settings import open_pdf_file


class GatePassPage(QWidget):
    """Challan module root: list of challans plus the document itself."""

    #: Emitted with the document number when a document is shown.
    document_opened = Signal(str)
    #: Emitted when the view returns to the challan list.
    list_shown = Signal()

    _COLUMNS = (
        "Gate Pass Number",
        "Date",
        "Party",
        "PO Number",
        "Invoice Number",
        "Items",
        "Qty",
        "PDF",
    )

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._rows: list[GatePass] = []
        self._gate_pass: GatePass | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._list = self._build_list()
        self._document = DocumentView()
        self._stack.addWidget(self._list)  # index 0 = list
        self._stack.addWidget(self._document)  # index 1 = document
        layout.addWidget(self._stack)

        self._document.back_requested.connect(self.reset_to_list)
        self._showing = "challan"
        self._toggle_button = self._document.add_action(
            "Open Invoice", self._toggle_document
        )

    # -- list ------------------------------------------------------------

    def _build_list(self) -> QWidget:
        """Toolbar + table of gate passes (read-only: they come from invoices)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText("Search by gate pass, invoice, party or PO...")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(240)
        self._search.textChanged.connect(self._refresh)

        self._delete_button = QPushButton("Delete Gate Pass")
        self._delete_button.setObjectName("DangerButton")
        self._delete_button.clicked.connect(self._delete_selected_gate_pass)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self._search, 1)
        layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(self._COLUMNS))
        self._table.setObjectName("POTable")
        self._table.setHorizontalHeaderLabels(self._COLUMNS)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(46)
        header = self._table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 140)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 115)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(4, 120)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(5, 75)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(6, 100)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(7, 110)

        self._empty = QLabel(
            "No gate passes yet. One is generated automatically with every invoice."
        )
        self._empty.setObjectName("EmptyState")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)

        layout.addWidget(self._table, 1)
        layout.addWidget(self._empty, 1)
        self._refresh()
        return page

    def _refresh(self, *_args) -> None:
        """Reload the challan list using the current search text."""
        self._rows = list_gate_passes(self._connection, self._search.text())
        selected_id = self.selected_gate_pass_id()
        self._table.setRowCount(0)

        bold = QFont(self.font())
        bold.setBold(True)
        for gate_pass in self._rows:
            row = self._table.rowCount()
            self._table.insertRow(row)
            number_item = QTableWidgetItem(gate_pass.gate_pass_number)
            number_item.setData(Qt.ItemDataRole.UserRole, gate_pass.id)
            number_item.setFont(bold)
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, number_item)

            d_item = QTableWidgetItem(gate_pass.gate_pass_date)
            d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, d_item)

            p_item = QTableWidgetItem(gate_pass.party_name)
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, p_item)

            po_item = QTableWidgetItem(gate_pass.po_number or "—")
            po_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, po_item)

            b_item = QTableWidgetItem(gate_pass.bill_number or "—")
            b_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, b_item)

            c_item = QTableWidgetItem(str(gate_pass.item_count))
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 5, c_item)

            quantity_item = QTableWidgetItem(f"{gate_pass.total_quantity:g}")
            quantity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 6, quantity_item)

            pdf_btn = QPushButton("Open PDF")
            pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background: #0284c7;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
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
            pdf_btn.clicked.connect(lambda _checked=False, bid=gate_pass.bill_id: self._open_bill_pdf(bid))
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(6, 4, 6, 4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.addWidget(pdf_btn)
            self._table.setCellWidget(row, 7, btn_container)

        has_rows = bool(self._rows)
        self._table.setVisible(has_rows)
        self._empty.setVisible(not has_rows)

    def selected_gate_pass_id(self) -> int | None:
        """Id of the highlighted challan row (None when nothing is selected)."""
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # -- documents -------------------------------------------------------

    def reset_to_list(self) -> None:
        """Show and refresh the challan list."""
        self._gate_pass = None
        self._refresh()
        self._stack.setCurrentIndex(0)
        self.list_shown.emit()

    def open_challan(self, gate_pass_id: int) -> None:
        """Show the CHALLAN / GATE PASS document."""
        gate_pass = get_gate_pass(self._connection, gate_pass_id)
        bill = get_bill(self._connection, gate_pass.bill_id) if gate_pass else None
        if gate_pass is None or bill is None:
            self.reset_to_list()
            return
        self._gate_pass = gate_pass
        self._showing = "challan"
        self._toggle_button.setText("Open Invoice")
        self._document.set_challan(gate_pass, bill)
        self._stack.setCurrentIndex(1)
        self.document_opened.emit(gate_pass.gate_pass_number)

    def open_bill_for(self, gate_pass_id: int) -> None:
        """Show the BILL that this challan belongs to."""
        gate_pass = get_gate_pass(self._connection, gate_pass_id)
        bill = get_bill(self._connection, gate_pass.bill_id) if gate_pass else None
        if gate_pass is None or bill is None:
            self.reset_to_list()
            return
        self._gate_pass = gate_pass
        self._showing = "bill"
        self._toggle_button.setText("Open Gate Pass")
        self._document.set_bill(bill)
        self._stack.setCurrentIndex(1)
        self.document_opened.emit(bill.bill_number)

    # -- internals -------------------------------------------------------

    def _toggle_document(self) -> None:
        """Switch between the challan and the bill it belongs to."""
        if self._gate_pass is None:
            return
        if self._showing == "challan":
            self.open_bill_for(self._gate_pass.id)
        else:
            self.open_challan(self._gate_pass.id)

    def _sync_buttons(self) -> None:
        enabled = self.selected_gate_pass_id() is not None
        self._delete_button.setEnabled(enabled)

    def _delete_selected_gate_pass(self) -> None:
        gate_pass_id = self.selected_gate_pass_id()
        if gate_pass_id is None:
            return
        gate_pass = get_gate_pass(self._connection, gate_pass_id)
        if gate_pass is None:
            self.reset_to_list()
            return
        answer = QMessageBox.question(
            self,
            "Delete Gate Pass",
            f"Delete gate pass {gate_pass.gate_pass_number} for {gate_pass.party_name}?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        delete_gate_pass(self._connection, gate_pass_id)
        self.reset_to_list()

    def _emit_open(self) -> None:
        gate_pass_id = self.selected_gate_pass_id()
        if gate_pass_id is not None:
            self.open_challan(gate_pass_id)

    def _open_selected_bill(self) -> None:
        gate_pass_id = self.selected_gate_pass_id()
        if gate_pass_id is not None:
            self.open_bill_for(gate_pass_id)

    def _open_bill_pdf(self, bill_id: int) -> None:
        try:
            pdf_path = get_or_create_bill_pdf(self._connection, bill_id)
            if pdf_path and pdf_path.exists():
                open_pdf_file(pdf_path)
            else:
                QMessageBox.warning(self, "PDF Not Found", "Could not generate or find the PDF file.")
        except Exception as exc:
            QMessageBox.critical(self, "Error Opening PDF", str(exc))


