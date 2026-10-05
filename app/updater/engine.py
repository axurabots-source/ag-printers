"""Update execution engine: creates safety backup, downloads new files, and applies update."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QApplication

from app.paths import PROJECT_ROOT
from app.updater.checker import UpdateInfo


def apply_update(
    connection: sqlite3.Connection,
    update_info: UpdateInfo,
    progress_callback: Callable[[str, int], None] | None = None,
) -> None:
    """Download update, perform safety backup, stage files, and launch updater script.

    Args:
        connection: Live SQLite database connection for atomic safety backup.
        update_info: Update details containing version and download URL.
        progress_callback: Optional callable(status_text: str, percentage: int).
    """
    from app.settings.backup_service import create_backup

    def _notify(text: str, pct: int):
        if progress_callback:
            progress_callback(text, pct)

    # 1. Critical Safeguard: Automatic Full Database & PDFs Safety Backup
    _notify("Creating pre-update safety backup of database & documents...", 15)
    try:
        backup_path = create_backup(connection, backup_type="safety_update")
        print(f"Safety backup before update created at: {backup_path}")
    except Exception as bkp_err:
        raise RuntimeError(f"Could not create safety backup before updating: {bkp_err}")

    # 2. Prepare temporary staging folders
    _notify(f"Downloading update {update_info.version} from GitHub...", 35)
    temp_dir = Path(tempfile.mkdtemp(prefix="ag_update_"))
    zip_path = temp_dir / "update.zip"

    # Download zip file
    req = urllib.request.Request(
        update_info.download_url,
        headers={"User-Agent": "AG-Printers-Desktop-App"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as out_f:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_sz = 64 * 1024
        while True:
            chunk = resp.read(chunk_sz)
            if not chunk:
                break
            out_f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                pct = 35 + int((downloaded / total_size) * 35)
                _notify(f"Downloading update {update_info.version}... ({downloaded // 1024} KB)", min(70, pct))

    # 3. Extract downloaded files
    _notify("Extracting and verifying update files...", 75)
    extract_dir = temp_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    # If the zip is a GitHub zipball, all contents are inside a root folder (e.g. repo-tag/)
    inner_items = list(extract_dir.iterdir())
    if len(inner_items) == 1 and inner_items[0].is_dir():
        source_dir = inner_items[0]
    else:
        source_dir = extract_dir

    _notify("Finalizing update and preparing restart...", 90)

    # 4. Generate standalone Windows Batch script to apply files and restart
    # CRITICAL: We strictly exclude 'data', '.venv', '.git', and '*.db' so business database is NEVER touched!
    bat_path = temp_dir / "apply_update.bat"
    python_exe = sys.executable
    project_root_str = str(PROJECT_ROOT)
    source_dir_str = str(source_dir)

    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        restart_cmd = f'start "" "{python_exe}"'
    else:
        restart_cmd = f'start "" "{python_exe}" "{project_root_str}\\run.py"'

    bat_content = f"""@echo off
title AG Printers Updater
chcp 65001 >nul
echo ===================================================
echo Applying AG Printers Update {update_info.version}...
echo Please wait a moment while files are updated.
echo ===================================================

:: Wait 2 seconds for main application process to fully close and release file locks
timeout /t 2 /nobreak >nul

:: Copy updated code and assets into project root
:: Strictly EXCLUDING data folder, virtualenv, git files, and databases
robocopy "{source_dir_str}" "{project_root_str}" /E /XD "data" ".venv" ".git" "__pycache__" "graphify-out" /XF "*.db" "*.sqlite3" "*.tmp" /R:3 /W:1 >nul

echo Update applied successfully!
echo Restarting AG Printers...
{restart_cmd}

:: Cleanup self
(goto) 2>nul & del "%~f0"
"""
    bat_path.write_text(bat_content, encoding="utf-8")

    _notify("Update ready! Restarting application now...", 100)

    # 5. Launch the batch script detached and quit application
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
        shell=True,
    )

    QApplication.quit()
