"""Filesystem paths used by AG Printers.

Every path is derived from the project location, so nothing depends on
hard-coded, computer-specific paths.
"""

from __future__ import annotations

from pathlib import Path

# Project root = folder that contains run.py (parent of the app/ package).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = DATA_DIR / "database"
DATABASE_FILE = DATABASE_DIR / "business.db"


def ensure_data_dirs() -> None:
    """Create the data folders if they do not exist yet."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
