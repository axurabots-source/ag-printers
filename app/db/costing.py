"""Costing engine for a selected PO item (V0.7, spec Step 4).

The specification fixes the three costing sections and their rows exactly
(``AG_Printers_PROJECT_SPEC.md`` Step 4), so they are declared here once and
used by both the database layer and the UI:

* ``GENERAL`` - Design, Plates, Card, Printing, Lamination, Pasting, Block,
  Cutting, Banding, Dai Make, Dai Cut, Others
* ``BARCODE STICKERS`` - Media, Ribbon, Electricity + Labour
* ``SAMPLING`` - Card, Printing, Others

Behaviour implemented here, exactly as the specification states it:

* the quantity is the selected PO item's own quantity - it is copied, never
  retyped (Step 3);
* a blank or zero rate is excluded from the totals and from the saved lines
  (Step 4);
* total cost is the sum of the three section totals, and
  ``per_unit_cost = total_cost / quantity`` (Step 4);
* the saved party-specific rates load automatically for the same party
  (Step 4), can be edited, and are stored again for future use.

Selling price, profit, sales, ledger and dashboard are NOT part of this
version, so no column for them exists.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

#: The three costing sections in specification order: (key, title, row names).
COSTING_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "general",
        "GENERAL",
        (
            "Design",
            "Plates",
            "Card",
            "Printing",
            "Lamination",
            "Pasting",
            "Block",
            "Cutting",
            "Banding",
            "Dai Make",
            "Dai Cut",
            "Sampling",
            "Others",
        ),
    ),
    ("barcode", "BARCODE STICKERS", ("Media", "Ribbon", "Electricity + Labour")),
    ("sampling", "SAMPLING", ("Card", "Printing", "Die / Block", "Proofing", "Others")),
)

#: section key -> display title.
SECTION_TITLES: dict[str, str] = {key: title for key, title, _ in COSTING_SECTIONS}

#: section key -> its row names.
SECTION_ROWS: dict[str, tuple[str, ...]] = {
    key: rows for key, _title, rows in COSTING_SECTIONS
}

#: Every (section, line name) pair in specification order.
ALL_LINES: tuple[tuple[str, str], ...] = tuple(
    (key, name) for key, _title, rows in COSTING_SECTIONS for name in rows
)

#: The section rows as a flat list, used to build the UI table.
ALL_LINE_NAMES: tuple[str, ...] = tuple(name for _section, name in ALL_LINES)


def is_known_line(section: str, line_name: str) -> bool:
    """True when (*section*, *line_name*) is one of the spec's costing rows."""
    rows = SECTION_ROWS.get(section)
    return rows is not None and line_name in rows


@dataclass(slots=True)
class CostingLine:
    """One costing row: a section row with the rate and its calculated amount."""

    section: str
    line_name: str
    rate: float = 0.0
    amount: float = 0.0
    #: Row order inside its section (used to rebuild the UI table).
    position: int = 0
    #: Filled when the line comes from the database.
    id: int | None = None

    @property
    def is_blank(self) -> bool:
        """A blank / zero rate is excluded from the costing (spec Step 4)."""
        return self.rate <= 0.0


@dataclass(slots=True)
class Costing:
    """A saved costing of an item."""

    id: int
    party_id: int
    quantity: float
    general_total: float
    barcode_total: float
    sampling_total: float
    total_cost: float
    per_unit_cost: float
    item_name: str = ""
    po_id: int | None = None
    po_item_id: int | None = None
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    # Filled by the reading queries.
    party_name: str = ""
    po_number: str = ""
    description: str = ""
    #: Only the non-blank lines are stored, so this is the display list.
    lines: list[CostingLine] = field(default_factory=list)
    #: Every spec row, filled in the UI so a blank row still shows a rate box.
    draft_lines: list[CostingLine] = field(default_factory=list)

    def lines_for(self, section: str) -> list[CostingLine]:
        """Saved lines of one section, in row order."""
        return [line for line in self.lines if line.section == section]

    def section_total(self, section: str) -> float:
        """Total of the saved lines of one section."""
        return sum(line.amount for line in self.lines_for(section))

    def rate_for(self, section: str, line_name: str) -> float:
        """Saved rate of one row, or 0.0 when that row was left blank."""
        for line in self.lines:
            if line.section == section and line.line_name == line_name:
                return line.rate
        return 0.0

    def line_names_in_use(self) -> list[str]:
        """Distinct saved line names - the autocomplete source for this item."""
        seen: list[str] = []
        for line in self.lines:
            if line.line_name not in seen:
                seen.append(line.line_name)
        return seen


@dataclass(frozen=True)
class SelectedPoItem:
    po_item_id: int
    po_id: int
    po_number: str
    party_id: int
    party_name: str
    description: str
    quantity: float
    purchase_rate: float



def calculate(lines: Sequence[CostingLine], quantity: float) -> dict[str, float]:
    """Section and total costs for *lines* and the PO *quantity*.

    Every line amount is ``rate x quantity`` - the quantity comes from the PO
    item, so it is never typed again. Lines with a blank or zero rate are
    excluded from every total, and ``per_unit = total / quantity`` (0 when the
    quantity is zero, so the UI can never divide by zero).
    """
    totals = {key: 0.0 for key in SECTION_ROWS}
    for line in lines:
        if line.is_blank:
            continue
        line.amount = line.rate * quantity
        if line.section in totals:
            totals[line.section] += line.amount
    total = sum(totals.values())
    return {
        **totals,
        "total_cost": total,
        "per_unit_cost": total / quantity if quantity else 0.0,
    }


# -- party-specific saved rates -------------------------------------------


def load_party_rates(
    connection: sqlite3.Connection, party_id: int
) -> dict[tuple[str, str], float]:
    """Saved rates of one party, keyed by ``(section, line name)``.

    Only rows of the party's own spec sections are returned, so a stale name
    can never be applied to an unknown row.
    """
    if not party_id or party_id <= 0:
        return {}
    rates: dict[tuple[str, str], float] = {}
    for row in connection.execute(
        "SELECT section, line_name, rate FROM party_rates WHERE party_id = ?",
        (party_id,),
    ):
        key = (str(row["section"]), str(row["line_name"]))
        if is_known_line(*key):
            rates[key] = float(row["rate"])
    return rates


def save_party_rates(
    connection: sqlite3.Connection,
    party_id: int,
    rates: dict[tuple[str, str], float],
) -> int:
    """Store the party's rates for future use, return the number written.

    Only non-blank rates are written, and a row the user cleared is deleted, so
    the party keeps exactly the rates they actually use. Re-saving a costing of
    the same party therefore updates the saved rates (spec Step 4).
    """
    if not party_id or party_id <= 0:
        raise ValueError("A costing always belongs to a party.")
    saved = 0
    for (section, line_name), rate in rates.items():
        if not is_known_line(section, line_name):
            continue
        if float(rate) <= 0.0:
            connection.execute(
                "DELETE FROM party_rates"
                " WHERE party_id = ? AND section = ?"
                "   AND line_name = ? COLLATE NOCASE",
                (party_id, section, line_name),
            )
            continue
        connection.execute(
            """
            INSERT INTO party_rates (party_id, section, line_name, rate)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(party_id, section, line_name COLLATE NOCASE)
            DO UPDATE SET rate = excluded.rate,
                          updated_at = datetime('now', 'localtime')
            """,
            (party_id, section, line_name, float(rate)),
        )
        saved += 1
    connection.commit()
    return saved


def rate_suggestions(
    connection: sqlite3.Connection, party_id: int, prefix: str
) -> list[str]:
    """Saved line names for the autocomplete (spec Step 4).

    Typing ``T`` may suggest a saved item such as ``Tag``: the party's own
    saved names come first, then any other saved name, then the fixed spec
    rows. Only the party's own rates are used, so one party never inherits
    another party's numbers silently.
    """
    term = prefix.strip().lower()
    if not term:
        return []
    found: list[str] = []
    queries = []
    if party_id and party_id > 0:
        queries.append(
            ("SELECT DISTINCT line_name FROM party_rates"
             " WHERE party_id = ? AND line_name LIKE ? COLLATE NOCASE",
             (party_id, f"%{term}%"))
        )
    queries.append(
        ("SELECT DISTINCT line_name FROM party_rates"
         " WHERE line_name LIKE ? COLLATE NOCASE",
         (f"%{term}%",))
    )
    for sql, params in queries:
        for row in connection.execute(sql, params):
            name = str(row["line_name"])
            if name not in found:
                found.append(name)
    for _section, name in ALL_LINES:
        if name.lower().startswith(term) and name not in found:
            found.append(name)
    return found


# -- saving and reading a costing ------------------------------------------


def build_draft_lines(
    rates: dict[tuple[str, str], float] | None = None,
) -> list[CostingLine]:
    """Every spec row, pre-filled with *rates*, in specification order.

    The UI uses this as its table model so a blank row still shows a rate box
    and a saved rate appears in its own section row.
    """
    saved = rates or {}
    return [
        CostingLine(section=section, line_name=name, rate=float(saved.get((section, name), 0.0)))
        for section, name in ALL_LINES
    ]


def save_costing(
    connection: sqlite3.Connection,
    *,
    party_id: int,
    item_name: str = "",
    quantity: float = 1000.0,
    lines: Sequence[CostingLine],
    notes: str = "",
    costing_id: int | None = None,
) -> int:
    """Create or update a costing sheet, return its id."""
    if not party_id or party_id <= 0:
        raise ValueError("Please select a Party for this costing.")
    item_title = str(item_name).strip() or "Untitled Job"
    qty = float(quantity) if float(quantity) > 0 else 1.0

    kept = [line for line in lines if not line.is_blank and is_known_line(line.section, line.line_name)]
    if not kept:
        raise ValueError("Enter at least one rate before saving the costing.")

    totals = calculate(kept, qty)
    if costing_id:
        connection.execute(
            """
            UPDATE costing
               SET party_id = ?, item_name = ?, quantity = ?, general_total = ?,
                   barcode_total = ?, sampling_total = ?, total_cost = ?,
                   per_unit_cost = ?, notes = ?, updated_at = datetime('now', 'localtime')
             WHERE id = ?
            """,
            (party_id, item_title, qty, totals["general"], totals["barcode"],
             totals["sampling"], totals["total_cost"], totals["per_unit_cost"],
             str(notes).strip(), int(costing_id)),
        )
        connection.execute("DELETE FROM costing_lines WHERE costing_id = ?", (int(costing_id),))
        cid = int(costing_id)
    else:
        cursor = connection.execute(
            """
            INSERT INTO costing
                (party_id, item_name, quantity, general_total, barcode_total,
                 sampling_total, total_cost, per_unit_cost, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (party_id, item_title, qty, totals["general"], totals["barcode"],
             totals["sampling"], totals["total_cost"], totals["per_unit_cost"],
             str(notes).strip()),
        )
        cid = int(cursor.lastrowid)

    connection.executemany(
        """
        INSERT INTO costing_lines (costing_id, section, line_name, rate, amount, position)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (cid, line.section, line.line_name, float(line.rate),
             float(line.rate) * qty, position)
            for position, line in enumerate(kept)
        ],
    )

    save_party_rates(
        connection,
        party_id,
        {(line.section, line.line_name): float(line.rate) for line in lines},
    )
    connection.commit()
    return cid


def get_costing(
    connection: sqlite3.Connection, costing_id: int
) -> Costing | None:
    """The saved costing by costing_id with its lines, or None."""
    row = connection.execute(
        """
        SELECT c.id, c.party_id, c.item_name, c.quantity,
               c.general_total, c.barcode_total, c.sampling_total,
               c.total_cost, c.per_unit_cost, c.notes, c.created_at, c.updated_at,
               p.name AS party_name
        FROM costing AS c
        JOIN parties AS p ON p.id = c.party_id
        WHERE c.id = ?
        """,
        (int(costing_id),),
    ).fetchone()
    if row is None:
        return None
    costing = Costing(
        id=int(row["id"]),
        party_id=int(row["party_id"]),
        quantity=float(row["quantity"]),
        general_total=float(row["general_total"]),
        barcode_total=float(row["barcode_total"]),
        sampling_total=float(row["sampling_total"]),
        total_cost=float(row["total_cost"]),
        per_unit_cost=float(row["per_unit_cost"]),
        item_name=row["item_name"] or "",
        notes=row["notes"] or "",
        created_at=row["created_at"] or "",
        updated_at=row["updated_at"] or "",
        party_name=row["party_name"],
        description=row["item_name"] or "",
    )
    costing.lines = [
        CostingLine(
            section=str(line["section"]),
            line_name=str(line["line_name"]),
            rate=float(line["rate"]),
            amount=float(line["amount"]),
            position=int(line["position"]),
            id=int(line["id"]),
        )
        for line in connection.execute(
            "SELECT id, section, line_name, rate, amount, position"
            " FROM costing_lines WHERE costing_id = ? ORDER BY position",
            (costing.id,),
        )
    ]
    return costing


def list_costings(
    connection: sqlite3.Connection, search: str = ""
) -> list[Costing]:
    """Costings, newest first; *search* matches item name or party."""
    sql = """
        SELECT c.id, c.party_id, c.item_name, c.quantity,
               c.general_total, c.barcode_total, c.sampling_total,
               c.total_cost, c.per_unit_cost, c.notes, c.created_at, c.updated_at,
               p.name AS party_name
        FROM costing AS c
        JOIN parties AS p ON p.id = c.party_id
    """
    params: list[object] = []
    term = search.strip()
    if term:
        like = f"%{term}%"
        sql += (
            " WHERE c.item_name LIKE ? COLLATE NOCASE"
            " OR p.name LIKE ? COLLATE NOCASE"
        )
        params = [like, like]
    sql += " ORDER BY c.id DESC"
    return [
        Costing(
            id=int(row["id"]),
            party_id=int(row["party_id"]),
            quantity=float(row["quantity"]),
            general_total=float(row["general_total"]),
            barcode_total=float(row["barcode_total"]),
            sampling_total=float(row["sampling_total"]),
            total_cost=float(row["total_cost"]),
            per_unit_cost=float(row["per_unit_cost"]),
            item_name=row["item_name"] or "",
            notes=row["notes"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            party_name=row["party_name"],
            description=row["item_name"] or "",
        )
        for row in connection.execute(sql, params)
    ]


def delete_costing(connection: sqlite3.Connection, costing_id: int) -> bool:
    """Delete a costing and its lines."""
    cursor = connection.execute(
        "DELETE FROM costing WHERE id = ?", (int(costing_id),)
    )
    connection.commit()
    return cursor.rowcount > 0

