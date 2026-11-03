"""Export Ledger Statement PDF Dialog with Party and Date selection."""

from __future__ import annotations

import sqlite3
from typing import Sequence

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.db.bills import Bill, list_bills
from app.db.parties import Party, get_party, list_parties
from app.ledger.statement_pdf import export_ledger_statement_pdf
from app.pdf_settings import open_pdf_file
from app.ui.calendar import (
    DATE_EDIT_STYLE,
    FILTER_COMBO_STYLE,
    PremiumCalendarWidget,
)

DIALOG_STYLE = """
QDialog {
    background-color: #FFFFFF;
}
QFrame#SummaryCard {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}
QFrame#PrivacyBadge {
    background-color: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 8px;
}
"""


class ExportLedgerPdfDialog(QDialog):
    """Modal dialog allowing users to select Party, Date range, and export a clean PDF statement."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        initial_party_id: int | None = None,
        initial_date_mode: str = "All Dates",
        initial_single_date: QDate | None = None,
        initial_date_from: QDate | None = None,
        initial_date_to: QDate | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self.setWindowTitle("Export Ledger Statement (PDF)")
        self.setFixedWidth(520)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)

        # Header Title
        title_lbl = QLabel("Generate Statement PDF")
        title_lbl.setStyleSheet("font-size: 19px; font-weight: 700; color: #0F172A;")
        sub_lbl = QLabel(
            "Select customer party and date range to export an official statement.\n"
            "Confidential net profit and cost figures are excluded automatically."
        )
        sub_lbl.setStyleSheet("font-size: 12px; color: #64748B; line-height: 1.4;")
        layout.addWidget(title_lbl)
        layout.addWidget(sub_lbl)

        # Form Frame
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        # 1. Party Selector
        party_lbl = QLabel("Customer / Party:")
        party_lbl.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none;")
        self._party_combo = QComboBox()
        self._party_combo.setStyleSheet(FILTER_COMBO_STYLE)
        self._party_combo.addItem("All Parties (All Round)", None)

        parties = list_parties(self._connection)
        sel_idx = 0
        for idx, p in enumerate(parties, start=1):
            self._party_combo.addItem(p.name, p.id)
            if initial_party_id is not None and p.id == initial_party_id:
                sel_idx = idx

        self._party_combo.setCurrentIndex(sel_idx)
        self._party_combo.currentIndexChanged.connect(self._update_preview)
        form_layout.addWidget(party_lbl)
        form_layout.addWidget(self._party_combo)

        # 2. Date Filter
        date_lbl = QLabel("Statement Period (Date Filter):")
        date_lbl.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none;")
        self._date_combo = QComboBox()
        self._date_combo.setStyleSheet(FILTER_COMBO_STYLE)
        self._date_combo.addItems([
            "All Dates",
            "Today",
            "This Month",
            "Specific Date",
            "Date Range",
        ])
        if initial_date_mode in [self._date_combo.itemText(i) for i in range(self._date_combo.count())]:
            self._date_combo.setCurrentText(initial_date_mode)

        self._date_combo.currentIndexChanged.connect(self._on_date_combo_changed)
        form_layout.addWidget(date_lbl)
        form_layout.addWidget(self._date_combo)

        # Specific Date
        self._single_date_edit = QDateEdit(initial_single_date or QDate.currentDate())
        self._single_date_edit.setCalendarPopup(True)
        self._single_date_edit.setCalendarWidget(PremiumCalendarWidget(self))
        self._single_date_edit.setDisplayFormat("dd MMM yyyy")
        self._single_date_edit.setStyleSheet(DATE_EDIT_STYLE)
        self._single_date_edit.setVisible(False)
        self._single_date_edit.dateChanged.connect(lambda _d: self._update_preview())
        form_layout.addWidget(self._single_date_edit)

        # Date Range Row (From / To)
        self._range_widget = QWidget()
        self._range_widget.setStyleSheet("border: none;")
        range_layout = QHBoxLayout(self._range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(10)

        r_from_lbl = QLabel("From:")
        r_from_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B; border: none;")
        self._from_edit = QDateEdit(initial_date_from or QDate.currentDate().addDays(-30))
        self._from_edit.setCalendarPopup(True)
        self._from_edit.setCalendarWidget(PremiumCalendarWidget(self))
        self._from_edit.setDisplayFormat("dd MMM yyyy")
        self._from_edit.setStyleSheet(DATE_EDIT_STYLE)
        self._from_edit.dateChanged.connect(lambda _d: self._update_preview())

        r_to_lbl = QLabel("To:")
        r_to_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B; border: none;")
        self._to_edit = QDateEdit(initial_date_to or QDate.currentDate())
        self._to_edit.setCalendarPopup(True)
        self._to_edit.setCalendarWidget(PremiumCalendarWidget(self))
        self._to_edit.setDisplayFormat("dd MMM yyyy")
        self._to_edit.setStyleSheet(DATE_EDIT_STYLE)
        self._to_edit.dateChanged.connect(lambda _d: self._update_preview())

        range_layout.addWidget(r_from_lbl)
        range_layout.addWidget(self._from_edit)
        range_layout.addWidget(r_to_lbl)
        range_layout.addWidget(self._to_edit)
        self._range_widget.setVisible(False)
        form_layout.addWidget(self._range_widget)

        layout.addWidget(form_frame)

        # 3. Live Preview / Count Summary
        self._summary_card = QFrame()
        self._summary_card.setObjectName("SummaryCard")
        sum_layout = QVBoxLayout(self._summary_card)
        sum_layout.setContentsMargins(14, 12, 14, 12)
        sum_layout.setSpacing(4)

        self._sum_invoices = QLabel("Loading preview...")
        self._sum_invoices.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
        self._sum_amount = QLabel("")
        self._sum_amount.setStyleSheet("font-size: 12px; font-weight: 600; color: #0284C7;")

        sum_layout.addWidget(self._sum_invoices)
        sum_layout.addWidget(self._sum_amount)
        layout.addWidget(self._summary_card)

        # 4. Confidentiality Notice Badge
        privacy_badge = QFrame()
        privacy_badge.setObjectName("PrivacyBadge")
        priv_layout = QHBoxLayout(privacy_badge)
        priv_layout.setContentsMargins(12, 8, 12, 8)
        priv_layout.setSpacing(8)

        priv_icon = QLabel("🔒")
        priv_icon.setStyleSheet("font-size: 14px; border: none;")
        priv_msg = QLabel("Profit & margin details will NOT be included in this PDF statement.")
        priv_msg.setStyleSheet("font-size: 11px; font-weight: 600; color: #1E40AF; border: none;")
        priv_layout.addWidget(priv_icon)
        priv_layout.addWidget(priv_msg, 1)
        layout.addWidget(privacy_badge)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("OutlineButton")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                color: #475569;
                font-size: 13px;
                font-weight: 600;
                padding: 9px 18px;
            }
            QPushButton:hover {
                background: #F8FAFC;
                border-color: #94A3B8;
                color: #0F172A;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        self._export_btn = QPushButton("📄 Generate & Open PDF")
        self._export_btn.setObjectName("PrimaryButton")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setStyleSheet("""
            QPushButton {
                background: #0284C7;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 20px;
            }
            QPushButton:hover {
                background: #0369A1;
            }
            QPushButton:pressed {
                background: #075985;
            }
        """)
        self._export_btn.clicked.connect(self._do_export)

        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._export_btn)
        layout.addLayout(btn_row)

        self._on_date_combo_changed()

    def _on_date_combo_changed(self) -> None:
        mode = self._date_combo.currentText()
        self._single_date_edit.setVisible(mode == "Specific Date")
        self._range_widget.setVisible(mode == "Date Range")
        self._update_preview()

    def _get_selected_date_range(self) -> tuple[str, str, str]:
        mode = self._date_combo.currentText()
        if mode == "Today":
            today_str = QDate.currentDate().toString("yyyy-MM-dd")
            lbl = f"Today ({QDate.currentDate().toString('dd-MMM-yyyy')})"
            return today_str, today_str, lbl
        elif mode == "This Month":
            today = QDate.currentDate()
            first_day = QDate(today.year(), today.month(), 1).toString("yyyy-MM-dd")
            last_day = QDate(today.year(), today.month(), today.daysInMonth()).toString("yyyy-MM-dd")
            lbl = f"Month of {QDate.currentDate().toString('MMMM yyyy')}"
            return first_day, last_day, lbl
        elif mode == "Specific Date":
            dt_str = self._single_date_edit.date().toString("yyyy-MM-dd")
            lbl = f"On {self._single_date_edit.date().toString('dd-MMM-yyyy')}"
            return dt_str, dt_str, lbl
        elif mode == "Date Range":
            from_str = self._from_edit.date().toString("yyyy-MM-dd")
            to_str = self._to_edit.date().toString("yyyy-MM-dd")
            lbl = f"{self._from_edit.date().toString('dd-MMM-yyyy')} to {self._to_edit.date().toString('dd-MMM-yyyy')}"
            return from_str, to_str, lbl
        return "", "", "All Dates (All Round)"

    def _get_matching_bills(self) -> list[Bill]:
        party_id = self._party_combo.currentData()
        date_from, date_to, _ = self._get_selected_date_range()
        return list_bills(
            self._connection,
            party_id=party_id,
            date_from=date_from,
            date_to=date_to,
        )

    def _update_preview(self) -> None:
        bills = self._get_matching_bills()
        count = len(bills)
        total_amt = sum(b.total_amount for b in bills)

        if count == 0:
            self._sum_invoices.setText("No invoices found for this selection.")
            self._sum_invoices.setStyleSheet("font-size: 13px; font-weight: 700; color: #DC2626;")
            self._sum_amount.setText("Total Amount: PKR 0.00")
            self._export_btn.setEnabled(False)
        else:
            self._sum_invoices.setText(f"{count} {'Invoice' if count == 1 else 'Invoices'} Found")
            self._sum_invoices.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
            self._sum_amount.setText(f"Total Invoiced Amount: PKR {total_amt:,.2f}")
            self._export_btn.setEnabled(True)

    def _do_export(self) -> None:
        bills = self._get_matching_bills()
        if not bills:
            QMessageBox.warning(self, "No Records", "No invoices match the chosen party and date criteria.")
            return

        party_id = self._party_combo.currentData()
        party_name = self._party_combo.currentText()
        party_details = ""

        if party_id is not None:
            party_obj = get_party(self._connection, party_id)
            if party_obj:
                parts = []
                if party_obj.contact_person:
                    parts.append(f"Contact: {party_obj.contact_person}")
                if party_obj.phone:
                    parts.append(f"Phone: {party_obj.phone}")
                if party_obj.address:
                    parts.append(f"Address: {party_obj.address}")
                party_details = " | ".join(parts)
        else:
            party_details = "Consolidated Billing Statement (All Active Accounts)"

        _, _, date_label = self._get_selected_date_range()

        try:
            pdf_path = export_ledger_statement_pdf(
                bills=bills,
                party_name=party_name,
                party_details=party_details,
                date_range_label=date_label,
            )
            if pdf_path and pdf_path.exists():
                open_pdf_file(pdf_path)
                self.accept()
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to generate statement PDF.")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"An error occurred while generating the PDF:\n{exc}")

