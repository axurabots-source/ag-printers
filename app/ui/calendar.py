"""Premium styled calendar and date filter controls for AG Printers."""

from __future__ import annotations

from PySide6.QtWidgets import QCalendarWidget

from app.ui.theme import CALENDAR_SVG, CHEVRON_DOWN_SVG


class PremiumCalendarWidget(QCalendarWidget):
    """Modern, sleek calendar widget matching AG Printers theme."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setGridVisible(False)
        self.setStyleSheet("""
            QCalendarWidget {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #0F172A;
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
                min-height: 46px;
                padding: 3px 6px;
            }
            QCalendarWidget QToolButton {
                color: #F8FAFC;
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                margin: 2px 4px;
                padding: 4px 10px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
            QCalendarWidget QToolButton:pressed {
                background-color: #1E293B;
            }
            QCalendarWidget QSpinBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 3px 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QCalendarWidget QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px;
                color: #0F172A;
            }
            QCalendarWidget QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QCalendarWidget QMenu::item:selected {
                background-color: #EFF6FF;
                color: #2563EB;
            }
            QCalendarWidget QTableView#qt_calendar_calendarview {
                background-color: #FFFFFF;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
                border: none;
                border-bottom-left-radius: 11px;
                border-bottom-right-radius: 11px;
                outline: none;
                font-size: 13px;
            }
            QCalendarWidget QTableView#qt_calendar_calendarview::item {
                border-radius: 6px;
                padding: 5px;
            }
            QCalendarWidget QTableView#qt_calendar_calendarview::item:hover {
                background-color: #F1F5F9;
                color: #2563EB;
            }
            QCalendarWidget QTableView#qt_calendar_calendarview::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 700;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #F8FAFC;
                color: #64748B;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                font-size: 11px;
                font-weight: 700;
                padding: 7px 0;
            }
        """)


DATE_EDIT_STYLE = f"""
QDateEdit {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 26px 6px 10px;
    font-size: 13px;
    color: #0F172A;
    font-weight: 500;
    min-width: 110px;
    min-height: 20px;
}}
QDateEdit:hover {{
    border-color: #2563EB;
}}
QDateEdit:focus {{
    border: 1px solid #2563EB;
}}
QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #E2E8F0;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background-color: #F8FAFC;
}}
QDateEdit::drop-down:hover {{
    background-color: #EFF6FF;
}}
QDateEdit::down-arrow {{
    image: url({CALENDAR_SVG});
    width: 14px;
    height: 14px;
}}
"""


FILTER_COMBO_STYLE = f"""
QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 30px 6px 12px;
    font-size: 13px;
    color: #0F172A;
    font-weight: 500;
    min-width: 115px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: #2563EB;
}}
QComboBox:focus {{
    border: 1px solid #2563EB;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border: none;
}}
QComboBox::down-arrow {{
    image: url({CHEVRON_DOWN_SVG});
    width: 12px;
    height: 12px;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #EFF6FF;
    selection-color: #2563EB;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}
"""


CLEAR_BTN_STYLE = """
QPushButton {
    background: #F1F5F9;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    min-height: 18px;
}
QPushButton:hover {
    background: #E2E8F0;
    color: #0F172A;
}
"""
