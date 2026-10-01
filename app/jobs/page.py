"""New Job / Billing Workspace page (V0.8).

Executive single-screen CRM terminal:
  1. Inline Party selection (no popup).
  2. Automatic document numbering for Bill and Delivery Challan.
  3. Job # and P.O. # direct manual inputs.
  4. Auto-expanding line items grid (no manual '+ Add Line' button required).
  5. Enter/Tab keyboard navigation for rapid data entry.
  6. Live CRM metric cards (Total Items, Total Qty, Net Invoice Amount).
  7. Vector SVG action icons (no emojis).
  8. One-click Save & Generate (Bill + Delivery Challan) and A4 Print Preview.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from PySide6.QtCore import QDate, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFocusEvent, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.bills import create_bill, suggest_bill_number, suggest_gate_pass_number
from app.db.parties import Party, list_parties
from app.jobs.a4_view import A4PrintPreviewDialog
from app.jobs.costing_drawer import JobCostingDrawer
from app.jobs.pdf_generator import get_or_create_bill_pdf
from app.ui.capitalized_input import capitalize_words, enable_auto_capitalization
from app.ui.theme import CHECK_SVG, EYE_SVG, REFRESH_SVG, TRASH_SVG


class CleanTableSpinBox(QDoubleSpinBox):
    """Smart numeric spinbox for Bill Items table:
    - Auto-selects text on click/focus so typing replaces the existing 0 immediately.
    - Clears the default 0 as soon as the user types a digit (0-9 or .), preventing '05' or '500'.
    - Fully preserves clean numeric typing and formatting.
    """

    def __init__(self, decimals: int = 2, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TableInput")
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setRange(0.0, 99999999.0)
        self.setDecimals(decimals)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        le = self.lineEdit()
        le.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mouse click auto-select
        orig_mp = le.mousePressEvent
        def on_mouse_press(e):
            if not le.hasFocus():
                orig_mp(e)
                QTimer.singleShot(0, self.selectAll)
            else:
                orig_mp(e)
        le.mousePressEvent = on_mouse_press

        # Key press handler: clear 0 when typing first digit
        orig_kp = le.keyPressEvent
        def on_key_press(e):
            if self.value() == 0.0 and e.text() and e.text() in "0123456789.":
                if not le.hasSelectedText():
                    le.clear()
            orig_kp(e)
        le.keyPressEvent = on_key_press

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)


class NewJobPage(QWidget):
    """Executive single-screen workspace for entering jobs, billing, and generating challans."""

    #: Emitted when a bill is created, passing the newly generated bill_id.
    bill_saved = Signal(int)

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._parties: list[Party] = []
        self._selected_party: Party | None = None
        self._is_updating_table = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 60)
        layout.setSpacing(16)

        # 1. Section Header ----------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("New Job & Invoicing Terminal")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Create and print Invoice & Gate Pass together on a single screen.")
        subtitle.setObjectName("FieldLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box)
        top_bar.addStretch(1)

        self._reset_btn = QPushButton("Reset Form")
        self._reset_btn.setObjectName("OutlineButton")
        self._reset_btn.setIcon(QIcon(REFRESH_SVG))
        self._reset_btn.setIconSize(QSize(15, 15))
        self._reset_btn.setToolTip("Clear all fields and restart")
        self._reset_btn.clicked.connect(self.reset_form)
        top_bar.addWidget(self._reset_btn)

        layout.addLayout(top_bar)

        # 2. Party Selection Card (Inline, No Popup) ----------------------------
        party_card = QFrame()
        party_card.setObjectName("ProfileCard")
        party_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        p_card_layout = QVBoxLayout(party_card)
        p_card_layout.setContentsMargins(20, 16, 20, 16)
        p_card_layout.setSpacing(10)

        party_title = QLabel("1. CLIENT & RECIPIENT INFORMATION")
        party_title.setObjectName("SectionLabel")
        p_card_layout.addWidget(party_title)

        party_row = QHBoxLayout()
        party_row.setSpacing(14)

        self._party_combo = QComboBox()
        self._party_combo.setObjectName("FormInput")
        self._party_combo.setMinimumWidth(340)
        self._party_combo.currentIndexChanged.connect(self._on_party_selected)
        party_row.addWidget(self._party_combo, 1)

        self._party_info = QLabel("Please choose a party to load invoicing tools.")
        self._party_info.setObjectName("FieldValue")
        party_row.addWidget(self._party_info, 2)

        p_card_layout.addLayout(party_row)
        layout.addWidget(party_card)

        # Placeholder Guide Card (Shows when no party is selected yet) ---------
        self._placeholder_guide = QFrame()
        self._placeholder_guide.setObjectName("ProfileCard")
        self._placeholder_guide.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        ph_layout = QVBoxLayout(self._placeholder_guide)
        ph_layout.setContentsMargins(32, 28, 32, 28)
        ph_layout.setSpacing(6)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ph_title = QLabel("Ready to Draft Invoice & Gate Pass")
        ph_title.setObjectName("DialogTitle")
        ph_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ph_sub = QLabel("Select a client from the dropdown above to load the invoicing terminal, document numbers, and auto-expanding items.")
        ph_sub.setObjectName("FieldLabel")
        ph_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ph_layout.addWidget(ph_title)
        ph_layout.addWidget(ph_sub)
        layout.addWidget(self._placeholder_guide)

        # 3. Bill & Challan Section (Shows once party is selected) -------------
        self._bill_container = QWidget()
        b_layout = QVBoxLayout(self._bill_container)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(16)

        # 3a. Metadata Card
        meta_card = QFrame()
        meta_card.setObjectName("ProfileCard")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(20, 18, 20, 18)
        meta_layout.setSpacing(12)

        meta_title = QLabel("2. DOCUMENT & ORDER IDENTIFIERS")
        meta_title.setObjectName("SectionLabel")
        meta_layout.addWidget(meta_title)

        meta_grid = QHBoxLayout()
        meta_grid.setSpacing(16)

        # Row 1: Date, Invoice #, Gate Pass #
        row1_grid = QHBoxLayout()
        row1_grid.setSpacing(14)

        # Date
        date_box = QVBoxLayout()
        date_box.setSpacing(4)
        date_lbl = QLabel("Date")
        date_lbl.setObjectName("FieldLabel")
        self._date_edit = QDateEdit()
        self._date_edit.setObjectName("FormInput")
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._date_edit.setDate(QDate.currentDate())
        self._date_edit.setMinimumWidth(165)
        self._date_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        date_box.addWidget(date_lbl)
        date_box.addWidget(self._date_edit)
        row1_grid.addLayout(date_box, 1)

        # Invoice # (Auto suggested, editable)
        bill_box = QVBoxLayout()
        bill_box.setSpacing(4)
        bill_lbl = QLabel("Invoice # (Auto)")
        bill_lbl.setObjectName("FieldLabel")
        self._bill_num_edit = QLineEdit()
        self._bill_num_edit.setObjectName("FormInput")
        enable_auto_capitalization(self._bill_num_edit)
        bill_box.addWidget(bill_lbl)
        bill_box.addWidget(self._bill_num_edit)
        row1_grid.addLayout(bill_box, 1)

        # Gate Pass # (Auto suggested, editable)
        dc_box = QVBoxLayout()
        dc_box.setSpacing(4)
        dc_lbl = QLabel("Gate Pass # (Auto)")
        dc_lbl.setObjectName("FieldLabel")
        self._dc_num_edit = QLineEdit()
        self._dc_num_edit.setObjectName("FormInput")
        enable_auto_capitalization(self._dc_num_edit)
        dc_box.addWidget(dc_lbl)
        dc_box.addWidget(self._dc_num_edit)
        row1_grid.addLayout(dc_box, 1)

        meta_layout.addLayout(row1_grid)

        # Row 2 (Alag row nichy): Reference numbers (P.O. #, Job #, Customer P.O. #)
        row2_grid = QHBoxLayout()
        row2_grid.setSpacing(14)

        # PO Number (Party PO, direct entry)
        po_box = QVBoxLayout()
        po_box.setSpacing(4)
        po_lbl = QLabel("P.O. # (From Party)")
        po_lbl.setObjectName("FieldLabel")
        self._po_edit = QLineEdit()
        self._po_edit.setObjectName("FormInput")
        self._po_edit.setPlaceholderText("e.g. PO-786")
        enable_auto_capitalization(self._po_edit)
        po_box.addWidget(po_lbl)
        po_box.addWidget(self._po_edit)
        row2_grid.addLayout(po_box, 1)

        # Job Number (Party Job #, direct entry)
        job_box = QVBoxLayout()
        job_box.setSpacing(4)
        job_lbl = QLabel("Job # (Party Job #)")
        job_lbl.setObjectName("FieldLabel")
        self._job_num_edit = QLineEdit()
        self._job_num_edit.setObjectName("FormInput")
        self._job_num_edit.setPlaceholderText("e.g. JB-1029")
        enable_auto_capitalization(self._job_num_edit)
        job_box.addWidget(job_lbl)
        job_box.addWidget(self._job_num_edit)
        row2_grid.addLayout(job_box, 1)

        # Customer PO Number (Direct entry)
        cust_po_box = QVBoxLayout()
        cust_po_box.setSpacing(4)
        cust_po_lbl = QLabel("Customer P.O. # (Manual)")
        cust_po_lbl.setObjectName("FieldLabel")
        self._cust_po_edit = QLineEdit()
        self._cust_po_edit.setObjectName("FormInput")
        self._cust_po_edit.setPlaceholderText("e.g. CUST-PO-104")
        enable_auto_capitalization(self._cust_po_edit)
        cust_po_box.addWidget(cust_po_lbl)
        cust_po_box.addWidget(self._cust_po_edit)
        row2_grid.addLayout(cust_po_box, 1)

        meta_layout.addLayout(row2_grid)
        b_layout.addWidget(meta_card)

        # 3b. Items Grid Card (Auto-Expanding Editable Table)
        table_card = QFrame()
        table_card.setObjectName("ProfileCard")
        t_card_layout = QVBoxLayout(table_card)
        t_card_layout.setContentsMargins(20, 18, 20, 18)
        t_card_layout.setSpacing(12)

        t_header = QHBoxLayout()
        t_header.setSpacing(12)
        grid_title = QLabel("3. INVOICE & GATE PASS ITEMS (AUTO-EXPANDING)")
        grid_title.setObjectName("SectionLabel")
        t_header.addWidget(grid_title)

        hint_badge = QLabel("Next row adds automatically as you type. Use Tab or Enter to navigate.")
        hint_badge.setObjectName("FieldLabel")
        t_header.addWidget(hint_badge)
        t_header.addStretch(1)

        clear_lines_btn = QPushButton("Clear Lines")
        clear_lines_btn.setObjectName("OutlineButton")
        clear_lines_btn.setIcon(QIcon(TRASH_SVG))
        clear_lines_btn.setIconSize(QSize(14, 14))
        clear_lines_btn.clicked.connect(self.clear_table)
        t_header.addWidget(clear_lines_btn)

        t_card_layout.addLayout(t_header)

        # Table Widget
        self._table = QTableWidget(0, 9)
        self._table.setObjectName("POTable")
        self._table.setHorizontalHeaderLabels([
            "SR NO",
            "DESCRIPTION *",
            "QTY *",
            "COST (RS.)",
            "SELL (RS.) *",
            "TOTAL (RS.)",
            "PROFIT/UNIT",
            "TOTAL PROFIT",
            "",
        ])
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(46)
        self._table.setMinimumHeight(240)
        self._table.setStyleSheet("""
            QTableWidget#POTable {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QTableWidget#POTable::item {
                border: none;
                outline: none;
            }
            QTableWidget#POTable::item:selected {
                background: transparent;
                border: none;
                outline: none;
            }
            QTableWidget#POTable::item:focus {
                background: transparent;
                border: none;
                outline: none;
            }
        """)

        header = self._table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 55)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 75)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 90)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(4, 90)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(5, 105)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(6, 100)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(7, 105)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(8, 44)

        self._table.currentCellChanged.connect(self._on_table_cell_changed)

        t_card_layout.addWidget(self._table)

        # 3c. CRM Metric Summary Tiles (Items, Qty, Amount, Profit - Strictly Centralized)
        metric_bar = QHBoxLayout()
        metric_bar.setSpacing(14)

        # Card 1: Total Items
        c1 = QFrame()
        c1.setObjectName("CrmMetricCard")
        c1_l = QVBoxLayout(c1)
        c1_l.setContentsMargins(12, 10, 12, 10)
        c1_l.setSpacing(3)
        c1_lbl = QLabel("TOTAL ITEMS")
        c1_lbl.setObjectName("CrmMetricLabel")
        c1_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._metric_items_val = QLabel("0 Items")
        self._metric_items_val.setObjectName("CrmMetricValue")
        self._metric_items_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c1_l.addWidget(c1_lbl)
        c1_l.addWidget(self._metric_items_val)
        metric_bar.addWidget(c1, 1)

        # Card 2: Total Qty
        c2 = QFrame()
        c2.setObjectName("CrmMetricCard")
        c2_l = QVBoxLayout(c2)
        c2_l.setContentsMargins(12, 10, 12, 10)
        c2_l.setSpacing(3)
        c2_lbl = QLabel("TOTAL QUANTITY")
        c2_lbl.setObjectName("CrmMetricLabel")
        c2_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._metric_qty_val = QLabel("0 Units")
        self._metric_qty_val.setObjectName("CrmMetricValue")
        self._metric_qty_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c2_l.addWidget(c2_lbl)
        c2_l.addWidget(self._metric_qty_val)
        metric_bar.addWidget(c2, 1)

        # Card 3: Grand Total
        c3 = QFrame()
        c3.setObjectName("CrmMetricCard")
        c3_l = QVBoxLayout(c3)
        c3_l.setContentsMargins(12, 10, 12, 10)
        c3_l.setSpacing(3)
        c3_lbl = QLabel("NET INVOICE AMOUNT")
        c3_lbl.setObjectName("CrmMetricLabel")
        c3_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._metric_amount_val = QLabel("Rs. 0.00")
        self._metric_amount_val.setObjectName("CrmMetricValueAccent")
        self._metric_amount_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c3_l.addWidget(c3_lbl)
        c3_l.addWidget(self._metric_amount_val)
        metric_bar.addWidget(c3, 1)

        # Card 4: Total Net Profit
        c4 = QFrame()
        c4.setObjectName("CrmMetricCard")
        c4_l = QVBoxLayout(c4)
        c4_l.setContentsMargins(12, 10, 12, 10)
        c4_l.setSpacing(3)
        c4_lbl = QLabel("TOTAL NET PROFIT")
        c4_lbl.setObjectName("CrmMetricLabel")
        c4_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._metric_profit_val = QLabel("Rs. 0.00")
        self._metric_profit_val.setObjectName("CrmMetricValueSuccess")
        self._metric_profit_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c4_l.addWidget(c4_lbl)
        c4_l.addWidget(self._metric_profit_val)
        metric_bar.addWidget(c4, 1)

        t_card_layout.addLayout(metric_bar)
        b_layout.addWidget(table_card)

        # 3e. Production Costing & Profit Drawer (Starts CLOSED by default)
        self._committed_inventory_materials: dict[int, list[tuple[int, float]]] = {}
        self._costing_drawer = JobCostingDrawer(connection=self._connection, parent=self)
        self._costing_drawer.costing_applied.connect(self._apply_costing_to_bill)
        self._costing_drawer.rate_applied.connect(self._apply_costing_rate_to_bill)
        self._costing_drawer.cost_unit_calculated.connect(self._on_costing_cost_received)
        self._costing_drawer.sell_price_calculated.connect(self._on_costing_sell_price_received)
        self._costing_drawer.material_selected.connect(self._on_costing_material_selected)
        b_layout.addWidget(self._costing_drawer)

        # 4. Actions Row: Save & Preview Buttons --------------------------------
        action_bar = QHBoxLayout()
        action_bar.setSpacing(14)
        action_bar.addStretch(1)

        self._preview_btn = QPushButton("Print / Preview A4 (Invoice & Gate Pass)...")
        self._preview_btn.setObjectName("OutlineButton")
        self._preview_btn.setIcon(QIcon(EYE_SVG))
        self._preview_btn.setIconSize(QSize(16, 16))
        self._preview_btn.setMinimumHeight(42)
        self._preview_btn.clicked.connect(self._open_preview)
        action_bar.addWidget(self._preview_btn)

        self._save_btn = QPushButton("Save & Generate Invoice + Gate Pass")
        self._save_btn.setObjectName("SuccessButton")
        self._save_btn.setIcon(QIcon(CHECK_SVG))
        self._save_btn.setIconSize(QSize(16, 16))
        self._save_btn.setMinimumHeight(42)
        self._save_btn.clicked.connect(self._save_job)
        action_bar.addWidget(self._save_btn)

        b_layout.addLayout(action_bar)
        b_layout.addSpacing(60)
        layout.addWidget(self._bill_container)
        layout.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        # Initialize
        self.load_parties()
        self._bill_container.setVisible(False)
        self._placeholder_guide.setVisible(True)

    # -- party loading & selection -----------------------------------------

    def load_parties(self) -> None:
        """Populate party dropdown from database."""
        self._party_combo.blockSignals(True)
        self._party_combo.clear()
        self._party_combo.addItem("Select Client / Party", None)
        self._parties = list_parties(self._connection)
        for p in self._parties:
            contact = f" ({p.contact_person})" if p.contact_person else ""
            self._party_combo.addItem(f"{p.name}{contact}", p.id)
        self._party_combo.blockSignals(False)

    def _on_party_selected(self, index: int) -> None:
        party_id = self._party_combo.currentData()
        if party_id is None:
            self._selected_party = None
            self._party_info.setText("Please choose a party to load invoicing tools.")
            self._bill_container.setVisible(False)
            self._placeholder_guide.setVisible(True)
            return

        self._selected_party = next((p for p in self._parties if p.id == party_id), None)
        if self._selected_party is not None:
            details = []
            if self._selected_party.phone:
                details.append(f"Phone: {self._selected_party.phone}")
            if self._selected_party.address:
                details.append(f"Address: {self._selected_party.address}")
            self._party_info.setText("  |  ".join(details) or "Active Client Profile")

            # Show Bill Section & prepare numbers
            self._bill_num_edit.setText(suggest_bill_number(self._connection))
            self._dc_num_edit.setText(suggest_gate_pass_number(self._connection))
            self._placeholder_guide.setVisible(False)
            self._bill_container.setVisible(True)

            if self._table.rowCount() == 0:
                self.add_row(focus_desc=False)

    # -- table row management (auto-expanding) -----------------------------

    def add_row(
        self,
        description: str = "",
        quantity: float = 0.0,
        cost_price: float = 0.0,
        rate: float = 0.0,
        focus_desc: bool = False,
    ) -> None:
        """Add an editable line row to the grid (defensive against Qt signal bools)."""
        if not isinstance(description, str):
            description = ""
        if not isinstance(quantity, (int, float)):
            quantity = 0.0
        if not isinstance(cost_price, (int, float)):
            cost_price = 0.0
        if not isinstance(rate, (int, float)):
            rate = 0.0

        row = self._table.rowCount()
        self._table.insertRow(row)

        # 0. Sr. No
        sr_lbl = QLabel(str(row + 1))
        sr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_lbl.setObjectName("FieldValue")
        sr_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._table.setCellWidget(row, 0, sr_lbl)

        # 1. Description (editable text)
        desc_edit = QLineEdit()
        desc_edit.setObjectName("FormInput")
        desc_edit.setPlaceholderText("Enter item description...")
        desc_edit.setText(capitalize_words(description))
        enable_auto_capitalization(desc_edit)
        desc_edit.textChanged.connect(self._on_row_data_changed)
        self._table.setCellWidget(row, 1, desc_edit)

        # 2. Quantity (editable number, centralized)
        qty_spin = CleanTableSpinBox(decimals=0)
        qty_spin.setValue(quantity)
        qty_spin.valueChanged.connect(self._on_row_data_changed)
        self._table.setCellWidget(row, 2, qty_spin)

        # 3. Cost Price (editable cost per unit, centralized)
        cost_spin = CleanTableSpinBox(decimals=2)
        cost_spin.setValue(cost_price)
        cost_spin.valueChanged.connect(self._on_row_data_changed)
        self._table.setCellWidget(row, 3, cost_spin)

        # 4. Sell Price / Rate (editable sell price per unit, centralized)
        rate_spin = CleanTableSpinBox(decimals=2)
        rate_spin.setValue(rate)
        rate_spin.valueChanged.connect(self._on_row_data_changed)
        self._table.setCellWidget(row, 4, rate_spin)

        # Keyboard Navigation: Enter key flow
        desc_edit.returnPressed.connect(qty_spin.setFocus)
        qty_spin.lineEdit().returnPressed.connect(cost_spin.setFocus)
        cost_spin.lineEdit().returnPressed.connect(rate_spin.setFocus)
        rate_spin.lineEdit().returnPressed.connect(self._on_rate_enter)

        # 5. Total Amount (calculated display: qty * sell_rate, centralized)
        amt_lbl = QLabel("0.00")
        amt_lbl.setObjectName("RowAmount")
        amt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        amt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._table.setCellWidget(row, 5, amt_lbl)

        # 6. Profit Per Unit (calculated display: sell_rate - cost_price, non-editable, centralized)
        unit_profit_lbl = QLabel("0.00")
        unit_profit_lbl.setObjectName("RowUnitProfit")
        unit_profit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unit_profit_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        unit_profit_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; qproperty-alignment: AlignCenter;")
        self._table.setCellWidget(row, 6, unit_profit_lbl)

        # 7. Total Net Profit (calculated display: (sell_rate - cost_price) * qty, non-editable, centralized)
        profit_lbl = QLabel("0.00")
        profit_lbl.setObjectName("RowProfit")
        profit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profit_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        profit_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; qproperty-alignment: AlignCenter;")
        self._table.setCellWidget(row, 7, profit_lbl)

        # 8. Remove Button (shifted left away from the right table border)
        del_wrap = QWidget()
        del_wrap.setStyleSheet("background: transparent; border: none;")
        del_layout = QHBoxLayout(del_wrap)
        del_layout.setContentsMargins(0, 0, 10, 0)
        del_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        del_btn = QPushButton()
        del_btn.setObjectName("RemoveRowButton")
        del_btn.setIcon(QIcon(TRASH_SVG))
        del_btn.setIconSize(QSize(15, 15))
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("Remove this row")
        del_btn.clicked.connect(self._on_remove_clicked)
        del_layout.addWidget(del_btn)
        self._table.setCellWidget(row, 8, del_wrap)

        self._refresh_sr_numbers()
        self._sync_totals()

        if focus_desc:
            desc_edit.setFocus()
            self._table.scrollToBottom()

    def _on_row_data_changed(self) -> None:
        """Triggered whenever description, qty, cost, or rate changes."""
        if self._is_updating_table:
            return

        self._sync_totals()

        # Auto-append next row if the last row currently has content
        total_rows = self._table.rowCount()
        if total_rows > 0:
            last_desc_w = self._table.cellWidget(total_rows - 1, 1)
            last_qty_w = self._table.cellWidget(total_rows - 1, 2)

            desc = last_desc_w.text().strip() if isinstance(last_desc_w, QLineEdit) else ""
            qty = last_qty_w.value() if isinstance(last_qty_w, QDoubleSpinBox) else 0.0

            if desc or qty > 0:
                self._is_updating_table = True
                self.add_row(focus_desc=False)
                self._is_updating_table = False

    def _on_rate_enter(self) -> None:
        """Handle Enter key in rate box: move cursor to next row description."""
        sender_edit = self.sender()
        target_row = -1
        for r in range(self._table.rowCount()):
            rate_w = self._table.cellWidget(r, 4)
            if isinstance(rate_w, QDoubleSpinBox) and rate_w.lineEdit() is sender_edit:
                target_row = r
                break

        if target_row == -1:
            return

        # If on the last row, ensure next row exists and focus it
        if target_row == self._table.rowCount() - 1:
            self.add_row(focus_desc=True)
        else:
            next_desc = self._table.cellWidget(target_row + 1, 1)
            if isinstance(next_desc, QLineEdit):
                next_desc.setFocus()

    def _on_remove_clicked(self) -> None:
        """Dynamic sender-based row removal avoiding index mismatch or signal bugs."""
        sender_btn = self.sender()
        for r in range(self._table.rowCount()):
            cell_w = self._table.cellWidget(r, 8)
            if cell_w is sender_btn or (cell_w is not None and sender_btn in cell_w.findChildren(QPushButton)):
                self._remove_row(r)
                break

    def _remove_row(self, row_idx: int) -> None:
        """Remove a row and refresh table state."""
        self._is_updating_table = True
        if self._table.rowCount() <= 1:
            self.clear_table()
            self._is_updating_table = False
            return

        self._table.removeRow(row_idx)

        # Shift committed materials indices down for rows after row_idx
        new_committed = {}
        for r, mats in self._committed_inventory_materials.items():
            if r < row_idx:
                new_committed[r] = mats
            elif r > row_idx:
                new_committed[r - 1] = mats
        self._committed_inventory_materials = new_committed

        self._refresh_sr_numbers()
        self._sync_totals()

        # If the new last row has content, make sure an empty trailing row exists
        last_r = self._table.rowCount() - 1
        if last_r >= 0:
            last_desc = self._table.cellWidget(last_r, 1)
            last_qty = self._table.cellWidget(last_r, 2)
            d_val = last_desc.text().strip() if isinstance(last_desc, QLineEdit) else ""
            q_val = last_qty.value() if isinstance(last_qty, QDoubleSpinBox) else 0.0
            if d_val or q_val > 0:
                self.add_row(focus_desc=False)

        self._is_updating_table = False

    def _refresh_sr_numbers(self) -> None:
        for r in range(self._table.rowCount()):
            sr_widget = self._table.cellWidget(r, 0)
            if isinstance(sr_widget, QLabel):
                sr_widget.setText(str(r + 1))

    def clear_table(self) -> None:
        self._is_updating_table = True
        self._committed_inventory_materials.clear()
        self._table.setRowCount(0)
        self.add_row(focus_desc=False)
        self._is_updating_table = False
        self._sync_totals()

    # -- calculation & synchronization -------------------------------------

    def _sync_totals(self) -> None:
        total_items = 0
        total_qty = 0.0
        grand_total = 0.0
        total_cost = 0.0
        total_profit = 0.0
        has_any_cost = False
        items_for_drawer = []

        for r in range(self._table.rowCount()):
            desc_widget = self._table.cellWidget(r, 1)
            qty_widget = self._table.cellWidget(r, 2)
            cost_widget = self._table.cellWidget(r, 3)
            rate_widget = self._table.cellWidget(r, 4)
            amt_widget = self._table.cellWidget(r, 5)
            unit_profit_widget = self._table.cellWidget(r, 6)
            total_profit_widget = self._table.cellWidget(r, 7)

            if not (
                isinstance(qty_widget, QDoubleSpinBox)
                and isinstance(cost_widget, QDoubleSpinBox)
                and isinstance(rate_widget, QDoubleSpinBox)
            ):
                continue

            qty = qty_widget.value()
            cost_p = cost_widget.value()
            rate_p = rate_widget.value()

            line_amt = qty * rate_p
            line_cost = qty * cost_p
            line_unit_profit = rate_p - cost_p
            line_total_profit = (rate_p - cost_p) * qty

            if isinstance(amt_widget, QLabel):
                amt_widget.setText(f"{line_amt:,.2f}")
                amt_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if isinstance(unit_profit_widget, QLabel):
                unit_profit_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if cost_p > 0:
                    u_sign = "+" if line_unit_profit >= 0 else ""
                    u_color = "#047857" if line_unit_profit >= 0 else "#DC2626"
                    unit_profit_widget.setText(f"{u_sign}{line_unit_profit:,.2f}")
                    unit_profit_widget.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {u_color}; qproperty-alignment: AlignCenter;")
                else:
                    unit_profit_widget.setText("0.00")
                    unit_profit_widget.setStyleSheet("font-size: 12px; color: #94A3B8; qproperty-alignment: AlignCenter;")

            if isinstance(total_profit_widget, QLabel):
                total_profit_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if cost_p > 0:
                    has_any_cost = True
                    sign = "+" if line_total_profit >= 0 else ""
                    color = "#047857" if line_total_profit >= 0 else "#DC2626"
                    total_profit_widget.setText(f"{sign}{line_total_profit:,.2f}")
                    total_profit_widget.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {color}; qproperty-alignment: AlignCenter;")
                else:
                    total_profit_widget.setText("0.00")
                    total_profit_widget.setStyleSheet("font-size: 12px; color: #94A3B8; qproperty-alignment: AlignCenter;")

            desc = desc_widget.text().strip() if isinstance(desc_widget, QLineEdit) else ""
            if desc or qty > 0:
                total_items += 1
                total_qty += qty
                grand_total += line_amt
                total_cost += line_cost
                if cost_p > 0:
                    total_profit += line_total_profit
                items_for_drawer.append({
                    "row_index": r,
                    "description": desc,
                    "quantity": qty,
                    "cost_price": cost_p,
                    "rate": rate_p,
                })

        # Update CRM metric cards
        self._metric_items_val.setText(f"{total_items} Items")
        self._metric_qty_val.setText(f"{total_qty:g} Units")
        self._metric_amount_val.setText(f"Rs. {grand_total:,.2f}")

        drawer_cost = self._costing_drawer.get_total_cost() if hasattr(self, "_costing_drawer") else 0.0
        final_profit = total_profit
        if drawer_cost > 0 and not has_any_cost:
            final_profit = grand_total - drawer_cost

        if hasattr(self, "_metric_profit_val"):
            p_sign = "+" if final_profit >= 0 else ""
            p_color = "#047857" if final_profit >= 0 else "#DC2626"
            self._metric_profit_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if total_items > 0 and (has_any_cost or drawer_cost > 0):
                self._metric_profit_val.setText(f"{p_sign}Rs. {final_profit:,.2f}")
                self._metric_profit_val.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {p_color}; qproperty-alignment: AlignCenter;")
            else:
                self._metric_profit_val.setText("Rs. 0.00")
                self._metric_profit_val.setStyleSheet("font-size: 16px; font-weight: 800; color: #64748B; qproperty-alignment: AlignCenter;")

        # Update Costing Drawer's items list
        if hasattr(self, "_costing_drawer"):
            self._costing_drawer.update_item_list(items_for_drawer)

    def _on_table_cell_changed(self, current_row: int, current_col: int, prev_row: int, prev_col: int) -> None:
        """Keep costing drawer synced with the currently selected or active table row."""
        if current_row < 0 or current_row >= self._table.rowCount():
            return
        if not hasattr(self, "_costing_drawer"):
            return
        desc_w = self._table.cellWidget(current_row, 1)
        qty_w = self._table.cellWidget(current_row, 2)
        cost_w = self._table.cellWidget(current_row, 3)
        rate_w = self._table.cellWidget(current_row, 4)
        desc = desc_w.text().strip() if isinstance(desc_w, QLineEdit) else ""
        qty = qty_w.value() if isinstance(qty_w, QDoubleSpinBox) else 0.0
        cost_p = cost_w.value() if isinstance(cost_w, QDoubleSpinBox) else 0.0
        rate_p = rate_w.value() if isinstance(rate_w, QDoubleSpinBox) else 0.0

        self._costing_drawer.sync_from_row(current_row, desc, qty, rate_p, cost_p)

    def _on_costing_cost_received(self, row_idx: int, unit_cost: float) -> None:
        """Automatically set Cost Price on the target bill row from the costing drawer."""
        if 0 <= row_idx < self._table.rowCount():
            cost_w = self._table.cellWidget(row_idx, 3)
            if isinstance(cost_w, QDoubleSpinBox):
                cost_w.blockSignals(True)
                cost_w.setValue(unit_cost)
                cost_w.blockSignals(False)
                self._sync_totals()

    def _on_costing_sell_price_received(self, row_idx: int, sell_price: float) -> None:
        """Set Sell Price on the target bill row when typed in costing drawer."""
        if 0 <= row_idx < self._table.rowCount():
            rate_w = self._table.cellWidget(row_idx, 4)
            if isinstance(rate_w, QDoubleSpinBox):
                rate_w.blockSignals(True)
                rate_w.setValue(sell_price)
                rate_w.blockSignals(False)
                self._sync_totals()

    def _on_costing_material_selected(self, row_idx: int, detail: str) -> None:
        """When user selects a material from barcode inventory, prefill line description if currently blank."""
        if 0 <= row_idx < self._table.rowCount():
            desc_w = self._table.cellWidget(row_idx, 1)
            if isinstance(desc_w, QLineEdit) and not desc_w.text().strip() and detail:
                desc_w.setText(capitalize_words(detail))

    def _apply_costing_to_bill(
        self,
        row_idx: int,
        sell_price: float,
        unit_cost: float,
        quantity: float,
        description: str = "",
    ) -> None:
        """Apply all costing values (Description, Quantity, Cost Price, Sell Rate) directly to the target bill row."""
        if self._table.rowCount() == 0:
            self.add_row(focus_desc=False)
        target_row = row_idx if 0 <= row_idx < self._table.rowCount() else 0

        self._is_updating_table = True

        desc_w = self._table.cellWidget(target_row, 1)
        qty_w = self._table.cellWidget(target_row, 2)
        cost_w = self._table.cellWidget(target_row, 3)
        rate_w = self._table.cellWidget(target_row, 4)

        if isinstance(desc_w, QLineEdit) and description:
            desc_w.setText(capitalize_words(description))

        if isinstance(qty_w, QDoubleSpinBox) and quantity > 0:
            qty_w.setValue(quantity)
        if isinstance(cost_w, QDoubleSpinBox) and unit_cost > 0:
            cost_w.setValue(unit_cost)
        if isinstance(rate_w, QDoubleSpinBox) and sell_price > 0:
            rate_w.setValue(sell_price)

        self._is_updating_table = False
        self._sync_totals()

        # Capture used barcode inventory materials BEFORE clearing drawer
        if hasattr(self, "_costing_drawer") and self._costing_drawer:
            used_mats = self._costing_drawer.get_selected_inventory_materials()
            if used_mats:
                self._committed_inventory_materials[target_row] = used_mats

        # Erase everything in costing sheet once applied so it is fresh for the next item
        if hasattr(self, "_costing_drawer"):
            self._costing_drawer.clear()
            if hasattr(self._costing_drawer, "apply_btn"):
                self._costing_drawer.apply_btn.setText(f"Applied to Line {target_row + 1}!")
                QTimer.singleShot(2000, lambda: self._costing_drawer.apply_btn.setText("Apply Sell Rate to Bill"))

    def _apply_costing_rate_to_bill(self, row_idx: int, price: float) -> None:
        """Apply button clicked from costing drawer."""
        if self._table.rowCount() == 0:
            self.add_row(focus_desc=False)
        target_row = row_idx if 0 <= row_idx < self._table.rowCount() else 0
        rate_w = self._table.cellWidget(target_row, 4)
        if isinstance(rate_w, QDoubleSpinBox):
            rate_w.setValue(price)
        self._sync_totals()

    def _collect_lines(self) -> list[dict[str, Any]]:
        """Collect non-empty line items, ignoring empty trailing buffer rows."""
        lines: list[dict[str, Any]] = []
        for r in range(self._table.rowCount()):
            desc_w = self._table.cellWidget(r, 1)
            qty_w = self._table.cellWidget(r, 2)
            cost_w = self._table.cellWidget(r, 3)
            rate_w = self._table.cellWidget(r, 4)

            desc = capitalize_words(desc_w.text().strip()) if isinstance(desc_w, QLineEdit) else ""
            qty = qty_w.value() if isinstance(qty_w, QDoubleSpinBox) else 0.0
            cost_price = cost_w.value() if isinstance(cost_w, QDoubleSpinBox) else 0.0
            rate = rate_w.value() if isinstance(rate_w, QDoubleSpinBox) else 0.0

            # Only accept lines that have either a description or positive quantity
            if desc or qty > 0:
                lines.append({
                    "row_index": r + 1,
                    "description": desc,
                    "quantity": qty,
                    "cost_price": cost_price,
                    "rate": rate,
                })
        return lines

    def _build_doc_data(self) -> dict[str, Any]:
        party_name = self._selected_party.name if self._selected_party else ""
        return {
            "party_id": self._selected_party.id if self._selected_party else None,
            "party_name": capitalize_words(party_name),
            "bill_date": self._date_edit.date().toString("yyyy-MM-dd"),
            "po_number": capitalize_words(self._po_edit.text().strip()),
            "job_number": capitalize_words(self._job_num_edit.text().strip()),
            "customer_po": capitalize_words(self._cust_po_edit.text().strip()),
            "bill_number": self._bill_num_edit.text().strip(),
            "gate_pass_number": self._dc_num_edit.text().strip(),
            "items": self._collect_lines(),
        }

    # -- actions: Preview & Save -------------------------------------------

    def _open_preview(self) -> None:
        data = self._build_doc_data()
        if not data["items"]:
            QMessageBox.warning(self, "No Items", "Please enter at least one line item before opening the preview.")
            return

        for item in data["items"]:
            if not item["description"]:
                QMessageBox.warning(self, "Missing Description", f"Line {item['row_index']} requires a description.")
                return
            if item["quantity"] <= 0:
                QMessageBox.warning(self, "Invalid Quantity", f"Line {item['row_index']} requires a quantity greater than zero.")
                return

        dlg = A4PrintPreviewDialog(data, parent=self.window())
        dlg.exec()

    def _save_job(self) -> None:
        if self._selected_party is None:
            QMessageBox.warning(self, "Select Client", "Please select a client / party first.")
            return

        data = self._build_doc_data()
        lines = data["items"]
        if not lines:
            QMessageBox.warning(self, "No Items", "Please enter at least one line item with description, quantity, and rate.")
            return

        # Validate that each entered line has a description and positive values
        for item in lines:
            if not item["description"]:
                QMessageBox.warning(self, "Missing Description", f"Line {item['row_index']} requires a description.")
                return
            if item["quantity"] <= 0:
                QMessageBox.warning(self, "Invalid Quantity", f"Line {item['row_index']} requires a quantity greater than zero.")
                return

        total_bill_amount = sum(item["quantity"] * item["rate"] for item in lines)
        total_line_cost = sum(item["quantity"] * item.get("cost_price", 0.0) for item in lines)
        prod_cost = total_line_cost if total_line_cost > 0 else (self._costing_drawer.get_total_cost() if hasattr(self, "_costing_drawer") else 0.0)
        net_profit = sum(item["quantity"] * (item["rate"] - item.get("cost_price", 0.0)) for item in lines) if total_line_cost > 0 else (total_bill_amount - prod_cost if prod_cost > 0 else 0.0)

        try:
            bill_id = create_bill(
                self._connection,
                party_id=self._selected_party.id,
                po_number=data["po_number"],
                job_number=data["job_number"],
                customer_po=data["customer_po"],
                bill_number=data["bill_number"],
                gate_pass_number=data["gate_pass_number"],
                bill_date=data["bill_date"],
                lines=[(item["description"], item["quantity"], item["rate"], item.get("cost_price", 0.0)) for item in lines],
                production_cost=prod_cost,
                profit=net_profit,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error Saving Invoice", str(exc))
            return

        # Deduct barcode inventory stock for any materials used in costing or in bill lines
        try:
            from app.db.barcode_inventory import deduct_barcode_inventory_stock, list_barcode_inventory

            deductions_by_id: dict[int, float] = {}

            # 1. From committed materials via costing drawer 'Apply'
            for mat_list in self._committed_inventory_materials.values():
                for item_id, qty in mat_list:
                    deductions_by_id[item_id] = deductions_by_id.get(item_id, 0.0) + float(qty)

            # 2. If no committed drawer materials, check currently active costing drawer
            if not deductions_by_id and hasattr(self, "_costing_drawer") and self._costing_drawer:
                for item_id, qty in self._costing_drawer.get_selected_inventory_materials():
                    deductions_by_id[item_id] = deductions_by_id.get(item_id, 0.0) + float(qty)

            # 3. For any bill line description matching an inventory item (case-insensitive)
            all_inv_items = list_barcode_inventory(self._connection)
            inv_by_desc = {item.detail.strip().lower(): item for item in all_inv_items}
            for line_item in lines:
                desc_clean = line_item["description"].strip().lower()
                if desc_clean in inv_by_desc:
                    inv_obj = inv_by_desc[desc_clean]
                    # If this item was not already accounted for by costing drawer, deduct the bill line quantity
                    if inv_obj.id not in deductions_by_id:
                        deductions_by_id[inv_obj.id] = float(line_item["quantity"])

            # Execute stock deduction
            for item_id, used_qty in deductions_by_id.items():
                if used_qty > 0:
                    try:
                        deduct_barcode_inventory_stock(self._connection, item_id, used_qty)
                    except Exception as err:
                        print(f"Warning: could not deduct inventory item {item_id}: {err}")

            self._committed_inventory_materials.clear()
            if hasattr(self, "_costing_drawer") and self._costing_drawer:
                self._costing_drawer.clear_inventory_materials()
        except Exception as inv_err:
            print(f"Warning: barcode inventory deduction encountered error: {inv_err}")

        # Automatically export PDF to the designated PDF export folder
        pdf_path_obj = None
        try:
            pdf_path_obj = get_or_create_bill_pdf(self._connection, bill_id)
        except Exception as pdf_err:
            print(f"Warning: could not export PDF on save: {pdf_err}")

        profit_note = f"Net Profit: Rs. {net_profit:,.2f}\n" if net_profit > 0 else ""
        pdf_note = f"PDF Saved: {pdf_path_obj.name}\n" if pdf_path_obj else ""

        # Success message with option to print
        answer = QMessageBox.information(
            self,
            "Invoice & Gate Pass Generated",
            f"Invoice #{data['bill_number']} and Gate Pass #{data['gate_pass_number']} have been generated and saved successfully.\n\n"
            f"Client: {data['party_name']}\n"
            f"Job #: {data['job_number'] or 'None'}\n"
            f"P.O. #: {data['po_number'] or 'None'}\n"
            f"Customer P.O. #: {data['customer_po'] or 'None'}\n"
            f"{profit_note}"
            f"{pdf_note}\n"
            "Would you like to open the A4 Print Preview now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if answer == QMessageBox.StandardButton.Yes:
            dlg = A4PrintPreviewDialog(data, parent=self.window())
            dlg.exec()

        self.bill_saved.emit(bill_id)
        self.reset_form()

    def reset_form(self) -> None:
        """Reset the form to ready state."""
        self._po_edit.clear()
        self._job_num_edit.clear()
        self._cust_po_edit.clear()
        self.clear_table()
        if hasattr(self, "_costing_drawer"):
            self._costing_drawer.clear()
        self._committed_inventory_materials.clear()
        self.load_parties()
        self._party_combo.setCurrentIndex(0)
        self._bill_container.setVisible(False)
        self._placeholder_guide.setVisible(True)
        self._selected_party = None

    def reset_to_list(self) -> None:
        """Called by MainWindow when switching to this tab."""
        self.load_parties()
