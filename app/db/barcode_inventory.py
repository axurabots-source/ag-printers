"""Database operations for Barcode Inventory.

Stores barcode raw materials and stock items (rolls, ribbons, labels) with:
- detail: Item name/specifications (e.g. 'Roll 50x25mm (1000 stickers)', 'Wax Ribbon 110mm')
- quantity: Current stock quantity
- rate: Unit cost/rate (Rs.)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


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


def create_barcode_inventory_item(
    connection: sqlite3.Connection, detail: str, quantity: float, rate: float
) -> int:
    """Insert a new barcode inventory item."""
    sql = """
        INSERT INTO barcode_inventory (detail, quantity, rate)
        VALUES (?, ?, ?)
    """
    cursor = connection.execute(sql, (detail.strip(), max(0.0, float(quantity)), max(0.0, float(rate))))
    connection.commit()
    return int(cursor.lastrowid)


def update_barcode_inventory_item(
    connection: sqlite3.Connection, item_id: int, detail: str, quantity: float, rate: float
) -> None:
    """Update an existing barcode inventory item."""
    sql = """
        UPDATE barcode_inventory
        SET detail = ?, quantity = ?, rate = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """
    connection.execute(sql, (detail.strip(), max(0.0, float(quantity)), max(0.0, float(rate)), item_id))
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

