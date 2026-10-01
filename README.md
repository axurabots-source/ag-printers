# AG Printers

Offline Windows desktop **Business Management Software** for a printing business.

**Version:** V0.7 (Costing)

> **Master reference:** [`AG_Printers_PROJECT_SPEC.md`](AG_Printers_PROJECT_SPEC.md) —
> the full project specification (goal, technology direction, modules, the
> party → PO → costing → bill → challan → ledger workflow, database rules,
> UI/UX direction, backup/restore plan, development rules and current status).

## Requirements

- Windows
- Python 3.13

## Setup

```powershell
# From the project folder
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python run.py
```

On first run the app creates its SQLite database at `data/database/business.db`.

## Project structure

```
AG Printers/
+-- run.py                    # Entry point
+-- requirements.txt
+-- README.md
+-- AG_Printers_PROJECT_SPEC.md  # Full project specification (master reference)
+-- .gitignore
+-- app/
|   +-- __init__.py           # App package + version
|   +-- main.py               # Bootstrap (database + window)
|   +-- main_window.py        # Shell: sidebar + header + content stack
|   +-- paths.py              # Project paths (no hard-coded paths)
|   +-- ui/
|   |   +-- theme.py          # Colours + style sheet
|   |   +-- sidebar.py        # Collapsible left navigation
|   |   +-- nav_button.py     # Sidebar item (pill active state)
|   |   +-- icons.py          # Qt-painted vector icons
|   |   +-- header.py         # Top header bar
|   |   +-- placeholder.py    # "Coming soon" page per module
|   +-- db/
|   |   +-- connection.py     # SQLite connection
|   |   +-- schema.py         # Schema versioning / migrations
|   |   +-- parties.py        # Parties repository
|   |   +-- purchase_orders.py# Purchase orders + items repository
|   |   +-- bills.py            # Bills, bill items and matching challans
|   +-- parties/
|   |   +-- page.py           # Parties module (list <-> profile)
|   |   +-- list_view.py      # Searchable parties list
|   |   +-- profile_view.py   # Party profile / details
|   |   +-- dialog.py         # Add / Edit party form
|   +-- purchase_orders/
|       +-- page.py           # PO module (list <-> details)
|       +-- list_view.py      # PO list (party filter + search)
|       +-- detail_view.py    # Read-only PO details
|       +-- form_dialog.py    # Add / Edit PO form (items + document)
|       +-- review_dialog.py  # Review screen for extracted document data
|       +-- item_selection.py # Selected PO items (internal ids, no Qt)
|       +-- select_dialog.py  # Tick the PO items needed for the next step
|   +-- bills/
|   |   +-- page.py           # Bills module (list <-> BILL document)
|   |   +-- list_view.py      # Searchable bills list
|   |   +-- create_dialog.py  # Create a bill from the selected PO items
|   |   +-- document_view.py  # Read-only BILL / CHALLAN document
|   +-- challans/
|       +-- page.py           # Gate Pass module (list <-> CHALLAN document)
+-- data/
    +-- database/
    |   +-- business.db       # Created automatically on first run
    +-- po_documents/         # Managed copies of PO source documents
```

## Database

- SQLite via Python's built-in `sqlite3` module.
- `business.db` is created automatically on first launch.
- A `schema_version` table records which migrations have been applied, so
  future versions can upgrade existing databases safely.
- Current schema version: **7** (baseline, parties, purchase orders + items,
  bills + bill items + gate passes, costing + costing lines + saved party
  rates; v7 drops the unique PO-number index because the number is supplied by
  the party and does not have to be globally unique).

### Relationships

- One **Party** -> many **Purchase Orders** (`purchase_orders.party_id`).
- One **Purchase Order** -> many **PO Items** (`po_items.po_id`,
  `ON DELETE CASCADE`).
- One **Purchase Order** -> many **Bills** (`bills.po_id`), and a bill always
  belongs to the same party as its PO (`bills.party_id`).
- One **Bill** -> many **Bill Items** (`bill_items.bill_id`); every line keeps the
  real `bill_items.po_item_id` of the PO item it came from
  (`ON DELETE RESTRICT`, so a billed item cannot be deleted).
- One **Bill** -> exactly one **Gate Pass / Challan** (`gate_passes.bill_id`,
  `UNIQUE`, created in the same transaction as the bill).

## PO numbering

The supplier's own PO number is the `purchase_orders.po_number` column, which is
always typed by the user from the party's document - AG Printers never generates
a PO number. The same number may exist for different parties, so it is not
globally unique; relationships always use the internal `id` columns.

## PO item selection (V0.5)

Open a saved PO and press **Select Items** in the details view: a checkbox
screen lists that PO's items (Description, Quantity, Purchase Rate, Amount)
while the PO number and party stay visible above the table. One or several
items can be ticked; *Select All* / *Clear* help with longer POs.

- Every ticked row keeps its real `po_items.id`, so a selection can never turn
  into unrelated free text.
- Quantity and purchase rate are read from the saved PO item - nothing has to
  be typed again.
- The selection is re-checked against the database before it is used, so an
  item that was removed in the meantime is reported instead of guessed.
- Selections live on the PO page (`selected_po_items`) for the later Costing,
  Bill and Challan versions. **No** new tables were needed for V0.5: the
  existing `po_items` rows already carry the internal ids, and the chain
  Party → PO → PO Item is kept through `purchase_orders.party_id` and
  `po_items.po_id`. Costing, Bill, Challan, profit and ledger logic are not
  part of this version.

## Bills and automatic challan / gate pass (V0.6)

Open a saved PO, press **Select Items** (V0.5) and then **Create Bill**. The
dialog shows the items with the quantity coming from the PO item, and both
internal numbers before saving:

- `BILL-0001`, `BILL-0002`, ... are generated by the app - the number is never
  typed by the user, and the party's own PO number is never used as an internal id.
- Saving the bill **always** creates its matching `CHALLAN-0001`,
  `CHALLAN-0002`, ... gate pass in the same transaction, so a bill can never
  exist without its challan. The challan is a separate record linked to the bill
  (`gate_passes.bill_id`, unique) - there is no standalone challan screen for
  creating one.
- Every bill line stores the real `po_item_id` and the quantity from the PO
  item; the description is read from `po_items` when the bill is shown, so PO
  item data is not copied into a second free-text table.

**Bills** → search by bill number / party / PO, open the `BILL` document
(number, challan number, PO number, party, date, items, quantity, rate, amount,
total) and switch to its `CHALLAN / GATE PASS` with one click.
**Gate Pass** → list of the challans that came from bills, each one opens its
own document or jumps to the linked bill. A challan is never created by hand.

Deleting a bill (with confirmation) removes its challan and its bill lines, and
leaves the PO and its items untouched. Costing, selling price / profit, ledger,
dashboard and PDF / printing are **not** part of this version.

## Costing (V0.7)

Open a saved PO, press **Select Items** (V0.5) and then **Cost Selected Items**.
The costing sheet shows the party, PO number, item and the quantity that comes
from the selected PO item - the quantity is read-only and never retyped.

The sheet always shows every row of the specification, in order, in three
sections:

- **GENERAL** - Design, Plates, Card, Printing, Lamination, Pasting, Block,
  Cutting, Banding, Dai Make, Dai Cut, Others
- **BARCODE STICKERS** - Media, Ribbon, Electricity + Labour
- **SAMPLING** - Card, Printing, Others

Each row has an editable item name (with the previously used names offered as
autocomplete) and an editable rate:

- A **blank or zero rate is excluded** from the costing - the row simply drops
  out of the totals, and only the filled rows are stored.
- Every row is a **per-unit rate**: `amount = PO quantity x rate`, so the
  section and total figures follow the PO item's own quantity.
- The summary shows the party, PO number, item, quantity, the **General**,
  **Barcode** and **Sampling** totals, the **Total Cost** and the
  **Per Unit Cost** (`total cost / quantity`), all updating as you type.
- A costing is always saved against the real `po_items.id` (`costing.po_item_id`),
  and the party, PO and quantity are read back from the database, so the
  relationship Party -> PO -> PO Item -> Costing stays intact.
- Editing a row also updates that party's saved rate for it
  (`party_rates`), so the next costing of the same party starts from the rates
  used last time. Only the rows that were filled are remembered.

Re-opening a saved costing reloads its stored lines; re-costing the same PO item
updates the existing costing instead of creating a second one. Selling price /
profit, new sales, ledger, dashboard and PDF / printing are **not** part of this
version.

## Status

- **V0.1 Foundation** - project layout, database, schema versioning.
- **V0.2 Main UI Shell** - sidebar, header, content area.
- **V0.3 Party Management** - parties list, search, add/edit, profile view,
  activate/deactivate.
- **V0.4 Purchase Orders (Step 1)** - PO list, party filter, search,
  add/edit/delete with confirmation and item rows, all entered manually.
- **V0.5 PO Items Selection** - tick one or more items of a saved PO; the
  selection keeps the real `po_items.id`, quantity comes from the PO item and
  is handed to the later Costing / Bill / Challan versions.
- **V0.6 Bills + automatic Challan / Gate Pass** - create a bill from the
  selected PO items, internal bill and challan numbers generated automatically,
  the matching challan created together with the bill, BILL and CHALLAN / GATE
  PASS documents viewable from both modules.
- **V0.7 Costing** - cost a selected PO item on the three specification
  sections, quantity taken from the PO item, blank/zero rates excluded, per-unit
  cost calculated, party's saved rates reused, saved against the real
  `po_items.id`.

Dashboard, sales, ledger, reports, items, PDF generation and settings will be
implemented in later versions.
