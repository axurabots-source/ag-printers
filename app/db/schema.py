"""Database schema and versioning (migration) helpers.

V0.1 ships only the versioning mechanism. Each future version appends its
SQL to ``MIGRATIONS`` under the next version number, so existing databases
can be upgraded in place.

Usage::

    connection = create_connection()
    initialize_database(connection)
"""

from __future__ import annotations

import sqlite3

#: Highest schema version known to this build of the application.
SCHEMA_VERSION = 14

#: Ordered migrations: version -> SQL script.
MIGRATIONS: dict[int, str] = {
    # V0.1 - foundation: versioning mechanism only, no application tables yet.
    1: """
    -- AG Printers V0.1 baseline migration.
    -- Application tables (parties, orders, bills, ...) will be added by
    -- future migrations.
    """,
    # V0.3 - Parties module.
    2: """
    CREATE TABLE parties (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT    NOT NULL,
        contact_person TEXT    NOT NULL DEFAULT '',
        phone          TEXT    NOT NULL DEFAULT '',
        email          TEXT    NOT NULL DEFAULT '',
        address        TEXT    NOT NULL DEFAULT '',
        notes          TEXT    NOT NULL DEFAULT '',
        is_active      INTEGER NOT NULL DEFAULT 1,
        created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX idx_parties_name ON parties(name COLLATE NOCASE);
    """,
    # V0.4 - Purchase Order module.
    3: """
    CREATE TABLE purchase_orders (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id             INTEGER NOT NULL REFERENCES parties(id)
                                       ON DELETE RESTRICT,
        po_number            TEXT    NOT NULL,
        po_date              TEXT    NOT NULL,
        source_document_path TEXT    NOT NULL DEFAULT '',
        notes                TEXT    NOT NULL DEFAULT '',
        created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE UNIQUE INDEX idx_purchase_orders_number
        ON purchase_orders(po_number COLLATE NOCASE);
    CREATE INDEX idx_purchase_orders_party ON purchase_orders(party_id);

    CREATE TABLE po_items (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id         INTEGER NOT NULL REFERENCES purchase_orders(id)
                                       ON DELETE CASCADE,
        description   TEXT    NOT NULL,
        quantity      REAL    NOT NULL DEFAULT 0,
        purchase_rate REAL    NOT NULL DEFAULT 0,
        created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX idx_po_items_po ON po_items(po_id);
    """,
    # V0.4 - Document import: keep the vendor's own PO reference separate from
    # the application's internal, globally unique serial (po_number).
    4: """
    ALTER TABLE purchase_orders
        ADD COLUMN vendor_reference TEXT NOT NULL DEFAULT '';
    CREATE INDEX idx_purchase_orders_vendor
        ON purchase_orders(vendor_reference COLLATE NOCASE);
    """,
    # V0.6 - Bill + the Challan / Gate Pass that is created with it.
    # A bill belongs to one Party and one PO and keeps the real po_items ids
    # through bill_items; the challan has its own number but is meaningless
    # without its bill, so it cascades and is unique per bill.
    5: """
    CREATE TABLE bills (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number  TEXT    NOT NULL,
        bill_date    TEXT    NOT NULL,
        party_id     INTEGER NOT NULL REFERENCES parties(id)
                                       ON DELETE RESTRICT,
        po_id        INTEGER NOT NULL REFERENCES purchase_orders(id)
                                       ON DELETE RESTRICT,
        total_amount REAL    NOT NULL DEFAULT 0,
        notes        TEXT    NOT NULL DEFAULT '',
        created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE UNIQUE INDEX idx_bills_number ON bills(bill_number COLLATE NOCASE);
    CREATE INDEX idx_bills_party ON bills(party_id);
    CREATE INDEX idx_bills_po ON bills(po_id);

    CREATE TABLE bill_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id    INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
        po_item_id INTEGER NOT NULL REFERENCES po_items(id)
                                  ON DELETE RESTRICT,
        quantity   REAL    NOT NULL DEFAULT 0,
        rate       REAL    NOT NULL DEFAULT 0,
        created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX idx_bill_items_bill ON bill_items(bill_id);
    CREATE INDEX idx_bill_items_po_item ON bill_items(po_item_id);

    CREATE TABLE gate_passes (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        gate_pass_number TEXT    NOT NULL,
        gate_pass_date   TEXT    NOT NULL,
        bill_id          INTEGER NOT NULL REFERENCES bills(id)
                                        ON DELETE CASCADE,
        notes            TEXT    NOT NULL DEFAULT '',
        created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE UNIQUE INDEX idx_gate_passes_number
        ON gate_passes(gate_pass_number COLLATE NOCASE);
    CREATE UNIQUE INDEX idx_gate_passes_bill ON gate_passes(bill_id);
    """,
    # V0.7 - Costing engine (spec Step 4) and the party-specific rates that feed
    # it. A costing belongs to one real po_items row, so the chain stays
    # Party -> PO -> PO Item -> Costing, and the rate rows are per party so the
    # saved rates load automatically when the same party is costed again.
    6: """
    CREATE TABLE costing (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id       INTEGER NOT NULL REFERENCES parties(id)
                                     ON DELETE RESTRICT,
        po_id          INTEGER NOT NULL REFERENCES purchase_orders(id)
                                     ON DELETE RESTRICT,
        po_item_id     INTEGER NOT NULL REFERENCES po_items(id)
                                     ON DELETE RESTRICT,
        quantity       REAL    NOT NULL DEFAULT 0,
        general_total  REAL    NOT NULL DEFAULT 0,
        barcode_total  REAL    NOT NULL DEFAULT 0,
        sampling_total REAL    NOT NULL DEFAULT 0,
        total_cost     REAL    NOT NULL DEFAULT 0,
        per_unit_cost  REAL    NOT NULL DEFAULT 0,
        notes          TEXT    NOT NULL DEFAULT '',
        created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE UNIQUE INDEX idx_costing_po_item ON costing(po_item_id);
    CREATE INDEX idx_costing_party ON costing(party_id);

    CREATE TABLE costing_lines (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        costing_id INTEGER NOT NULL REFERENCES costing(id) ON DELETE CASCADE,
        section    TEXT    NOT NULL,
        line_name  TEXT    NOT NULL,
        rate       REAL    NOT NULL DEFAULT 0,
        amount     REAL    NOT NULL DEFAULT 0,
        position   INTEGER NOT NULL DEFAULT 0,
        created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX idx_costing_lines_costing ON costing_lines(costing_id);

    CREATE TABLE party_rates (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id   INTEGER NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
        section    TEXT    NOT NULL,
        line_name  TEXT    NOT NULL,
        rate       REAL    NOT NULL DEFAULT 0,
        created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE UNIQUE INDEX idx_party_rates_key
        ON party_rates(party_id, section, line_name COLLATE NOCASE);
    """,
    # V0.7.1 - PO numbering is the Party's own reference, not ours.
    # The application must never invent a PO number, and two different parties
    # may legitimately use the same one, so the global uniqueness index from
    # migration 3 is replaced by a plain lookup index. No column and no row is
    # touched here: existing PO numbers are kept exactly as they are.
    7: """
    DROP INDEX IF EXISTS idx_purchase_orders_number;
    CREATE INDEX idx_purchase_orders_number
        ON purchase_orders(po_number COLLATE NOCASE);
    """,
    # V0.8 - Job / Billing Workspace: direct manual bills and PO entries.
    # - bills.po_id is nullable (jobs without pre-existing PO records).
    # - bills.po_number stores the party's PO number directly.
    # - bill_items.description stores the item description directly.
    # - bill_items.po_item_id is nullable.
    8: """
    CREATE TABLE bills_new (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number  TEXT    NOT NULL,
        bill_date    TEXT    NOT NULL,
        party_id     INTEGER NOT NULL REFERENCES parties(id) ON DELETE RESTRICT,
        po_id        INTEGER REFERENCES purchase_orders(id) ON DELETE SET NULL,
        po_number    TEXT    NOT NULL DEFAULT '',
        total_amount REAL    NOT NULL DEFAULT 0,
        notes        TEXT    NOT NULL DEFAULT '',
        created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    INSERT INTO bills_new (id, bill_number, bill_date, party_id, po_id, po_number, total_amount, notes, created_at, updated_at)
    SELECT b.id, b.bill_number, b.bill_date, b.party_id, b.po_id,
           COALESCE((SELECT po.po_number FROM purchase_orders po WHERE po.id = b.po_id), ''),
           b.total_amount, b.notes, b.created_at, b.updated_at
    FROM bills b;
    DROP TABLE bills;
    ALTER TABLE bills_new RENAME TO bills;
    CREATE UNIQUE INDEX idx_bills_number ON bills(bill_number COLLATE NOCASE);
    CREATE INDEX idx_bills_party ON bills(party_id);
    CREATE INDEX idx_bills_po ON bills(po_id);

    CREATE TABLE bill_items_new (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id     INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
        po_item_id  INTEGER REFERENCES po_items(id) ON DELETE SET NULL,
        description TEXT    NOT NULL DEFAULT '',
        quantity    REAL    NOT NULL DEFAULT 0,
        rate        REAL    NOT NULL DEFAULT 0,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    INSERT INTO bill_items_new (id, bill_id, po_item_id, description, quantity, rate, created_at, updated_at)
    SELECT bi.id, bi.bill_id, bi.po_item_id,
           COALESCE((SELECT pi.description FROM po_items pi WHERE pi.id = bi.po_item_id), ''),
           bi.quantity, bi.rate, bi.created_at, bi.updated_at
    FROM bill_items bi;
    DROP TABLE bill_items;
    ALTER TABLE bill_items_new RENAME TO bill_items;
    CREATE INDEX idx_bill_items_bill ON bill_items(bill_id);
    CREATE INDEX idx_bill_items_po_item ON bill_items(po_item_id);
    """,
    9: """
    ALTER TABLE bills ADD COLUMN job_number TEXT NOT NULL DEFAULT '';
    """,
    10: """
    CREATE TABLE costing_new (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id       INTEGER NOT NULL REFERENCES parties(id) ON DELETE RESTRICT,
        item_name      TEXT NOT NULL DEFAULT '',
        quantity       REAL NOT NULL DEFAULT 1000,
        general_total  REAL NOT NULL DEFAULT 0,
        barcode_total  REAL NOT NULL DEFAULT 0,
        sampling_total REAL NOT NULL DEFAULT 0,
        total_cost     REAL NOT NULL DEFAULT 0,
        per_unit_cost  REAL NOT NULL DEFAULT 0,
        notes          TEXT NOT NULL DEFAULT '',
        created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    INSERT INTO costing_new (id, party_id, item_name, quantity, general_total, barcode_total, sampling_total, total_cost, per_unit_cost, notes, created_at, updated_at)
    SELECT id, party_id, '', quantity, general_total, barcode_total, sampling_total, total_cost, per_unit_cost, notes, created_at, updated_at FROM costing;
    DROP TABLE costing;
    ALTER TABLE costing_new RENAME TO costing;
    CREATE INDEX idx_costing_party ON costing(party_id);
    """,
    11: """
    ALTER TABLE bills ADD COLUMN production_cost REAL NOT NULL DEFAULT 0;
    ALTER TABLE bills ADD COLUMN profit REAL NOT NULL DEFAULT 0;
    """,
    12: """
    ALTER TABLE bill_items ADD COLUMN cost_price REAL NOT NULL DEFAULT 0;
    """,
    13: """
    CREATE TABLE barcode_inventory (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        detail      TEXT    NOT NULL,
        quantity    REAL    NOT NULL DEFAULT 0,
        rate        REAL    NOT NULL DEFAULT 0,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX idx_barcode_inventory_detail ON barcode_inventory(detail COLLATE NOCASE);
    """,
    14: """
    ALTER TABLE bills ADD COLUMN pdf_path TEXT NOT NULL DEFAULT '';
    """,
}

_VERSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def get_current_version(connection: sqlite3.Connection) -> int:
    """Return the highest applied schema version (0 = empty database)."""
    row = connection.execute(
        "SELECT MAX(version) AS version FROM schema_version"
    ).fetchone()
    return int(row["version"] or 0)


def initialize_database(connection: sqlite3.Connection) -> int:
    """Create the database structure and apply any pending migrations.

    Returns the schema version after initialisation.
    """
    connection.execute(_VERSION_TABLE_SQL)
    connection.commit()

    current = get_current_version(connection)
    for version in range(current + 1, SCHEMA_VERSION + 1):
        sql = MIGRATIONS.get(version)
        if not sql:
            raise RuntimeError(
                f"Missing migration for schema version {version}."
            )
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.executescript(sql)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (version,),
        )
        connection.commit()

    return get_current_version(connection)
