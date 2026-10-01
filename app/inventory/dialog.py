"""Add / Edit Barcode Inventory Item Dialog."""

from __future__ import annotations

import sqlite3
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.db.barcode_inventory import (
    BarcodeInventoryItem,
    create_barcode_inventory_item,
    update_barcode_inventory_item,
)
from app.ui.capitalized_input import CapitalizedLineEdit, capitalize_words


class CleanNumericSpinBox(QDoubleSpinBox):
    """Numeric input that selects all text on focus and clears default zero."""

    def __init__(self, decimals: int = 2, parent=None) -> None:
        super().__init__(parent)
        self.setDecimals(decimals)
        self.setRange(0.0, 99999999.0)
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setObjectName("FormInput")

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.selectAll()

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.selectAll()


class BarcodeItemDialog(QDialog):
    """Dialog to create or edit a barcode stock inventory item."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        item: BarcodeInventoryItem | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._item = item
        self.setModal(True)
        self.setFixedWidth(460)

        is_edit = item is not None
        self.setWindowTitle("Edit Barcode Item" if is_edit else "Add Barcode Item")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("Edit Barcode Item" if is_edit else "New Barcode Inventory Item")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel("Enter item detail, current stock quantity, and unit rate.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        layout.addLayout(title_box)

        # Form Card
        form_card = QFrame()
        form_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        form = QFormLayout(form_card)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        def make_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; border: none; background: transparent;")
            return lbl

        # 1. Detail / Description
        self._detail_edit = CapitalizedLineEdit()
        self._detail_edit.setObjectName("FormInput")
        self._detail_edit.setPlaceholderText("e.g. Roll 50x25mm (1000 Pcs) or Wax Ribbon 110mm")
        form.addRow(make_label("Detail / Description *"), self._detail_edit)

        # 2. Quantity
        self._qty_spin = CleanNumericSpinBox(decimals=0)
        self._qty_spin.setValue(100.0 if not is_edit else item.quantity)
        form.addRow(make_label("Stock Quantity *"), self._qty_spin)

        # 3. Rate (Rs.)
        self._rate_spin = CleanNumericSpinBox(decimals=2)
        self._rate_spin.setValue(0.0 if not is_edit else item.rate)
        form.addRow(make_label("Unit Rate (Rs.) *"), self._rate_spin)

        # 4. Total Value preview
        self._value_lbl = QLabel("Rs. 0.00")
        self._value_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #047857; border: none; background: transparent;")
        form.addRow(make_label("Total Value"), self._value_lbl)

        layout.addWidget(form_card)

        # Update preview when qty or rate changes
        self._qty_spin.valueChanged.connect(self._update_total_preview)
        self._rate_spin.valueChanged.connect(self._update_total_preview)

        # Populate if editing
        if is_edit and item is not None:
            self._detail_edit.setText(item.detail)
            self._qty_spin.setValue(item.quantity)
            self._rate_spin.setValue(item.rate)

        self._update_total_preview()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("OutlineButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Item" if not is_edit else "Update Item")
        save_btn.setObjectName("PrimaryButton")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        self._detail_edit.setFocus()

    def _update_total_preview(self) -> None:
        qty = self._qty_spin.value()
        rate = self._rate_spin.value()
        val = qty * rate
        self._value_lbl.setText(f"Rs. {val:,.2f}")

    def _save(self) -> None:
        detail = capitalize_words(self._detail_edit.text().strip())
        if not detail:
            QMessageBox.warning(self, "Missing Detail", "Please enter the item detail / description.")
            self._detail_edit.setFocus()
            return

        qty = max(0.0, self._qty_spin.value())
        rate = max(0.0, self._rate_spin.value())

        try:
            if self._item is None:
                create_barcode_inventory_item(self._connection, detail, qty, rate)
            else:
                update_barcode_inventory_item(self._connection, self._item.id, detail, qty, rate)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Item", f"Could not save barcode inventory item:\n{e}")
