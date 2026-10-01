"""Costings list view and page container for the modern visual Costing module."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.costing.editor import CostingEditor
from app.db.costing import (
    Costing,
    delete_costing,
    get_costing,
    list_costings,
)

_COLUMNS = (
    "Item Description",
    "Party",
    "Quantity",
    "General (Rs.)",
    "Barcode (Rs.)",
    "Sampling (Rs.)",
    "Total Cost (Rs.)",
    "Per Unit (Rs.)",
    "Date",
)


class CostingsListView(QWidget):
    """Search toolbar and data table of saved costing sheets."""

    new_requested = Signal()
    open_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._rows: list[Costing] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self._search = QLineEdit()
        self._search.setObjectName("SearchBox")
        self._search.setPlaceholderText("Search by item name or party...")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(260)
        self._search.textChanged.connect(self.refresh)
        toolbar.addWidget(self._search, 1)

        self._delete_button = QPushButton("Delete")
        self._delete_button.setObjectName("DangerButton")
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._emit_delete)
        toolbar.addWidget(self._delete_button)

        self._open_button = QPushButton("Open Costing")
        self._open_button.setObjectName("OutlineButton")
        self._open_button.setEnabled(False)
        self._open_button.clicked.connect(self._emit_open)
        toolbar.addWidget(self._open_button)

        self._new_button = QPushButton("+ New Costing")
        self._new_button.setObjectName("PrimaryButton")
        self._new_button.setStyleSheet("""
            QPushButton#PrimaryButton {
                background-color: #059669;
                color: #FFFFFF;
                font-weight: 700;
                padding: 7px 18px;
                border-radius: 6px;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #047857;
            }
        """)
        self._new_button.clicked.connect(self.new_requested.emit)
        toolbar.addWidget(self._new_button)

        layout.addLayout(toolbar)

        # Table
        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setObjectName("POTable")
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(46)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(2, len(_COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._sync_buttons)
        self._table.activated.connect(lambda _index: self._emit_open())

        self._empty = QLabel("No costing sheets recorded yet. Click '+ New Costing' to create one.")
        self._empty.setObjectName("EmptyState")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #6B7280; font-size: 11pt; padding: 40px;")
        self._empty.setVisible(False)

        layout.addWidget(self._table, 1)
        layout.addWidget(self._empty, 1)
        self.refresh()

    def refresh(self, search: str = "") -> None:
        """Reload the costings list from database."""
        term = search if search else self._search.text()
        self._rows = list_costings(self._connection, term)
        self._table.setRowCount(len(self._rows))
        for row, costing in enumerate(self._rows):
            values = (
                costing.item_name or costing.description,
                costing.party_name,
                f"{costing.quantity:,.0f}",
                f"{costing.general_total:,.2f}",
                f"{costing.barcode_total:,.2f}",
                f"{costing.sampling_total:,.2f}",
                f"{costing.total_cost:,.2f}",
                f"{costing.per_unit_cost:,.2f}",
                (costing.created_at or "")[:10],
            )
            for column, text in enumerate(values):
                cell = QTableWidgetItem(text)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, costing.id)
                if column >= 2:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(row, column, cell)

        has_rows = bool(self._rows)
        self._table.setVisible(has_rows)
        self._empty.setVisible(not has_rows)
        self._sync_buttons()

    def selected_costing_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return int(value) if value is not None else None

    def _sync_buttons(self) -> None:
        enabled = self.selected_costing_id() is not None
        self._open_button.setEnabled(enabled)
        self._delete_button.setEnabled(enabled)

    def _emit_open(self) -> None:
        cid = self.selected_costing_id()
        if cid is not None:
            self.open_requested.emit(cid)

    def _emit_delete(self) -> None:
        cid = self.selected_costing_id()
        if cid is not None:
            self.delete_requested.emit(cid)


class CostingPage(QWidget):
    """Costing module container: switches between list view and visual editor."""

    document_opened = Signal(str)
    list_shown = Signal()

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._list = CostingsListView(connection)
        self._editor = CostingEditor(connection)
        self._stack.addWidget(self._list)    # index 0 = list
        self._stack.addWidget(self._editor)  # index 1 = costing sheet
        layout.addWidget(self._stack)

        self._list.new_requested.connect(self.new_costing)
        self._list.open_requested.connect(self.open_costing)
        self._list.delete_requested.connect(self._delete_costing)
        self._editor.saved.connect(self._on_saved)
        self._editor.cancel_requested.connect(self.reset_to_list)

    def reset_to_list(self) -> None:
        """Show and refresh the costings list."""
        self._list.refresh()
        self._stack.setCurrentIndex(0)
        self.list_shown.emit()

    def new_costing(self) -> None:
        """Open a fresh costing calculation sheet."""
        self._editor.reset_form()
        self._stack.setCurrentIndex(1)
        self.document_opened.emit("New Costing Sheet")

    def open_costing(self, costing_id: int) -> bool:
        """Open an existing costing sheet for editing."""
        if not self._editor.load_costing_by_id(costing_id):
            return False
        self._stack.setCurrentIndex(1)
        self.document_opened.emit(f"Costing #{costing_id}")
        return True

    def _on_saved(self, costing_id: int) -> None:
        """After saving, refresh list and return to list view."""
        self.reset_to_list()

    def _delete_costing(self, costing_id: int) -> None:
        """Confirm and delete a saved costing sheet."""
        costing = get_costing(self._connection, costing_id)
        if costing is None:
            self.reset_to_list()
            return

        answer = QMessageBox.question(
            self,
            "Delete Costing",
            f"Delete the costing sheet for '{costing.item_name or costing.description}' ({costing.party_name})?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        delete_costing(self._connection, costing_id)
        self.reset_to_list()
