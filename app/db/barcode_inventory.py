"""Database operations for Barcode Inventory.

Stores barcode raw materials and stock items (rolls, ribbons, labels) with:
- detail: Item name/specifications (e.g. 'Roll 50x25mm (1000 stickers)', 'Wax Ribbon 110mm')
- quantity: Current stock quantity
- rate: Unit cost/rate (Rs.)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class BarcodeInventoryItem:
    """A single stock record in Barcode Inventory."""

    id: int
    detail: str
    quantity: float
    rate: float
    created_at: str = ""
    updated_at: str = ""

    @property
    def total_value(self) -> float:
        """Total inventory value of this item (quantity * rate)."""
        return round(self.quantity * self.rate, 2)


def _row_to_item(row: sqlite3.Row) -> BarcodeInventoryItem:
    return BarcodeInventoryItem(
        id=int(row["id"]),
        detail=str(row["detail"]),
        quantity=float(row["quantity"] or 0.0),
        rate=float(row["rate"] or 0.0),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def list_barcode_inventory(
    connection: sqlite3.Connection, query: str = ""
) -> list[BarcodeInventoryItem]:
    """Retrieve barcode inventory items, optionally filtered by detail."""
    clean_query = query.strip()
    if clean_query:
        sql = """
            SELECT id, detail, quantity, rate, created_at, updated_at
            FROM barcode_inventory
            WHERE detail LIKE ?
            ORDER BY detail COLLATE NOCASE ASC
        """
        rows = connection.execute(sql, (f"%{clean_query}%",)).fetchall()
    else:
        sql = """
            SELECT id, detail, quantity, rate, created_at, updated_at
            FROM barcode_inventory
            ORDER BY id DESC
        """
        rows = connection.execute(sql).fetchall()

    return [_row_to_item(r) for r in rows]


def get_barcode_inventory_item(
    connection: sqlite3.Connection, item_id: int
) -> BarcodeInventoryItem | None:
    """Fetch a single barcode inventory item by ID."""
    sql = """
        SELECT id, detail, quantity, rate, created_at, updated_at
        FROM barcode_inventory
        WHERE id = ?
    """
    row = connection.execute(sql, (item_id,)).fetchone()
    return _row_to_item(row) if row else None


def record_barcode_inventory_in_log(
    connection: sqlite3.Connection,
    item_id: int,
    quantity: float,
    notes: str = "Stock Added",
) -> int:
    """Record an inward stock movement log."""
    clean_qty = max(0.0, float(quantity))
    if clean_qty <= 0:
        return 0
    sql = """
        INSERT INTO barcode_inventory_in_logs (inventory_item_id, quantity, notes, created_at)
        VALUES (?, ?, ?, datetime('now', 'localtime'))
    """
    cursor = connection.execute(sql, (int(item_id), clean_qty, (notes or "").strip()))
    connection.commit()
    return int(cursor.lastrowid)


def create_barcode_inventory_item(
    connection: sqlite3.Connection,
    detail: str,
    quantity: float,
    rate: float,
    notes: str = "Initial Stock",
) -> int:
    """Insert a new barcode inventory item and record initial stock in log if quantity > 0."""
    clean_qty = max(0.0, float(quantity))
    sql = """
        INSERT INTO barcode_inventory (detail, quantity, rate, created_at, updated_at)
        VALUES (?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
    """
    cursor = connection.execute(
        sql, (detail.strip(), clean_qty, max(0.0, float(rate)))
    )
    item_id = int(cursor.lastrowid)
    if clean_qty > 0:
        record_barcode_inventory_in_log(connection, item_id, clean_qty, notes=notes)
    connection.commit()
    return item_id


def update_barcode_inventory_item(
    connection: sqlite3.Connection, item_id: int, detail: str, quantity: float, rate: float
) -> None:
    """Update an existing barcode inventory item and log positive manual adjustments."""
    prev_item = get_barcode_inventory_item(connection, item_id)
    new_qty = max(0.0, float(quantity))
    sql = """
        UPDATE barcode_inventory
        SET detail = ?, quantity = ?, rate = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """
    connection.execute(sql, (detail.strip(), new_qty, max(0.0, float(rate)), item_id))
    if prev_item and new_qty > prev_item.quantity:
        diff = round(new_qty - prev_item.quantity, 2)
        record_barcode_inventory_in_log(connection, item_id, diff, notes="Stock Adjustment")
    connection.commit()


def delete_barcode_inventory_item(
    connection: sqlite3.Connection, item_id: int
) -> None:
    """Delete an item from barcode inventory."""
    connection.execute("DELETE FROM barcode_inventory WHERE id = ?", (item_id,))
    connection.commit()


def get_barcode_inventory_summary(connection: sqlite3.Connection) -> dict[str, float]:
    """Calculate summary statistics for barcode inventory."""
    sql = """
        SELECT
            COUNT(*) AS total_items,
            COALESCE(SUM(quantity), 0) AS total_qty,
            COALESCE(SUM(quantity * rate), 0) AS total_value
        FROM barcode_inventory
    """
    row = connection.execute(sql).fetchone()
    if row:
        return {
            "total_items": float(row["total_items"] or 0),
            "total_qty": float(row["total_qty"] or 0.0),
            "total_value": float(row["total_value"] or 0.0),
        }
    return {"total_items": 0.0, "total_qty": 0.0, "total_value": 0.0}


def deduct_barcode_inventory_stock(
    connection: sqlite3.Connection, item_id: int, quantity_to_deduct: float
) -> None:
    """Deduct stock quantity from a barcode inventory item when a job/bill is saved."""
    sql = """
        UPDATE barcode_inventory
        SET quantity = MAX(0.0, quantity - ?),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """
    connection.execute(sql, (max(0.0, float(quantity_to_deduct)), int(item_id)))
    connection.commit()


def add_barcode_inventory_stock(
    connection: sqlite3.Connection,
    item_id: int,
    quantity_to_add: float,
    notes: str = "Stock Added",
    record_log: bool = True,
) -> None:
    """Add stock quantity to an existing barcode inventory item and update updated_at."""
    clean_qty = max(0.0, float(quantity_to_add))
    if clean_qty <= 0:
        return
    sql = """
        UPDATE barcode_inventory
        SET quantity = quantity + ?,
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """
    connection.execute(sql, (clean_qty, int(item_id)))
    if record_log:
        record_barcode_inventory_in_log(connection, item_id, clean_qty, notes=notes)
    connection.commit()


def get_last_in_movement(
    connection: sqlite3.Connection, item_id: int
) -> dict[str, any] | None:
    """Get the most recent inward movement for an item."""
    sql = """
        SELECT quantity, created_at, notes
        FROM barcode_inventory_in_logs
        WHERE inventory_item_id = ? AND quantity > 0
        ORDER BY id DESC
        LIMIT 1
    """
    row = connection.execute(sql, (item_id,)).fetchone()
    if row:
        return {
            "quantity": float(row["quantity"] or 0.0),
            "created_at": str(row["created_at"]),
            "notes": str(row["notes"] or ""),
        }
    return None


def get_last_out_movement(
    connection: sqlite3.Connection, item_id: int
) -> dict[str, any] | None:
    """Get the most recent outward deduction movement for an item."""
    sql = """
        SELECT d.quantity, d.created_at,
               COALESCE(b.bill_number, '') AS bill_number,
               COALESCE(p.name, '') AS party_name
        FROM bill_inventory_deductions d
        LEFT JOIN bills b ON b.id = d.bill_id
        LEFT JOIN parties p ON p.id = b.party_id
        WHERE d.inventory_item_id = ? AND d.quantity > 0
        ORDER BY d.id DESC
        LIMIT 1
    """
    row = connection.execute(sql, (item_id,)).fetchone()
    if row:
        return {
            "quantity": float(row["quantity"] or 0.0),
            "created_at": str(row["created_at"]),
            "bill_number": str(row["bill_number"] or ""),
            "party_name": str(row["party_name"] or ""),
        }
    return None


def get_all_last_movements(
    connection: sqlite3.Connection,
) -> tuple[dict[int, dict], dict[int, dict]]:
    """Retrieve last IN and last OUT movements for all items in batch."""
    in_sql = """
        SELECT l.inventory_item_id, l.quantity, l.created_at, l.notes
        FROM barcode_inventory_in_logs l
        INNER JOIN (
            SELECT inventory_item_id, MAX(id) AS max_id
            FROM barcode_inventory_in_logs
            WHERE quantity > 0
            GROUP BY inventory_item_id
        ) latest ON l.id = latest.max_id
    """
    last_in: dict[int, dict] = {}
    try:
        for r in connection.execute(in_sql).fetchall():
            last_in[int(r["inventory_item_id"])] = {
                "quantity": float(r["quantity"] or 0.0),
                "created_at": str(r["created_at"]),
                "notes": str(r["notes"] or ""),
            }
    except Exception:
        pass

    out_sql = """
        SELECT d.inventory_item_id, d.quantity, d.created_at,
               COALESCE(b.bill_number, '') AS bill_number,
               COALESCE(p.name, '') AS party_name
        FROM bill_inventory_deductions d
        INNER JOIN (
            SELECT inventory_item_id, MAX(id) AS max_id
            FROM bill_inventory_deductions
            WHERE quantity > 0
            GROUP BY inventory_item_id
        ) latest ON d.id = latest.max_id
        LEFT JOIN bills b ON b.id = d.bill_id
        LEFT JOIN parties p ON p.id = b.party_id
    """
    last_out: dict[int, dict] = {}
    try:
        for r in connection.execute(out_sql).fetchall():
            last_out[int(r["inventory_item_id"])] = {
                "quantity": float(r["quantity"] or 0.0),
                "created_at": str(r["created_at"]),
                "bill_number": str(r["bill_number"] or ""),
                "party_name": str(r["party_name"] or ""),
            }
    except Exception:
        pass

    return last_in, last_out


def get_in_history(
    connection: sqlite3.Connection, item_id: int
) -> list[dict]:
    """Return all inward stock history records for an item."""
    sql = """
        SELECT id, inventory_item_id, quantity, notes, created_at
        FROM barcode_inventory_in_logs
        WHERE inventory_item_id = ? AND quantity > 0
        ORDER BY id DESC
    """
    try:
        rows = connection.execute(sql, (item_id,)).fetchall()
        return [
            {
                "id": int(r["id"]),
                "inventory_item_id": int(r["inventory_item_id"]),
                "quantity": float(r["quantity"] or 0.0),
                "notes": str(r["notes"] or ""),
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]
    except Exception:
        return []


def get_out_history(
    connection: sqlite3.Connection, item_id: int
) -> list[dict]:
    """Return all outward deduction history records for an item."""
    sql = """
        SELECT d.id, d.bill_id, d.inventory_item_id, d.quantity, d.created_at,
               COALESCE(b.bill_number, 'BILL-' || d.bill_id) AS bill_number,
               COALESCE(b.bill_date, date(d.created_at)) AS bill_date,
               COALESCE(p.name, 'Direct Sale') AS party_name
        FROM bill_inventory_deductions d
        LEFT JOIN bills b ON b.id = d.bill_id
        LEFT JOIN parties p ON p.id = b.party_id
        WHERE d.inventory_item_id = ? AND d.quantity > 0
        ORDER BY d.id DESC
    """
    try:
        rows = connection.execute(sql, (item_id,)).fetchall()
        return [
            {
                "id": int(r["id"]),
                "bill_id": int(r["bill_id"]),
                "inventory_item_id": int(r["inventory_item_id"]),
                "quantity": float(r["quantity"] or 0.0),
                "created_at": str(r["created_at"]),
                "bill_number": str(r["bill_number"]),
                "bill_date": str(r["bill_date"]),
                "party_name": str(r["party_name"]),
            }
            for r in rows
        ]
    except Exception:
        return []


def get_bill_inventory_deductions(
    connection: sqlite3.Connection, bill_id: int
) -> dict[int, float]:
    """Get a mapping of {inventory_item_id: quantity} currently deducted by this bill."""
    sql = """
        SELECT inventory_item_id, SUM(quantity) AS qty
        FROM bill_inventory_deductions
        WHERE bill_id = ?
        GROUP BY inventory_item_id
    """
    rows = connection.execute(sql, (bill_id,)).fetchall()
    return {int(r["inventory_item_id"]): float(r["qty"] or 0.0) for r in rows}


def record_bill_inventory_deductions(
    connection: sqlite3.Connection, bill_id: int, deductions: dict[int, float]
) -> None:
    """Replace the recorded inventory deductions for a bill with the new state."""
    connection.execute("DELETE FROM bill_inventory_deductions WHERE bill_id = ?", (bill_id,))
    for item_id, qty in deductions.items():
        if qty > 0:
            connection.execute(
                """
                INSERT INTO bill_inventory_deductions (bill_id, inventory_item_id, quantity)
                VALUES (?, ?, ?)
                """,
                (bill_id, int(item_id), float(qty)),
            )
    connection.commit()


def restore_bill_inventory_deductions(
    connection: sqlite3.Connection, bill_id: int
) -> None:
    """Refund any stock deducted by this bill back to barcode_inventory and delete the records."""
    deductions = get_bill_inventory_deductions(connection, bill_id)
    for item_id, qty in deductions.items():
        if qty > 0:
            add_barcode_inventory_stock(connection, item_id, qty)
    connection.execute("DELETE FROM bill_inventory_deductions WHERE bill_id = ?", (bill_id,))
    connection.commit()


