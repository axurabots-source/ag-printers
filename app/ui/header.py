"""Top header bar shown above the main content area with unique executive widgets."""

from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import __version__

PAGE_METADATA: dict[str, str] = {
    "Dashboard": "Real-time metrics, financial summary & recent invoices",
    "New Job": "Create & print customer bills, delivery challans and pads",
    "Parties": "Customer & vendor profiles, ledgers and balances",
    "Party Profile": "Detailed party transactions, ledger view and statements",
    "Gate Pass": "Delivery challans, gate passes and dispatch history",
    "Bills": "All generated invoices, receivable tracking and statuses",
    "Costing": "Printing cost estimation, paper calculations & job margins",
    "Inventory": "Raw materials, paper stock and consumable inventory",
    "Ledger": "General financial ledger, credit/debit entries and balance sheet",
    "Settings": "System preferences, database maintenance and automated backups",
}


class HeaderBar(QFrame):
    """Executive top bar: dynamic title/subtitle on left, live clock & status chips on right."""

    update_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(72)

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 0)
        root.setSpacing(16)

        # ── Left: Accent bar + Page Title + Context Subtitle ─────────────────
        left_box = QHBoxLayout()
        left_box.setSpacing(12)

        self._accent_bar = QFrame()
        self._accent_bar.setObjectName("HeaderAccentBar")
        self._accent_bar.setFixedSize(4, 32)
        left_box.addWidget(self._accent_bar)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._title = QLabel("Dashboard")
        self._title.setObjectName("HeaderTitle")
        self._subtitle = QLabel(PAGE_METADATA.get("Dashboard", "AG Printers Business Management"))
        self._subtitle.setObjectName("HeaderSubtitle")

        text_col.addWidget(self._title)
        text_col.addWidget(self._subtitle)
        left_box.addLayout(text_col)

        root.addLayout(left_box)
        root.addStretch(1)

        # ── Right: Executive Utility Chips ──────────────────────────────────
        right_box = QHBoxLayout()
        right_box.setSpacing(10)
        right_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 1. System Status Chip (Pill with glowing emerald dot)
        self._status_chip = QFrame()
        self._status_chip.setObjectName("HeaderStatusChip")
        status_layout = QHBoxLayout(self._status_chip)
        status_layout.setContentsMargins(10, 4, 12, 4)
        status_layout.setSpacing(6)

        status_dot = QLabel("●")
        status_dot.setObjectName("HeaderStatusDot")
        status_text = QLabel("System Active")
        status_text.setObjectName("HeaderStatusText")

        status_layout.addWidget(status_dot)
        status_layout.addWidget(status_text)
        right_box.addWidget(self._status_chip)

        # 2. Live Date & Time Chip
        self._clock_chip = QFrame()
        self._clock_chip.setObjectName("HeaderClockChip")
        clock_layout = QHBoxLayout(self._clock_chip)
        clock_layout.setContentsMargins(12, 4, 14, 4)
        clock_layout.setSpacing(6)

        self._clock_text = QLabel()
        self._clock_text.setObjectName("HeaderClockText")
        clock_layout.addWidget(self._clock_text)
        right_box.addWidget(self._clock_chip)

        # 3. Enterprise Branding Chip
        self._brand_chip = QFrame()
        self._brand_chip.setObjectName("HeaderBrandChip")
        brand_layout = QHBoxLayout(self._brand_chip)
        brand_layout.setContentsMargins(12, 4, 12, 4)
        brand_layout.setSpacing(6)

        brand_name = QLabel("AG PRINTERS")
        brand_name.setObjectName("HeaderBrandName")
        brand_sep = QLabel("•")
        brand_sep.setObjectName("HeaderBrandSep")
        brand_loc = QLabel("FAISALABAD")
        brand_loc.setObjectName("HeaderBrandLoc")

        brand_layout.addWidget(brand_name)
        brand_layout.addWidget(brand_sep)
        brand_layout.addWidget(brand_loc)
        right_box.addWidget(self._brand_chip)

        # 4. Version Badge
        version_badge = QLabel(f"v{__version__}")
        version_badge.setObjectName("VersionBadge")
        version_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_box.addWidget(version_badge)

        # 5. Live Update Available Pill (starts hidden, appears when GitHub has new release)
        self._update_btn = QPushButton()
        self._update_btn.setObjectName("HeaderUpdateBtn")
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.setStyleSheet("""
            QPushButton#HeaderUpdateBtn {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 13px;
                padding: 4px 14px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#HeaderUpdateBtn:hover {
                background-color: #1D4ED8;
            }
        """)
        self._update_btn.setVisible(False)
        self._update_btn.clicked.connect(self.update_clicked.emit)
        right_box.addWidget(self._update_btn)

        root.addLayout(right_box)

        # Setup Live Timer for Clock
        self._update_clock()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # update every 1 second
        self._timer.timeout.connect(self._update_clock)
        self._timer.start()

    def _update_clock(self) -> None:
        """Update live clock text with formatted date and current 12-hour time."""
        now = datetime.now()
        # Example: Thu, 01 Oct 2026   |   01:30:15 AM
        date_part = now.strftime("%a, %d %b %Y")
        time_part = now.strftime("%I:%M:%S %p")
        self._clock_text.setText(f"{date_part}   |   {time_part}")

    def set_page_title(self, page_name: str) -> None:
        """Update page title and contextual subtitle dynamically."""
        self._title.setText(page_name)
        subtitle = PAGE_METADATA.get(page_name)
        if not subtitle:
            if "bill" in page_name.lower():
                subtitle = "Document details, print preview & payment record"
            elif "challan" in page_name.lower() or "gate pass" in page_name.lower():
                subtitle = "Delivery record, dispatch items & gate pass preview"
            elif "party" in page_name.lower():
                subtitle = "Party ledger, transaction history & contact overview"
            else:
                subtitle = "AG Printers Business Management"
        self._subtitle.setText(subtitle)

    def show_update_badge(self, version: str) -> None:
        """Display an eye-catching update notification button in the header."""
        self._update_btn.setText(f"🚀 Update {version}")
        self._update_btn.setVisible(True)

