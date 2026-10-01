"""SQLite connection handling for AG Printers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.paths import DATABASE_FILE, ensure_data_dirs


def create_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the SQLite database, creating the file if it does not exist.

    Defaults to ``data/database/business.db`` inside the project folder.
    """
    if db_path is None:
        ensure_data_dirs()
        db_path = DATABASE_FILE
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
