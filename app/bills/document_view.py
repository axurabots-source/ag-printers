"""Read-only BILL and CHALLAN / GATE PASS documents (V0.6).

One widget renders either document, so the bill and its matching challan are
always shown from the same records. Rates and totals appear on the BILL only,
while the CHALLAN / GATE PASS shows the same items and quantities - the content
stays consistent and each document keeps its clear purpose (spec Step 6).
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.bills import Bill, GatePass


class DocumentView(QWidget):
    """Shows one BILL or one CHALLAN / GATE PASS with its linked document."""

    #: Emitted when the user leaves the document.
    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._fields: dict[str, QLabel] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(14)

        # Action row (pages may add their own buttons) ---------------------
        back = QPushButton("< Back to List")
        back.setObjectName("OutlineButton")
        back.clicked.connect(self.back_requested.emit)
        self._actions = QHBoxLayout()
        self._actions.setSpacing(10)
        self._actions.addWidget(back)
        self._actions.addStretch(1)
        outer.addLayout(self._actions)

        # Document card ----------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("ProfileCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(32, 28, 32, 28)
        form.setSpacing(18)

        self._title = QLabel("INVOICE")
        self._title.setObjectName("ProfileName")
        self._number = QLabel("-")
        self._number.setObjectName("FieldValue")
        self._party = QLabel("-")
        self._party.setObjectName("FieldValue")
        self._party.setWordWrap(True)
        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(self._title)
        head.addWidget(self._number, 0, Qt.AlignmentFlag.AlignBottom)
        head.addStretch(1)
        head.addWidget(self._party, 0, Qt.AlignmentFlag.AlignBottom)
        form.addLayout(head)

        self._note = QLabel("")
        self._note.setObjectName("DocPill")
        self._note.setWordWrap(True)
        form.addWidget(self._note)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        def add_field(key: str, row: int, column: int) -> None:
            caption = QLabel(key)
            caption.setObjectName("FieldLabel")
            value = QLabel("-")
            value.setObjectName("FieldValue")
            value.setWordWrap(True)
            self._fields[key] = value
            grid.addWidget(caption, row, column)
            grid.addWidget(value, row + 1, column)

        add_field("Document Number", 0, 0)
        add_field("Date", 0, 1)
        add_field("Party", 2, 0)
        add_field("PO Number", 2, 1)
        add_field("Related Document", 4, 0)
        add_field("Items", 4, 1)
        form.addLayout(grid)

        self._items = QTableWidget(0, 4)
        self._items.setObjectName("POTable")
        self._items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._items.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._items.setShowGrid(False)
        self._items.verticalHeader().setVisible(False)
        self._items.verticalHeader().setDefaultSectionSize(40)
        form.addWidget(self._items)

        self._total = QLabel("-")
        self._total.setObjectName("TotalBar")
        form.addWidget(self._total)
        form.addStretch(1)

        body_layout.addWidget(card)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # -- page hooks --------------------------------------------------------

    def add_action(self, text: str, slot, danger: bool = False) -> QPushButton:
        """Add one page-specific action button to the document's top row."""
        button = QPushButton(text)
        button.setObjectName("DangerButton" if danger else "OutlineButton")
        button.clicked.connect(slot)
        self._actions.insertWidget(self._actions.count() - 1, button)
        return button

    # -- data --------------------------------------------------------------

    def set_bill(self, bill: Bill) -> None:
        """Render the INVOICE document of *bill*."""
        self._render(
            kind="INVOICE",
            number=bill.bill_number,
            date=bill.bill_date,
            party=bill.party_name,
            po_number=bill.po_number,
            related=bill.gate_pass_number,
            note=(
                "Gate Pass "
                f"{bill.gate_pass_number or '-'} was created automatically "
                "with this invoice."
            ),
            rows=[
                (item.description, item.quantity, item.rate) for item in bill.items
            ],
            show_rates=True,
            summary=(
                f"Total: {bill.total_amount:,.2f}   ·   "
                f"{bill.item_count} item(s)   ·   Qty {bill.total_quantity:g}"
            ),
        )

    def set_challan(self, gate_pass: GatePass, bill: Bill) -> None:
        """Render the GATE PASS that belongs to *bill*."""
        self._render(
            kind="GATE PASS",
            number=gate_pass.gate_pass_number,
            date=gate_pass.gate_pass_date,
            party=bill.party_name,
            po_number=bill.po_number,
            related=bill.bill_number,
            note=(
                f"This gate pass belongs to INVOICE {bill.bill_number} "
                "(one gate pass per invoice)."
            ),
            rows=[(item.description, item.quantity) for item in bill.items],
            show_rates=False,
            summary=f"{bill.item_count} item(s)   ·   Qty {bill.total_quantity:g}",
        )

    # -- internals ---------------------------------------------------------

    def _render(
        self,
        *,
        kind: str,
        number: str,
        date: str,
        party: str,
        po_number: str,
        related: str,
        note: str,
        rows: Sequence[tuple],
        show_rates: bool,
        summary: str,
    ) -> None:
        """Fill every part of the document."""
        self._title.setText(kind)
        self._number.setText(number)
        self._party.setText(party or "-")
        self._note.setText(note)
        self._fields["Document Number"].setText(number or "-")
        self._fields["Date"].setText(date or "-")
        self._fields["Party"].setText(party or "-")
        self._fields["PO Number"].setText(po_number or "-")
        self._fields["Related Document"].setText(related or "-")
        self._fields["Items"].setText(str(len(rows)))

        headers = ["Description", "Quantity"]
        if show_rates:
            headers += ["Rate", "Amount"]
        self._items.setColumnCount(len(headers))
        self._items.setHorizontalHeaderLabels(headers)
        header = self._items.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(headers)):
            header.setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )

        self._items.setRowCount(0)
        for row in rows:
            index = self._items.rowCount()
            self._items.insertRow(index)
            description, quantity = row[0], row[1]
            self._items.setItem(index, 0, QTableWidgetItem(str(description)))
            self._items.setItem(index, 1, QTableWidgetItem(f"{quantity:g}"))
            if show_rates:
                rate = float(row[2])
                self._items.setItem(index, 2, QTableWidgetItem(f"{rate:,.2f}"))
                self._items.setItem(
                    index, 3, QTableWidgetItem(f"{quantity * rate:,.2f}")
                )
        self._total.setText(summary)

