# AG PRINTERS — PROJECT SPECIFICATION

**Version: 0.2**
**Purpose: Master reference for the coding agent**

---

## 1. PROJECT GOAL

AG Printers is an offline-first Windows desktop application for a printing business.

Core principles:

* Fast and lightweight.
* Works locally without requiring internet for normal business operations.
* SQLite stores structured business data.
* Business data is preserved when the application is updated.
* The application should be modular and easy to update later.
* Keep the UI modern, professional and practical.
* Avoid unnecessary dependencies.
* Do not build the entire system at once.
* Build one small version/module at a time and test it before continuing.
* Final UI polish/redesign will be done after the main functional modules are complete.

---

## 2. TECHNOLOGY DIRECTION

* Python
* PySide6
* SQLite via Python's built-in `sqlite3`
* ReportLab for PDF generation
* PyInstaller for final Windows packaging

Avoid unnecessary dependencies.

### Important removed technology

The application **does NOT use**:

* Tesseract OCR
* PyMuPDF for PO extraction
* PO image scanning
* PO image upload
* OCR processing
* scanned-document extraction

The PO workflow is now **manual data entry only**.

---

## 3. MAIN MODULES

The planned system contains:

1. Dashboard
2. New Job (Workspace)
3. Parties
4. Purchase Orders
5. Bills
6. Gate Pass / Challan
7. Costing
8. Barcode Inventory
9. Sales / Selling Price
10. Ledger
11. Reports
12. Items
13. Settings
14. Backup / Restore / Database Tools

Some modules are developed later.

Existing modules must remain working when new modules are added.

---

# 4. USER'S CURRENT NORMAL WORKFLOW

The main business workflow is:

**PARTY**

↓

**PURCHASE ORDER**

↓

**PO ITEMS**

↓

**JOB / BILLING WORKSPACE**

↓

**COSTING**

↓

**SELLING PRICE / PARTY PO RATE**

↓

**PROFIT / LOSS**

↓

**BILL**

↓

**AUTOMATIC CHALLAN / GATE PASS**

↓

**PDF DOCUMENTS**

↓

**LEDGER / HISTORY**

↓

**REPORTS / DASHBOARD**

---

# 5. PARTY

The user first selects an existing party or creates a new party.

Party information includes:

* Party name
* Contact person
* Phone
* Email
* Address
* Notes
* Active/inactive status
* Created/updated information

A party can have many purchase orders.

Party-specific costing rates are associated with the selected party.

---

# 6. PURCHASE ORDER

## 6.1 Important PO Business Rule

**PO number is provided by the Party/vendor.**

AG Printers must NOT generate PO numbers.

Do NOT use:

* PO-0001
* PO-0002
* internal serial numbers
* automatic PO numbering

The user enters the PO number received from the Party.

### PO uniqueness

The Party's PO number is an external business reference.

It must NOT be globally unique.

The same PO number may exist for different Parties.

Do not use the external PO number as an internal database primary key.

Internal database IDs must be used for relationships.

---

## 6.2 PO Entry

The PO is entered manually.

The PO form should contain:

* Party
* PO Number
* PO Date
* PO Items

PO item information:

* Description
* Quantity
* Party Rate / PO Rate, when available

The user should not need to type the same information again later.

---

## 6.3 Party PO Rate

A Party may provide a rate in the PO.

Example:

* Description: Shopping Bag
* Quantity: 1,000
* Party PO Rate: Rs. 40 per unit

If a PO rate exists, later billing/profit workflows should be able to use that rate automatically.

If the PO does not contain a rate, the selling rate can be entered manually later.

The software must clearly distinguish:

**Party PO Rate / Selling Rate**

from

**Actual Internal Cost**

---

## 6.4 PO → Bill relationship

A PO can have multiple bills.

A PO can contain multiple PO items.

A selected PO item must remain linked to its real `po_items.id`.

Do not duplicate PO items unnecessarily.

---

# 7. PO ITEM SELECTION

When creating a job/bill/costing record, the user should be able to select relevant item(s) from a saved PO.

The user should not repeatedly type information already available in the PO.

Quantity should normally come from the selected PO item.

The selected PO item relationship must be preserved using the real internal PO item ID.

Multiple PO items may be selected.

---

# 8. JOB / BILLING WORKSPACE ("NEW JOB")

The **New Job** workspace is placed directly below **Dashboard** on the main sidebar navigation rail:
`Dashboard` → **`New Job`** → `Parties` → `Purchase Orders` → ...

It serves as the unified, single-screen workspace for daily business operations. The user should not have to jump across different popups or screens.

### 8.1 Single-Screen Workflow

1. **Party Selection (Inline, No Popup):**
   - User selects the Party from an inline search/dropdown on the same screen.
   - Immediately upon selection, the Bill & Job UI appears below it.

2. **PO Number (Party-Provided, Direct Manual Entry):**
   - The user receives the PO number from the party.
   - The user enters the PO number directly inside the bill/job form without being forced to create a separate PO document first.

3. **Editable Bill Grid (Manual Entry):**
   - Columns:
     * `SR.` (Serial number: 1, 2, 3...)
     * `DESCRIPTION` (Editable text)
     * `QUANTITY` (Editable numeric quantity)
     * `RATE` (Editable unit rate / selling price)
     * `TOTAL AMOUNT` (Auto-calculated: Quantity × Rate)
   - Dynamic row addition / deletion.
   - Real-time total calculation.

4. **Dual-Document Generation (Bill + Delivery Challan):**
   - Bill and Challan are generated together from the same entered data.
   - Layout is identical between the two documents; on the challan, the title badge reads **Delivery Challan** (or Challan / Gate Pass), while on the bill it reads **BILL**.
   - Ready for A4-size printing (Page 1 = Bill, Page 2 = Delivery Challan).

### 8.2 Physical Pad & Print Layout Reference

Based on AG Printers physical printed pad:
- **Header Left:**
  * Logo mark: "AG"
  * Title: **AG PRINTERS**
  * Tagline: "Deals in All Kind of Offset Printing & Labels"
- **Header Right:**
  * Suite # 4, 1st Floor, Sultania Center
  * St # 7, Munshi Mohallah,
  * Aminpur Bazar, Faisalabad.
  * Mob: +92 300 966 9060
  * E-mail: agprinters33@gmail.com
- **Badge:**
  * Centered bordered pill: `[ Delivery Challan ]` or `[ Bill ]`
- **Fields Row:**
  * Left: `DATE: __________`, `M/S: __________` (Party Name)
  * Right: `Bill # / D.C. #: __________`, `P.O. #: __________`
- **Table Structure:**
  * Clean boxed grid with serial numbers, item descriptions, quantities, and rates/amounts on the bill.
- **Footer:**
  * Left: `RECEIVER SIGNATURE`
  * Right: `SIGNATURE`

---

# 9. COSTING

Costing is one of the main business functions.

The costing should be available from the Job/Billing Workspace.

The user should not need to leave the main job screen to calculate costing.

The costing UI should use expandable/dropdown sections rather than showing the entire detailed costing sheet permanently.

Exactly three main costing sections exist:

## GENERAL

* Design
* Plates
* Card
* Printing
* Lamination
* Pasting
* Block
* Cutting
* Banding
* Dai Make
* Dai Cut
* Others

## BARCODE STICKERS

* Media
* Ribbon
* Electricity + Labour

## SAMPLING

* Card
* Printing
* Others

---

## 9.1 Costing behavior

* Saved Party-specific rates should load automatically after selecting a Party.
* Costing line fields should support saved-item autocomplete.
* User can edit a loaded rate.
* Blank/zero rates are excluded from final costing calculations.
* Quantity comes from the relevant selected PO item/job context.
* User should not repeatedly retype a known quantity.
* Calculate total cost.
* Calculate per-unit cost:

**Total Cost ÷ Quantity**

The detailed costing lines are internal costing information and should NOT appear as separate bill lines.

---

# 10. SELLING PRICE / PARTY PO RATE

The software must support two cases.

## Case A — Party PO already contains a rate

Example:

Quantity = 1,000

Party PO Rate = Rs. 40

Actual Cost = Rs. 31/unit

The software should calculate:

**Selling Rate = Rs. 40**

**Cost per Unit = Rs. 31**

**Profit per Unit = Rs. 9**

**Total Profit = Rs. 9,000**

**Margin = 22.5%**

The user should not need to type the selling rate again when the Party PO rate is already available.

---

## Case B — Party PO does not contain a rate

The user can enter the selling rate manually.

The software then calculates:

**Selling Rate − Actual Cost = Profit per Unit**

and:

**Profit per Unit × Quantity = Total Profit**

---

## 10.1 Loss case

If:

**Actual Cost > Selling Rate**

the software must clearly show the negative result.

Example:

Selling Rate = Rs. 40

Cost = Rs. 43

Profit/Loss = **-Rs. 3 per unit**

Total Loss should also be calculated.

Do not hide negative profit.

---

# 11. BARCODE INVENTORY

Barcode-related inventory is a separate business area.

It should have its own section/module rather than being mixed into the normal costing screen.

Initial barcode costing components include:

* Media
* Ribbon
* Electricity + Labour

The exact stock/inventory workflow should be designed separately when this module is implemented.

Do not invent stock-management rules before the Barcode Inventory task is started.

---

# 12. BILL

A Bill is created from the selected/costed job or PO item.

The bill should contain:

* Bill number
* Date
* Party
* PO number, when applicable
* Item/description
* Quantity
* Selling price per unit
* Total

Bill numbers are generated internally.

Example:

* BILL-0001
* BILL-0002

Bill numbers must be globally unique.

The Party's external PO number must NOT be used as the Bill number.

---

## 12.1 Internal costing vs Bill

Internal costing lines must NOT appear as separate billing lines.

The Bill only uses:

* Description
* Quantity
* Selling/Sale Rate
* Total

Costing remains internal business information.

---

# 13. AUTOMATIC GATE PASS / CHALLAN

Every Bill created should automatically generate its corresponding Gate Pass / Challan.

Relationship:

* One PO can have multiple Bills.
* Each Bill has one corresponding Challan/Gate Pass.
* Bill and Challan are separate records but linked.

Challan numbers are generated internally.

Example:

* CHALLAN-0001
* CHALLAN-0002

The Challan should clearly be labelled:

**CHALLAN / GATE PASS**

The Bill should clearly be labelled:

**BILL**

Relevant information should remain consistent between the two documents.

---

# 14. PDF DOCUMENTS

The system should generate print-ready PDFs.

Planned combined output:

1. BILL — Party Copy
2. BILL — Vendor Copy
3. CHALLAN / GATE PASS — Party Copy
4. CHALLAN / GATE PASS — Vendor Copy

Vendor copies should automatically be saved in the application's managed local vendor-copy folder.

The ledger/history should later provide a PDF action/link that opens the locally saved document.

PDF generation is a later functional module.

---

# 15. LEDGER / HISTORY

"Ledger" means business transaction/history tracking, not a full accounting system.

The party ledger should show information such as:

* Date
* Party
* PO number
* Bill number
* Challan number
* Item
* Quantity
* Cost
* Selling price
* Profit/Loss
* PDF/document access

Records must remain traceable through their database relationships.

Vendor-side history may also be supported where required.

---

# 16. IMPORTANT DATA RELATIONSHIPS

Conceptually:

**Party**

└── many Purchase Orders

    └── many PO Items

        └── Job / Costing / Sale context

            └── Bill

                └── corresponding Challan / Gate Pass

                    └── Ledger / Documents

Use internal database IDs for relationships.

Never use external PO numbers as internal primary keys.

Keep database logic separate from UI logic.

---

# 17. DATABASE RULES

SQLite is the local database.

Use migrations/schema versions so future application updates can safely change the database structure.

Current implemented entities include:

* parties
* purchase_orders
* po_items
* bills
* bill_items
* gate_passes
* costing
* costing_lines
* party_rates
* schema/version information

Future entities may include:

* ledger/history
* barcode inventory
* sales/reporting support
* document metadata

Do not create unnecessary duplicate entities.

Use appropriate indexes for frequently searched fields.

Database growth alone should not be treated as a reason to change database technology.

---

# 18. DOCUMENT STORAGE

The application is now **manual-entry based for Purchase Orders**.

There is no active PO image/document import workflow.

The old OCR/document-import implementation has been removed.

Existing legacy document data may remain on disk/database for preservation, but new PO creation does not depend on documents or OCR.

Do not reintroduce:

* Tesseract
* PyMuPDF PO extraction
* OCR
* Scan Document button
* Browse PO image button
* Extracted-text review screen
* OCR background workers

unless a future task explicitly requests a completely new document feature.

---

# 19. UI / UX DIRECTION

The application should feel like modern professional business software.

Current shell:

* Sidebar
* Top header
* Main content area
* Modern blue + green visual theme
* Collapsible sidebar
* Expanded mode: icons + labels
* Collapsed mode: icons only
* Smooth sidebar/active-item animation
* Active navigation item uses a distinctive rounded/curved background
* Professional spacing and typography

Keep UI consistent across modules.

The user wants practical screens with clear workflows, not decorative complexity.

### Important UI principle

The new Job/Billing Workspace should reduce unnecessary navigation.

The user should be able to:

**Select Party → Enter/Review Job → Cost → Set Selling Rate → See Profit**

from one main working screen.

Do not make the interface unnecessarily complicated.

Final visual redesign/polish will be done later.

---

# 20. DASHBOARD / REPORTING PLAN

Later dashboard can show:

* Total parties
* Total POs
* Total bills
* Total challans
* Quantity
* Sales
* Cost
* Profit/Loss
* Monthly activity
* Party activity
* Profit trends
* Bill trends

Filters may include:

* Today
* Week
* Month
* Year
* Custom date
* Party

A document relationship view may later show:

**PO → Bill → Challan → Costing → Ledger**

---

# 21. BACKUP / RESTORE

Business data must be protected.

Planned features:

* Manual backup
* Automatic backup
* Restore
* Database integrity check
* Database optimization/maintenance
* Local backup
* Cloud-sync-friendly backup folder

Before destructive operations or major database changes, create a backup where appropriate.

A backup should include the SQLite database and required business files.

---

# 22. TEST / CLEAN DATA

The user prefers a database clean/test-data mechanism rather than maintaining a separate test database for normal development testing.

Later Settings/Database Tools can provide:

* Clean test data
* Backup before cleaning
* Confirmation before destructive action
* Database integrity check
* Optimize/VACUUM where appropriate

Do not implement this unless the current development version calls for it.

---

# 23. FINAL WINDOWS PACKAGING

Final customers should not need to manually install:

* Python
* SQLite
* PySide6
* Other dependencies

The final application should be packaged as a Windows executable/installer.

Business data should remain outside the executable so application updates do not overwrite customer data.

---

# 24. FUTURE UPDATE MODEL

The application will use versioning, for example:

* 1.0.0 initial release
* 1.0.1 bug fix
* 1.1.0 new feature
* 2.0.0 major change

Database migrations must allow newer application versions to upgrade existing databases safely.

Future versions may include an updater that:

* checks for a new application version
* backs up data
* downloads/installs the update
* runs database migrations
* preserves existing business data

Normal offline operation should not depend on an internet connection.

---

# 25. DEVELOPMENT RULES FOR THE CODING AGENT

These rules are important:

1. Do not build the entire project from this document in one step.
2. Work version-by-version and task-by-task.
3. Before changing code, inspect the existing implementation.
4. Do not overwrite working modules unnecessarily.
5. Reuse existing database, migration, theme and UI architecture.
6. Do not add dependencies unless they are actually needed.
7. After each task, run appropriate tests/smoke tests.
8. Confirm existing functionality still works.
9. Stop after the requested task.
10. Do not automatically start the next version.
11. Keep changes small enough to review.
12. When a requirement is ambiguous, preserve existing working behavior and ask for clarification rather than inventing business rules.
13. Never delete existing business data as part of a feature cleanup unless explicitly requested.
14. Before removing old code, inspect its dependencies and verify that existing workflows do not depend on it.
15. Preserve database relationships and existing records during migrations.
16. Do not perform final UI redesign/polish unless explicitly requested.

---

# 26. CURRENT DEVELOPMENT STATUS

Completed:

* V0.1 Foundation
* V0.2 Main UI Shell
* V0.2 Sidebar improvements
* V0.3 Party Management
* V0.4 Purchase Order Management
* V0.5 PO Items Selection
* V0.6 Bill + Automatic Challan/Gate Pass
* V0.7 Costing Engine
* PO numbering cleanup
* OCR/image-upload cleanup

---

## 26.1 Current database/schema status

Current schema version:

**v7**

Major implemented database progression:

* v1 — foundation/schema version
* v2 — parties
* v3 — purchase orders / PO items
* v4 — legacy vendor-reference/import support
* v5 — bills / bill items / gate passes
* v6 — costing / costing lines / party rates
* v7 — Party-provided PO numbering; removal of global PO uniqueness; legacy vendor reference migrated into PO number

Existing databases must continue to migrate safely.

---

## 26.2 Current implemented functionality

### V0.3 — Party Management

Implemented:

* Party list
* Search
* Add
* Edit
* Activate/deactivate
* Party profile
* Contact information
* Notes
* Created/updated information

### V0.4 — Purchase Orders

Current PO workflow is **manual entry**.

PO contains:

* Party
* Party-provided PO number
* PO date
* PO items
* Description
* Quantity
* Party rate when available

PO number is NOT generated by software.

### V0.5 — PO Items Selection

Implemented:

* Select one or multiple PO items
* Real `po_items.id` preserved
* Quantity/rate loaded from saved PO item
* Selection re-verified against database
* Used by later costing/billing workflows

### V0.6 — Bill + Automatic Challan

Implemented:

* Bill creation from selected PO items
* Globally unique internal Bill number
* Bill items linked to real PO items
* Automatic Challan/Gate Pass
* Globally unique internal Challan number
* Bill ↔ Challan relationship
* Bill/Challan document views

### V0.7 — Costing Engine

Implemented:

* General costing
* Barcode costing
* Sampling costing
* Party-specific saved rates
* Rate autocomplete
* Costing saved against actual `po_item_id`
* Quantity read from the relevant PO item
* Blank/zero rates excluded
* Total cost
* Per-unit cost
* Costing persistence after restart

The V0.7 costing engine currently provides the foundation for the new combined Job/Billing Workspace.

---

# 27. REMOVED FEATURES

The following old functionality has been intentionally removed:

* PO image upload
* PO scanned document upload
* PO document browsing/import
* Tesseract OCR
* OCR extraction
* PyMuPDF PO text extraction
* OCR background thread
* Extracted-document review screen
* OCR status UI
* OCR-specific dependencies

Do not restore these features unless explicitly requested in a future task.

---

# 28. NEXT DEVELOPMENT DIRECTION

The next major functional feature is the **Job / Billing Workspace**.

The intended concept is:

**Party Selection**

↓

**Manual Bill/Job Entry**

↓

**Costing on the same screen**

↓

**Selling/Party PO Rate**

↓

**Profit/Loss**

↓

**Bill**

↓

**Automatic Challan**

The workspace should contain expandable costing sections:

* General
* Sampling
* Barcode

A separate:

**Barcode Inventory**

module/section will handle barcode-specific inventory functionality.

Do not implement the entire future system automatically.

Each new feature must be implemented as a separate, testable task.

---

# 29. IMPORTANT BUSINESS RULE SUMMARY

The coding agent must remember these rules:

### PO

**Party provides PO number.**

AG Printers does not generate PO numbers.

Same PO number may exist for different Parties.

### Bill

AG Printers generates the Bill number.

Bill number is globally unique.

### Challan

AG Printers generates the Challan/Gate Pass number.

Challan number is globally unique.

### Costing

Cost is calculated internally using the costing structure.

### Selling Price

If Party PO already contains a rate:

**use Party PO rate automatically.**

If Party PO has no rate:

**allow manual selling rate entry.**

### Profit

**Selling Rate − Actual Cost = Profit/Loss per Unit**

**Profit/Loss per Unit × Quantity = Total Profit/Loss**

### Data integrity

Never use external PO numbers as database primary keys.

Always preserve internal IDs and relationships.

### Existing data

Never delete existing business data during cleanup or feature development unless explicitly requested.

---

**This document is the master project reference.**

The current coding task always takes priority over future modules.

The coding agent must implement only the requested task, test it, verify existing functionality, and stop.
