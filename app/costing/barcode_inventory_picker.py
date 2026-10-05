"""Embedded Barcode Inventory Material Picker for Barcode Costing Sheets.

Allows picking raw materials (rolls, ribbons, labels) from the Barcode Inventory,
specifying the quantity needed for the job, and automatically calculating the cost.
Used exclusively in Barcode Costing. Designed with compact responsive layout.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.barcode_inventory import BarcodeInventoryItem, list_barcode_inventory
from app.db.connection import create_connection
from app.inventory.dialog import CleanNumericSpinBox
from app.ui.theme import CHEVRON_DOWN_SVG


COMBO_CSS = """
QComboBox {
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 28px 5px 10px;
    font-size: 11px;
    font-weight: 600;
    color: #0F172A;
    min-height: 18px;
}
QComboBox:hover {
    border-color: #3B82F6;
    background-color: #F8FAFC;
}
QComboBox:focus, QComboBox:on {
    border: 1.5px solid #2563EB;
    background-color: #FFFFFF;
}
QComboBox QLineEdit {
    border: none;
    background: transparent;
    font-size: 11px;
    font-weight: 600;
    color: #0F172A;
    padding: 0;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
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
    min-height: 26px;
    padding: 3px 8px;
    border-radius: 4px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #F1F5F9;
}
"""


class BarcodeMaterialRow:
    """Represents one material item added to the barcode costing sheet."""

    def __init__(
        self,
        item_id: int,
        detail: str,
        qty: float,
        rate: float,
        on_change_callback,
        on_remove_callback,
    ) -> None:
        self.item_id = item_id
        self.detail = detail
        self._on_change = on_change_callback
        self._on_remove = on_remove_callback

        # Qty spinbox (compact)
        self.qty_spin = CleanNumericSpinBox(decimals=0)
        self.qty_spin.setRange(0.01, 1000000.0)
        self.qty_spin.setValue(qty)
        self.qty_spin.setFixedWidth(56)
        self.qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_spin.setStyleSheet("font-size: 11px; font-weight: 700; padding: 2px;")
        self.qty_spin.valueChanged.connect(self._recalc)

        # Rate spinbox (compact)
        self.rate_spin = CleanNumericSpinBox(decimals=2)
        self.rate_spin.setRange(0.0, 1000000.0)
        self.rate_spin.setValue(rate)
        self.rate_spin.setFixedWidth(78)
        self.rate_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rate_spin.setStyleSheet("font-size: 11px; font-weight: 700; padding: 2px;")
        self.rate_spin.valueChanged.connect(self._recalc)

        # Cost label
        self.cost_lbl = QLabel(f"Rs. {self.get_cost():,.2f}")
        self.cost_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cost_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #047857;")

        # Delete button
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(24, 24)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #FECACA;
                border-radius: 4px;
                color: #DC2626;
                font-size: 11px;
                font-weight: 700;
                background-color: #FEF2F2;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                border-color: #FCA5A5;
            }
        """)
        self.del_btn.clicked.connect(lambda: self._on_remove(self))

    def _recalc(self) -> None:
        cost = self.get_cost()
        self.cost_lbl.setText(f"Rs. {cost:,.2f}")
        self._on_change(self.qty_spin.value())

    def get_cost(self) -> float:
        return round(self.qty_spin.value() * self.rate_spin.value(), 2)


class SearchableProductSelect(QFrame):
    """Modern Select2-style dropdown with a search box built directly inside the dropdown popup."""

    item_selected = Signal(object)  # Emits BarcodeInventoryItem | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[BarcodeInventoryItem] = []
        self._current_item: BarcodeInventoryItem | None = None

        self.setObjectName("SearchableDropdownTrigger")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#SearchableDropdownTrigger {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 0px 8px;
            }
            QFrame#SearchableDropdownTrigger:hover {
                border-color: #3B82F6;
                background-color: #F8FAFC;
            }
        """)

        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(6, 2, 6, 2)
        h_layout.setSpacing(6)

        self._lbl_text = QLabel("Select material from inventory...")
        self._lbl_text.setStyleSheet("font-size: 11px; font-weight: 600; color: #0F172A; border: none; background: transparent;")
        h_layout.addWidget(self._lbl_text, 1)

        self._lbl_arrow = QLabel("▼")
        self._lbl_arrow.setStyleSheet("font-size: 10px; color: #64748B; border: none; background: transparent;")
        h_layout.addWidget(self._lbl_arrow)

        # Popup Window
        self._popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._popup.setObjectName("SearchableDropdownPopup")
        self._popup.setStyleSheet("""
            QFrame#SearchableDropdownPopup {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
            }
        """)

        p_layout = QVBoxLayout(self._popup)
        p_layout.setContentsMargins(8, 8, 8, 8)
        p_layout.setSpacing(6)

        # Search box directly inside the popup!
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Search products (e.g. 50x25, wax, ribbon)...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11.5px;
                color: #0F172A;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 1.5px solid #2563EB;
            }
        """)
        self._search_input.setFixedHeight(30)
        self._search_input.textChanged.connect(self._filter_items)
        self._search_input.returnPressed.connect(self._select_top_item)
        p_layout.addWidget(self._search_input)

        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #E2E8F0;
                background-color: #FFFFFF;
                border-radius: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #F1F5F9;
            }
            QListWidget::item:hover {
                background-color: #EFF6FF;
            }
            QListWidget::item:selected {
                background-color: #DBEAFE;
                color: #1E40AF;
            }
        """)
        self._list_widget.itemClicked.connect(self._on_list_item_clicked)
        p_layout.addWidget(self._list_widget)

    def mousePressEvent(self, event) -> None:
        self.show_popup()
        super().mousePressEvent(event)

    def show_popup(self) -> None:
        if not self._items:
            return
        pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        self._popup.setFixedWidth(max(self.width(), 380))
        self._popup.setFixedHeight(260)
        self._popup.move(pos)
        self._popup.show()
        self._search_input.clear()
        self._filter_items("")
        self._search_input.setFocus()

    def set_items(self, items: list[BarcodeInventoryItem], preserve_id: int | None = None) -> None:
        self._items = items
        target_item = None
        if preserve_id is not None:
            target_item = next((it for it in items if it.id == preserve_id), None)
        if target_item is None and items:
            target_item = items[0]
        self.set_current_item(target_item)

    def set_current_item(self, item: BarcodeInventoryItem | None) -> None:
        self._current_item = item
        if item is not None:
            self._lbl_text.setText(f"{item.detail}  ·  Rs. {item.rate:,.2f}  ·  Stock: {item.quantity:,.0f}")
            self.setToolTip(f"In Stock: {item.quantity:,.0f} units | Unit Rate: Rs. {item.rate:,.2f}")
        else:
            self._lbl_text.setText("No items in Barcode Inventory (Go to Inventory in sidebar)")
            self.setToolTip("")

    def current_item(self) -> BarcodeInventoryItem | None:
        return self._current_item

    def count(self) -> int:
        return len(self._items)

    def currentText(self) -> str:
        return self._lbl_text.text()

    def currentIndex(self) -> int:
        if self._current_item is not None:
            for i, it in enumerate(self._items):
                if it.id == self._current_item.id:
                    return i
        return -1

    def itemText(self, index: int) -> str:
        if 0 <= index < len(self._items):
            it = self._items[index]
            return f"{it.detail}  ·  Rs. {it.rate:,.2f}  ·  Stock: {it.quantity:,.0f}"
        return ""

    def itemData(self, index: int) -> BarcodeInventoryItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._items):
            self.set_current_item(self._items[index])
            self.item_selected.emit(self._items[index])

    def _filter_items(self, text: str) -> None:
        self._list_widget.clear()
        q = text.strip().lower()
        matched = 0
        for it in self._items:
            if not q or q in it.detail.lower():
                w_item = QListWidgetItem()
                w_item.setData(Qt.ItemDataRole.UserRole, it)
                w_item.setText(f"{it.detail}\n  ↳ Rate: Rs. {it.rate:,.2f}   |   Stock: {it.quantity:,.0f} units")
                self._list_widget.addItem(w_item)
                matched += 1

        if matched == 0:
            empty_item = QListWidgetItem(f"No products found matching '{text.strip()}'")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            empty_item.setForeground(Qt.GlobalColor.gray)
            self._list_widget.addItem(empty_item)
        elif self._list_widget.count() > 0:
            self._list_widget.setCurrentRow(0)

    def _select_top_item(self) -> None:
        if self._list_widget.count() > 0:
            item = self._list_widget.currentItem() or self._list_widget.item(0)
            if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
                self._on_list_item_clicked(item)

    def _on_list_item_clicked(self, list_item: QListWidgetItem) -> None:
        data = list_item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, BarcodeInventoryItem):
            self.set_current_item(data)
            self._popup.hide()
            self.item_selected.emit(data)


class BarcodeInventoryCostingWidget(QFrame):
    """Component embedded inside Barcode Stickers & Labels costing section.

    Loads items from barcode inventory and allows calculating exact material costs.
    Designed with responsive two-tier layout so it never causes horizontal overflow.
    """

    cost_changed = Signal()
    qty_changed = Signal(float)
    item_selected = Signal(str)

    def __init__(self, connection: sqlite3.Connection | None = None, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection or create_connection()
        self._rows: list[BarcodeMaterialRow] = []
        self._inventory_items: list[BarcodeInventoryItem] = []

        self.setObjectName("BarcodeInventorySection")
        self.setStyleSheet("""
            QFrame#BarcodeInventorySection {
                background-color: #F8FAFC;
                border: 1.5px dashed #CBD5E1;
                border-radius: 8px;
                margin: 4px 6px 8px 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. Section Header Row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        lbl_badge = QLabel("📦 INVENTORY RAW MATERIALS (ROLLS & RIBBONS)")
        lbl_badge.setStyleSheet("font-size: 10px; font-weight: 800; color: #1E40AF; letter-spacing: 0.5px; border: none; background: transparent;")
        header_row.addWidget(lbl_badge)

        self.lbl_mat_total = QLabel("Material Cost: Rs. 0.00")
        self.lbl_mat_total.setStyleSheet("""
            background-color: #EFF6FF;
            color: #1E40AF;
            border: 1px solid #DBEAFE;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        header_row.addStretch(1)
        header_row.addWidget(self.lbl_mat_total)

        layout.addLayout(header_row)

        # 2. Responsive 2-Tier Selector Controls
        # Row A: Unified Material Dropdown (Click to open list with internal search box)
        row_a = QHBoxLayout()
        row_a.setSpacing(8)

        lbl_item = QLabel("🔍 Material:")
        lbl_item.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; border: none; background: transparent;")
        row_a.addWidget(lbl_item)

        self._combo = SearchableProductSelect(self)
        self._combo.item_selected.connect(self._on_material_selected)
        row_a.addWidget(self._combo, 1)

        layout.addLayout(row_a)

        # Row B: Qty + Rate + Add Button
        row_b = QHBoxLayout()
        row_b.setSpacing(8)

        lbl_q = QLabel("Qty:")
        lbl_q.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569; border: none; background: transparent;")
        row_b.addWidget(lbl_q)

        self._input_qty = CleanNumericSpinBox(decimals=0)
        self._input_qty.setRange(1.0, 1000000.0)
        self._input_qty.setValue(1.0)
        self._input_qty.setFixedWidth(65)
        self._input_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._input_qty.setStyleSheet("font-size: 11px; font-weight: 700; padding: 3px;")
        self._input_qty.valueChanged.connect(self._on_input_qty_changed)
        row_b.addWidget(self._input_qty)

        lbl_r = QLabel("Rate (Rs):")
        lbl_r.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569; border: none; background: transparent;")
        row_b.addWidget(lbl_r)

        self._input_rate = CleanNumericSpinBox(decimals=2)
        self._input_rate.setRange(0.0, 1000000.0)
        self._input_rate.setValue(0.0)
        self._input_rate.setFixedWidth(85)
        self._input_rate.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._input_rate.setStyleSheet("font-size: 11px; font-weight: 700; padding: 3px;")
        row_b.addWidget(self._input_rate)

        row_b.addStretch(1)

        self._add_btn = QPushButton("+ Add Material")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setFixedHeight(28)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-radius: 5px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self._add_btn.clicked.connect(self._add_current_material)
        row_b.addWidget(self._add_btn)

        layout.addLayout(row_b)

        # 3. Materials Table (Ultra-compact, strictly non-overflowing)
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Item Detail",
            "Qty",
            "Rate",
            "Cost",
            "",
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E2E8F0;
                background-color: #FFFFFF;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #F1F5F9;
                color: #475569;
                font-size: 10px;
                font-weight: 700;
                border: none;
                border-bottom: 1px solid #CBD5E1;
                padding: 3px 4px;
            }
        """)

        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 85)
        self._table.setColumnWidth(3, 90)
        self._table.setColumnWidth(4, 34)
        self._table.setFixedHeight(28)

        layout.addWidget(self._table)

        # 4. Empty placeholder hint
        self._hint_lbl = QLabel("No barcode inventory materials added yet. Choose from above and click '+ Add Material'.")
        self._hint_lbl.setStyleSheet("font-size: 10.5px; color: #94A3B8; font-style: italic; border: none; background: transparent; padding: 2px 2px;")
        layout.addWidget(self._hint_lbl)

        # Load inventory into combo
        self.refresh_inventory()

    def _on_input_qty_changed(self, val: float) -> None:
        if val > 0:
            self.qty_changed.emit(val)

    def set_default_qty(self, qty: float) -> None:
        """Update picker input qty when sheet calculator qty changes."""
        if qty > 0 and abs(self._input_qty.value() - qty) > 0.001:
            self._input_qty.blockSignals(True)
            self._input_qty.setValue(qty)
            self._input_qty.blockSignals(False)

    def _repopulate_combo(self, preserve_selection: bool = True) -> None:
        cur_id = self._combo.current_item().id if self._combo.current_item() else None
        self._combo.set_items(self._inventory_items, preserve_id=(cur_id if preserve_selection else None))
        cur = self._combo.current_item()
        if cur is not None:
            self._input_rate.setValue(cur.rate)
            self._add_btn.setEnabled(True)
            self.item_selected.emit(cur.detail)
        else:
            self._input_rate.setValue(0.0)
            self._add_btn.setEnabled(False)

    def refresh_inventory(self) -> None:
        """Reload available items from barcode_inventory table with updated stock counts."""
        self._inventory_items = list_barcode_inventory(self._connection)
        self._repopulate_combo(preserve_selection=True)

    def _on_material_selected(self, item: BarcodeInventoryItem | None) -> None:
        if item is not None:
            self._input_rate.setValue(item.rate)
            self.item_selected.emit(item.detail)

    def _add_current_material(self) -> None:
        item = self._combo.current_item()
        if not isinstance(item, BarcodeInventoryItem):
            return

        qty = max(0.01, self._input_qty.value())
        rate = max(0.0, self._input_rate.value())

        # Check if already added
        for existing in self._rows:
            if existing.item_id == item.id:
                # Increment qty
                existing.qty_spin.setValue(existing.qty_spin.value() + qty)
                return

        row = BarcodeMaterialRow(
            item_id=item.id,
            detail=item.detail,
            qty=qty,
            rate=rate,
            on_change_callback=self._on_row_changed,
            on_remove_callback=self._remove_row,
        )
        self._rows.append(row)
        self._rebuild_table()
        self._on_row_changed(qty)

    def _remove_row(self, row: BarcodeMaterialRow) -> None:
        if row in self._rows:
            self._rows.remove(row)
            self._rebuild_table()
            self._on_row_changed()

    def _on_row_changed(self, qty: float | None = None) -> None:
        total = self.get_total()
        self.lbl_mat_total.setText(f"Material Cost: Rs. {total:,.2f}")
        self.cost_changed.emit()
        if qty is not None and qty > 0:
            self.qty_changed.emit(qty)

    def _rebuild_table(self) -> None:
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._rows))

        has_rows = len(self._rows) > 0
        self._table.setVisible(has_rows)
        self._hint_lbl.setVisible(not has_rows)

        if has_rows:
            table_h = min(180, 26 + len(self._rows) * 34)
            self._table.setFixedHeight(table_h)

        for r_idx, row in enumerate(self._rows):
            self._table.setRowHeight(r_idx, 32)

            # 0. Detail
            d_lbl = QLabel(row.detail)
            d_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #1E293B; padding-left: 4px;")
            self._table.setCellWidget(r_idx, 0, d_lbl)

            # 1. Qty
            self._table.setCellWidget(r_idx, 1, row.qty_spin)

            # 2. Rate
            self._table.setCellWidget(r_idx, 2, row.rate_spin)

            # 3. Cost
            self._table.setCellWidget(r_idx, 3, row.cost_lbl)

            # 4. Remove
            self._table.setCellWidget(r_idx, 4, row.del_btn)

    def get_total(self) -> float:
        """Sum of all selected barcode inventory materials."""
        return round(sum(r.get_cost() for r in self._rows), 2)

    def get_selected_description(self) -> str:
        """Return the detail of the selected barcode material(s)."""
        if self._rows:
            return ", ".join(r.detail for r in self._rows if r.detail)
        item = self._combo.current_item()
        if isinstance(item, BarcodeInventoryItem) and item.detail:
            return item.detail
        return ""

    def get_selected_materials(self) -> list[tuple[int, float]]:
        """List of (item_id, quantity) for all chosen materials to deduct on bill save."""
        if self._rows:
            return [(r.item_id, float(r.qty_spin.value())) for r in self._rows if r.item_id]

        item = self._combo.current_item()
        if isinstance(item, BarcodeInventoryItem) and item.id:
            qty = float(self._input_qty.value())
            if qty > 0:
                return [(item.id, qty)]
        return []

    def clear(self) -> None:
        """Clear all selected materials and reload inventory stock."""
        self._rows.clear()
        self._rebuild_table()
        self._input_qty.blockSignals(True)
        self._input_qty.setValue(1.0)
        self._input_qty.blockSignals(False)
        self.refresh_inventory()
        self._on_row_changed()

