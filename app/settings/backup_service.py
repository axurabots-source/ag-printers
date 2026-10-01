"""Core backup, restore, validation and data clearing engine for AG Printers."""

from __future__ import annotations

import datetime
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from app import __version__
from app.db.schema import SCHEMA_VERSION
from app.paths import DATABASE_FILE
from app.pdf_settings import get_pdf_export_dir
from app.settings.config import (
    get_backup_dir,
    get_retention_count,
    is_auto_backup_enabled,
    record_backup_success,
)


def _format_timestamp(dt: datetime.datetime | None = None) -> tuple[str, str]:
    """Return (filename_timestamp 'YYYY-MM-DD_HH-MM-SS', display_timestamp 'DD Mon YYYY, HH:MM AM/PM')."""
    now = dt or datetime.datetime.now()
    file_ts = now.strftime("%Y-%m-%d_%H-%M-%S")
    display_ts = now.strftime("%d %b %Y, %I:%M %p")
    return file_ts, display_ts


def _get_table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Gather count of records per business table."""
    tables = [
        "parties",
        "purchase_orders",
        "po_items",
        "bills",
        "bill_items",
        "gate_passes",
        "costing",
        "costing_lines",
        "party_rates",
        "barcode_inventory",
    ]
    counts: dict[str, int] = {}
    for tbl in tables:
        try:
            row = connection.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            counts[tbl] = int(row[0]) if row else 0
        except Exception:
            counts[tbl] = 0
    return counts


def create_backup(
    connection: sqlite3.Connection,
    backup_type: str = "manual",
    custom_dir: Path | None = None,
) -> Path:
    """Create a safe, atomic ZIP backup containing the SQLite database and all saved PDFs.
    
    Structure:
        AG_Printers_Backup/
        ├── database/
        │   └── database.db
        ├── PDFs/
        │   ├── Bills/
        │   └── Challans/
        └── backup_info.json

    Returns the Path of the generated .zip file.
    """
    backup_dir = custom_dir or get_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    file_ts, display_ts = _format_timestamp()

    if backup_type == "auto":
        zip_filename = f"AG_Printers_AutoBackup_{file_ts}.zip"
    elif backup_type == "safety_restore":
        zip_filename = f"Before_Restore_{file_ts}.zip"
    elif backup_type == "safety_clear":
        zip_filename = f"Before_Clear_Data_{file_ts}.zip"
    else:
        zip_filename = f"AG_Printers_Backup_{file_ts}.zip"

    final_zip_path = backup_dir / zip_filename
    temp_zip_path = backup_dir / f"{zip_filename}.tmp_{os.getpid()}"

    temp_stage_dir = Path(tempfile.mkdtemp(prefix="ag_backup_stage_"))

    try:
        # 1. Safe SQLite live backup
        db_stage_dir = temp_stage_dir / "database"
        db_stage_dir.mkdir(parents=True, exist_ok=True)
        backup_db_path = db_stage_dir / "database.db"

        # Online consistent backup
        dst_conn = sqlite3.connect(str(backup_db_path))
        try:
            connection.backup(dst_conn)
        finally:
            dst_conn.close()

        # 2. Gather PDF files
        pdf_dir = get_pdf_export_dir()
        bills_pdf_dir = temp_stage_dir / "PDFs" / "Bills"
        challans_pdf_dir = temp_stage_dir / "PDFs" / "Challans"
        bills_pdf_dir.mkdir(parents=True, exist_ok=True)
        challans_pdf_dir.mkdir(parents=True, exist_ok=True)

        bills_count = 0
        challans_count = 0

        if pdf_dir.exists():
            for f in pdf_dir.glob("*.pdf"):
                if f.is_file():
                    fname_lower = f.name.lower()
                    # Copy to Bills and/or Challans folder
                    if "challan" in fname_lower:
                        shutil.copy2(f, challans_pdf_dir / f.name)
                        challans_count += 1
                    else:
                        shutil.copy2(f, bills_pdf_dir / f.name)
                        bills_count += 1

        # 3. Create backup_info.json metadata
        counts = _get_table_counts(connection)
        metadata = {
            "backup_name": zip_filename,
            "timestamp": file_ts,
            "display_time": display_ts,
            "application": "AG Printers",
            "app_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "backup_type": backup_type,
            "record_counts": counts,
            "pdf_counts": {
                "bills_pdfs": bills_count,
                "challans_pdfs": challans_count,
            },
        }

        info_path = temp_stage_dir / "backup_info.json"
        info_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Package into ZIP file atomically
        with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            prefix = "AG_Printers_Backup"
            for root, _dirs, files in os.walk(temp_stage_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(temp_stage_dir)
                    archive_name = f"{prefix}/{rel_p.as_posix()}"
                    zf.write(full_p, archive_name)

        # Atomic rename
        if final_zip_path.exists():
            final_zip_path.unlink()
        temp_zip_path.rename(final_zip_path)

        # Record metadata for manual/auto backups
        if backup_type in ("manual", "auto"):
            record_backup_success(final_zip_path.name, display_ts)

        # Apply retention cleanup if this was an auto backup
        if backup_type == "auto":
            cleanup_old_backups(backup_dir, get_retention_count())

        return final_zip_path

    except Exception:
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        raise
    finally:
        shutil.rmtree(temp_stage_dir, ignore_errors=True)


def validate_backup(zip_path: Path) -> tuple[bool, str, dict[str, Any]]:
    """Validate a backup ZIP file before restoring.
    
    Checks:
    - ZIP archive validity
    - Presence of backup_info.json
    - Presence of database file
    - SQLite integrity check (PRAGMA integrity_check)
    - Presence of fundamental tables (parties, bills, gate_passes)

    Returns (is_valid: bool, error_message: str, metadata: dict).
    """
    if not zip_path.exists():
        return False, "Selected backup file does not exist.", {}

    if not zipfile.is_zipfile(zip_path):
        return False, "Selected file is not a valid ZIP archive.", {}

    temp_dir = Path(tempfile.mkdtemp(prefix="ag_validate_"))
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()

            # Locate backup_info.json
            info_name = next((n for n in namelist if n.endswith("backup_info.json")), None)
            if not info_name:
                return False, "Archive is missing required 'backup_info.json' metadata.", {}

            try:
                info_data = json.loads(zf.read(info_name).decode("utf-8"))
            except Exception as e:
                return False, f"Could not read backup_info.json: {e}", {}

            # Locate database file
            db_entry = next((n for n in namelist if n.endswith("database.db") or n.endswith(".db")), None)
            if not db_entry:
                return False, "Archive is missing the database file (database/database.db).", {}

            # Extract database to test
            extracted_db = temp_dir / "test.db"
            with zf.open(db_entry) as sf, open(extracted_db, "wb") as df:
                shutil.copyfileobj(sf, df)

            # Test database validity
            test_conn = sqlite3.connect(str(extracted_db))
            try:
                test_conn.row_factory = sqlite3.Row
                res = test_conn.execute("PRAGMA integrity_check").fetchone()
                if not res or res[0] != "ok":
                    return False, f"Database corruption detected: {res[0] if res else 'Unknown error'}", {}

                # Check required tables
                tables = {
                    r["name"]
                    for r in test_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                required_tables = {"parties", "bills", "gate_passes"}
                if not required_tables.issubset(tables):
                    missing = required_tables - tables
                    return False, f"Database is missing essential tables: {', '.join(missing)}", {}
            finally:
                test_conn.close()

            return True, "", info_data

    except Exception as exc:
        return False, f"Validation failed: {str(exc)}", {}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def restore_backup(
    connection: sqlite3.Connection,
    zip_path: Path,
) -> dict[str, Any]:
    """Restore database and PDF documents from a validated backup ZIP file.
    
    1. Creates automatic safety backup 'Before_Restore_YYYY-MM-DD_HH-MM-SS.zip'.
    2. Validates backup archive and database.
    3. Safely restores SQLite database into the live connection and file.
    4. Restores PDF documents into current PDF export directory.
    """
    # 1. Automatic safety backup
    safety_backup_path = create_backup(connection, backup_type="safety_restore")

    # 2. Validate
    is_valid, err, metadata = validate_backup(zip_path)
    if not is_valid:
        raise ValueError(f"Invalid backup file: {err}")

    temp_dir = Path(tempfile.mkdtemp(prefix="ag_restore_"))
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        # Locate extracted database
        db_files = list(temp_dir.glob("**/database.db"))
        if not db_files:
            db_files = list(temp_dir.glob("**/*.db"))
        if not db_files:
            raise ValueError("No database file found in extracted backup.")

        extracted_db = db_files[0]

        # 3. Restore SQLite database
        src_conn = sqlite3.connect(str(extracted_db))
        try:
            # Online restore into live connection
            src_conn.backup(connection)
        finally:
            src_conn.close()

        # Also write the physical file to disk
        if DATABASE_FILE.exists():
            shutil.copy2(extracted_db, DATABASE_FILE)

        # 4. Restore PDF files
        pdf_target_dir = get_pdf_export_dir()
        pdf_target_dir.mkdir(parents=True, exist_ok=True)
        pdf_restored_count = 0

        for pdf_file in temp_dir.glob("**/*.pdf"):
            if pdf_file.is_file():
                dest = pdf_target_dir / pdf_file.name
                shutil.copy2(pdf_file, dest)
                pdf_restored_count += 1

        return {
            "success": True,
            "safety_backup": safety_backup_path.name,
            "restored_from": zip_path.name,
            "pdfs_restored": pdf_restored_count,
            "metadata": metadata,
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def clear_business_data(connection: sqlite3.Connection) -> dict[str, Any]:
    """Permanently delete business records from the database in a safe transaction.
    
    1. Creates automatic safety backup 'Before_Clear_Data_YYYY-MM-DD_HH-MM-SS.zip'.
    2. Deletes records from business tables while strictly preserving:
       - Schema & tables
       - schema_version
       - Settings and configuration
    """
    # 1. Automatic safety backup
    safety_backup = create_backup(connection, backup_type="safety_clear")

    # 2. Delete business records in a safe transaction
    tables_to_clear = [
        "gate_passes",
        "bill_items",
        "bills",
        "costing_lines",
        "costing",
        "po_items",
        "purchase_orders",
        "party_rates",
        "barcode_inventory",
        "parties",
    ]

    deleted_counts: dict[str, int] = {}

    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("PRAGMA foreign_keys = OFF")

        for table in tables_to_clear:
            row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            count = int(row[0]) if row else 0
            connection.execute(f"DELETE FROM {table}")
            deleted_counts[table] = count

        # Reset SQLite auto-increment sequences for these tables
        placeholders = ", ".join("?" for _ in tables_to_clear)
        connection.execute(
            f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})",
            tables_to_clear,
        )

        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()

        return {
            "success": True,
            "safety_backup": safety_backup.name,
            "deleted_counts": deleted_counts,
            "total_records_cleared": sum(deleted_counts.values()),
        }

    except Exception as exc:
        connection.rollback()
        connection.execute("PRAGMA foreign_keys = ON")
        raise RuntimeError(f"Clear business data failed and was safely rolled back: {exc}")


def cleanup_old_backups(backup_dir: Path, keep_count: int) -> int:
    """Remove older automatic backups exceeding keep_count.
    
    CRITICAL:
    - ONLY removes files named 'AG_Printers_AutoBackup_*.zip'.
    - NEVER deletes manual backups ('AG_Printers_Backup_*.zip').
    - NEVER deletes safety backups ('Before_*.zip').
    """
    if keep_count <= 0:
        return 0

    if not backup_dir.exists():
        return 0

    auto_files = [
        f for f in backup_dir.glob("AG_Printers_AutoBackup_*.zip")
        if f.is_file()
    ]

    # Sort oldest first (by mtime)
    auto_files.sort(key=lambda p: p.stat().st_mtime)

    deleted = 0
    while len(auto_files) > keep_count:
        oldest = auto_files.pop(0)
        try:
            oldest.unlink()
            deleted += 1
        except Exception:
            pass

    return deleted


def check_and_run_auto_backup(connection: sqlite3.Connection) -> Path | None:
    """Run daily automatic backup if enabled and not already performed today."""
    if not is_auto_backup_enabled():
        return None

    backup_dir = get_backup_dir()
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # Check if an auto-backup was already created today
    for f in backup_dir.glob(f"AG_Printers_AutoBackup_{today_str}_*.zip"):
        if f.is_file():
            return None

    try:
        return create_backup(connection, backup_type="auto")
    except Exception as exc:
        print(f"Warning: Daily auto backup failed: {exc}")
        return None


def get_backup_folder_stats() -> dict[str, Any]:
    """Retrieve statistics of backups in the designated backup folder."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return {
            "total_count": 0,
            "total_size_mb": 0.0,
            "latest_file": "",
            "latest_time": "",
        }

    zip_files = [f for f in backup_dir.glob("*.zip") if f.is_file()]
    total_count = len(zip_files)
    total_bytes = sum(f.stat().st_size for f in zip_files)
    total_mb = round(total_bytes / (1024 * 1024), 2)

    latest_file = ""
    latest_time = ""
    if zip_files:
        zip_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        newest = zip_files[0]
        latest_file = newest.name
        latest_dt = datetime.datetime.fromtimestamp(newest.stat().st_mtime)
        latest_time = latest_dt.strftime("%d %b %Y, %I:%M %p")

    return {
        "total_count": total_count,
        "total_size_mb": total_mb,
        "latest_file": latest_file,
        "latest_time": latest_time,
    }
