"""Searchable list of parties (search, add, open profile, delete)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.parties import Party, delete_party, get_party, list_parties
from app.ui.theme import GREEN, TEXT_MUTED


def _format_datetime(val: str | None) -> str:
    """Format an ISO/SQLite timestamp into a clean, human-readable date and time."""
    if not val:
        return "-"
    try:
        clean = str(val).strip().replace("T", " ")
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(val)


DELETE_BUTTON_STYLE = """
QPushButton#DeleteButton {
    background-color: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 8px;
    color: #DC2626;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
}
QPushButton#DeleteButton:hover {
    background-color: #FEE2E2;
    border: 1px solid #F87171;
    color: #B91C1C;
}
QPushButton#DeleteButton:disabled {
    background-color: #F9FAFB;
    color: #9CA3AF;
    border: 1px solid #E5E7EB;
}
"""

PARTY_TABLE_STYLE = """
QTableWidget#PartyTable {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    color: #0F172A;
    font-size: 13px;
    outline: none;
}
QTableWidget#PartyTable::item {
    padding: 6px 12px;
    border: none;
    outline: none;
}
QTableWidget#PartyTable::item:focus {
    border: none;
    outline: none;
}
QTableWidget#PartyTable::item:selected {
    background-color: #E6EEFB;
    color: #0F172A;
    border: none;
    outline: none;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #64748B;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 12px;
}
"""


class PartiesListView(QWidget):
    """Toolbar (search + actions) above a table of parties."""

    #: Emitted when the user opens a party's profile.
    open_party = Signal(int)
    #: Emitted when the user clicks "Add Party".
    add_requested = Signal()

    _COLUMNS = ("Name", "Contact Person", "Phone", "Status", "Date & Time")

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._rows: list[Party] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Toolbar -------------------------------------------------------
        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText(
            "Search parties by name, contact, phone or email..."
        )
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(280)

        self._view_button = QPushButton("View Profile")
        self._view_button.setObjectName("OutlineButton")
        self._view_button.setEnabled(False)
        self._view_button.clicked.connect(self._open_selected)

        self._delete_button = QPushButton("Delete Party")
        self._delete_button.setObjectName("DeleteButton")
        self._delete_button.setStyleSheet(DELETE_BUTTON_STYLE)
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._delete_selected)

        add_button = QPushButton("+ Add Party")
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self.add_requested.emit)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self._search, 1)
        toolbar.addWidget(self._view_button)
        toolbar.addWidget(self._delete_button)
        toolbar.addWidget(add_button)
        layout.addLayout(toolbar)

        # Table ---------------------------------------------------------
        self._table = QTableWidget(0, len(self._COLUMNS))
        self._table.setObjectName("PartyTable")
        self._table.setStyleSheet(PARTY_TABLE_STYLE)
        self._table.setHorizontalHeaderLabels(self._COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(46)

        header = self._table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(3, 110)
        self._table.setColumnWidth(4, 190)

        self._search.textChanged.connect(self.refresh)
        self._table.itemSelectionChanged.connect(self._sync_selection)
        # Double-click or Enter opens profile
        self._table.cellDoubleClicked.connect(lambda _r, _c: self._open_selected())
        self._table.activated.connect(lambda _index: self._open_selected())

        # Right-click context menu
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        self._empty = QLabel("No parties found. Add your first party to get started.")
        self._empty.setObjectName("EmptyState")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)

        layout.addWidget(self._table, 1)
        layout.addWidget(self._empty, 1)

        self.refresh()

    # -- data ----------------------------------------------------------

    def refresh(self, _search_text: str | None = None) -> None:
        """Reload parties from the database using the current search text."""
        self._rows = list_parties(self._connection, self._search.text())
        selected_id = self.selected_party_id()
        self._table.setRowCount(0)

        bold = QFont()
        bold.setBold(True)
        for party in self._rows:
            row = self._table.rowCount()
            self._table.insertRow(row)

            name_item = QTableWidgetItem(party.name)
            name_item.setData(Qt.ItemDataRole.UserRole, party.id)
            name_item.setFont(bold)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, name_item)

            contact_item = QTableWidgetItem(party.contact_person or "-")
            contact_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 1, contact_item)

            phone_item = QTableWidgetItem(party.phone or "-")
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, phone_item)

            if party.is_active:
                status = QTableWidgetItem("Active")
                status.setForeground(QColor(GREEN))
            else:
                status = QTableWidgetItem("Inactive")
                status.setForeground(QColor(TEXT_MUTED))
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 3, status)

            dt_item = QTableWidgetItem(_format_datetime(party.updated_at))
            dt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 4, dt_item)

        has_rows = bool(self._rows)
        self._table.setVisible(has_rows)
        self._empty.setVisible(not has_rows)

        # Keep the same row selected after a refresh when possible.
        if selected_id is not None:
            for row in range(self._table.rowCount()):
                item = self._table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self._table.selectRow(row)
                    break
        self._sync_selection()

    def selected_party_id(self) -> int | None:
        """Id of the highlighted party row (None when nothing is selected)."""
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # -- internals -----------------------------------------------------

    def _sync_selection(self) -> None:
        has_sel = self.selected_party_id() is not None
        self._view_button.setEnabled(has_sel)
        self._delete_button.setEnabled(has_sel)

    def _open_selected(self) -> None:
        party_id = self.selected_party_id()
        if party_id is not None:
            self.open_party.emit(party_id)

    def _delete_selected(self) -> None:
        party_id = self.selected_party_id()
        if party_id is None:
            return

        party = get_party(self._connection, party_id)
        party_name = party.name if party else f"Party #{party_id}"

        reply = QMessageBox.question(
            self,
            "Delete Party",
            f"Are you sure you want to delete '{party_name}'?\n\nThis will remove the party from the system.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, error_msg = delete_party(self._connection, party_id)
        if not ok:
            QMessageBox.warning(
                self,
                "Cannot Delete Party",
                error_msg,
                QMessageBox.StandardButton.Ok,
            )
            return

        QMessageBox.information(
            self,
            "Party Deleted",
            f"Party '{party_name}' was successfully deleted.",
            QMessageBox.StandardButton.Ok,
        )
        self.refresh()

    def _show_context_menu(self, pos) -> None:
        party_id = self.selected_party_id()
        if party_id is None:
            return
        menu = QMenu(self)
        view_action = menu.addAction("View Profile")
        view_action.triggered.connect(self._open_selected)
        menu.addSeparator()
        delete_action = menu.addAction("Delete Party")
        delete_action.triggered.connect(self._delete_selected)
        menu.exec(self._table.viewport().mapToGlobal(pos))