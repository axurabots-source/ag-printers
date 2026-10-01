"""Party profile (details) view with Edit / Activate / Delete / Back actions."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.db.parties import Party


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
"""


class PartyProfileView(QWidget):
    """Read-only party profile card with actions."""

    #: Emitted when the user wants to go back to the parties list.
    back_requested = Signal()
    #: Emitted with the party id when Edit Party is clicked.
    edit_requested = Signal(int)
    #: Emitted with the party id when Activate/Deactivate is clicked.
    toggle_requested = Signal(int)
    #: Emitted with the party id when Delete Party is clicked.
    delete_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._party: Party | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 24)
        outer.setSpacing(14)

        # Action row ----------------------------------------------------
        back = QPushButton("< Back to Parties")
        back.setObjectName("OutlineButton")
        back.clicked.connect(self.back_requested.emit)

        self._toggle = QPushButton("Deactivate")
        self._toggle.setObjectName("OutlineButton")
        self._toggle.clicked.connect(self._emit_toggle)

        delete_btn = QPushButton("Delete Party")
        delete_btn.setObjectName("DeleteButton")
        delete_btn.setStyleSheet(DELETE_BUTTON_STYLE)
        delete_btn.clicked.connect(self._emit_delete)

        edit = QPushButton("Edit Party")
        edit.setObjectName("PrimaryButton")
        edit.clicked.connect(self._emit_edit)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(back)
        actions.addStretch(1)
        actions.addWidget(delete_btn)
        actions.addWidget(self._toggle)
        actions.addWidget(edit)
        outer.addLayout(actions)

        # Scrollable profile card ---------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("ProfileCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 28)
        card_layout.setSpacing(20)

        # Header: party name + status pill
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        self._name = QLabel()
        self._name.setObjectName("ProfileName")
        self._status = QLabel()
        self._status.setObjectName("StatusPill")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(self._name)
        header_row.addWidget(self._status)
        header_row.addStretch(1)
        card_layout.addLayout(header_row)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        card_layout.addWidget(divider)

        # Details grid
        form = QVBoxLayout()
        form.setSpacing(16)
        card_layout.addLayout(form)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._fields: dict[str, QLabel] = {}

        def add_field(key: str, row: int, column: int, span: int = 1) -> None:
            label = QLabel(key)
            label.setObjectName("FieldLabel")
            value = QLabel("-")
            value.setObjectName("FieldValue")
            value.setWordWrap(True)
            self._fields[key] = value
            grid.addWidget(label, row, column, 1, span)
            grid.addWidget(value, row + 1, column, 1, span)

        add_field("Contact Person", 0, 0)
        add_field("Phone", 0, 1)
        add_field("Email", 2, 0, 2)
        add_field("Address", 4, 0, 2)
        add_field("Notes", 6, 0, 2)
        add_field("Created", 8, 0)
        add_field("Updated", 8, 1)
        form.addLayout(grid)
        form.addStretch(1)

        body_layout.addWidget(card)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # -- data ----------------------------------------------------------

    def set_party(self, party: Party) -> None:
        """Populate the profile with the given party."""
        self._party = party
        self._name.setText(party.name)
        self._status.setText("Active" if party.is_active else "Inactive")
        self._status.setProperty("active", party.is_active)
        # Re-run styling so the dynamic [active] property takes effect.
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._toggle.setText("Deactivate" if party.is_active else "Activate")

        values = {
            "Contact Person": party.contact_person,
            "Phone": party.phone,
            "Email": party.email,
            "Address": party.address,
            "Notes": party.notes,
            "Created": _format_datetime(party.created_at),
            "Updated": _format_datetime(party.updated_at),
        }
        for key, label in self._fields.items():
            text = values.get(key, "")
            label.setText(text if text else "-")

    # -- internals -----------------------------------------------------

    def _emit_edit(self) -> None:
        if self._party is not None:
            self.edit_requested.emit(self._party.id)

    def _emit_toggle(self) -> None:
        if self._party is not None:
            self.toggle_requested.emit(self._party.id)

    def _emit_delete(self) -> None:
        if self._party is not None:
            self.delete_requested.emit(self._party.id)
