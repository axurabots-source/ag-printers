"""Colors and stylesheet for the AG Printers desktop shell.

Keeping the look in one place lets later versions restyle the app
without touching page code. Pure Qt style sheets - no extra libraries.
"""

from __future__ import annotations

from pathlib import Path

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
CHEVRON_DOWN_SVG = str(_ASSETS_DIR / "chevron-down.svg").replace("\\", "/")
CHEVRON_UP_SVG = str(_ASSETS_DIR / "chevron-up.svg").replace("\\", "/")
CHEVRON_DOWN_SM_SVG = str(_ASSETS_DIR / "chevron-down-sm.svg").replace("\\", "/")
CALENDAR_SVG = str(_ASSETS_DIR / "calendar.svg").replace("\\", "/")
TRASH_SVG = str(_ASSETS_DIR / "trash.svg").replace("\\", "/")
REFRESH_SVG = str(_ASSETS_DIR / "refresh.svg").replace("\\", "/")
EYE_SVG = str(_ASSETS_DIR / "eye.svg").replace("\\", "/")
CHECK_SVG = str(_ASSETS_DIR / "check.svg").replace("\\", "/")

# -- Palette ---------------------------------------------------------------
WINDOW_BG = "#F3F4F6"
ACCENT = "#2563EB"          # header badge / placeholder cards (unchanged)
ACCENT_SOFT = "#EFF6FF"
HEADER_BG = "#FFFFFF"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"
TEXT_PRIMARY = "#111827"
TEXT_MUTED = "#6B7280"

# Sidebar palette - black surface, premium deep blue primary,
# green as a subtle secondary accent (accent only - never a border)
SIDEBAR_BG = "#090B0F"       # near-black surface (elegant, not harsh)
SIDEBAR_HOVER = "#171B22"    # raised surface on hover
SIDEBAR_TEXT = "#C8CFDA"     # soft grey text
SIDEBAR_MUTED = "#6B7280"    # muted labels / footer
SIDEBAR_ICON = "#8A93A3"     # inactive icon stroke
SIDEBAR_FOCUS = "#94A3B8"    # neutral focus ring on the dark rail
PRIMARY = "#1D4E89"          # premium deep blue (active pill, logo)
PRIMARY_HOVER = "#24589B"    # deep blue hover lift
GREEN = "#10B981"            # secondary accent (dots, status) - no borders
FOCUS_RING = "#94A3B8"       # neutral focus ring for content buttons

APP_STYLESHEET = f"""
* {{
    font-family: "Plus Jakarta Sans", "Inter", "Segoe UI", -apple-system, sans-serif;
}}
QMainWindow {{
    background-color: {WINDOW_BG};
}}
QWidget#Central {{
    background-color: {WINDOW_BG};
}}
QFrame#Sidebar {{
    background-color: {SIDEBAR_BG};
    border: none;
}}
QLabel#LogoMark {{
    background-color: {PRIMARY};
    color: #FFFFFF;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
}}
QLabel#SidebarTitle {{
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 700;
}}
QLabel#SidebarSubtitle {{
    color: {SIDEBAR_MUTED};
    font-size: 11px;
}}
QLabel#SectionLabel {{
    color: {SIDEBAR_MUTED};
    font-size: 10px;
    font-weight: 700;
}}
QLabel#SidebarFooter {{
    color: {SIDEBAR_MUTED};
    font-size: 11px;
}}
QPushButton#SidebarToggle {{
    background-color: transparent;
    border: 2px solid transparent;
    border-radius: 8px;
}}
QPushButton#SidebarToggle:hover {{
    background-color: {SIDEBAR_HOVER};
}}
QPushButton#SidebarToggle:focus {{
    border: 2px solid {SIDEBAR_FOCUS};
}}
QFrame#HeaderBar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid {BORDER};
}}
QFrame#HeaderAccentBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E3A8A, stop:1 #3B82F6);
    border-radius: 2px;
}}
QLabel#HeaderTitle {{
    color: {TEXT_PRIMARY};
    font-size: 19px;
    font-weight: 800;
    letter-spacing: -0.2px;
}}
QLabel#HeaderSubtitle {{
    color: {TEXT_MUTED};
    font-size: 11.5px;
    font-weight: 500;
}}
QFrame#HeaderStatusChip {{
    background-color: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 13px;
}}
QLabel#HeaderStatusDot {{
    color: #16A34A;
    font-size: 10px;
}}
QLabel#HeaderStatusText {{
    color: #15803D;
    font-size: 11px;
    font-weight: 700;
}}
QFrame#HeaderClockChip {{
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 13px;
}}
QLabel#HeaderClockText {{
    color: #334155;
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QFrame#HeaderBrandChip {{
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 13px;
}}
QLabel#HeaderBrandName {{
    color: #F8FAFC;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}}
QLabel#HeaderBrandSep {{
    color: #64748B;
    font-size: 10px;
}}
QLabel#HeaderBrandLoc {{
    color: #94A3B8;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
}}
QLabel#VersionBadge {{
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
}}
QFrame#PlaceholderCard {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QLabel#PlaceholderIcon {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT};
    border-radius: 28px;
    font-size: 18px;
    font-weight: 700;
}}
QLabel#PlaceholderTitle {{
    color: {TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#PlaceholderText {{
    color: {TEXT_MUTED};
    font-size: 13px;
}}
QStatusBar {{
    background-color: {HEADER_BG};
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QLineEdit#SearchBox, QComboBox#SearchBox {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 9px 14px;
}}
QLineEdit#SearchBox:focus, QComboBox#SearchBox:focus {{
    border: 1px solid {PRIMARY};
}}
QPushButton#PrimaryButton {{
    background-color: {PRIMARY};
    border: 2px solid transparent;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 9px 18px;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton#PrimaryButton:focus {{
    border: 2px solid {FOCUS_RING};
}}
QPushButton#OutlineButton {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 8px 16px;
}}
QPushButton#OutlineButton:hover {{
    border: 1px solid {PRIMARY};
    color: {PRIMARY};
}}
QPushButton#OutlineButton:focus {{
    border: 2px solid {FOCUS_RING};
}}
QPushButton#OutlineButton:disabled {{
    background-color: #F9FAFB;
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
}}
QTableWidget#PartyTable, QTableWidget#POTable {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 10px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    selection-background-color: #E6EEFB;
    selection-color: {TEXT_PRIMARY};
    outline: none;
}}
QTableWidget#PartyTable::item, QTableWidget#POTable::item {{
    padding: 6px 12px;
    border: none;
    outline: none;
}}
QTableWidget#PartyTable::item:focus, QTableWidget#POTable::item:focus {{
    border: none;
    outline: none;
}}
QHeaderView::section {{
    background-color: #F8FAFC;
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    font-size: 11px;
    font-weight: 700;
    padding: 10px 12px;
}}
QLabel#EmptyState {{
    color: {TEXT_MUTED};
    font-size: 14px;
}}
QFrame#ProfileCard {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QLabel#ProfileName {{
    color: {TEXT_PRIMARY};
    font-size: 24px;
    font-weight: 700;
}}
QLabel#StatusPill {{
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 12px;
}}
QLabel#StatusPill[active="true"] {{
    background-color: #ECFDF5;
    color: #059669;
}}
QLabel#StatusPill[active="false"] {{
    background-color: #F1F5F9;
    color: #64748B;
}}
QLabel#FieldLabel {{
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#FieldValue {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QDialog#PartyDialog {{
    background-color: #FFFFFF;
}}
QLabel#DialogTitle {{
    color: {TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 700;
}}
QLineEdit#FormInput {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 8px 12px;
}}
QLineEdit#FormInput:hover {{
    border: 1px solid #94A3B8;
}}
QLineEdit#FormInput:focus {{
    border: 1.5px solid {PRIMARY};
    background-color: #FFFFFF;
}}
QDateEdit#FormInput {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 6px 24px 6px 10px;
    min-width: 155px;
}}
QDateEdit#FormInput:hover {{
    border: 1px solid #94A3B8;
}}
QDateEdit#FormInput:focus {{
    border: 1.5px solid {PRIMARY};
}}
QDateEdit#FormInput::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #E5E7EB;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background-color: #F8FAFC;
}}
QDateEdit#FormInput::down-arrow {{
    image: url({CHEVRON_DOWN_SVG});
    width: 10px;
    height: 10px;
}}
QComboBox#FormInput {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 8px 36px 8px 12px;
}}
QComboBox#FormInput:hover {{
    border: 1px solid #94A3B8;
}}
QComboBox#FormInput:focus {{
    border: 1.5px solid {PRIMARY};
    background-color: #FFFFFF;
}}
QComboBox#FormInput::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    border-left: 1px solid #E5E7EB;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background-color: #F8FAFC;
}}
QComboBox#FormInput::drop-down:hover {{
    background-color: #F1F5F9;
}}
QComboBox#FormInput::down-arrow {{
    image: url({CHEVRON_DOWN_SVG});
    width: 14px;
    height: 14px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    selection-background-color: #EFF6FF;
    selection-color: {PRIMARY};
    padding: 6px;
}}
QDoubleSpinBox#FormInput {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 6px 28px 6px 10px;
}}
QDoubleSpinBox#FormInput:hover {{
    border: 1px solid #94A3B8;
}}
QDoubleSpinBox#FormInput:focus {{
    border: 1.5px solid {PRIMARY};
    background-color: #FFFFFF;
}}
QDoubleSpinBox#FormInput::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    height: 16px;
    border-left: 1px solid #E5E7EB;
    border-bottom: 1px solid #E5E7EB;
    background-color: #F8FAFC;
    border-top-right-radius: 7px;
}}
QDoubleSpinBox#FormInput::up-button:hover {{
    background-color: #E2E8F0;
}}
QDoubleSpinBox#FormInput::up-arrow {{
    image: url({CHEVRON_UP_SVG});
    width: 10px;
    height: 10px;
}}
QDoubleSpinBox#FormInput::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    height: 16px;
    border-left: 1px solid #E5E7EB;
    background-color: #F8FAFC;
    border-bottom-right-radius: 7px;
}}
QDoubleSpinBox#FormInput::down-button:hover {{
    background-color: #E2E8F0;
}}
QDoubleSpinBox#FormInput::down-arrow {{
    image: url({CHEVRON_DOWN_SM_SVG});
    width: 10px;
    height: 10px;
}}
QDoubleSpinBox#TableInput {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
    padding: 2px 4px;
    qproperty-alignment: AlignCenter;
}}
QDoubleSpinBox#TableInput:focus {{
    border: 1.5px solid {PRIMARY};
    background-color: #F8FAFC;
}}
QDoubleSpinBox#TableInput::up-button, QDoubleSpinBox#TableInput::down-button {{
    width: 0px;
    height: 0px;
    border: none;
}}
QDoubleSpinBox#TableInput QLineEdit {{
    background: transparent;
    border: none;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
    qproperty-alignment: AlignCenter;
}}
QLabel#RowAmount {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 700;
    padding: 0px 4px;
    qproperty-alignment: AlignCenter;
}}
QLabel#RowProfit {{
    font-size: 13px;
    font-weight: 700;
    padding: 0px 4px;
    qproperty-alignment: AlignCenter;
}}
QPushButton#RemoveRowButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #94A3B8;
    font-size: 13px;
    padding: 4px;
}}
QPushButton#RemoveRowButton:hover {{
    background-color: #FEF2F2;
    border: 1px solid #EF4444;
}}
QPlainTextEdit#FormInput {{
    background-color: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    padding: 8px 12px;
}}
QPlainTextEdit#FormInput:focus {{
    border: 1px solid {PRIMARY};
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    spacing: 8px;
}}
QPushButton#DangerButton {{
    background-color: #FFFFFF;
    border: 1px solid #FCA5A5;
    border-radius: 8px;
    color: #DC2626;
    font-size: 13px;
    padding: 8px 16px;
}}
QPushButton#DangerButton:hover {{
    background-color: #FEF2F2;
    border: 1px solid #EF4444;
}}
QPushButton#DangerButton:focus {{
    border: 2px solid {FOCUS_RING};
}}
QPushButton#SuccessButton {{
    background-color: #059669;
    border: 1px solid transparent;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
    padding: 9px 20px;
}}
QPushButton#SuccessButton:hover {{
    background-color: #047857;
}}
QPushButton#SuccessButton:pressed {{
    background-color: #065F46;
}}
QPushButton#SuccessButton:focus {{
    border: 2px solid #6EE7B7;
}}
QFrame#CrmMetricCard {{
    background-color: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#CrmMetricCard:hover {{
    border: 1px solid #CBD5E1;
}}
QLabel#CrmMetricLabel {{
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
}}
QLabel#CrmMetricValue {{
    color: {TEXT_PRIMARY};
    font-size: 17px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}}
QLabel#CrmMetricValueAccent {{
    color: #059669;
    font-size: 18px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}}
QLabel#CrmMetricValueSuccess {{
    color: #047857;
    font-size: 18px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}}
QLabel#TotalBar {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 700;
}}
QDialog#BillCreateDialog, QDialog#POFormDialog, QDialog#POItemSelectionDialog {{
    background-color: #FFFFFF;
}}

/* Global Modern Minimalist Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #F8FAFC;
    width: 10px;
    margin: 14px 0 14px 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}
QScrollBar::sub-line:vertical {{
    border: none;
    background: #E2E8F0;
    height: 12px;
    subcontrol-position: top;
    subcontrol-origin: margin;
    border-radius: 4px;
}}
QScrollBar::sub-line:vertical:hover {{
    background: #1D4E89;
}}
QScrollBar::add-line:vertical {{
    border: none;
    background: #E2E8F0;
    height: 12px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
    border-radius: 4px;
}}
QScrollBar::add-line:vertical:hover {{
    background: #1D4E89;
}}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
    width: 0px;
    height: 0px;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: #F8FAFC;
    height: 10px;
    margin: 0 14px 0 14px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94A3B8;
}}
QScrollBar::sub-line:horizontal {{
    border: none;
    background: #E2E8F0;
    width: 12px;
    subcontrol-position: left;
    subcontrol-origin: margin;
    border-radius: 4px;
}}
QScrollBar::sub-line:horizontal:hover {{
    background: #1D4E89;
}}
QScrollBar::add-line:horizontal {{
    border: none;
    background: #E2E8F0;
    width: 12px;
    subcontrol-position: right;
    subcontrol-origin: margin;
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal:hover {{
    background: #1D4E89;
}}
QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
    width: 0px;
    height: 0px;
    background: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
"""
