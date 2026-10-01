"""Filesystem paths used by AG Printers.

Every path is derived from the project location, so nothing depends on
hard-coded, computer-specific paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root: When frozen (PyInstaller EXE), point to the directory containing the executable;
# when running from source, point to the repository root containing run.py.
if getattr(sys, "frozen", False):
    _EXE_DIR = Path(sys.executable).resolve().parent
    if (_EXE_DIR / "data").exists():
        PROJECT_ROOT = _EXE_DIR
    elif (Path.cwd() / "data").exists():
        PROJECT_ROOT = Path.cwd()
    elif (_EXE_DIR.parent.parent / "data").exists():
        PROJECT_ROOT = _EXE_DIR.parent.parent
    else:
        PROJECT_ROOT = _EXE_DIR
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = DATA_DIR / "database"
DATABASE_FILE = DATABASE_DIR / "business.db"


def ensure_data_dirs() -> None:
    """Create the data folders if they do not exist yet."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
