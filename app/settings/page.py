"""Settings screen for AG Printers: Backup, Restore, Automation, and Safe Data Clearing."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.pdf_settings import get_pdf_export_dir, set_pdf_export_dir
from app.settings.backup_service import (
    clear_business_data,
    create_backup,
    get_backup_folder_stats,
    restore_backup,
    validate_backup,
)
from app.settings.config import (
    get_backup_dir,
    get_last_backup_info,
    get_retention_count,
    is_auto_backup_enabled,
    set_auto_backup_enabled,
    set_backup_dir,
    set_retention_count,
)
from app.updater.checker import UpdateCheckerThread, UpdateInfo
from app.updater.dialog import UpdateDialog


class ClearDataConfirmDialog(QDialog):
    """Safety modal requiring the user to explicitly type 'CLEAR'."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirm Clear Business Data")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog {
                background: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        warn_title = QLabel("Permanently Clear Business Data?")
        warn_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #dc2626;")
        layout.addWidget(warn_title)

        warn_body = QLabel(
            "This action will permanently remove all business records (Parties, Purchase Orders, "
            "Invoices, Gate Passes, Costing, and Barcode Inventory) from the database.<br/><br/>"
            "<b>A safety backup of the current database and PDFs will be created automatically first.</b><br/><br/>"
            "To confirm this destructive action, please type <b>CLEAR</b> below:"
        )
        warn_body.setWordWrap(True)
        warn_body.setStyleSheet("font-size: 12px; color: #334155; line-height: 1.4;")
        layout.addWidget(warn_body)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type CLEAR to confirm")
        self._input.setStyleSheet("""
            QLineEdit {
                background: #f1f5f9;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                color: #0f172a;
            }
        """)
        layout.addWidget(self._input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._confirm_btn = QPushButton("Create Backup & Clear Data")
        self._confirm_btn.setStyleSheet("""
            QPushButton {
                background: #dc2626;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 700;
            }
            QPushButton:hover { background: #b91c1c; }
        """)
        self._confirm_btn.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(self._confirm_btn)

        layout.addLayout(btn_row)

    def _validate_and_accept(self) -> None:
        if self._input.text().strip() == "CLEAR":
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Confirmation Required",
                "You must type 'CLEAR' in uppercase to confirm clearing data.",
            )


class SettingsPage(QWidget):
    """Central configuration and data lifecycle management screen."""

    data_reloaded = Signal()

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: #f8fafc;")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(28, 22, 28, 28)
        self._layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        sub = QLabel("Manage system preferences, automated backups, file recovery, and database lifecycle")
        sub.setStyleSheet("font-size: 12px; color: #64748b;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        self._layout.addLayout(title_box)

        # 1. General & Documents Section
        self._build_general_section()

        # 2. Backup & Restore Section
        self._build_backup_section()

        # 3. Application Updates Section (GitHub Releases)
        self._build_updater_section()

        # 4. Clear Data (Danger Zone) Section
        self._build_clear_data_section()

        self._layout.addStretch(1)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

        self.refresh()

    def reset_to_list(self) -> None:
        self.refresh()

    # -- General / Documents --------------------------------------------------

    def _build_general_section(self) -> None:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        sec_hdr = QLabel("GENERAL")
        sec_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        layout.addWidget(sec_hdr)

        row = QHBoxLayout()
        row.setSpacing(12)

        lbl_box = QVBoxLayout()
        lbl_box.setSpacing(2)
        lbl_title = QLabel("PDF Save Folder")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")
        self._pdf_dir_lbl = QLabel()
        self._pdf_dir_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        lbl_box.addWidget(lbl_title)
        lbl_box.addWidget(self._pdf_dir_lbl)
        row.addLayout(lbl_box)
        row.addStretch(1)

        change_pdf_btn = QPushButton("Change Folder")
        change_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_pdf_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        change_pdf_btn.clicked.connect(self._on_change_pdf_dir)
        row.addWidget(change_pdf_btn)

        open_pdf_btn = QPushButton("Open Folder")
        open_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_pdf_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        open_pdf_btn.clicked.connect(self._on_open_pdf_dir)
        row.addWidget(open_pdf_btn)

        layout.addLayout(row)
        self._layout.addWidget(card)

    # -- Backup & Restore -----------------------------------------------------

    def _build_backup_section(self) -> None:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        sec_hdr = QLabel("BACKUP & RESTORE")
        sec_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        layout.addWidget(sec_hdr)

        # 1. Backup Location Row
        loc_row = QHBoxLayout()
        loc_row.setSpacing(12)

        loc_box = QVBoxLayout()
        loc_box.setSpacing(2)
        loc_title = QLabel("Backup Location")
        loc_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #0f172a;")
        self._backup_dir_lbl = QLabel()
        self._backup_dir_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        loc_box.addWidget(loc_title)
        loc_box.addWidget(self._backup_dir_lbl)
        loc_row.addLayout(loc_box)
        loc_row.addStretch(1)

        change_loc_btn = QPushButton("Change Location")
        change_loc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_loc_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        change_loc_btn.clicked.connect(self._on_change_backup_dir)
        loc_row.addWidget(change_loc_btn)

        open_bk_btn = QPushButton("Open Backup Folder")
        open_bk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_bk_btn.setStyleSheet("""
            QPushButton {
                background: #e2e8f0;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #cbd5e1; }
        """)
        open_bk_btn.clicked.connect(self._on_open_backup_dir)
        loc_row.addWidget(open_bk_btn)
        layout.addLayout(loc_row)

        # Separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #f1f5f9;")
        layout.addWidget(sep)

        # 2. Status & Info Row
        status_box = QHBoxLayout()
        status_box.setSpacing(20)

        last_bk_vbox = QVBoxLayout()
        last_bk_vbox.setSpacing(2)
        last_bk_title = QLabel("Last Successful Backup")
        last_bk_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        self._last_backup_lbl = QLabel("Never")
        self._last_backup_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        last_bk_vbox.addWidget(last_bk_title)
        last_bk_vbox.addWidget(self._last_backup_lbl)
        status_box.addLayout(last_bk_vbox)

        count_vbox = QVBoxLayout()
        count_vbox.setSpacing(2)
        count_title = QLabel("Archived Backups")
        count_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b;")
        self._backup_count_lbl = QLabel("0 files")
        self._backup_count_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        count_vbox.addWidget(count_title)
        count_vbox.addWidget(self._backup_count_lbl)
        status_box.addLayout(count_vbox)

        status_box.addStretch(1)

        # Main Action Buttons
        self._create_bk_btn = QPushButton("Create Backup Now")
        self._create_bk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._create_bk_btn.setStyleSheet("""
            QPushButton {
                background: #1d4e89;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background: #24589b; }
        """)
        self._create_bk_btn.clicked.connect(self._on_create_backup)
        status_box.addWidget(self._create_bk_btn)

        self._restore_bk_btn = QPushButton("Restore Backup")
        self._restore_bk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restore_bk_btn.setStyleSheet("""
            QPushButton {
                background: #e0f2fe;
                color: #0369a1;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background: #bae6fd; }
        """)
        self._restore_bk_btn.clicked.connect(self._on_restore_backup)
        status_box.addWidget(self._restore_bk_btn)

        layout.addLayout(status_box)

        # Separator line
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #f1f5f9;")
        layout.addWidget(sep2)

        # 3. Automation & Retention Options
        opt_row = QHBoxLayout()
        opt_row.setSpacing(24)

        self._auto_backup_cb = QCheckBox("Automatic Daily Backup on Startup")
        self._auto_backup_cb.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                font-weight: 600;
                color: #1e293b;
            }
        """)
        self._auto_backup_cb.toggled.connect(self._on_auto_backup_toggled)
        opt_row.addWidget(self._auto_backup_cb)

        opt_row.addSpacing(12)

        retention_lbl = QLabel("Keep Last:")
        retention_lbl.setStyleSheet("font-size: 12px; color: #475569;")
        opt_row.addWidget(retention_lbl)

        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(1, 100)
        self._retention_spin.setSuffix(" backups")
        self._retention_spin.setStyleSheet("""
            QSpinBox {
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                background: #f1f5f9;
                color: #0f172a;
            }
        """)
        self._retention_spin.valueChanged.connect(self._on_retention_changed)
        opt_row.addWidget(self._retention_spin)

        opt_row.addStretch(1)
        layout.addLayout(opt_row)

        self._layout.addWidget(card)

    # -- Application Updates (GitHub Releases) --------------------------------

    def _build_updater_section(self) -> None:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        sec_hdr = QLabel("APPLICATION UPDATES")
        sec_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        layout.addWidget(sec_hdr)

        row = QHBoxLayout()
        row.setSpacing(16)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        info_title = QLabel(f"AG Printers Desktop (Installed: v{__version__})")
        info_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        self._update_status_lbl = QLabel("Channel: GitHub Releases (axurabots-source/ag-printers)")
        self._update_status_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        info_box.addWidget(info_title)
        info_box.addWidget(self._update_status_lbl)
        row.addLayout(info_box, 1)

        self._check_update_btn = QPushButton("Check for Updates")
        self._check_update_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #94a3b8; }
        """)
        self._check_update_btn.clicked.connect(self._manual_check_update)
        row.addWidget(self._check_update_btn)

        layout.addLayout(row)
        self._layout.addWidget(card)

    def _manual_check_update(self) -> None:
        self._check_update_btn.setEnabled(False)
        self._update_status_lbl.setText("Checking GitHub for newer releases...")
        self._updater_thread = UpdateCheckerThread(parent=self)
        self._updater_thread.update_available.connect(self._on_settings_update_available)
        self._updater_thread.up_to_date.connect(self._on_settings_up_to_date)
        self._updater_thread.check_failed.connect(self._on_settings_update_failed)
        self._updater_thread.start()

    def _on_settings_update_available(self, info: UpdateInfo) -> None:
        self._check_update_btn.setEnabled(True)
        self._update_status_lbl.setText(f"🚀 New update {info.version} is available!")
        dlg = UpdateDialog(self._connection, info, parent=self)
        dlg.exec()

    def _on_settings_up_to_date(self) -> None:
        self._check_update_btn.setEnabled(True)
        self._update_status_lbl.setText(f"✓ You are running the latest version (v{__version__}).")

    def _on_settings_update_failed(self, err: str) -> None:
        self._check_update_btn.setEnabled(True)
        self._update_status_lbl.setText("Could not connect to GitHub releases.")

    # -- Clear Data (Danger Zone) ---------------------------------------------

    def _build_clear_data_section(self) -> None:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        sec_hdr = QLabel("CLEAR DATA (DANGER ZONE)")
        sec_hdr.setStyleSheet("font-size: 11px; font-weight: 700; color: #dc2626; letter-spacing: 0.5px;")
        layout.addWidget(sec_hdr)

        row = QHBoxLayout()
        row.setSpacing(16)

        desc_box = QVBoxLayout()
        desc_box.setSpacing(2)
        desc_title = QLabel("Clear Business Data")
        desc_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        desc_body = QLabel(
            "Permanently wipes customer bills, gate passes, purchase orders, costing sheets, and inventory records. "
            "System settings and schema structure are never touched. An automatic safety backup is always generated first."
        )
        desc_body.setWordWrap(True)
        desc_body.setStyleSheet("font-size: 12px; color: #64748b; line-height: 1.4;")
        desc_box.addWidget(desc_title)
        desc_box.addWidget(desc_body)
        row.addLayout(desc_box, 1)

        clear_btn = QPushButton("Clear Business Data")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #dc2626;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background: #b91c1c; }
        """)
        clear_btn.clicked.connect(self._on_clear_business_data)
        row.addWidget(clear_btn)

        layout.addLayout(row)
        self._layout.addWidget(card)

    # -- Event Handlers -------------------------------------------------------

    def refresh(self) -> None:
        """Reload all configuration paths, statuses and stats from disk."""
        # 1. PDF Export Dir
        pdf_dir = get_pdf_export_dir()
        self._pdf_dir_lbl.setText(str(pdf_dir))

        # 2. Backup Location
        bk_dir = get_backup_dir()
        self._backup_dir_lbl.setText(str(bk_dir))

        # 3. Status
        stats = get_backup_folder_stats()
        last_time, last_file = get_last_backup_info()
        display_time = last_time or stats["latest_time"] or "No backup recorded yet"
        self._last_backup_lbl.setText(display_time)

        if stats["total_count"] > 0:
            self._backup_count_lbl.setText(f"{stats['total_count']} archives ({stats['total_size_mb']} MB)")
        else:
            self._backup_count_lbl.setText("0 archives")

        # 4. Settings Toggles
        self._auto_backup_cb.blockSignals(True)
        self._auto_backup_cb.setChecked(is_auto_backup_enabled())
        self._auto_backup_cb.blockSignals(False)

        self._retention_spin.blockSignals(True)
        self._retention_spin.setValue(get_retention_count())
        self._retention_spin.blockSignals(False)

    def _on_change_pdf_dir(self) -> None:
        current = str(get_pdf_export_dir())
        chosen = QFileDialog.getExistingDirectory(self, "Select PDF Save Folder", current)
        if chosen:
            set_pdf_export_dir(chosen)
            self.refresh()

    def _on_open_pdf_dir(self) -> None:
        p = get_pdf_export_dir()
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)], check=False)

    def _on_change_backup_dir(self) -> None:
        current = str(get_backup_dir())
        chosen = QFileDialog.getExistingDirectory(self, "Select Backup Storage Folder", current)
        if chosen:
            set_backup_dir(chosen)
            self.refresh()

    def _on_open_backup_dir(self) -> None:
        p = get_backup_dir()
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))
            else:
                subprocess.run(["xdg-open", str(p)], check=False)

    def _on_auto_backup_toggled(self, checked: bool) -> None:
        set_auto_backup_enabled(checked)

    def _on_retention_changed(self, value: int) -> None:
        set_retention_count(value)

    def _on_create_backup(self) -> None:
        try:
            zip_path = create_backup(self._connection, backup_type="manual")
            self.refresh()
            QMessageBox.information(
                self,
                "Backup Successful",
                f"Backup created successfully.\n\n"
                f"File: {zip_path.name}\n"
                f"Location: {zip_path.parent}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Backup Creation Failed",
                f"Could not complete backup operation:\n\n{str(exc)}",
            )

    def _on_restore_backup(self) -> None:
        current_dir = str(get_backup_dir())
        chosen_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup ZIP to Restore",
            current_dir,
            "Backup Archives (*.zip);;All Files (*.*)",
        )
        if not chosen_file:
            return

        zip_path = Path(chosen_file)

        # 1. Validate first
        is_valid, err_msg, meta = validate_backup(zip_path)
        if not is_valid:
            QMessageBox.critical(
                self,
                "Invalid Backup Archive",
                f"The selected file cannot be restored:\n\n{err_msg}",
            )
            return

        # 2. Confirmation Dialog
        app_ver = meta.get("app_version", "Unknown")
        created_at = meta.get("display_time") or meta.get("timestamp", "Unknown")
        answer = QMessageBox.warning(
            self,
            "Restore this backup?",
            f"Are you sure you want to restore this backup?\n\n"
            f"Archive: {zip_path.name}\n"
            f"Created: {created_at} (Version: {app_ver})\n\n"
            "Current application data will be replaced by the selected backup. "
            "A safety backup of the current data will be created first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        # 3. Perform Restore
        try:
            res = restore_backup(self._connection, zip_path)
            self.refresh()
            self.data_reloaded.emit()

            QMessageBox.information(
                self,
                "Restore Completed",
                f"Backup restored successfully.\n\n"
                f"Restored From: {res['restored_from']}\n"
                f"PDFs Restored: {res['pdfs_restored']}\n"
                f"Safety Backup Created: {res['safety_backup']}\n\n"
                "All views and documents have been refreshed.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Restore Failed",
                f"Failed to restore backup:\n\n{str(exc)}",
            )

    def _on_clear_business_data(self) -> None:
        dlg = ClearDataConfirmDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            res = clear_business_data(self._connection)
            self.refresh()
            self.data_reloaded.emit()

            QMessageBox.information(
                self,
                "Business Data Cleared",
                f"Business records cleared successfully.\n\n"
                f"Total Records Cleared: {res['total_records_cleared']}\n"
                f"Safety Backup Saved: {res['safety_backup']}\n\n"
                "The database structure and configuration remain intact.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Clear Data Failed",
                f"Failed to clear business data:\n\n{str(exc)}",
            )
