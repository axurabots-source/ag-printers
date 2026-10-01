"""Main application window: sidebar + header + content area."""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.bills.page import BillsPage
from app.challans.page import GatePassPage
from app.costing import CostingPage
from app.dashboard import DashboardPage
from app.inventory.page import InventoryPage
from app.jobs.page import NewJobPage
from app.ledger.page import LedgerPage
from app.parties.page import PartiesPage
from app.settings import SettingsPage, check_and_run_auto_backup
from app.ui.header import HeaderBar
from app.ui.placeholder import PlaceholderPage
from app.ui.sidebar import Sidebar
from app.updater import UpdateCheckerThread, UpdateDialog, UpdateInfo


class MainWindow(QMainWindow):
    """Top-level shell for AG Printers."""

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self.setWindowTitle("AG Printers")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)

        central = QWidget()
        central.setObjectName("Central")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = Sidebar()
        root.addWidget(self._sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._header = HeaderBar()
        right_layout.addWidget(self._header)

        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}
        for name in Sidebar.NAV_ITEMS:
            if name == "Dashboard":
                dash_page = DashboardPage(self._connection)
                dash_page.navigate_requested.connect(self._show_page)
                page: QWidget = dash_page
            elif name == "New Job":
                page = NewJobPage(self._connection)
                page.bill_saved.connect(self._on_job_bill_saved)
            elif name == "Parties":
                page = PartiesPage(self._connection)
                page.profile_opened.connect(self._on_profile_opened)
                page.profile_closed.connect(self._on_profile_closed)
            elif name in ("Invoices", "Bills"):
                page = BillsPage(self._connection)
                page.document_opened.connect(self._on_document_opened)
                page.list_shown.connect(self._on_bills_list_shown)
                page.new_requested.connect(lambda: self._show_page("New Job"))
            elif name == "Gate Pass":
                page = GatePassPage(self._connection)
                page.document_opened.connect(self._on_document_opened)
                page.list_shown.connect(self._on_gate_pass_list_shown)
            elif name == "Costing":
                page = CostingPage(self._connection)
                page.document_opened.connect(self._on_costing_opened)
                page.list_shown.connect(self._on_costing_list_shown)
            elif name == "Inventory":
                page = InventoryPage(self._connection)
            elif name == "Ledger":
                page = LedgerPage(self._connection)
            elif name == "Settings":
                settings_page = SettingsPage(self._connection)
                settings_page.data_reloaded.connect(self._on_data_reloaded)
                page = settings_page
            else:
                page = PlaceholderPage(name)
            self._stack.addWidget(page)
            self._pages[name] = page
        right_layout.addWidget(self._stack, 1)

        root.addWidget(right, 1)
        self.setCentralWidget(central)

        self._sidebar.page_selected.connect(self._show_page)
        self.statusBar().showMessage("Ready")

        # Automatic backup check on startup
        try:
            auto_zip = check_and_run_auto_backup(self._connection)
            if auto_zip:
                self.statusBar().showMessage(f"Daily auto-backup created: {auto_zip.name}", 5000)
        except Exception as e:
            print(f"Auto-backup warning: {e}")

        # Auto-update background check via GitHub Releases
        self._latest_update_info: UpdateInfo | None = None
        self._header.update_clicked.connect(self._on_header_update_clicked)
        self._update_checker = UpdateCheckerThread(parent=self)
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.start()

    def _on_update_available(self, info: UpdateInfo) -> None:
        self._latest_update_info = info
        self._header.show_update_badge(info.version)
        self.statusBar().showMessage(f"Update {info.version} is available! Click update in header to review.", 8000)

    def _on_header_update_clicked(self) -> None:
        if self._latest_update_info is not None:
            dlg = UpdateDialog(self._connection, self._latest_update_info, parent=self)
            dlg.exec()

    def _show_page(self, page_name: str) -> None:
        """Switch the content stack to the selected module page."""
        page = self._pages.get(page_name)
        if page is None:
            return
        if isinstance(
            page, (DashboardPage, NewJobPage, PartiesPage, BillsPage, GatePassPage, CostingPage, LedgerPage, InventoryPage, SettingsPage)
        ):
            page.reset_to_list()
        self._stack.setCurrentWidget(page)
        self._sidebar.set_active_page(page_name)
        self._header.set_page_title(page_name)
        self.statusBar().showMessage(page_name)

    def _on_data_reloaded(self) -> None:
        """Called when database data is restored or cleared, refreshing all pages."""
        for p in self._pages.values():
            if hasattr(p, "reset_to_list"):
                try:
                    p.reset_to_list()
                except Exception:
                    pass
            elif hasattr(p, "refresh"):
                try:
                    p.refresh()
                except Exception:
                    pass
        self.statusBar().showMessage("Database and application data reloaded", 4000)

    def _on_job_bill_saved(self, bill_id: int) -> None:
        """Status note when a bill & challan are saved from New Job workspace."""
        self.statusBar().showMessage(f"Job saved successfully as Invoice #{bill_id}")

    def _on_profile_opened(self, party_name: str) -> None:
        """Header/status update when a party profile is shown."""
        self._header.set_page_title("Party Profile")
        self.statusBar().showMessage(f"Party: {party_name}")

    def _on_profile_closed(self) -> None:
        """Header/status update when returning to the parties list."""
        self._header.set_page_title("Parties")
        self.statusBar().showMessage("Parties")

    def _on_document_opened(self, number: str) -> None:
        """Status note when an invoice or gate pass document is shown."""
        self.statusBar().showMessage(f"Document: {number}")

    def _on_bills_list_shown(self) -> None:
        """Header/status update when the invoices list is shown."""
        self._header.set_page_title("Invoices")
        self.statusBar().showMessage("Invoices")

    def _on_gate_pass_list_shown(self) -> None:
        """Header/status update when the challan list is shown."""
        self._header.set_page_title("Gate Pass")
        self.statusBar().showMessage("Gate Pass")

    def _on_costing_opened(self, description: str) -> None:
        """Status note when a costing sheet is shown (V0.7)."""
        self._header.set_page_title("Costing")
        self.statusBar().showMessage(f"Costing: {description}")

    def _on_costing_list_shown(self) -> None:
        """Header/status update when the costings list is shown."""
        self._header.set_page_title("Costing")
        self.statusBar().showMessage("Costing")
