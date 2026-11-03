# AG PRINTERS — AGENT & SESSION GUIDELINES

## 1. Project Overview & Context
**AG Printers** is a fast, offline-first Windows desktop Business Management Application tailored for the printing industry.

* **Current Release Version:** `v1.0.5`
* **Database Schema Version:** `17` (SQLite, automatic migration engine)
* **Tech Stack:** Python 3.13+, PySide6 (Qt), SQLite (`sqlite3` built-in), PyInstaller.
* **Architecture:** Modular architecture with clean separation between UI (`app/ui`, `app/<module>/page.py`) and Database Repositories (`app/db/<module>.py`).
* **Main Workflow:** Party → Purchase Order → PO Items → Job / Billing Workspace → Costing → Profit/Loss → Bill → Gate Pass / Challan → Ledger (Khata) → Reports.

---

## 2. Active Session: AG Khata (Ledger & Accounts)
The current active focus of this session is the **AG Khata (Ledger)** module:

* **Primary File:** [`app/ledger/page.py`](file:///d:/AG%20Printers/app/ledger/page.py)
* **Party Profile & History:** [`app/parties/profile_view.py`](file:///d:/AG%20Printers/app/parties/profile_view.py)
* **Database Models:** [`app/db/bills.py`](file:///d:/AG%20Printers/app/db/bills.py) & [`app/db/schema.py`](file:///d:/AG%20Printers/app/db/schema.py)
* **Shell Integration:** [`app/main_window.py`](file:///d:/AG%20Printers/app/main_window.py)

### Current Capabilities:
1. **Profit Ledger:** Displays all generated bills with Invoice #, Date, Party Name, PO #, Gate Pass #, Total Amount, Net Profit, and PDF link.
2. **KPI Header Cards:** Live calculation of Total Invoiced, Total Cost, Total Net Profit, and Average Margin %.
3. **Advanced Filtering:** Real-time search across all columns + Party filter dropdown (*All Parties (All Round)* or specific party) + multi-mode date picker (*All Dates, Today, This Month, Specific Date, Date Range*).
4. **Official Statement / Ledger PDF Export:** Interactive **Export Statement PDF** modal dialog with live preview. Renders multi-page A4 vector PDF showing Sr, Date, Invoice #, Party Name, PO #, Gate Pass, and Total Amount (PKR) with grand totals.
5. **Strict Profit Confidentiality:** Excludes Net Profit, Production Cost, and Margin % from the customer/client-facing PDF statement.

### Khata Roadmap & Next Steps:
* **Debit / Credit (Jama-Udhar) Ledger:** Tracking payments received, partial payments, and outstanding balances per party.
* **Accounting Reconciliation:** Balancing invoices against actual receipts.

---

## 3. Barcode Inventory (Stock Movements & Audit Logs)
* **Primary Files:** [`app/inventory/page.py`](file:///d:/AG%20Printers/app/inventory/page.py), [`app/inventory/history_dialog.py`](file:///d:/AG%20Printers/app/inventory/history_dialog.py), [`app/db/barcode_inventory.py`](file:///d:/AG%20Printers/app/db/barcode_inventory.py)
* **Schema Migration:** Version 17 in [`app/db/schema.py`](file:///d:/AG%20Printers/app/db/schema.py) (`barcode_inventory_in_logs`).
* **Capabilities:**
  1. Replaced "Date Added" & "Last Updated" with **Last In** and **Last Out** columns.
  2. Each cell displays bold Quantity on top (`+Qty` in emerald green or `-Qty` in crimson red) and compact formatted date beneath (`DD-Mon-YYYY`).
  3. Interactive click on **Last In** opens a modal audit table showing all inward entries (date, quantity received, notes/supplier).
  4. Interactive click on **Last Out** opens a modal audit table showing all outward bill deductions (date, quantity deducted, bill/invoice #, party name).
  5. Interactive click on **Detail / Description** opens the Edit Item modal directly.
  6. Removed Edit & Delete buttons from the table row; table now cleanly retains only **+ Stock**, while **Delete Item** is located safely inside the Edit dialog.
  7. Compact responsive layout preventing table cutoff when sidebar is opened.

---

## 4. PDF Document Engine & Auto Font-Shrink
* **Primary File:** [`app/jobs/a4_view.py`](file:///d:/AG%20Printers/app/jobs/a4_view.py)
* **Capabilities:**
  1. Implemented `_draw_fitting_text` using `QFontMetricsF`.
  2. If any table row description, customer name, or meta chip overflows its allocated cell width, font size dynamically shrinks down (with micro-adjustments) so text is never truncated, clipped, or hidden.

---

## 5. Version 1.0.5 Changelog & Release Summary
* **Release Date:** 03-Nov-2026
* **Key Features & Enhancements:**
  1. **Ledger Statement PDF Export:** Dedicated high-quality multi-page A4 PDF statement generator (`app/ledger/statement_pdf.py`) with company logo, brand headers, alternating row styles, and grand total calculations.
  2. **Party & Date Range Selection:** Added real-time Party filter dropdown on the Ledger screen and an interactive **Export Statement PDF** modal (`app/ledger/export_dialog.py`) with live invoice count and total amount preview.
  3. **Strict Profit Confidentiality:** Excludes Net Profit, Production Cost, and Margin percentages from all client-facing exported statement PDFs.
  4. **Multi-page Vector Pagination:** Dynamic multi-page pagination (`Page X of Y`) ensuring no overflow or table clipping across large invoice records.

---

## 6. Version 1.0.4 Changelog & Release Summary
* **Release Date:** 26-Oct-2026
* **Key Features & Enhancements:**
  1. **Pick & Drop Row Reordering:** Interactive drag-and-drop table row reordering for Bill items (`DragHandleCell` with visual drop indicator line) and `▲`/`▼` nudge buttons.
  2. **Flexible Billing Items:** Quantity and Sell Rate made optional; blank values smoothly suppress `0` / `0.00` on bills and PDF exports.
  3. **PDF Alignment & Font Auto-Shrink:** Description header and row text left-aligned; `_draw_fitting_text` with `QFontMetricsF` ensures long text never clips or hides.
  4. **Barcode Inventory Stock Movements:** Added **Last In** and **Last Out** columns with `+Qty` (green) / `-Qty` (red) on top and date beneath.
  5. **Movement Audit Popups:** Clickable cells open complete historical log tables for Inward stock entries (`barcode_inventory_in_logs`) and Outward deductions (`bill_inventory_deductions`).
  6. **Product Detail Click & Safe Delete:** Clicking product detail in table opens Edit Dialog directly. Delete button moved safely inside Edit Dialog; table retains clean single `+ Stock` button.
  7. **Sidebar Open Layout Fix:** Compact table column layout (from 830px to 647px fixed) prevents table from getting pushed off-screen when sidebar opens.

---

## 7. Agent Engineering Rules & Guidelines
1. **Preserve Existing Architecture:** Never break existing working modules (Parties, Bills, Challans, Costing, Inventory, Settings).
2. **Offline-First & Zero Extra Bloat:** Keep dependencies lean. Avoid adding unnecessary heavy third-party packages.
3. **Database Integrity:**
   * Always write migrations in [`app/db/schema.py`](file:///d:/AG%20Printers/app/db/schema.py) when altering tables.
   * Preserve user business data during updates.
4. **UI/UX Consistency:** Use established design tokens from [`app/ui/theme.py`](file:///d:/AG%20Printers/app/ui/theme.py) and consistent styling with the existing PySide6 screens.
5. **Session Continuity:** Always check this file and [`AG_Printers_PROJECT_SPEC.md`](file:///d:/AG%20Printers/AG_Printers_PROJECT_SPEC.md) before implementing changes.
