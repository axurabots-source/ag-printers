"""Barcode Inventory Management Screen.

Dedicated module to manage raw materials (media rolls, wax ribbons, labels)
specifying Detail, Stock Quantity, and Unit Rate, used exclusively in Barcode Costing.
"""

from __future__ import annotations

from datetime import datetime
import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.barcode_inventory import (
    BarcodeInventoryItem,
    delete_barcode_inventory_item,
    get_barcode_inventory_summary,
    list_barcode_inventory,
)
from app.inventory.dialog import BarcodeItemDialog


def _format_timestamp(val: str | None) -> str:
    """Format timestamp into readable date and time."""
    if not val:
        return "-"
    try:
        clean = str(val).strip().replace("T", " ")
        return datetime.fromisoformat(clean).strftime("%d-%b-%Y %I:%M %p")
    except Exception:
        return str(val)[:16] if val else "-"


class InventoryPage(QWidget):
    """Executive view for Barcode Stock Inventory and Rate cards."""

    inventory_updated = Signal()

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._items: list[BarcodeInventoryItem] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 1. Top Executive Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("Barcode Inventory")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("Dedicated stock and rate management for rolls, ribbons & media used in Barcode Costing.")
        subtitle.setObjectName("FieldLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_bar.addLayout(title_box, 1)

        self._add_btn = QPushButton("+ Add Barcode Item")
        self._add_btn.setObjectName("PrimaryButton")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._open_add_dialog)
        top_bar.addWidget(self._add_btn)

        layout.addLayout(top_bar)

        # 2. Metric KPI Cards
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        self._kpi_items = self._create_kpi_card("TOTAL ITEMS", "0 Items", "#1E293B", "#F8FAFC")
        self._kpi_qty = self._create_kpi_card("TOTAL STOCK QUANTITY", "0 Units", "#2563EB", "#EFF6FF")
        self._kpi_val = self._create_kpi_card("TOTAL STOCK VALUE", "Rs. 0.00", "#047857", "#ECFDF5")

        kpi_row.addWidget(self._kpi_items)
        kpi_row.addWidget(self._kpi_qty)
        kpi_row.addWidget(self._kpi_val)
        layout.addLayout(kpi_row)

        # 3. Search and Filter Bar
        search_card = QFrame()
        search_card.setObjectName("ProfileCard")
        search_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        s_layout = QHBoxLayout(search_card)
        s_layout.setContentsMargins(14, 10, 14, 10)
        s_layout.setSpacing(10)

        s_icon = QLabel("🔍")
        s_icon.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        s_layout.addWidget(s_icon)

        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("FormInput")
        self._search_edit.setPlaceholderText("Search barcode inventory by detail / description...")
        self._search_edit.setStyleSheet("border: none; background: transparent; font-size: 13px; color: #1E293B;")
        self._search_edit.textChanged.connect(self.refresh)
        s_layout.addWidget(self._search_edit, 1)

        layout.addWidget(search_card)

        # 4. Inventory Items Table Card
        table_card = QFrame()
        table_card.setObjectName("ProfileCard")
        table_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;")
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(16, 16, 16, 16)
        t_layout.setSpacing(10)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Sr.",
            "Detail / Item Description",
            "Stock Qty",
            "Unit Rate (Rs.)",
            "Total Value (Rs.)",
            "Date Added",
            "Last Updated",
            "Actions",
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setShowGrid(False)
        self._table.setStyleSheet("""
            QTableWidget {
                border: none;
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

        h_header = self._table.horizontalHeader()
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        h_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(0, 45)
        self._table.setColumnWidth(2, 95)
        self._table.setColumnWidth(3, 115)
        self._table.setColumnWidth(4, 125)
        self._table.setColumnWidth(5, 145)
        self._table.setColumnWidth(6, 145)
        self._table.setColumnWidth(7, 130)

        t_layout.addWidget(self._table)
        layout.addWidget(table_card, 1)

        # Initial load
        self.refresh()

    def _create_kpi_card(self, label: str, value: str, text_color: str, bg_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px 16px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.5px; border: none; background: transparent;")
        c_layout.addWidget(lbl)

        val_lbl = QLabel(value)
        val_lbl.setObjectName("KPIValue")
        val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {text_color}; border: none; background: transparent;")
        c_layout.addWidget(val_lbl)

        # Store label reference on card
        card.val_label = val_lbl  # type: ignore[attr-defined]
        return card

    def reset_to_list(self) -> None:
        """Called when user navigates to this page from sidebar."""
        self.refresh()

    def refresh(self) -> None:
        """Reload inventory items from database."""
        query = self._search_edit.text() if hasattr(self, "_search_edit") else ""
        self._items = list_barcode_inventory(self._connection, query)

        # Update KPI summary
        summary = get_barcode_inventory_summary(self._connection)
        if hasattr(self, "_kpi_items"):
            self._kpi_items.val_label.setText(f"{int(summary['total_items'])} Items")  # type: ignore[attr-defined]
            self._kpi_qty.val_label.setText(f"{summary['total_qty']:,.0f} Units")  # type: ignore[attr-defined]
            self._kpi_val.val_label.setText(f"Rs. {summary['total_value']:,.2f}")  # type: ignore[attr-defined]

        # Populate table
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            self._table.setRowHeight(row, 44)

            # 0. Sr.
            sr_lbl = QLabel(str(row + 1))
            sr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sr_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
            self._table.setCellWidget(row, 0, sr_lbl)

            # 1. Detail / Description
            detail_lbl = QLabel(item.detail)
            detail_lbl.setStyleSheet("color: #0F172A; font-size: 13px; font-weight: 600; padding-left: 8px;")
            self._table.setCellWidget(row, 1, detail_lbl)

            # 2. Quantity
            qty_lbl = QLabel(f"{item.quantity:,.0f}" if item.quantity.is_integer() else f"{item.quantity:,.2f}")
            qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_lbl.setStyleSheet("color: #1E293B; font-size: 12px; font-weight: 700;")
            self._table.setCellWidget(row, 2, qty_lbl)

            # 3. Unit Rate
            rate_lbl = QLabel(f"Rs. {item.rate:,.2f}")
            rate_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rate_lbl.setStyleSheet("color: #2563EB; font-size: 12px; font-weight: 700;")
            self._table.setCellWidget(row, 3, rate_lbl)

            # 4. Total Value
            val_lbl = QLabel(f"Rs. {item.total_value:,.2f}")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setStyleSheet("color: #047857; font-size: 12px; font-weight: 700;")
            self._table.setCellWidget(row, 4, val_lbl)

            # 5. Date Added
            created_lbl = QLabel(_format_timestamp(item.created_at))
            created_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            created_lbl.setStyleSheet("color: #64748B; font-size: 11.5px; font-weight: 500;")
            self._table.setCellWidget(row, 5, created_lbl)

            # 6. Last Updated
            updated_lbl = QLabel(_format_timestamp(item.updated_at))
            updated_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            updated_lbl.setStyleSheet("color: #2563EB; font-size: 11.5px; font-weight: 600;")
            self._table.setCellWidget(row, 6, updated_lbl)

            # 7. Actions (Edit / Delete)
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 4, 4, 4)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("OutlineButton")
            edit_btn.setFixedSize(56, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    color: #2563EB;
                    font-size: 11px;
                    font-weight: 600;
                    background-color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #EFF6FF;
                    border-color: #93C5FD;
                }
            """)
            edit_btn.clicked.connect(lambda _, it=item: self._open_edit_dialog(it))
            act_layout.addWidget(edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(60, 28)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #FECACA;
                    border-radius: 4px;
                    color: #DC2626;
                    font-size: 11px;
                    font-weight: 600;
                    background-color: #FEF2F2;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                    border-color: #FCA5A5;
                }
            """)
            del_btn.clicked.connect(lambda _, it=item: self._delete_item(it))
            act_layout.addWidget(del_btn)

            self._table.setCellWidget(row, 7, act_widget)

    def _open_add_dialog(self) -> None:
        dlg = BarcodeItemDialog(self._connection, parent=self)
        if dlg.exec():
            self.refresh()
            self.inventory_updated.emit()

    def _open_edit_dialog(self, item: BarcodeInventoryItem) -> None:
        dlg = BarcodeItemDialog(self._connection, item=item, parent=self)
        if dlg.exec():
            self.refresh()
            self.inventory_updated.emit()

    def _delete_item(self, item: BarcodeInventoryItem) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{item.detail}' from barcode inventory?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_barcode_inventory_item(self._connection, item.id)
            self.refresh()
            self.inventory_updated.emit()
