"""Modern modal dialog prompting the user to review and apply an update."""

from __future__ import annotations

import sqlite3
import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app import __version__
from app.updater.checker import UpdateInfo
from app.updater.engine import apply_update


class UpdateDialog(QDialog):
    """User-facing dialog showing release changelog, safety backup guarantee, and update button."""

    _progress_signal = Signal(str, int)
    _error_signal = Signal(str)

    def __init__(self, connection: sqlite3.Connection, update_info: UpdateInfo, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._info = update_info
        self._is_updating = False

        self.setWindowTitle(f"New Update Available - {self._info.version}")
        self.setFixedSize(540, 440)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Title & Version Comparison
        t_box = QVBoxLayout()
        t_box.setSpacing(4)

        head_lbl = QLabel(f"🚀 New Version Available: {self._info.version}")
        head_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A;")
        t_box.addWidget(head_lbl)

        ver_sub = QLabel(f"Current Installed Version: v{__version__}  ➜  Latest: {self._info.version}")
        ver_sub.setStyleSheet("font-size: 11.5px; color: #475569; font-weight: 600;")
        t_box.addWidget(ver_sub)
        layout.addLayout(t_box)

        # Release Notes Card
        notes_card = QFrame()
        notes_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        n_layout = QVBoxLayout(notes_card)
        n_layout.setContentsMargins(12, 10, 12, 10)
        n_layout.setSpacing(6)

        notes_title = QLabel("What's New in this Update:")
        notes_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #334155; border: none; background: transparent;")
        n_layout.addWidget(notes_title)

        notes_view = QTextEdit()
        notes_view.setReadOnly(True)
        notes_view.setPlainText(self._info.notes)
        notes_view.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                color: #1E293B;
                line-height: 1.4;
            }
        """)
        n_layout.addWidget(notes_view)
        layout.addWidget(notes_card, 1)

        # Safety Assurance Shield
        safety_banner = QFrame()
        safety_banner.setStyleSheet("""
            QFrame {
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        sb_layout = QHBoxLayout(safety_banner)
        sb_layout.setContentsMargins(4, 4, 4, 4)
        sb_layout.setSpacing(8)

        shield_icon = QLabel("🛡️")
        shield_icon.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        sb_layout.addWidget(shield_icon)

        safety_text = QLabel("Safety Shield: A full database and documents backup is automatically created before applying.")
        safety_text.setStyleSheet("font-size: 10.5px; color: #166534; font-weight: 600; border: none; background: transparent;")
        safety_text.setWordWrap(True)
        sb_layout.addWidget(safety_text, 1)
        layout.addWidget(safety_banner)

        # Progress Indicator (starts hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
                font-weight: 700;
                color: #0F172A;
                background-color: #F8FAFC;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #475569; font-weight: 600;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setVisible(False)
        layout.addWidget(self.status_lbl)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.addStretch(1)

        self.cancel_btn = QPushButton("Remind Me Later")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 11.5px;
                font-weight: 600;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.cancel_btn)

        self.update_btn = QPushButton("Update Now & Restart")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
            }
        """)
        self.update_btn.clicked.connect(self._start_update)
        btn_box.addWidget(self.update_btn)

        layout.addLayout(btn_box)

        self._progress_signal.connect(self._on_progress)
        self._error_signal.connect(self._on_error)

    def _start_update(self) -> None:
        if self._is_updating:
            return
        self._is_updating = True

        self.update_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setVisible(True)
        self.status_lbl.setText("Starting update process...")

        def _worker():
            try:
                apply_update(
                    self._connection,
                    self._info,
                    progress_callback=lambda txt, pct: self._progress_signal.emit(txt, pct),
                )
            except Exception as err:
                self._error_signal.emit(str(err))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _on_progress(self, text: str, pct: int) -> None:
        self.status_lbl.setText(text)
        self.progress_bar.setValue(pct)

    def _on_error(self, err_msg: str) -> None:
        self._is_updating = False
        self.update_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.status_lbl.setText(f"Update failed: {err_msg}")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #DC2626; font-weight: 700;")
