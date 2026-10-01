"""Repository helpers for Bills and their automatic Challan / Gate Pass (V0.6).

Specification reference (``AG_Printers_PROJECT_SPEC.md``):

* Step 5 - *Bill*: a bill is generated from the selected PO item(s) and holds
  bill number, date, party, PO number, items, quantity, rate and total. Bill
  numbers must be internally unique, and a party's external PO number is never
  used as an internal id.
* Step 6 - *Automatic Gate Pass / Challan*: "Every bill created should
  automatically generate its corresponding Gate Pass / Challan", one PO can
  have many bills, each bill has exactly one challan, and the two documents
  are separate but linked records.
* Section 5 - the chain Party -> PO -> PO items -> Bill -> Challan is kept
  with internal ids: ``bills.party_id``, ``bills.po_id`` and
  ``bill_items.po_item_id``. Item text is *not* duplicated - the description
  is read from the linked ``po_items`` row.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

#: Internal document numbers - sequential, unique, never typed by the user.
BILL_NUMBER_PREFIX = "BILL"
GATE_PASS_NUMBER_PREFIX = "CHALLAN"
NUMBER_WIDTH = 4


def format_bill_number(value: int) -> str:
    """Format an internal bill serial: ``1`` -> ``BILL-0001``."""
    return f"{BILL_NUMBER_PREFIX}-{value:0{NUMBER_WIDTH}d}"


def format_gate_pass_number(value: int) -> str:
    """Format an internal challan serial: ``1`` -> ``CHALLAN-0001``."""
    return f"{GATE_PASS_NUMBER_PREFIX}-{value:0{NUMBER_WIDTH}d}"


@dataclass(slots=True)
class BillItem:
    """One billed line: a real PO item or manual entry plus quantity and rate."""

    id: int
    bill_id: int
    po_item_id: int | None
    quantity: float
    rate: float
    description: str = ""
    po_id: int = 0
    cost_price: float = 0.0

    @property
    def amount(self) -> float:
        """Line value (quantity x rate)."""
        return self.quantity * self.rate

    @property
    def profit(self) -> float:
        """Line profit ((rate - cost_price) x quantity)."""
        return (self.rate - self.cost_price) * self.quantity


@dataclass(slots=True)
class GatePass:
    """The Challan / Gate Pass that belongs to exactly one bill."""

    id: int
    gate_pass_number: str
    gate_pass_date: str
    bill_id: int
    notes: str
    created_at: str
    updated_at: str
    bill_number: str = ""
    party_name: str = ""
    po_number: str = ""
    job_number: str = ""
    item_count: int = 0
    total_quantity: float = 0.0


@dataclass(slots=True)
class Bill:
    """A bill for one party and optional PO, linked to its challan."""

    id: int
    bill_number: str
    bill_date: str
    party_id: int
    po_id: int | None
    total_amount: float
    notes: str
    created_at: str
    updated_at: str
    party_name: str = ""
    po_number: str = ""
    job_number: str = ""
    production_cost: float = 0.0
    profit: float = 0.0
    items: list[BillItem] = field(default_factory=list)
    gate_pass: GatePass | None = None
    #: Number of billed lines; filled by the list query (items not loaded).
    items_count: int = 0
    #: Matching challan number, also filled by the list query.
    gate_pass_number_value: str = ""
    pdf_path: str = ""

    @property
    def item_count(self) -> int:
        """Number of billed lines (loaded items win over the count column)."""
        return len(self.items) or self.items_count

    @property
    def total_quantity(self) -> float:
        """Sum of the billed quantities."""
        return sum(item.quantity for item in self.items)

    @property
    def gate_pass_number(self) -> str:
        """Number of the matching challan ("" when it is missing)."""
        if self.gate_pass is not None:
            return self.gate_pass.gate_pass_number
        return self.gate_pass_number_value


# -- internal document numbers ---------------------------------------------


def _suggest_number(
    connection: sqlite3.Connection, table: str, column: str, prefix: str
) -> str:
    """Next free internal serial for *table* (highest existing + 1)."""
    highest = 0
    for row in connection.execute(f"SELECT {column} FROM {table}"):
        match = re.search(r"(\d+)$", row[column] or "")
        if match:
            highest = max(highest, int(match.group(1)))
    candidate = highest + 1
    while connection.execute(
        f"SELECT 1 FROM {table} WHERE {column} = ? COLLATE NOCASE",
        (f"{prefix}-{candidate:0{NUMBER_WIDTH}d}",),
    ).fetchone():
        candidate += 1
    return f"{prefix}-{candidate:0{NUMBER_WIDTH}d}"


def suggest_bill_number(connection: sqlite3.Connection) -> str:
    """Next free internal bill number, e.g. ``BILL-0001``."""
    return _suggest_number(connection, "bills", "bill_number", BILL_NUMBER_PREFIX)


def suggest_gate_pass_number(connection: sqlite3.Connection) -> str:
    """Next free internal challan number, e.g. ``CHALLAN-0001``."""
    return _suggest_number(
        connection, "gate_passes", "gate_pass_number", GATE_PASS_NUMBER_PREFIX
    )


# -- creating a bill together with its challan -----------------------------


def create_bill(
    connection: sqlite3.Connection,
    *,
    po_id: int | None = None,
    party_id: int | None = None,
    po_number: str = "",
    job_number: str = "",
    bill_number: str = "",
    gate_pass_number: str = "",
    bill_date: str,
    lines: Sequence[tuple | dict],
    production_cost: float = 0.0,
    profit: float = 0.0,
    notes: str = "",
    gate_pass_date: str = "",
    pdf_path: str = "",
) -> int:
    """Create a bill with its items AND its matching challan, return the id.

    Supports both:
    1) PO-linked lines: ``(po_item_id, rate)``
    2) Manual lines: ``(description, quantity, rate)`` or
       ``(po_item_id, description, quantity, rate)`` or dicts with keys:
       ``po_item_id``, ``description``, ``quantity``, ``rate``.
    """
    if not lines:
        raise ValueError("At least one bill item is required.")

    if party_id is None:
        if po_id is None:
            raise ValueError("Party is required to create a bill.")
        po_row = connection.execute(
            "SELECT party_id, po_number FROM purchase_orders WHERE id = ?", (po_id,)
        ).fetchone()
        if po_row is None:
            raise ValueError("The selected PO no longer exists.")
        party_id = int(po_row["party_id"])
        if not po_number:
            po_number = str(po_row["po_number"] or "")
    elif po_id is not None and not po_number:
        po_row = connection.execute(
            "SELECT po_number FROM purchase_orders WHERE id = ?", (po_id,)
        ).fetchone()
        if po_row is not None:
            po_number = str(po_row["po_number"] or "")

    prepared: list[tuple[int | None, str, float, float, float]] = []

    # Check if lines are legacy (po_item_id, rate)
    first = lines[0]
    if isinstance(first, tuple) and len(first) == 2:
        wanted = [int(item_id) for item_id, _rate in lines]
        placeholders = ", ".join("?" for _ in wanted)
        rows = {
            int(row["id"]): row
            for row in connection.execute(
                f"SELECT id, po_id, description, quantity FROM po_items WHERE id IN ({placeholders})",
                wanted,
            )
        }
        for item_id, rate in lines:
            row = rows.get(int(item_id))
            if row is None or (po_id is not None and int(row["po_id"]) != int(po_id)):
                raise ValueError(f"PO item {item_id} does not belong to this PO.")
            price = float(rate)
            if price < 0:
                raise ValueError("Bill rate cannot be negative.")
            prepared.append(
                (int(item_id), str(row["description"]), float(row["quantity"]), price, 0.0)
            )
    else:
        for item in lines:
            cost = 0.0
            if isinstance(item, dict):
                p_item_id = item.get("po_item_id")
                desc = str(item.get("description", "")).strip()
                qty = float(item.get("quantity", 0.0))
                rate = float(item.get("rate", 0.0))
                cost = float(item.get("cost_price", 0.0))
            elif isinstance(item, tuple):
                if len(item) == 3:
                    p_item_id = None
                    desc = str(item[0]).strip()
                    qty = float(item[1])
                    rate = float(item[2])
                    cost = 0.0
                elif len(item) == 4:
                    if isinstance(item[0], (int, type(None))) and isinstance(item[1], str):
                        p_item_id = item[0]
                        desc = str(item[1]).strip()
                        qty = float(item[2])
                        rate = float(item[3])
                        cost = 0.0
                    else:
                        p_item_id = None
                        desc = str(item[0]).strip()
                        qty = float(item[1])
                        rate = float(item[2])
                        cost = float(item[3])
                elif len(item) == 5:
                    p_item_id = item[0]
                    desc = str(item[1]).strip()
                    qty = float(item[2])
                    rate = float(item[3])
                    cost = float(item[4])
                else:
                    raise ValueError(f"Invalid line item format: {item}")
            else:
                raise ValueError(f"Invalid line item format: {item}")

            if not desc:
                raise ValueError("Item description cannot be empty.")
            if qty < 0:
                raise ValueError("Item quantity cannot be negative.")
            if rate < 0:
                raise ValueError("Item rate cannot be negative.")
            if cost < 0:
                cost = 0.0
            prepared.append((p_item_id, desc, qty, rate, cost))

    total = sum(quantity * price for _id, _desc, quantity, price, _cost in prepared)
    number = bill_number.strip() if bill_number.strip() else suggest_bill_number(connection)
    challan_num = (
        gate_pass_number.strip()
        if gate_pass_number.strip()
        else suggest_gate_pass_number(connection)
    )
    date = str(bill_date).strip()

    try:
        cursor = connection.execute(
            """
            INSERT INTO bills
                (bill_number, bill_date, party_id, po_id, po_number, job_number, total_amount, production_cost, profit, notes, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                number,
                date,
                party_id,
                po_id,
                str(po_number).strip(),
                str(job_number).strip(),
                total,
                float(production_cost or 0.0),
                float(profit or 0.0),
                str(notes).strip(),
                str(pdf_path).strip(),
            ),
        )
        bill_id = int(cursor.lastrowid)
        connection.executemany(
            "INSERT INTO bill_items (bill_id, po_item_id, description, quantity, rate, cost_price)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (bill_id, item_id, desc, quantity, price, cost)
                for item_id, desc, quantity, price, cost in prepared
            ],
        )
        connection.execute(
            "INSERT INTO gate_passes (gate_pass_number, gate_pass_date, bill_id)"
            " VALUES (?, ?, ?)",
            (challan_num, str(gate_pass_date).strip() or date, bill_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return bill_id


def update_bill_pdf_path(connection: sqlite3.Connection, bill_id: int, pdf_path: str) -> None:
    """Record or update the saved PDF file path for a bill."""
    connection.execute(
        "UPDATE bills SET pdf_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (str(pdf_path).strip(), bill_id),
    )
    connection.commit()


# -- reading ---------------------------------------------------------------

_BILL_SELECT = """
    SELECT b.id, b.bill_number, b.bill_date, b.party_id, b.po_id,
           COALESCE(b.job_number, '') AS job_number,
           b.total_amount,
           COALESCE(b.production_cost, 0) AS production_cost,
           COALESCE(b.profit, 0) AS profit,
           b.notes, b.created_at, b.updated_at,
           COALESCE(b.pdf_path, '') AS pdf_path,
           p.name AS party_name,
           COALESCE(NULLIF(b.po_number, ''), po.po_number, '') AS po_number,
           COUNT(bi.id) AS item_count,
           (SELECT g.gate_pass_number FROM gate_passes AS g
             WHERE g.bill_id = b.id) AS gate_pass_number
    FROM bills AS b
    JOIN parties AS p ON p.id = b.party_id
    LEFT JOIN purchase_orders AS po ON po.id = b.po_id
    LEFT JOIN bill_items AS bi ON bi.bill_id = b.id
"""

_GATE_PASS_SELECT = """
    SELECT g.id, g.gate_pass_number, g.gate_pass_date, g.bill_id, g.notes,
           g.created_at, g.updated_at,
           b.bill_number, p.name AS party_name,
           COALESCE(b.job_number, '') AS job_number,
           COALESCE(NULLIF(b.po_number, ''), po.po_number, '') AS po_number,
           (SELECT COUNT(*) FROM bill_items WHERE bill_id = b.id) AS item_count,
           (SELECT COALESCE(SUM(quantity), 0) FROM bill_items WHERE bill_id = b.id)
               AS total_quantity
    FROM gate_passes AS g
    JOIN bills AS b ON b.id = g.bill_id
    JOIN parties AS p ON p.id = b.party_id
    LEFT JOIN purchase_orders AS po ON po.id = b.po_id
"""


def _bill_from_row(row: sqlite3.Row) -> Bill:
    keys = row.keys()
    return Bill(
        id=row["id"],
        bill_number=row["bill_number"],
        bill_date=row["bill_date"],
        party_id=row["party_id"],
        po_id=row["po_id"],
        total_amount=float(row["total_amount"]),
        production_cost=float(row["production_cost"]) if "production_cost" in keys else 0.0,
        profit=float(row["profit"]) if "profit" in keys else 0.0,
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        party_name=row["party_name"],
        po_number=row["po_number"] or "",
        job_number=row["job_number"] if "job_number" in keys else "",
        items_count=int(row["item_count"]),
        gate_pass_number_value=(row["gate_pass_number"] or ""),
        pdf_path=row["pdf_path"] if "pdf_path" in keys else "",
    )


def _gate_pass_from_row(row: sqlite3.Row) -> GatePass:
    keys = row.keys()
    return GatePass(
        id=row["id"],
        gate_pass_number=row["gate_pass_number"],
        gate_pass_date=row["gate_pass_date"],
        bill_id=row["bill_id"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        bill_number=row["bill_number"],
        party_name=row["party_name"],
        po_number=row["po_number"] or "",
        job_number=row["job_number"] if "job_number" in keys else "",
        item_count=int(row["item_count"]) if "item_count" in keys else 0,
        total_quantity=(
            float(row["total_quantity"]) if "total_quantity" in keys else 0.0
        ),
    )


def list_bills(
    connection: sqlite3.Connection,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[Bill]:
    """Bills, newest first; *search* matches bill number, party, PO or challan number."""
    sql = _BILL_SELECT
    where_parts: list[str] = []
    params: list[object] = []
    term = search.strip()
    if term:
        like = f"%{term}%"
        where_parts.append(
            "(b.bill_number LIKE ? COLLATE NOCASE"
            " OR p.name LIKE ? COLLATE NOCASE"
            " OR COALESCE(NULLIF(b.po_number, ''), po.po_number, '') LIKE ? COLLATE NOCASE"
            " OR (SELECT g.gate_pass_number FROM gate_passes AS g WHERE g.bill_id = b.id) LIKE ? COLLATE NOCASE)"
        )
        params.extend([like, like, like, like])
    if date_from.strip():
        where_parts.append("b.bill_date >= ?")
        params.append(date_from.strip())
    if date_to.strip():
        where_parts.append("b.bill_date <= ?")
        params.append(date_to.strip())

    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    sql += " GROUP BY b.id ORDER BY b.id DESC"
    return [_bill_from_row(row) for row in connection.execute(sql, params)]



def list_gate_passes(
    connection: sqlite3.Connection, search: str = ""
) -> list[GatePass]:
    """Challans, newest first; *search* matches challan, bill, party or PO."""
    sql = _GATE_PASS_SELECT
    params: list[object] = []
    term = search.strip()
    if term:
        like = f"%{term}%"
        sql += (
            " WHERE g.gate_pass_number LIKE ? COLLATE NOCASE"
            " OR b.bill_number LIKE ? COLLATE NOCASE"
            " OR p.name LIKE ? COLLATE NOCASE"
            " OR COALESCE(NULLIF(b.po_number, ''), po.po_number, '') LIKE ? COLLATE NOCASE"
        )
        params = [like, like, like, like]
    sql += " ORDER BY g.id DESC"
    return [_gate_pass_from_row(row) for row in connection.execute(sql, params)]


def _load_bill_items(connection: sqlite3.Connection, bill_id: int) -> list[BillItem]:
    """Billed lines; description comes from bill_items or linked PO item."""
    return [
        BillItem(
            id=row["id"],
            bill_id=row["bill_id"],
            po_item_id=row["po_item_id"] if row["po_item_id"] is not None else None,
            quantity=float(row["quantity"]),
            rate=float(row["rate"]),
            description=row["description"] or "",
            po_id=row["po_id"] if row["po_id"] is not None else 0,
            cost_price=float(row["cost_price"]) if "cost_price" in row.keys() else 0.0,
        )
        for row in connection.execute(
            """
            SELECT bi.id, bi.bill_id, bi.po_item_id, bi.quantity, bi.rate,
                   COALESCE(bi.cost_price, 0) AS cost_price,
                   COALESCE(NULLIF(bi.description, ''), i.description, '') AS description,
                   COALESCE(i.po_id, 0) AS po_id
            FROM bill_items AS bi
            LEFT JOIN po_items AS i ON i.id = bi.po_item_id
            WHERE bi.bill_id = ?
            ORDER BY bi.id
            """,
            (bill_id,),
        )
    ]


def get_gate_pass_for_bill(
    connection: sqlite3.Connection, bill_id: int
) -> GatePass | None:
    """The matching challan of one bill, or None."""
    row = connection.execute(
        _GATE_PASS_SELECT + " WHERE g.bill_id = ?", (bill_id,)
    ).fetchone()
    return _gate_pass_from_row(row) if row is not None else None


def get_bill(connection: sqlite3.Connection, bill_id: int) -> Bill | None:
    """One bill with its items and its matching challan."""
    row = connection.execute(
        _BILL_SELECT + " WHERE b.id = ? GROUP BY b.id", (bill_id,)
    ).fetchone()
    if row is None:
        return None
    bill = _bill_from_row(row)
    bill.items = _load_bill_items(connection, bill.id)
    bill.gate_pass = get_gate_pass_for_bill(connection, bill.id)
    return bill


def get_gate_pass(
    connection: sqlite3.Connection, gate_pass_id: int
) -> GatePass | None:
    """One challan / gate pass, or None."""
    row = connection.execute(
        _GATE_PASS_SELECT + " WHERE g.id = ?", (gate_pass_id,)
    ).fetchone()
    return _gate_pass_from_row(row) if row is not None else None


# -- maintenance -----------------------------------------------------------


def delete_bill(connection: sqlite3.Connection, bill_id: int) -> bool:
    """Delete a bill; its challan and its bill items go with it."""
    if (
        connection.execute("SELECT 1 FROM bills WHERE id = ?", (bill_id,)).fetchone()
        is None
    ):
        return False
    connection.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
    connection.commit()
    return True


def delete_gate_pass(connection: sqlite3.Connection, gate_pass_id: int) -> bool:
    """Delete a gate pass record."""
    if (
        connection.execute("SELECT 1 FROM gate_passes WHERE id = ?", (gate_pass_id,)).fetchone()
        is None
    ):
        return False
    connection.execute("DELETE FROM gate_passes WHERE id = ?", (gate_pass_id,))
    connection.commit()
    return True


def po_has_bills(connection: sqlite3.Connection, po_id: int) -> int:
    """How many bills already exist for a PO (checked before deleting a PO)."""
    row = connection.execute(
        "SELECT COUNT(*) AS total FROM bills WHERE po_id = ?", (po_id,)
    ).fetchone()
    return int(row["total"] or 0)


def list_bills_for_po(connection: sqlite3.Connection, po_id: int) -> list[Bill]:
    """Bills of one PO, newest first, each with its matching challan number.

    Used by the PO list / details so the user can see which POs already have
    bills (and therefore challans) without leaving the Purchase Orders module.
    """
    sql = _BILL_SELECT + " WHERE b.po_id = ? GROUP BY b.id ORDER BY b.id DESC"
    bills = [_bill_from_row(row) for row in connection.execute(sql, (po_id,))]
    for bill in bills:
        bill.gate_pass = get_gate_pass_for_bill(connection, bill.id)
    return bills



