"""Smart Collapsible Costing Drawer for New Job / Billing Terminal.

Features:
- Starts CLOSED (Collapsed) by default to keep the UI clean and clutter-free.
- Automatically pushes calculated Cost / Unit into the active Bill line's Cost Price!
- Displays which item is currently being costed (Description, Quantity, Sell Rate).
- Generous side spacing and modern minimal card aesthetic.
- Auto-syncs quantity from the targeted Bill row.
- Live Net Profit & Margin calculations that save directly with the bill and ledger.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.costing.calculator import CollapsibleSection, PriceInputGroup, _fmt
from app.ui.theme import CHEVRON_DOWN_SVG


class JobCostingDrawer(QFrame):
    """Smart Collapsible Costing & Profit Drawer for New Job workspace."""

    #: Emitted whenever Cost / Unit is calculated, passing (row_index, unit_cost).
    cost_unit_calculated = Signal(int, float)
    #: Emitted whenever Sell Price is entered/changed, passing (row_index, sell_price).
    sell_price_calculated = Signal(int, float)
    #: Emitted when user clicks "Apply Rate to Bill", passing (row_index, sell_price, unit_cost, quantity).
    costing_applied = Signal(int, float, float, float)
    #: Emitted when user clicks "Apply Rate to Bill", passing (row_index, sell_price).
    rate_applied = Signal(int, float)
    #: Emitted whenever costs change.
    values_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.is_expanded = False
        self._target_row = 0
        self._is_syncing = False
        self._sections: dict[str, CollapsibleSection] = {}

        self.setObjectName("ProfileCard")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(20, 16, 20, 16)
        outer_layout.setSpacing(12)

        # 1. Clickable Drawer Header Bar ----------------------------------------
        self.header_btn = QFrame()
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setObjectName("DrawerHeaderFrame")
        self.header_btn.setStyleSheet("""
            QFrame#DrawerHeaderFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 14px;
            }
            QFrame#DrawerHeaderFrame:hover {
                background-color: #F1F5F9;
                border-color: #CBD5E1;
            }
        """)

        h_layout = QHBoxLayout(self.header_btn)
        h_layout.setContentsMargins(6, 4, 6, 4)
        h_layout.setSpacing(12)

        # Title & Subtitle
        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        lbl_title = QLabel("4. PRODUCTION COSTING & PROFIT ESTIMATOR (OPTIONAL)")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #1E293B; letter-spacing: 0.5px;")
        self.lbl_sub = QLabel("Calculate exact cost price per unit — automatically updates the bill row above")
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        t_box.addWidget(lbl_title)
        t_box.addWidget(self.lbl_sub)
        h_layout.addLayout(t_box, 1)

        # Live Header Profit Pill
        self.header_pill = QLabel("Estimated Profit: Rs. 0.00 (0.0%)")
        self.header_pill.setStyleSheet("""
            background-color: #FFFFFF;
            color: #64748B;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 700;
        """)
        h_layout.addWidget(self.header_pill)

        # Toggle Button Indicator
        self.toggle_btn = QLabel("▼ Open Costing")
        self.toggle_btn.setStyleSheet("""
            QLabel {
                color: #2563EB;
                background-color: #EFF6FF;
                border: 1px solid #DBEAFE;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel:hover {
                background-color: #DBEAFE;
            }
        """)
        h_layout.addWidget(self.toggle_btn)

        outer_layout.addWidget(self.header_btn)

        # 2. Drawer Body Container (Starts HIDDEN / COLLAPSED) -------------------
        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(6, 4, 6, 8)
        body_layout.setSpacing(14)

        # Active Item Target Strip
        target_strip = QFrame()
        target_strip.setObjectName("TargetStrip")
        target_strip.setStyleSheet("""
            QFrame#TargetStrip {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        ts_layout = QVBoxLayout(target_strip)
        ts_layout.setContentsMargins(14, 10, 14, 10)
        ts_layout.setSpacing(8)

        ts_row1 = QHBoxLayout()
        ts_row1.setSpacing(10)

        lbl_target_hint = QLabel("Costing Target:")
        lbl_target_hint.setStyleSheet("font-size: 12px; font-weight: 700; color: #475569; border: none; background: transparent;")
        ts_row1.addWidget(lbl_target_hint)

        self.item_combo = QComboBox()
        self.item_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.item_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.item_combo.setMinimumContentsLength(8)
        self.item_combo.view().setTextElideMode(Qt.TextElideMode.ElideRight)
        self.item_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 30px 6px 12px;
                font-size: 12px;
                font-weight: 700;
                color: #0F172A;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #3B82F6;
                background-color: #F8FAFC;
            }
            QComboBox:focus {
                border: 1.5px solid #2563EB;
                background-color: #FFFFFF;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #E2E8F0;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: #F8FAFC;
            }
            QComboBox::drop-down:hover {
                background-color: #EFF6FF;
            }
            QComboBox::down-arrow {
                image: url(""" + CHEVRON_DOWN_SVG + """);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                selection-background-color: #EFF6FF;
                selection-color: #1E40AF;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F1F5F9;
            }
        """)
        self.item_combo.currentIndexChanged.connect(self._on_combo_index_changed)
        ts_row1.addWidget(self.item_combo, 1)

        self.apply_btn = QPushButton("Apply Sell Rate to Bill")
        self.apply_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11.5px;
                font-weight: 700;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
        """)
        self.apply_btn.clicked.connect(self._on_apply_rate_clicked)
        ts_row1.addWidget(self.apply_btn)

        self.reset_btn = QPushButton("Reset Inputs")
        self.reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #64748B;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11.5px;
                font-weight: 600;
                min-height: 20px;
            }
            QPushButton:hover {
                color: #DC2626;
                border-color: #FCA5A5;
                background-color: #FEF2F2;
            }
        """)
        self.reset_btn.clicked.connect(self.clear)
        ts_row1.addWidget(self.reset_btn)

        ts_layout.addLayout(ts_row1)

        self.lbl_auto_note = QLabel("Calculated Cost/Unit will automatically write into the Bill's Cost Price column.")
        self.lbl_auto_note.setStyleSheet("font-size: 11px; color: #047857; font-weight: 600; border: none; background: transparent;")
        self.lbl_auto_note.setWordWrap(True)
        ts_layout.addWidget(self.lbl_auto_note)

        body_layout.addWidget(target_strip)

        # 3. Parameters & KPI Card ---------------------------------------------
        kpi_card = QFrame()
        kpi_card.setObjectName("KpiCard")
        kpi_card.setStyleSheet("""
            QFrame#KpiCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        kpi_layout = QVBoxLayout(kpi_card)
        kpi_layout.setContentsMargins(16, 14, 16, 14)
        kpi_layout.setSpacing(12)

        # Row 1: The 4 Steps
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        # 1. Total Cost
        b_cost = QVBoxLayout()
        b_cost.setSpacing(3)
        lbl_c1 = QLabel("1. PRODUCTION COST (SUM)")
        lbl_c1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_c1.setStyleSheet("border: none; background: transparent; color: #64748B; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;")
        self.val_total_cost = QLabel("Rs. 0.00")
        self.val_total_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_total_cost.setStyleSheet("border: none; background: transparent; color: #0F172A; font-size: 18px; font-weight: 800;")
        b_cost.addWidget(lbl_c1)
        b_cost.addWidget(self.val_total_cost)
        row1.addLayout(b_cost, 3)

        # 2. Quantity (Auto synced with active bill row)
        b_qty = QVBoxLayout()
        b_qty.setSpacing(3)
        lbl_q = QLabel("2. ITEM QTY (PCS)")
        lbl_q.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_q.setStyleSheet("border: none; background: transparent; color: #64748B; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;")
        self.qty_edit = QLineEdit("1000")
        self.qty_edit.setValidator(QIntValidator(1, 10000000, self))
        self.qty_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 13px;
                font-weight: 700;
                color: #0F172A;
            }
            QLineEdit:focus { border: 1.5px solid #2563EB; }
        """)
        self.qty_edit.setFixedHeight(30)
        self.qty_edit.textChanged.connect(self._recalculate)
        b_qty.addWidget(lbl_q)
        b_qty.addWidget(self.qty_edit)
        row1.addLayout(b_qty, 2)

        # 3. Unit Cost (Auto written into Bill Cost Price)
        b_unit = QVBoxLayout()
        b_unit.setSpacing(3)
        lbl_u = QLabel("3. COST / UNIT (AUTO-SYNC)")
        lbl_u.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_u.setStyleSheet("border: none; background: transparent; color: #047857; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;")
        self.val_unit_cost = QLabel("Rs. 0.00")
        self.val_unit_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_unit_cost.setStyleSheet("border: none; background: transparent; color: #047857; font-size: 18px; font-weight: 800;")
        b_unit.addWidget(lbl_u)
        b_unit.addWidget(self.val_unit_cost)
        row1.addLayout(b_unit, 3)

        # 4. Sell Price / Unit
        b_sell = QVBoxLayout()
        b_sell.setSpacing(3)
        lbl_s = QLabel("4. SELL RATE / UNIT")
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_s.setStyleSheet("border: none; background: transparent; color: #2563EB; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;")

        sell_wrap = QHBoxLayout()
        sell_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sell_price_input = PriceInputGroup(placeholder="0.00", width=160, height=32)
        self.sell_price_input.valueChanged.connect(self._recalculate)
        sell_wrap.addWidget(self.sell_price_input)

        b_sell.addWidget(lbl_s)
        b_sell.addLayout(sell_wrap)
        row1.addLayout(b_sell, 3)

        kpi_layout.addLayout(row1)

        # Thin divider line
        div = QFrame()
        div.setStyleSheet("background-color: #F1F5F9; border: none; max-height: 1px;")
        div.setFixedHeight(1)
        kpi_layout.addWidget(div)

        # Row 2: Live Profit Outcomes (Clean & borderless)
        row2 = QHBoxLayout()
        row2.setContentsMargins(10, 4, 10, 2)
        row2.setSpacing(16)

        def make_stat(title: str, default: str, color: str = "#0F172A"):
            box = QVBoxLayout()
            box.setSpacing(2)
            t = QLabel(title)
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setStyleSheet("border: none; background: transparent; font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
            v = QLabel(default)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet(f"border: none; background: transparent; font-size: 16px; font-weight: 800; color: {color};")
            box.addWidget(t)
            box.addWidget(v)
            return box, v

        s1, self.val_unit_profit = make_stat("PROFIT / PIECE", "Rs. 0.00", "#059669")
        s2, self.val_total_profit = make_stat("NET PROFIT (THIS ITEM)", "Rs. 0.00", "#047857")
        s3, self.val_margin = make_stat("PROFIT MARGIN", "0.0%", "#059669")

        row2.addLayout(s1, 3)
        row2.addLayout(s2, 4)
        row2.addLayout(s3, 3)

        kpi_layout.addLayout(row2)
        body_layout.addWidget(kpi_card)

        # 4. Collapsible Process Sections (All start CLOSED) --------------------
        sec_general = CollapsibleSection(
            key="general",
            title="General Printing & Finishing",
            subtitle="Design, plates, paper card, printing, lamination, and sampling",
            row_names=(
                "Design",
                "Plates",
                "Card (Paper)",
                "Printing",
                "Lamination",
                "Pasting",
                "Block",
                "Cutting",
                "Banding",
                "Dai Make",
                "Dai Cut",
                "Others",
            ),
            include_sampling_sub=True,
        )
        sec_general.cost_changed.connect(self._recalculate)
        self._sections["general"] = sec_general
        body_layout.addWidget(sec_general)

        sec_barcode = CollapsibleSection(
            key="barcode",
            title="Barcode Stickers & Labels",
            subtitle="Stock materials from Barcode Inventory + Electricity & Labour",
            row_names=("Electricity + Labour", "Others"),
            include_sampling_sub=False,
            include_inventory_picker=True,
        )
        sec_barcode.cost_changed.connect(self._recalculate)
        self._sections["barcode"] = sec_barcode
        body_layout.addWidget(sec_barcode)

        sec_sampling = CollapsibleSection(
            key="sampling",
            title="Sampling & Prototyping (Dedicated)",
            subtitle="Pre-production mockups, test cards, trial printing, and proofing",
            row_names=(
                "Sample Design",
                "Sample Card",
                "Sample Printing",
                "Sample Die / Block",
                "Sample Proofing / Testing",
                "Sample Others",
            ),
            include_sampling_sub=False,
        )
        sec_sampling.cost_changed.connect(self._recalculate)
        self._sections["sampling"] = sec_sampling
        body_layout.addWidget(sec_sampling)

        self.body.setVisible(False)
        outer_layout.addWidget(self.body)

        self.header_btn.mousePressEvent = self._toggle_drawer

    def _toggle_drawer(self, event) -> None:
        self.is_expanded = not self.is_expanded
        self.body.setVisible(self.is_expanded)
        self.toggle_btn.setText("▲ Close Costing" if self.is_expanded else "▼ Open Costing")
        self.header_btn.setStyleSheet(f"""
            QFrame#DrawerHeaderFrame {{
                background-color: {"#F1F5F9" if self.is_expanded else "#F8FAFC"};
                border: 1px solid {"#CBD5E1" if self.is_expanded else "#E2E8F0"};
                border-radius: 8px;
                padding: 10px 14px;
            }}
            QFrame#DrawerHeaderFrame:hover {{
                background-color: #F1F5F9;
            }}
        """)

    def _on_apply_rate_clicked(self) -> None:
        qty = self.get_quantity()
        total_cost = self.get_total_cost()
        unit_cost = (total_cost / qty) if qty > 0 else 0.0
        sell_price = self.get_sell_price()

        self.costing_applied.emit(self._target_row, sell_price, unit_cost, qty)
        if sell_price > 0:
            self.rate_applied.emit(self._target_row, sell_price)

    def _on_combo_index_changed(self, index: int) -> None:
        row_idx = self.item_combo.currentData()
        if row_idx is not None and not self._is_syncing:
            self._target_row = int(row_idx)

    def update_item_list(self, items: list[dict]) -> None:
        """Refresh the combo box list of bill items."""
        self._is_syncing = True
        self.item_combo.blockSignals(True)
        self.item_combo.clear()

        for idx, it in enumerate(items):
            desc = it.get("description", "").strip() or f"Line {idx + 1}"
            qty = it.get("quantity", 0.0)
            self.item_combo.addItem(f"Line {idx + 1}: {desc} ({qty:g} pcs)", idx)

        # Restore target row if valid
        if 0 <= self._target_row < len(items):
            self.item_combo.setCurrentIndex(self._target_row)
        elif items:
            self._target_row = 0
            self.item_combo.setCurrentIndex(0)

        self.item_combo.blockSignals(False)
        self._is_syncing = False

    def sync_from_row(self, row_idx: int, desc: str, qty: float, sell_rate: float, cost_price: float = 0.0) -> None:
        """Sync when user selects or edits a specific row in the bill table."""
        self._target_row = row_idx
        if 0 <= row_idx < self.item_combo.count():
            self.item_combo.blockSignals(True)
            self.item_combo.setCurrentIndex(row_idx)
            self.item_combo.blockSignals(False)

        if qty > 0 and self.qty_edit.text() != str(int(qty)):
            self.qty_edit.blockSignals(True)
            self.qty_edit.setText(str(int(qty)))
            self.qty_edit.blockSignals(False)

        if sell_rate > 0 and self.get_sell_price() == 0.0:
            self.sell_price_input.setText(f"{sell_rate:.2f}")

        self._recalculate()

    def get_quantity(self) -> float:
        try:
            return max(1.0, float(self.qty_edit.text().strip() or 1.0))
        except ValueError:
            return 1.0

    def get_selected_inventory_materials(self) -> list[tuple[int, float]]:
        """Returns list of (item_id, qty) for all barcode materials chosen in drawer."""
        sec = self._sections.get("barcode")
        if sec and hasattr(sec, "barcode_inventory_picker") and sec.barcode_inventory_picker:
            return sec.barcode_inventory_picker.get_selected_materials()
        return []

    def clear_inventory_materials(self) -> None:
        """Clear materials after successful save."""
        sec = self._sections.get("barcode")
        if sec and hasattr(sec, "barcode_inventory_picker") and sec.barcode_inventory_picker:
            sec.barcode_inventory_picker.clear()

    def get_total_cost(self) -> float:
        return sum(sec.update_subtotal() for sec in self._sections.values())

    def get_sell_price(self) -> float:
        return self.sell_price_input.get_value()

    def get_total_profit(self) -> float:
        cost = self.get_total_cost()
        sell_price = self.get_sell_price()
        qty = self.get_quantity()
        if sell_price > 0:
            return (sell_price * qty) - cost
        return 0.0

    def _recalculate(self) -> None:
        total_cost = self.get_total_cost()
        qty = self.get_quantity()
        unit_cost = (total_cost / qty) if qty > 0 else 0.0
        sell_price = self.get_sell_price()

        self.val_total_cost.setText(f"Rs. {_fmt(total_cost)}")
        self.val_unit_cost.setText(f"Rs. {_fmt(unit_cost)}")

        # Automatically push Cost / Unit to active Bill row!
        if unit_cost > 0 and not self._is_syncing:
            self.cost_unit_calculated.emit(self._target_row, unit_cost)

        if sell_price > 0:
            unit_profit = sell_price - unit_cost
            total_profit = unit_profit * qty
            total_sale = sell_price * qty
            margin = (total_profit / total_sale * 100.0) if total_sale > 0 else 0.0

            if total_profit >= 0:
                color = "#047857"
                sign = "+"
            else:
                color = "#DC2626"
                sign = ""

            self.val_unit_profit.setText(f"{sign}Rs. {_fmt(unit_profit)}")
            self.val_unit_profit.setStyleSheet(f"border: none; background: transparent; font-size: 16px; font-weight: 800; color: {color};")

            self.val_total_profit.setText(f"{sign}Rs. {_fmt(total_profit)}")
            self.val_total_profit.setStyleSheet(f"border: none; background: transparent; font-size: 18px; font-weight: 800; color: {color};")

            self.val_margin.setText(f"{margin:+.1f}%")
            self.val_margin.setStyleSheet(f"border: none; background: transparent; font-size: 16px; font-weight: 800; color: {color};")

            self.header_pill.setText(f"Profit: {sign}Rs. {_fmt(total_profit)} ({margin:+.1f}%)")
            self.header_pill.setStyleSheet(f"""
                background-color: {"#ECFDF5" if total_profit >= 0 else "#FEF2F2"};
                color: {color};
                border: 1px solid {"#A7F3D0" if total_profit >= 0 else "#FCA5A5"};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
            """)
        else:
            self.val_unit_profit.setText("Rs. 0.00")
            self.val_unit_profit.setStyleSheet("border: none; background: transparent; font-size: 16px; font-weight: 800; color: #64748B;")
            self.val_total_profit.setText("Rs. 0.00")
            self.val_total_profit.setStyleSheet("border: none; background: transparent; font-size: 18px; font-weight: 800; color: #64748B;")
            self.val_margin.setText("0.0%")
            self.val_margin.setStyleSheet("border: none; background: transparent; font-size: 16px; font-weight: 800; color: #64748B;")

            self.header_pill.setText("Estimated Profit: Rs. 0.00 (0.0%)")
            self.header_pill.setStyleSheet("""
                background-color: #FFFFFF;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
            """)

        self.values_changed.emit()

    def clear(self) -> None:
        """Reset costing inputs to clean state."""
        for sec in self._sections.values():
            sec.clear()
        self.sell_price_input.clear()
        self._recalculate()
