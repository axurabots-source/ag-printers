"""Application bootstrap: database + main window."""

from __future__ import annotations

import sys

from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from app.db import create_connection, initialize_database
from app.main_window import MainWindow
from app.ui.theme import APP_STYLESHEET


def run() -> int:
    """Start the application and return its exit code."""
    # Ensure Windows taskbar displays the custom application icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("axurabots.agprinters.app.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("AG Printers")
    app.setOrganizationName("AG Printers")

    # Set application icon (Taskbar, system tray, window headers)
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
    if not icon_path.exists():
        icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Load custom modern typeface (Plus Jakarta Sans)
    font_path = Path(__file__).resolve().parent / "ui" / "fonts" / "PlusJakartaSans.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
        app.setFont(QFont("Plus Jakarta Sans", 10))
    else:
        app.setFont(QFont("Segoe UI", 10))

    # Modern professional desktop look (pure Qt style sheets).
    app.setStyleSheet(APP_STYLESHEET)

    # Open (and on first run create) the database, then apply migrations.
    connection = create_connection()
    version = initialize_database(connection)
    print(f"Database ready (schema version {version}).")

    window = MainWindow(connection)
    window.show()

    exit_code = app.exec()
    connection.close()
    return exit_code
