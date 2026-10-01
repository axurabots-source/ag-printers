"""Add / Edit party dialog used by the Parties module."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.db.parties import Party, create_party, party_name_exists, update_party


class PartyDialog(QDialog):
    """Form to create a new party or edit an existing one."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        party: Party | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._connection = connection
        self._party = party
        #: Id of the party saved on accept (None when cancelled).
        self.saved_party_id: int | None = None

        self.setObjectName("PartyDialog")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Edit Party" if party else "Add Party")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(16)

        def make_label(text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("FieldLabel")
            return label

        from app.ui.capitalized_input import enable_auto_capitalization

        def make_input(placeholder: str = "", auto_cap: bool = False) -> QLineEdit:
            field = QLineEdit()
            field.setObjectName("FormInput")
            field.setPlaceholderText(placeholder)
            if auto_cap:
                enable_auto_capitalization(field)
            return field

        self._name = make_input("Required", auto_cap=True)
        self._contact = make_input(auto_cap=True)
        self._phone = make_input("+91 98765 43210")
        self._email = make_input("name@example.com")
        self._address = QPlainTextEdit()
        self._address.setObjectName("FormInput")
        self._address.setFixedHeight(64)
        enable_auto_capitalization(self._address)
        self._notes = QPlainTextEdit()
        self._notes.setObjectName("FormInput")
        self._notes.setFixedHeight(64)
        enable_auto_capitalization(self._notes)
        self._active = QCheckBox("Active")

        form.addRow(make_label("Party Name *"), self._name)
        form.addRow(make_label("Contact Person"), self._contact)
        form.addRow(make_label("Phone"), self._phone)
        form.addRow(make_label("Email"), self._email)
        form.addRow(make_label("Address"), self._address)
        form.addRow(make_label("Notes"), self._notes)
        form.addRow(make_label("Status"), self._active)
        layout.addLayout(form)

        if party is not None:
            self.setWindowTitle("Edit Party")
            self._name.setText(party.name)
            self._contact.setText(party.contact_person)
            self._phone.setText(party.phone)
            self._email.setText(party.email)
            self._address.setPlainText(party.address)
            self._notes.setPlainText(party.notes)
            self._active.setChecked(party.is_active)
        else:
            self.setWindowTitle("Add Party")
            self._active.setChecked(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("OutlineButton")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Party")
        save.setObjectName("PrimaryButton")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        self._name.setFocus()

    # -- saving --------------------------------------------------------

    def _save(self) -> None:
        """Validate the form, persist the party and accept the dialog."""
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Party name is required.")
            self._name.setFocus()
            return

        exclude_id = self._party.id if self._party else None
        if party_name_exists(self._connection, name, exclude_id):
            QMessageBox.warning(
                self,
                "Duplicate party",
                f"A party named \"{name}\" already exists.",
            )
            self._name.setFocus()
            return

        email = self._email.text().strip()
        if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
            QMessageBox.warning(
                self,
                "Invalid email",
                "Enter a valid email address or leave the field empty.",
            )
            self._email.setFocus()
            return

        values = dict(
            name=name,
            contact_person=self._contact.text().strip(),
            phone=self._phone.text().strip(),
            email=email,
            address=self._address.toPlainText().strip(),
            notes=self._notes.toPlainText().strip(),
            is_active=self._active.isChecked(),
        )
        if self._party is None:
            self.saved_party_id = create_party(self._connection, **values)
        else:
            update_party(self._connection, self._party.id, **values)
            self.saved_party_id = self._party.id
        self.accept()
