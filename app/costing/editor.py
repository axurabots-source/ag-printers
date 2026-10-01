"""Costing editor: visual interactive calculation sheet with collapsible sections.

Features:
- Premium minimal design with wide spacing and modern typography.
- 3 Collapsible / Dropdown sections: General, Barcode Stickers, Sampling.
- Distinct vector logo badges for each section.
- Sampling is available in both General and as a dedicated separate section.
- Real-time instant live calculation of section subtotals, grand total, and per-unit cost.
- Direct party selection and automatic loading of party saved rates.
"""

from __future__ import annotations

import sqlite3
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QDoubleValidator,
    QIntValidator,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.db.costing import (
    CostingLine,
    get_costing,
    load_party_rates,
    save_costing,
)
from app.ui.capitalized_input import enable_auto_capitalization


def _fmt(val: float) -> str:
    """Format float with commas and 2 decimal places."""
    return f"{val:,.2f}"


class SectionLogoBadge(QWidget):
    """Clean vector emblem badge rendered via QPainter for each costing section."""

    def __init__(self, kind: str, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(44, 44)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(2, 2, 40, 40)
        if self.kind == "general":
            bg_color = QColor("#EFF6FF")
            border_color = QColor("#BFDBFE")
            icon_color = QColor("#1D4ED8")
        elif self.kind == "barcode":
            bg_color = QColor("#FAF5FF")
            border_color = QColor("#E9D5FF")
            icon_color = QColor("#7E22CE")
        else:  # sampling
            bg_color = QColor("#ECFDF5")
            border_color = QColor("#A7F3D0")
            icon_color = QColor("#047857")

        # Background rounded badge
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(rect, 10, 10)

        # Draw specific vector glyph
        painter.setPen(QPen(icon_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.kind == "general":
            # Offset Press / Stacked paper layers & roller
            painter.drawRoundedRect(QRectF(11, 14, 22, 16), 3, 3)
            painter.drawLine(QPointF(11, 21), QPointF(33, 21))
            painter.drawEllipse(QPointF(22, 10), 4.5, 4.5)
        elif self.kind == "barcode":
            # Barcode vertical stripes & scan laser
            lines = [13, 16, 18, 22, 25, 27, 30]
            for x in lines:
                painter.drawLine(QPointF(x, 14), QPointF(x, 29))
            painter.setPen(QPen(QColor("#EF4444"), 1.4, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(10, 21.5), QPointF(34, 21.5))
        else:
            # Sampling / Lab Flask & Color Palette Swatch
            path = QPainterPath()
            path.moveTo(20, 12)
            path.lineTo(24, 12)
            path.lineTo(24, 17)
            path.lineTo(30, 29)
            path.cubicTo(31, 31, 29, 32, 27, 32)
            path.lineTo(17, 32)
            path.cubicTo(15, 32, 13, 31, 14, 29)
            path.lineTo(20, 17)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(16.5, 25), QPointF(27.5, 25))

        painter.end()


class CostingRowWidget(QFrame):
    """Single operation row inside a section table with live rate calculation."""

    rate_changed = Signal()

    def __init__(self, section: str, line_name: str, parent=None) -> None:
        super().__init__(parent)
        self.section = section
        self.line_name = line_name
        self.setObjectName("CostingRowWidget")
        self.setStyleSheet("""
            QFrame#CostingRowWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F3F4F6;
                padding: 6px 12px;
            }
            QFrame#CostingRowWidget:hover {
                background-color: #F9FAFB;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # 1. Process name
        name_box = QHBoxLayout()
        name_box.setSpacing(8)
        bullet = QLabel("•")
        bullet.setStyleSheet("color: #6B7280; font-size: 14pt; font-weight: bold;")
        self.name_label = QLabel(line_name)
        self.name_label.setStyleSheet("color: #111827; font-size: 10.5pt; font-weight: 500;")
        name_box.addWidget(bullet)
        name_box.addWidget(self.name_label)
        layout.addLayout(name_box, 3)

        # 2. Calculation Type Tag
        # Setup operations (Die make, Design, Block, Plates) are typically fixed lot or unit
        is_fixed = line_name in ("Design", "Plates", "Block", "Dai Make", "Proofing", "Die / Block")
        tag_text = "Setup / Fixed" if is_fixed else "Per Unit × Qty"
        tag_bg = "#FEF3C7" if is_fixed else "#EEF2FF"
        tag_color = "#92400E" if is_fixed else "#3730A3"
        self.is_fixed_calculation = is_fixed

        tag = QLabel(tag_text)
        tag.setStyleSheet(f"""
            background-color: {tag_bg};
            color: {tag_color};
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 8.5pt;
            font-weight: 600;
        """)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tag, 2)

        # 3. Rate Input Box
        rate_box = QHBoxLayout()
        rate_box.setSpacing(4)
        rs_lbl = QLabel("Rs.")
        rs_lbl.setStyleSheet("color: #6B7280; font-size: 9.5pt; font-weight: 500;")
        rate_box.addWidget(rs_lbl)

        self.rate_edit = QLineEdit()
        self.rate_edit.setPlaceholderText("0.00")
        self.rate_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        validator = QDoubleValidator(0.0, 9999999.0, 4, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.rate_edit.setValidator(validator)
        self.rate_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 10pt;
                font-weight: 500;
                color: #111827;
            }
            QLineEdit:focus {
                border: 1.5px solid #2563EB;
                background-color: #F8FAFC;
            }
        """)
        self.rate_edit.setFixedWidth(110)
        self.rate_edit.textChanged.connect(lambda: self.rate_changed.emit())
        rate_box.addWidget(self.rate_edit)
        layout.addLayout(rate_box, 2)

        # 4. Calculated Amount
        self.amount_label = QLabel("0.00")
        self.amount_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.amount_label.setStyleSheet("color: #111827; font-size: 10pt; font-weight: 600;")
        self.amount_label.setFixedWidth(120)
        layout.addWidget(self.amount_label, 2)

    def get_rate(self) -> float:
        try:
            return float(self.rate_edit.text().replace(",", "").strip() or 0.0)
        except ValueError:
            return 0.0

    def set_rate(self, rate: float) -> None:
        self.rate_edit.blockSignals(True)
        self.rate_edit.setText(f"{rate:g}" if rate > 0 else "")
        self.rate_edit.blockSignals(False)

    def update_amount(self, quantity: float) -> float:
        rate = self.get_rate()
        if rate <= 0:
            amt = 0.0
        elif self.is_fixed_calculation:
            amt = rate
        else:
            amt = rate * quantity
        self.amount_label.setText(_fmt(amt))
        if amt > 0:
            self.amount_label.setStyleSheet("color: #1E40AF; font-size: 10pt; font-weight: 700;")
        else:
            self.amount_label.setStyleSheet("color: #9CA3AF; font-size: 10pt; font-weight: 500;")
        return amt


class CollapsibleSectionCard(QFrame):
    """Modern collapsible / accordion section with Logo, title, live total, and table body."""

    toggled = Signal(bool)

    def __init__(self, key: str, title: str, subtitle: str, row_names: tuple[str, ...], parent=None) -> None:
        super().__init__(parent)
        self.key = key
        self.row_names = row_names
        self.is_expanded = True
        self.row_widgets: list[CostingRowWidget] = []

        self.setObjectName("CollapsibleSectionCard")
        self.setStyleSheet("""
            QFrame#CollapsibleSectionCard {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
        """)

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Header (Clickable Dropdown Toggle)
        self.header_btn = QFrame()
        self.header_btn.setObjectName("SectionHeaderFrame")
        self.header_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header_btn.setStyleSheet("""
            QFrame#SectionHeaderFrame {
                background-color: #F9FAFB;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
                border-bottom: 1px solid #E5E7EB;
                padding: 10px 16px;
            }
            QFrame#SectionHeaderFrame:hover {
                background-color: #F3F4F6;
            }
        """)

        header_layout = QHBoxLayout(self.header_btn)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(14)

        # Section Vector Logo
        self.logo_badge = SectionLogoBadge(key)
        header_layout.addWidget(self.logo_badge)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11.5pt; font-weight: 700; color: #111827;")
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 9pt; color: #6B7280;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box, 1)

        # Section Subtotal Pill
        self.subtotal_pill = QLabel("Subtotal: Rs. 0.00")
        self.subtotal_pill.setStyleSheet("""
            background-color: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 10pt;
            font-weight: 700;
        """)
        header_layout.addWidget(self.subtotal_pill)

        # Chevron indicator (dropdown toggle)
        self.chevron = QLabel("▲")
        self.chevron.setStyleSheet("color: #4B5563; font-size: 11pt; font-weight: bold; margin-left: 6px;")
        header_layout.addWidget(self.chevron)

        card_layout.addWidget(self.header_btn)

        # 2. Body Container (holds table rows)
        self.body_container = QWidget()
        body_layout = QVBoxLayout(self.body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Table Column Headers
        table_hdr = QFrame()
        table_hdr.setStyleSheet("background-color: #F3F4F6; border-bottom: 1px solid #E5E7EB;")
        hdr_layout = QHBoxLayout(table_hdr)
        hdr_layout.setContentsMargins(24, 8, 24, 8)
        hdr_layout.setSpacing(12)

        def make_th(text: str, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
            l = QLabel(text)
            l.setStyleSheet("color: #4B5563; font-size: 8.5pt; font-weight: 700; letter-spacing: 0.5px;")
            l.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            return l

        hdr_layout.addWidget(make_th("OPERATION / PROCESS ITEM"), 3)
        hdr_layout.addWidget(make_th("CALCULATION METHOD", Qt.AlignmentFlag.AlignCenter), 2)
        hdr_layout.addWidget(make_th("RATE (RS.)", Qt.AlignmentFlag.AlignRight), 2)
        hdr_layout.addWidget(make_th("SUBTOTAL (RS.)", Qt.AlignmentFlag.AlignRight), 2)
        body_layout.addWidget(table_hdr)

        # Populate rows
        for row_name in row_names:
            row_widget = CostingRowWidget(key, row_name)
            self.row_widgets.append(row_widget)
            body_layout.addWidget(row_widget)

        card_layout.addWidget(self.body_container)

        # Connect click event
        self.header_btn.mousePressEvent = self._toggle_collapse

    def _toggle_collapse(self, event) -> None:
        self.is_expanded = not self.is_expanded
        self.body_container.setVisible(self.is_expanded)
        self.chevron.setText("▲" if self.is_expanded else "▼")
        self.toggled.emit(self.is_expanded)

    def set_subtotal(self, amt: float) -> None:
        self.subtotal_pill.setText(f"Subtotal: Rs. {_fmt(amt)}")


class CostingEditor(QWidget):
    """Primary visual costing calculation workspace with KPI cards and accordion sections."""

    saved = Signal(int)
    cancel_requested = Signal()

    def __init__(self, connection: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self._connection = connection
        self._current_costing_id: int | None = None
        self._sections: dict[str, CollapsibleSectionCard] = {}

        self.setObjectName("CostingEditor")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll Area for the entire canvas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #F8FAFC; }")

        canvas = QWidget()
        canvas.setObjectName("CanvasWidget")
        canvas.setStyleSheet("QWidget#CanvasWidget { background-color: #F8FAFC; }")
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(28, 24, 28, 28)
        canvas_layout.setSpacing(20)

        # Top Bar (Back button, Title, Actions)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(16)

        self.back_btn = QPushButton("← Back to List")
        self.back_btn.setObjectName("OutlineButton")
        self.back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.back_btn.clicked.connect(self.cancel_requested.emit)
        top_bar.addWidget(self.back_btn)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        page_title = QLabel("Costing Sheet & Quotation Calculator")
        page_title.setStyleSheet("font-size: 16pt; font-weight: 800; color: #111827;")
        page_sub = QLabel("Interactive unit economics, offset printing operations, stickers, and sampling breakdown")
        page_sub.setStyleSheet("font-size: 9.5pt; color: #6B7280;")
        title_box.addWidget(page_title)
        title_box.addWidget(page_sub)
        top_bar.addLayout(title_box, 1)

        self.reset_btn = QPushButton("Reset Form")
        self.reset_btn.setObjectName("OutlineButton")
        self.reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.reset_btn.clicked.connect(self.reset_form)
        top_bar.addWidget(self.reset_btn)

        self.save_btn = QPushButton("Save Costing Sheet")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.save_btn.setStyleSheet("""
            QPushButton#PrimaryButton {
                background-color: #059669;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 10pt;
                padding: 8px 20px;
                border-radius: 7px;
                border: none;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #047857;
            }
        """)
        self.save_btn.clicked.connect(self.save_costing)
        top_bar.addWidget(self.save_btn)

        canvas_layout.addLayout(top_bar)

        # 2. Executive KPI Cards Banner
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(14)

        self.kpi_total = self._build_kpi_card(
            "TOTAL PRODUCTION COST", "Rs. 0.00", "#ECFDF5", "#059669", "#A7F3D0"
        )
        self.kpi_unit = self._build_kpi_card(
            "PER UNIT COST", "Rs. 0.00 / pc", "#EFF6FF", "#2563EB", "#BFDBFE"
        )
        self.kpi_general = self._build_kpi_card(
            "GENERAL PRINTING", "Rs. 0.00", "#F9FAFB", "#374151", "#E5E7EB"
        )
        self.kpi_barcode_sample = self._build_kpi_card(
            "BARCODE & SAMPLING", "Rs. 0.00", "#F9FAFB", "#374151", "#E5E7EB"
        )

        kpi_bar.addWidget(self.kpi_total, 3)
        kpi_bar.addWidget(self.kpi_unit, 3)
        kpi_bar.addWidget(self.kpi_general, 2)
        kpi_bar.addWidget(self.kpi_barcode_sample, 2)
        canvas_layout.addLayout(kpi_bar)

        # 3. Job Parameters Card (Party, Item Title, Quantity)
        params_card = QFrame()
        params_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                padding: 16px 20px;
            }
        """)
        params_layout = QVBoxLayout(params_card)
        params_layout.setContentsMargins(18, 14, 18, 14)
        params_layout.setSpacing(12)

        param_title = QLabel("JOB & PARTY PARAMETERS")
        param_title.setStyleSheet("font-size: 9pt; font-weight: 800; color: #4B5563; letter-spacing: 0.5px;")
        params_layout.addWidget(param_title)

        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(16)

        # Party selector
        party_box = QVBoxLayout()
        party_box.setSpacing(4)
        lbl_p = QLabel("Client / Party *")
        lbl_p.setStyleSheet("font-size: 9pt; font-weight: 600; color: #374151;")
        self.party_combo = QComboBox()
        self.party_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 10pt;
                color: #111827;
            }
            QComboBox:focus { border: 1.5px solid #2563EB; }
        """)
        self.party_combo.currentIndexChanged.connect(self._on_party_selected)
        party_box.addWidget(lbl_p)
        party_box.addWidget(self.party_combo)
        inputs_row.addLayout(party_box, 3)

        # Item title
        item_box = QVBoxLayout()
        item_box.setSpacing(4)
        lbl_i = QLabel("Item Description / Job Name *")
        lbl_i.setStyleSheet("font-size: 9pt; font-weight: 600; color: #374151;")
        self.item_edit = QLineEdit()
        self.item_edit.setPlaceholderText("e.g. Perfume Mono Carton 350gsm with Matte Lamination")
        self.item_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 10pt;
                color: #111827;
            }
            QLineEdit:focus { border: 1.5px solid #2563EB; }
        """)
        enable_auto_capitalization(self.item_edit)
        item_box.addWidget(lbl_i)
        item_box.addWidget(self.item_edit)
        inputs_row.addLayout(item_box, 4)

        # Quantity
        qty_box = QVBoxLayout()
        qty_box.setSpacing(4)
        lbl_q = QLabel("Order Quantity *")
        lbl_q.setStyleSheet("font-size: 9pt; font-weight: 600; color: #374151;")
        qty_inner = QHBoxLayout()
        qty_inner.setSpacing(4)
        self.qty_edit = QLineEdit("1000")
        self.qty_edit.setValidator(QIntValidator(1, 10000000, self))
        self.qty_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 10pt;
                font-weight: 600;
                color: #111827;
            }
            QLineEdit:focus { border: 1.5px solid #2563EB; }
        """)
        self.qty_edit.textChanged.connect(self._recalculate_all)
        qty_inner.addWidget(self.qty_edit)
        qty_box.addWidget(lbl_q)
        qty_box.addLayout(qty_inner)
        inputs_row.addLayout(qty_box, 2)

        params_layout.addLayout(inputs_row)

        # Quick preset pills for quantity
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        lbl_preset = QLabel("Quick Presets:")
        lbl_preset.setStyleSheet("font-size: 8.5pt; color: #6B7280; font-weight: 600;")
        preset_row.addWidget(lbl_preset)
        for preset in (500, 1000, 2500, 5000, 10000, 25000):
            btn = QPushButton(f"{preset:,}")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F3F4F6;
                    border: 1px solid #E5E7EB;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 8.5pt;
                    font-weight: 600;
                    color: #374151;
                }
                QPushButton:hover {
                    background-color: #E5E7EB;
                    color: #111827;
                }
            """)
            btn.clicked.connect(lambda _, q=preset: self.qty_edit.setText(str(q)))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        params_layout.addLayout(preset_row)

        canvas_layout.addWidget(params_card)

        # 4. Collapsible Dropdown Sections
        section_configs = [
            (
                "general",
                "1. GENERAL PRINTING & FINISHING",
                "Design, Plates, Paper Card, Printing, Lamination, Die Making, Die Cut, and Sampling",
                (
                    "Design",
                    "Plates",
                    "Card",
                    "Printing",
                    "Lamination",
                    "Pasting",
                    "Block",
                    "Cutting",
                    "Banding",
                    "Dai Make",
                    "Dai Cut",
                    "Sampling",
                    "Others",
                ),
            ),
            (
                "barcode",
                "2. BARCODE STICKERS & LABELS",
                "Thermal Media Rolls, Ribbon Wax, Electricity & Machine Labour",
                ("Media", "Ribbon", "Electricity + Labour"),
            ),
            (
                "sampling",
                "3. SAMPLING & PROTOTYPING (STANDALONE)",
                "Pre-production mockups, test cards, trial printing, and proofing charges",
                ("Card", "Printing", "Die / Block", "Proofing", "Others"),
            ),
        ]

        for key, title, sub, rows in section_configs:
            section_card = CollapsibleSectionCard(key, title, sub, rows)
            self._sections[key] = section_card
            for r_widget in section_card.row_widgets:
                r_widget.rate_changed.connect(self._recalculate_all)
            canvas_layout.addWidget(section_card)

        # 5. Notes / Remarks area
        notes_card = QFrame()
        notes_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 12px 16px;")
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(12, 10, 12, 10)
        lbl_notes = QLabel("Internal Costing Notes & Assumptions")
        lbl_notes.setStyleSheet("font-size: 9pt; font-weight: 700; color: #4B5563;")
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("e.g. Paper calculated at 350gsm Art Card from local stock; plates rate includes CTP charges.")
        self.notes_edit.setStyleSheet("border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 10px; font-size: 9.5pt;")
        enable_auto_capitalization(self.notes_edit)
        notes_layout.addWidget(lbl_notes)
        notes_layout.addWidget(self.notes_edit)
        canvas_layout.addWidget(notes_card)

        # Spacer at bottom
        canvas_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        scroll.setWidget(canvas)
        root.addWidget(scroll)

        self._load_parties()
        self._recalculate_all()

    def _build_kpi_card(self, title: str, default_val: str, bg: str, text_color: str, border_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border_color};
                border-radius: 10px;
                padding: 14px 18px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {text_color}; font-size: 8pt; font-weight: 800; letter-spacing: 0.5px;")
        v_lbl = QLabel(default_val)
        v_lbl.setStyleSheet(f"color: {text_color}; font-size: 15pt; font-weight: 800;")
        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        card.value_label = v_lbl  # type: ignore[attr-defined]
        return card

    def _load_parties(self) -> None:
        """Populate party dropdown from database."""
        self.party_combo.blockSignals(True)
        self.party_combo.clear()
        self.party_combo.addItem("-- Select Party --", None)
        try:
            for row in self._connection.execute("SELECT id, name FROM parties ORDER BY name"):
                self.party_combo.addItem(str(row["name"]), int(row["id"]))
        except Exception:
            pass
        self.party_combo.blockSignals(False)

    def _on_party_selected(self) -> None:
        party_id = self.party_combo.currentData()
        if not party_id:
            return
        # Load party saved rates
        saved_rates = load_party_rates(self._connection, int(party_id))
        if saved_rates:
            for section_card in self._sections.values():
                for row_w in section_card.row_widgets:
                    key = (row_w.section, row_w.line_name)
                    if key in saved_rates:
                        row_w.set_rate(saved_rates[key])
            self._recalculate_all()

    def get_quantity(self) -> float:
        try:
            val = float(self.qty_edit.text().strip() or 1.0)
            return max(1.0, val)
        except ValueError:
            return 1.0

    def _recalculate_all(self) -> None:
        """Recalculate amounts for every row, every section, and grand totals."""
        qty = self.get_quantity()
        grand_total = 0.0
        sec_totals: dict[str, float] = {}

        for sec_key, section_card in self._sections.items():
            sec_sum = 0.0
            for row_w in section_card.row_widgets:
                sec_sum += row_w.update_amount(qty)
            sec_totals[sec_key] = sec_sum
            section_card.set_subtotal(sec_sum)
            grand_total += sec_sum

        per_unit = grand_total / qty if qty > 0 else 0.0

        # Update KPI cards
        self.kpi_total.value_label.setText(f"Rs. {_fmt(grand_total)}")  # type: ignore[attr-defined]
        self.kpi_unit.value_label.setText(f"Rs. {_fmt(per_unit)} / pc")  # type: ignore[attr-defined]
        self.kpi_general.value_label.setText(f"Rs. {_fmt(sec_totals.get('general', 0.0))}")  # type: ignore[attr-defined]
        self.kpi_barcode_sample.value_label.setText(
            f"Rs. {_fmt(sec_totals.get('barcode', 0.0) + sec_totals.get('sampling', 0.0))}"  # type: ignore[attr-defined]
        )

    def reset_form(self) -> None:
        """Reset form fields and clear rates."""
        self._current_costing_id = None
        self.item_edit.clear()
        self.qty_edit.setText("1000")
        self.notes_edit.clear()
        for section_card in self._sections.values():
            for row_w in section_card.row_widgets:
                row_w.set_rate(0.0)
        self._recalculate_all()

    def load_costing_by_id(self, costing_id: int) -> bool:
        """Load an existing costing record into the visual editor."""
        costing = get_costing(self._connection, costing_id)
        if not costing:
            return False

        self._current_costing_id = costing.id
        self._load_parties()

        # Select party
        for i in range(self.party_combo.count()):
            if self.party_combo.itemData(i) == costing.party_id:
                self.party_combo.setCurrentIndex(i)
                break

        self.item_edit.setText(costing.item_name or costing.description)
        self.qty_edit.setText(str(int(costing.quantity)))
        self.notes_edit.setText(costing.notes)

        # Clear all rates first
        for section_card in self._sections.values():
            for row_w in section_card.row_widgets:
                row_w.set_rate(0.0)

        # Load saved line rates
        for line in costing.lines:
            if line.section in self._sections:
                for row_w in self._sections[line.section].row_widgets:
                    if row_w.line_name.lower() == line.line_name.lower():
                        row_w.set_rate(line.rate)

        self._recalculate_all()
        return True

    def save_costing(self) -> None:
        """Validate and commit the current costing sheet to SQLite."""
        party_id = self.party_combo.currentData()
        if not party_id:
            QMessageBox.warning(self, "Missing Party", "Please select a Client / Party for this costing.")
            return

        item_name = self.item_edit.text().strip()
        if not item_name:
            QMessageBox.warning(self, "Missing Item", "Please enter an Item Description or Job Name.")
            return

        qty = self.get_quantity()
        lines: list[CostingLine] = []

        for sec_key, section_card in self._sections.items():
            for row_w in section_card.row_widgets:
                rate = row_w.get_rate()
                if rate > 0:
                    lines.append(CostingLine(
                        section=sec_key,
                        line_name=row_w.line_name,
                        rate=rate,
                        amount=row_w.get_rate() if row_w.is_fixed_calculation else rate * qty,
                    ))

        if not lines:
            QMessageBox.warning(self, "No Rates", "Please enter at least one rate before saving the costing sheet.")
            return

        try:
            cid = save_costing(
                self._connection,
                party_id=int(party_id),
                item_name=item_name,
                quantity=qty,
                lines=lines,
                notes=self.notes_edit.text().strip(),
                costing_id=self._current_costing_id,
            )
            self._current_costing_id = cid
            QMessageBox.information(self, "Saved", f"Costing Sheet for '{item_name}' saved successfully!")
            self.saved.emit(cid)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save costing sheet:\n{e}")
