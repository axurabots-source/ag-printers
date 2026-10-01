"""Repository helpers for the Parties module (V0.3)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class Party:
    """One business party (customer / supplier) record."""

    id: int
    name: str
    contact_person: str
    phone: str
    email: str
    address: str
    notes: str
    is_active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Party":
        """Build a Party from a database row."""
        return cls(
            id=row["id"],
            name=row["name"],
            contact_person=row["contact_person"],
            phone=row["phone"],
            email=row["email"],
            address=row["address"],
            notes=row["notes"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def list_parties(connection: sqlite3.Connection, search: str = "") -> list[Party]:
    """Return parties matching *search* (name/contact/phone/email).

    Active parties sort first, then alphabetically by name.
    """
    sql = "SELECT * FROM parties"
    params: list[object] = []
    term = search.strip()
    if term:
        sql += (
            " WHERE name LIKE ? COLLATE NOCASE"
            " OR contact_person LIKE ? COLLATE NOCASE"
            " OR phone LIKE ? COLLATE NOCASE"
            " OR email LIKE ? COLLATE NOCASE"
        )
        like = f"%{term}%"
        params = [like, like, like, like]
    sql += " ORDER BY is_active DESC, name COLLATE NOCASE ASC"
    rows = connection.execute(sql, params).fetchall()
    return [Party.from_row(row) for row in rows]


def get_party(connection: sqlite3.Connection, party_id: int) -> Party | None:
    """Return one party by id, or None when it does not exist."""
    row = connection.execute(
        "SELECT * FROM parties WHERE id = ?", (party_id,)
    ).fetchone()
    return Party.from_row(row) if row else None


def party_name_exists(
    connection: sqlite3.Connection, name: str, exclude_id: int | None = None
) -> bool:
    """True when another party already uses *name* (case-insensitive)."""
    sql = "SELECT 1 FROM parties WHERE name = ? COLLATE NOCASE"
    params: list[object] = [name.strip()]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    return connection.execute(sql, params).fetchone() is not None


def create_party(
    connection: sqlite3.Connection,
    *,
    name: str,
    contact_person: str = "",
    phone: str = "",
    email: str = "",
    address: str = "",
    notes: str = "",
    is_active: bool = True,
) -> int:
    """Insert a new party and return its id."""
    cursor = connection.execute(
        """
        INSERT INTO parties
            (name, contact_person, phone, email, address, notes, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip(),
            contact_person.strip(),
            phone.strip(),
            email.strip(),
            address.strip(),
            notes.strip(),
            1 if is_active else 0,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_party(
    connection: sqlite3.Connection,
    party_id: int,
    *,
    name: str,
    contact_person: str,
    phone: str,
    email: str,
    address: str,
    notes: str,
    is_active: bool,
) -> None:
    """Update an existing party and bump its updated_at timestamp."""
    connection.execute(
        """
        UPDATE parties
        SET name = ?, contact_person = ?, phone = ?, email = ?,
            address = ?, notes = ?, is_active = ?,
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
        """,
        (
            name.strip(),
            contact_person.strip(),
            phone.strip(),
            email.strip(),
            address.strip(),
            notes.strip(),
            1 if is_active else 0,
            party_id,
        ),
    )
    connection.commit()


def set_party_active(
    connection: sqlite3.Connection, party_id: int, active: bool
) -> None:
    """Activate or deactivate a party (bumps updated_at)."""
    connection.execute(
        "UPDATE parties SET is_active = ?, updated_at = datetime('now', 'localtime')"
        " WHERE id = ?",
        (1 if active else 0, party_id),
    )
    connection.commit()


def delete_party(connection: sqlite3.Connection, party_id: int) -> tuple[bool, str]:
    """Delete a party if no purchase orders, bills, or costing records are linked.

    Returns (True, "") on success, or (False, reason) if it cannot be deleted.
    """
    reasons = []

    cur = connection.execute(
        "SELECT COUNT(*) FROM bills WHERE party_id = ?", (party_id,)
    )
    bill_count = cur.fetchone()[0]
    if bill_count > 0:
        reasons.append(f"{bill_count} Bill(s)")

    cur = connection.execute(
        "SELECT COUNT(*) FROM purchase_orders WHERE party_id = ?", (party_id,)
    )
    po_count = cur.fetchone()[0]
    if po_count > 0:
        reasons.append(f"{po_count} Purchase Order(s)")

    cur = connection.execute(
        "SELECT COUNT(*) FROM costing WHERE party_id = ?", (party_id,)
    )
    costing_count = cur.fetchone()[0]
    if costing_count > 0:
        reasons.append(f"{costing_count} Costing record(s)")

    if reasons:
        return False, f"Cannot delete party because it is linked to: {', '.join(reasons)}."

    connection.execute("DELETE FROM party_rates WHERE party_id = ?", (party_id,))
    connection.execute("DELETE FROM parties WHERE id = ?", (party_id,))
    connection.commit()
    return True, ""

