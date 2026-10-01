"""PDF settings and directory persistence for AG Printers.

Manages the user-selected local machine folder where all Bill & Challan PDFs are saved.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from app.paths import DATA_DIR, ensure_data_dirs

CONFIG_FILE = DATA_DIR / "pdf_folder.txt"
DEFAULT_PDF_DIR = DATA_DIR / "exported_bills"


def get_pdf_export_dir() -> Path:
    """Return the currently selected PDF export directory on the local machine."""
    ensure_data_dirs()
    if CONFIG_FILE.exists():
        try:
            content = CONFIG_FILE.read_text(encoding="utf-8").strip()
            if content:
                p = Path(content).resolve()
                p.mkdir(parents=True, exist_ok=True)
                return p
        except Exception:
            pass

    DEFAULT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_PDF_DIR


def set_pdf_export_dir(path: Path | str) -> Path:
    """Save the user-selected PDF export directory."""
    ensure_data_dirs()
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(str(p), encoding="utf-8")
    return p


def build_pdf_filename(party_name: str, bill_date: str, bill_number: str) -> str:
    """Generate a clean, unique filename containing Party Name + Date + Bill Number.

    Example:
        'Packages_Limited_2026-09-30_Bill_BILL-0001.pdf'
    """
    clean_party = re.sub(r'[\\/*?:"<>|]', "", party_name or "General").strip()
    clean_party = re.sub(r"\s+", "_", clean_party)
    clean_doc = re.sub(r'[\\/*?:"<>|]', "", bill_number or "Doc").strip()
    clean_date = re.sub(r'[\\/*?:"<>|]', "", bill_date or "Date").strip()

    return f"{clean_party}_{clean_date}_Bill_{clean_doc}.pdf"


def open_pdf_file(filepath: Path | str) -> bool:
    """Open a PDF directly in the operating system's default PDF viewer (not opening folder)."""
    p = Path(filepath)
    if not p.exists():
        return False

    try:
        if sys.platform == "win32":
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return True
    except Exception:
        return False
