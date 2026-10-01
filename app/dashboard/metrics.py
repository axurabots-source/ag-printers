"""Analytics and business metrics queries for AG Printers Dashboard."""

from __future__ import annotations

import sqlite3
from typing import Any


def get_kpi_metrics(connection: sqlite3.Connection) -> dict[str, Any]:
    """Retrieve high-level business indicators (revenue, profit, counts, inventory)."""
    # Bills & Financials
    bills_row = connection.execute(
        """
        SELECT 
            COUNT(*) AS total_bills,
            COALESCE(SUM(total_amount), 0) AS total_revenue,
            COALESCE(SUM(profit), 0) AS total_profit
        FROM bills
        """
    ).fetchone()

    total_bills = int(bills_row["total_bills"] or 0)
    total_revenue = float(bills_row["total_revenue"] or 0.0)
    total_profit = float(bills_row["total_profit"] or 0.0)
    profit_margin = (total_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # Gate Passes / Challans count
    gp_row = connection.execute("SELECT COUNT(*) AS total_gp FROM gate_passes").fetchone()
    total_gate_passes = int(gp_row["total_gp"] or 0)

    # Active Parties count
    parties_row = connection.execute(
        "SELECT COUNT(*) AS total_parties FROM parties WHERE is_active = 1"
    ).fetchone()
    total_parties = int(parties_row["total_parties"] or 0)

    # Barcode Inventory
    inv_row = connection.execute(
        """
        SELECT 
            COUNT(*) AS total_items,
            COALESCE(SUM(quantity), 0) AS total_qty,
            COALESCE(SUM(quantity * rate), 0) AS total_val,
            COALESCE(SUM(CASE WHEN quantity <= 10 THEN 1 ELSE 0 END), 0) AS low_stock_count
        FROM barcode_inventory
        """
    ).fetchone()

    inventory_items = int(inv_row["total_items"] or 0)
    inventory_qty = float(inv_row["total_qty"] or 0.0)
    inventory_val = float(inv_row["total_val"] or 0.0)
    low_stock_count = int(inv_row["low_stock_count"] or 0)

    return {
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "profit_margin": profit_margin,
        "total_bills": total_bills,
        "total_gate_passes": total_gate_passes,
        "total_parties": total_parties,
        "inventory_items": inventory_items,
        "inventory_qty": inventory_qty,
        "inventory_val": inventory_val,
        "low_stock_count": low_stock_count,
    }


def get_revenue_trend(
    connection: sqlite3.Connection, limit: int = 10
) -> list[dict[str, Any]]:
    """Retrieve chronological revenue and profit trend points.
    
    If there are multiple bills across dates, groups by date or displays the most
    recent bills in ascending order for charting.
    """
    rows = connection.execute(
        """
        SELECT 
            b.bill_date AS date_label,
            b.bill_number,
            p.name AS party_name,
            b.total_amount,
            b.profit
        FROM bills AS b
        JOIN parties AS p ON p.id = b.party_id
        ORDER BY b.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    # Reverse to chronological order (oldest to newest among recent items)
    items = list(reversed(rows))
    result: list[dict[str, Any]] = []
    for r in items:
        result.append({
            "label": str(r["bill_number"]),
            "date": str(r["date_label"]),
            "party": str(r["party_name"]),
            "revenue": float(r["total_amount"] or 0.0),
            "profit": float(r["profit"] or 0.0),
        })
    return result


def get_top_clients(
    connection: sqlite3.Connection, limit: int = 5
) -> list[dict[str, Any]]:
    """Retrieve top parties ranked by billed revenue."""
    rows = connection.execute(
        """
        SELECT 
            p.name AS party_name,
            COUNT(b.id) AS bills_count,
            COALESCE(SUM(b.total_amount), 0) AS total_revenue,
            COALESCE(SUM(b.profit), 0) AS total_profit
        FROM parties AS p
        JOIN bills AS b ON b.party_id = p.id
        GROUP BY p.id
        ORDER BY total_revenue DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    total_billed = sum(float(r["total_revenue"] or 0.0) for r in rows) or 1.0
    result: list[dict[str, Any]] = []
    for r in rows:
        rev = float(r["total_revenue"] or 0.0)
        share = (rev / total_billed * 100.0) if total_billed > 0 else 0.0
        result.append({
            "party_name": str(r["party_name"]),
            "bills_count": int(r["bills_count"] or 0),
            "revenue": rev,
            "profit": float(r["total_profit"] or 0.0),
            "share_percentage": round(share, 1),
        })
    return result


def get_recent_bills(
    connection: sqlite3.Connection, limit: int = 6
) -> list[dict[str, Any]]:
    """Retrieve recent bills with challan number and PDF path."""
    rows = connection.execute(
        """
        SELECT 
            b.id,
            b.bill_number,
            b.bill_date,
            p.name AS party_name,
            COALESCE(NULLIF(b.po_number, ''), '') AS po_number,
            b.total_amount,
            COALESCE(b.profit, 0) AS profit,
            COALESCE(b.pdf_path, '') AS pdf_path,
            (SELECT g.gate_pass_number FROM gate_passes AS g WHERE g.bill_id = b.id) AS gate_pass_number
        FROM bills AS b
        JOIN parties AS p ON p.id = b.party_id
        ORDER BY b.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return [
        {
            "id": int(r["id"]),
            "bill_number": str(r["bill_number"]),
            "date": str(r["bill_date"]),
            "party_name": str(r["party_name"]),
            "po_number": str(r["po_number"] or "-"),
            "total_amount": float(r["total_amount"] or 0.0),
            "profit": float(r["profit"] or 0.0),
            "pdf_path": str(r["pdf_path"] or ""),
            "gate_pass_number": str(r["gate_pass_number"] or "-"),
        }
        for r in rows
    ]


def get_inventory_status(
    connection: sqlite3.Connection, limit: int = 6
) -> list[dict[str, Any]]:
    """Retrieve barcode stock items ordered by lowest stock first."""
    rows = connection.execute(
        """
        SELECT id, detail, quantity, rate, updated_at
        FROM barcode_inventory
        ORDER BY quantity ASC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return [
        {
            "id": int(r["id"]),
            "detail": str(r["detail"]),
            "quantity": float(r["quantity"] or 0.0),
            "rate": float(r["rate"] or 0.0),
            "total_value": float((r["quantity"] or 0.0) * (r["rate"] or 0.0)),
            "is_low_stock": float(r["quantity"] or 0.0) <= 10.0,
        }
        for r in rows
    ]
