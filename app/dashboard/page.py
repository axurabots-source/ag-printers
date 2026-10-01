"""Clean and minimalist executive dashboard for AG Printers."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.dashboard.charts import TopClientsWidget, TrendChartWidget
from app.dashboard.metrics import (
    get_inventory_status,
    get_kpi_metrics,
    get_recent_bills,
    get_revenue_trend,
    get_top_clients,
)
from app.jobs.pdf_generator import get_or_create_bill_pdf
from app.pdf_settings import open_pdf_file
from app.ui import icons


class KpiCard(QFrame):
    """Clean metric card with SVG icon, title, value, and subtitle without heavy boxes."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str,
        icon_kind: str,
        is_profit: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header: clean SVG icon + Title (no box around text/icon)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        color = "#059669" if is_profit else "#1d4e89"
        self._icon_lbl = QLabel()
        self._icon_lbl.setPixmap(icons.pixmap(icon_kind, color, 18))
        top_row.addWidget(self._icon_lbl)

        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        top_row.addWidget(self._title_lbl)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        # Main Value
        self._value_lbl = QLabel(value)
        val_color = "#059669" if is_profit else "#0f172a"
        self._value_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {val_color};")
        layout.addWidget(self._value_lbl)

        # Subtitle
        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(self._sub_lbl)

    def update_metrics(self, value: str, subtitle: str) -> None:
        self._value_lbl.setText(value)
        self._sub_lbl.setText(subtitle)


class DashboardPage(QWidget):
    """Sober, professional corporate dashboard adhering to AG Printers design language."""

    navigate_requested = Signal(str)

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Clean scroll area with no horizontal scrollbar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #f8fafc;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 28px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background: #f8fafc;")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(36, 24, 36, 60)
        self._layout.setSpacing(20)

        # 1. Top Bar
        self._build_top_bar()

        # 2. KPI Cards Row
        self._build_kpi_cards()

        # 3. Charts Row
        self._build_charts_row()

        # 4. Details Grid (Recent Bills & Deliveries + Inventory Left)
        self._build_details_grid()

        # Generous wide bottom breathing room so nothing touches screen edges
        self._layout.addSpacing(60)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        self.refresh()

    def reset_to_list(self) -> None:
        self.refresh()

    def _build_top_bar(self) -> None:
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        sub = QLabel("Overview of sales, net profit, invoices and stock")
        sub.setStyleSheet("font-size: 12px; color: #64748b;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        top_bar.addLayout(title_box)

        top_bar.addStretch(1)

        # Actions
        actions_box = QHBoxLayout()
        actions_box.setSpacing(8)

        new_job_btn = QPushButton("+ New Job")
        new_job_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_job_btn.setStyleSheet("""
            QPushButton {
                background: #1d4e89;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #24589b; }
        """)
        new_job_btn.clicked.connect(lambda: self.navigate_requested.emit("New Job"))
        actions_box.addWidget(new_job_btn)

        ledger_btn = QPushButton("Ledger")
        ledger_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ledger_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        ledger_btn.clicked.connect(lambda: self.navigate_requested.emit("Ledger"))
        actions_box.addWidget(ledger_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setIcon(icons.icon("dashboard", "#334155", 14))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        actions_box.addWidget(refresh_btn)

        top_bar.addLayout(actions_box)
        self._layout.addLayout(top_bar)

    def _build_kpi_cards(self) -> None:
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self._card_rev = KpiCard(
            title="Total Revenue",
            value="Rs. 0.00",
            subtitle="0 Billed Invoices",
            icon_kind="sales",
            is_profit=False,
        )
        cards_grid.addWidget(self._card_rev, 0, 0)

        self._card_profit = KpiCard(
            title="Net Profit",
            value="Rs. 0.00",
            subtitle="0.0% Margin",
            icon_kind="reports",
            is_profit=True,
        )
        cards_grid.addWidget(self._card_profit, 0, 1)

        self._card_docs = KpiCard(
            title="Invoices & Gate Passes",
            value="0 Invoices / 0 Gate Passes",
            subtitle="Active Clients: 0",
            icon_kind="bills",
            is_profit=False,
        )
        cards_grid.addWidget(self._card_docs, 0, 2)

        self._card_inv = KpiCard(
            title="Stock Inventory",
            value="0 Units",
            subtitle="Valuation: Rs. 0.00",
            icon_kind="items",
            is_profit=False,
        )
        cards_grid.addWidget(self._card_inv, 0, 3)

        self._layout.addLayout(cards_grid)

    def _build_charts_row(self) -> None:
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)

        # Left: Financial Trends
        trend_frame = QFrame()
        trend_frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        trend_layout = QVBoxLayout(trend_frame)
        trend_layout.setContentsMargins(16, 14, 16, 14)
        trend_layout.setSpacing(8)

        th_lbl = QLabel("Revenue & Profit Trends")
        th_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        trend_layout.addWidget(th_lbl)

        self._trend_chart = TrendChartWidget()
        trend_layout.addWidget(self._trend_chart)

        charts_row.addWidget(trend_frame, 3)

        # Right: Top Clients
        self._top_clients = TopClientsWidget()
        charts_row.addWidget(self._top_clients, 2)

        self._layout.addLayout(charts_row)

    def _build_details_grid(self) -> None:
        details_row = QHBoxLayout()
        details_row.setSpacing(12)

        # Left: Recent Invoices Table
        bills_frame = QFrame()
        bills_frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        bills_vbox = QVBoxLayout(bills_frame)
        bills_vbox.setContentsMargins(16, 14, 16, 14)
        bills_vbox.setSpacing(10)

        bills_hdr = QHBoxLayout()
        b_title = QLabel("Recent Invoices & Deliveries")
        b_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        bills_hdr.addWidget(b_title)
        bills_hdr.addStretch(1)

        # Sleek scrolling buttons
        scroll_btn_box = QHBoxLayout()
        scroll_btn_box.setSpacing(4)

        up_btn = QPushButton("▲")
        up_btn.setToolTip("Scroll Invoices Up")
        up_btn.setFixedSize(26, 26)
        up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        up_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                border: none;
                border-radius: 6px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #e2e8f0;
                color: #1d4e89;
            }
            QPushButton:pressed {
                background: #cbd5e1;
            }
        """)
        up_btn.clicked.connect(lambda: self._scroll_bills(-1))
        scroll_btn_box.addWidget(up_btn)

        down_btn = QPushButton("▼")
        down_btn.setToolTip("Scroll Invoices Down")
        down_btn.setFixedSize(26, 26)
        down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        down_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                border: none;
                border-radius: 6px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #e2e8f0;
                color: #1d4e89;
            }
            QPushButton:pressed {
                background: #cbd5e1;
            }
        """)
        down_btn.clicked.connect(lambda: self._scroll_bills(1))
        scroll_btn_box.addWidget(down_btn)

        bills_hdr.addLayout(scroll_btn_box)
        bills_hdr.addSpacing(6)

        view_ledger_btn = QPushButton("View All →")
        view_ledger_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_ledger_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #1d4e89;
                font-weight: 600;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        view_ledger_btn.clicked.connect(lambda: self.navigate_requested.emit("Ledger"))
        bills_hdr.addWidget(view_ledger_btn)
        bills_vbox.addLayout(bills_hdr)

        self._bills_table = QTableWidget(0, 7)
        self._bills_table.setObjectName("DashboardBillsTable")
        self._bills_table.setHorizontalHeaderLabels([
            "Invoice #",
            "Client / Party",
            "Date",
            "Gate Pass",
            "Total",
            "Profit",
            "PDF",
        ])
        self._bills_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._bills_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._bills_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._bills_table.setShowGrid(False)
        self._bills_table.verticalHeader().setVisible(False)
        self._bills_table.verticalHeader().setDefaultSectionSize(38)
        self._bills_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background: transparent;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #475569;
                font-size: 11px;
                font-weight: 600;
                padding: 4px;
                border: none;
            }
            QTableWidget::item {
                border: none;
                padding: 2px;
                font-size: 11px;
                color: #1e293b;
            }
            QScrollBar:vertical {
                border: none;
                background: #f8fafc;
                width: 10px;
                margin: 16px 0 16px 0;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: #e2e8f0;
                height: 14px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-radius: 4px;
            }
            QScrollBar::sub-line:vertical:hover {
                background: #1d4e89;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: #e2e8f0;
                height: 14px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical:hover {
                background: #1d4e89;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 0px;
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f8fafc;
                height: 10px;
                margin: 0 16px 0 16px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #cbd5e1;
                min-width: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #94a3b8;
            }
            QScrollBar::sub-line:horizontal {
                border: none;
                background: #e2e8f0;
                width: 14px;
                subcontrol-position: left;
                subcontrol-origin: margin;
                border-radius: 4px;
            }
            QScrollBar::sub-line:horizontal:hover {
                background: #1d4e89;
            }
            QScrollBar::add-line:horizontal {
                border: none;
                background: #e2e8f0;
                width: 14px;
                subcontrol-position: right;
                subcontrol-origin: margin;
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal:hover {
                background: #1d4e89;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                width: 0px;
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        hdr = self._bills_table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, width in {0: 80, 2: 110, 3: 90, 4: 90, 5: 85, 6: 70}.items():
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self._bills_table.setColumnWidth(col, width)

        self._bills_table.setFixedHeight(230)
        bills_vbox.addWidget(self._bills_table)

        details_row.addWidget(bills_frame, 3)

        # Right: Barcode Inventory Left
        inv_frame = QFrame()
        inv_frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        inv_vbox = QVBoxLayout(inv_frame)
        inv_vbox.setContentsMargins(16, 14, 16, 14)
        inv_vbox.setSpacing(10)

        inv_hdr = QHBoxLayout()
        i_title = QLabel("Stock Inventory Left")
        i_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        inv_hdr.addWidget(i_title)
        inv_hdr.addStretch(1)

        manage_inv_btn = QPushButton("Manage →")
        manage_inv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        manage_inv_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #1d4e89;
                font-weight: 600;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        manage_inv_btn.clicked.connect(lambda: self.navigate_requested.emit("Inventory"))
        inv_hdr.addWidget(manage_inv_btn)
        inv_vbox.addLayout(inv_hdr)

        self._inv_items_container = QVBoxLayout()
        self._inv_items_container.setSpacing(6)
        inv_vbox.addLayout(self._inv_items_container)
        inv_vbox.addStretch(1)

        details_row.addWidget(inv_frame, 2)

        self._layout.addLayout(details_row)

    def refresh(self) -> None:
        # 1. KPI
        kpi = get_kpi_metrics(self._connection)
        self._card_rev.update_metrics(
            f"Rs. {kpi['total_revenue']:,.2f}",
            f"{kpi['total_bills']} billed invoices",
        )
        self._card_profit.update_metrics(
            f"Rs. {kpi['total_profit']:,.2f}",
            f"{kpi['profit_margin']:.1f}% profit margin",
        )
        self._card_docs.update_metrics(
            f"{kpi['total_bills']} Invoices / {kpi['total_gate_passes']} Gate Passes",
            f"Active Clients: {kpi['total_parties']}",
        )
        low_txt = f"{kpi['low_stock_count']} low stock" if kpi['low_stock_count'] > 0 else "Stock healthy"
        self._card_inv.update_metrics(
            f"{kpi['inventory_qty']:g} Units",
            f"Valuation: Rs. {kpi['inventory_val']:,.2f} ({low_txt})",
        )

        # 2. Charts
        trend_data = get_revenue_trend(self._connection, limit=8)
        self._trend_chart.set_data(trend_data)

        top_clients = get_top_clients(self._connection, limit=5)
        self._top_clients.set_data(top_clients)

        # 3. Table
        recent_bills = get_recent_bills(self._connection, limit=10)
        self._bills_table.setRowCount(0)

        bold = QFont()
        bold.setBold(True)

        for bill in recent_bills:
            row = self._bills_table.rowCount()
            self._bills_table.insertRow(row)

            def _cell(text: str) -> QTableWidgetItem:
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return it

            bn = _cell(bill["bill_number"])
            bn.setFont(bold)
            self._bills_table.setItem(row, 0, bn)

            self._bills_table.setItem(row, 1, _cell(bill["party_name"]))
            self._bills_table.setItem(row, 2, _cell(bill["date"]))
            self._bills_table.setItem(row, 3, _cell(bill["gate_pass_number"]))
            self._bills_table.setItem(row, 4, _cell(f"{bill['total_amount']:,.0f}"))

            prof_it = _cell(f"{bill['profit']:,.0f}" if bill["profit"] > 0 else "—")
            if bill["profit"] > 0:
                prof_it.setForeground(QColor("#059669"))
                prof_it.setFont(bold)
            self._bills_table.setItem(row, 5, prof_it)

            # PDF Button
            pdf_btn = QPushButton("PDF")
            pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background: #1d4e89;
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 3px 6px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover { background: #24589b; }
            """)
            bid = bill["id"]
            pdf_btn.clicked.connect(lambda _checked=False, b=bid: self._open_bill_pdf(b))
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.addWidget(pdf_btn)
            self._bills_table.setCellWidget(row, 6, btn_container)

        # 4. Inventory Left List (No nested boxes on text, clean layout)
        inv_items = get_inventory_status(self._connection, limit=5)
        while self._inv_items_container.count():
            item = self._inv_items_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not inv_items:
            empty_inv = QLabel("No stock items recorded.")
            empty_inv.setStyleSheet("font-size: 11px; color: #94a3b8; font-style: italic; padding: 8px;")
            empty_inv.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._inv_items_container.addWidget(empty_inv)
        else:
            for item in inv_items:
                row_widget = QWidget()
                r_layout = QHBoxLayout(row_widget)
                r_layout.setContentsMargins(0, 4, 0, 4)
                r_layout.setSpacing(8)

                desc_box = QVBoxLayout()
                desc_box.setSpacing(1)
                item_name = QLabel(item["detail"])
                item_name.setStyleSheet("font-size: 12px; font-weight: 600; color: #1e293b;")
                item_sub = QLabel(f"Rate: Rs. {item['rate']:,.0f}  ·  Val: Rs. {item['total_value']:,.0f}")
                item_sub.setStyleSheet("font-size: 11px; color: #64748b;")
                desc_box.addWidget(item_name)
                desc_box.addWidget(item_sub)
                r_layout.addLayout(desc_box)

                r_layout.addStretch(1)

                # Stock qty & status as clean plain text (no box around text)
                qty_box = QVBoxLayout()
                qty_box.setSpacing(1)
                qty_box.setAlignment(Qt.AlignmentFlag.AlignRight)

                qty_lbl = QLabel(f"{item['quantity']:g} left")
                qty_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #0f172a;")
                qty_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                qty_box.addWidget(qty_lbl)

                status_color = "#dc2626" if item["is_low_stock"] else "#059669"
                status_text = "Low Stock" if item["is_low_stock"] else "In Stock"
                status_lbl = QLabel(status_text)
                status_lbl.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {status_color};")
                status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                qty_box.addWidget(status_lbl)

                r_layout.addLayout(qty_box)
                self._inv_items_container.addWidget(row_widget)

    def _scroll_bills(self, direction: int) -> None:
        sb = self._bills_table.verticalScrollBar()
        step = self._bills_table.verticalHeader().defaultSectionSize() or 38
        sb.setValue(sb.value() + (direction * step))

    def _open_bill_pdf(self, bill_id: int) -> None:
        try:
            pdf_path = get_or_create_bill_pdf(self._connection, bill_id)
            if pdf_path and pdf_path.exists():
                open_pdf_file(pdf_path)
            else:
                QMessageBox.warning(self, "PDF Not Found", "Could not generate or locate the PDF file.")
        except Exception as exc:
            QMessageBox.critical(self, "Error Opening PDF", str(exc))
