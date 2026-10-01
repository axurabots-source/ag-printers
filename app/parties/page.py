"""Parties page: container switching between list and profile views."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from app.db.parties import delete_party, get_party, set_party_active
from app.parties.dialog import PartyDialog
from app.parties.list_view import PartiesListView
from app.parties.profile_view import PartyProfileView


class PartiesPage(QWidget):
    """Parties module root: searchable list <-> party profile."""

    #: Emitted with the party name when a profile is shown (header title).
    profile_opened = Signal(str)
    #: Emitted when the view returns to the parties list.
    profile_closed = Signal()

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._list = PartiesListView(connection)
        self._profile = PartyProfileView()
        self._stack.addWidget(self._list)  # index 0 = list
        self._stack.addWidget(self._profile)  # index 1 = profile
        layout.addWidget(self._stack)

        self._list.open_party.connect(self.open_profile)
        self._list.add_requested.connect(lambda: self._open_dialog(None))
        self._profile.back_requested.connect(self.reset_to_list)
        self._profile.edit_requested.connect(
            lambda party_id: self._open_dialog(party_id)
        )
        self._profile.toggle_requested.connect(self._toggle_active)
        self._profile.delete_requested.connect(self._delete_party)

    # -- public API (used by MainWindow) -------------------------------

    def reset_to_list(self) -> None:
        """Show and refresh the parties list (closes any open profile)."""
        self._list.refresh()
        self._stack.setCurrentIndex(0)
        self.profile_closed.emit()

    def open_profile(self, party_id: int) -> None:
        """Show the profile for *party_id* (falls back to the list)."""
        party = get_party(self._connection, party_id)
        if party is None:
            self.reset_to_list()
            return
        self._profile.set_party(party)
        self._stack.setCurrentIndex(1)
        self.profile_opened.emit(party.name)

    # -- internals -----------------------------------------------------

    def _open_dialog(self, party_id: int | None) -> None:
        """Open the add dialog (party_id None) or edit dialog for a party."""
        party = get_party(self._connection, party_id) if party_id else None
        dialog = PartyDialog(self._connection, party=party, parent=self.window())
        if dialog.exec() and dialog.saved_party_id is not None:
            self._list.refresh()
            self.open_profile(dialog.saved_party_id)

    def _toggle_active(self, party_id: int) -> None:
        """Activate / deactivate the party shown in the profile."""
        party = get_party(self._connection, party_id)
        if party is None:
            self.reset_to_list()
            return
        set_party_active(self._connection, party_id, not party.is_active)
        self._list.refresh()
        self.open_profile(party_id)

    def _delete_party(self, party_id: int) -> None:
        """Delete the party currently shown in the profile view."""
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
        self.reset_to_list()

