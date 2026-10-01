"""Bills page (V0.6): list <-> BILL / CHALLAN document, create + delete."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from app.bills.document_view import DocumentView
from app.bills.list_view import BillsListView
from app.db.bills import Bill, delete_bill, get_bill


class BillsPage(QWidget):
    """Bill module root: bills list plus the bill and challan documents."""

    #: Emitted with the bill number when a BILL document is shown.
    document_opened = Signal(str)
    #: Emitted when the view returns to the bill list.
    list_shown = Signal()
    #: Emitted when user clicks New Bill to open New Job workspace.
    new_requested = Signal()

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._bill: Bill | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._list = BillsListView(connection)
        self._document = DocumentView()
        self._stack.addWidget(self._list)  # index 0 = list
        self._stack.addWidget(self._document)  # index 1 = document
        layout.addWidget(self._stack)

        self._list.new_requested.connect(self._new_bill)
        self._list.delete_requested.connect(self._delete_bill)
        self._list.open_requested.connect(self.open_bill)
        self._document.back_requested.connect(self.reset_to_list)

        self._challan_button = self._document.add_action(
            "Open Challan", self._open_current_challan
        )
        self._delete_button = self._document.add_action(
            "Delete Bill", self._delete_current, danger=True
        )

    # -- public API (used by MainWindow and the PO module) -------------

    def reset_to_list(self) -> None:
        """Show and refresh the bills list."""
        self._bill = None
        self._list.refresh()
        self._stack.setCurrentIndex(0)
        self.list_shown.emit()

    def open_bill(self, bill_id: int) -> None:
        """Show the BILL document for *bill_id*."""
        bill = get_bill(self._connection, bill_id)
        if bill is None:
            self.reset_to_list()
            return
        self._bill = bill
        self._document.set_bill(bill)
        self._challan_button.setEnabled(bill.gate_pass is not None)
        self._stack.setCurrentIndex(1)
        self.document_opened.emit(bill.bill_number)

    def open_challan(self, bill_id: int) -> None:
        """Show the CHALLAN / GATE PASS that belongs to *bill_id*."""
        bill = get_bill(self._connection, bill_id)
        if bill is None or bill.gate_pass is None:
            QMessageBox.information(
                self, "No challan", "This bill has no matching challan."
            )
            return
        self._bill = bill
        self._document.set_challan(bill.gate_pass, bill)
        self._challan_button.setEnabled(False)
        self._stack.setCurrentIndex(1)
        self.document_opened.emit(bill.gate_pass.gate_pass_number)

    # -- internals -----------------------------------------------------

    def _new_bill(self) -> None:
        """Switch to New Job workspace to create a new bill."""
        self.new_requested.emit()

    def _open_current_challan(self) -> None:
        """Show the challan of the document currently on screen."""
        if self._bill is not None:
            self.open_challan(self._bill.id)

    def _delete_current(self) -> None:
        if self._bill is not None:
            self._delete_bill(self._bill.id)

    def _delete_bill(self, bill_id: int) -> None:
        """Delete a bill after confirmation; its matching challan goes too."""
        bill = get_bill(self._connection, bill_id)
        if bill is None:
            self.reset_to_list()
            return
        answer = QMessageBox.question(
            self,
            "Delete Bill",
            f"Delete bill {bill.bill_number} for {bill.party_name}?\n\n"
            f"Its matching challan {bill.gate_pass_number or '-'} and every "
            "billed line will be removed. This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        delete_bill(self._connection, bill_id)
        self.reset_to_list()
