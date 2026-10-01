"""Costing & Quotation Calculator: focused production cost & profit calculation.

Flow:
1. User enters process costs in the sections below (e.g. Design: 10, Plates: 20 -> Total Cost: 30).
2. User enters Quantity (e.g. 10 pcs -> Cost Per Unit: 3.00).
3. User enters Selling Price Per Unit (e.g. 5.00).
4. System calculates:
   - Profit Per Piece (e.g. Rs. 2.00)
   - Net Profit Total (e.g. Rs. 20.00)
   - Profit Margin % (e.g. 40.0%)

Design Highlights:
- Premium minimalist card layout with generous breathing room and bottom space.
- Zero horizontal overflow; perfectly centered responsive table.
- Attached 'Rs.' prefix directly integrated into price input boxes (no awkward gaps).
- Total Invoice Value removed as requested.
- 3 Sections starting closed by default (General, Barcode, Sampling).
- General section includes an expandable Sampling sub-table, plus there is a dedicated Sampling section.
"""

from __future__ import annotations

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
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


def _fmt(val: float) -> str:
    return f"{val:,.2f}"


class SectionIconBadge(QWidget):
    """Crisp 28x28 vector emblem for section headers."""

    def __init__(self, kind: str, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(28, 28)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(1, 1, 26, 26)
        if self.kind == "general":
            bg = QColor("#EFF6FF")
            border = QColor("#BFDBFE")
            pen_color = QColor("#2563EB")
        elif self.kind == "barcode":
            bg = QColor("#FAF5FF")
            border = QColor("#E9D5FF")
            pen_color = QColor("#7E22CE")
        else:
            bg = QColor("#ECFDF5")
            border = QColor("#A7F3D0")
            pen_color = QColor("#059669")

        p.setBrush(bg)
        p.setPen(QPen(border, 1.0))
        p.drawRoundedRect(rect, 6, 6)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(pen_color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

        if self.kind == "general":
            p.drawRoundedRect(QRectF(7, 10, 14, 11), 2, 2)
            p.drawLine(QPointF(7, 14.5), QPointF(21, 14.5))
            p.drawEllipse(QPointF(14, 7), 2.5, 2.5)
        elif self.kind == "barcode":
            for x in (7.5, 10.5, 12.5, 15.5, 17.5, 20.5):
                p.drawLine(QPointF(x, 8), QPointF(x, 20))
        else:
            path = QPainterPath()
            path.moveTo(12.5, 7.5)
            path.lineTo(15.5, 7.5)
            path.lineTo(15.5, 11)
            path.lineTo(19.5, 19.5)
            path.cubicTo(20, 20.5, 19, 21, 18, 21)
            path.lineTo(10, 21)
            path.cubicTo(9, 21, 8, 20.5, 8.5, 19.5)
            path.lineTo(12.5, 11)
            path.closeSubpath()
            p.drawPath(path)
            p.drawLine(QPointF(10.5, 16.5), QPointF(17.5, 16.5))

        p.end()


class PriceInputGroup(QFrame):
    """Sleek unified input box with attached 'Rs.' prefix and zero wasted gap."""

    valueChanged = Signal()

    def __init__(self, placeholder="0.00", width=160, height=32, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setObjectName("PriceInputGroup")
        self._update_style(focused=False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Prefix Badge 'Rs.'
        self.lbl_prefix = QLabel("Rs.")
        self.lbl_prefix.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_prefix.setStyleSheet("""
            QLabel {
                background-color: #F8FAFC;
                color: #64748B;
                font-size: 11px;
                font-weight: 700;
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
                border-right: 1px solid #CBD5E1;
                padding: 0px 4px;
            }
        """)
        self.lbl_prefix.setFixedWidth(30)
        layout.addWidget(self.lbl_prefix)

        # Inner Number Field
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        validator = QDoubleValidator(0.0, 99999999.0, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.edit.setValidator(validator)
        self.edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                padding: 2px 8px;
                font-size: 13px;
                font-weight: 700;
                color: #0F172A;
            }
        """)
        self.edit.textChanged.connect(lambda: self.valueChanged.emit())

        # Forward focus events to style outer frame
        orig_focus_in = self.edit.focusInEvent
        orig_focus_out = self.edit.focusOutEvent

        def on_focus_in(e):
            self._update_style(focused=True)
            orig_focus_in(e)

        def on_focus_out(e):
            self._update_style(focused=False)
            orig_focus_out(e)

        self.edit.focusInEvent = on_focus_in
        self.edit.focusOutEvent = on_focus_out

        layout.addWidget(self.edit)

    def _update_style(self, focused: bool) -> None:
        if focused:
            self.setStyleSheet("""
                QFrame#PriceInputGroup {
                    background-color: #F8FAFC;
                    border: 1.5px solid #2563EB;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#PriceInputGroup {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                }
                QFrame#PriceInputGroup:hover {
                    border-color: #94A3B8;
                }
            """)

    def text(self) -> str:
        return self.edit.text()

    def setText(self, val: str) -> None:
        self.edit.setText(val)

    def clear(self) -> None:
        self.edit.blockSignals(True)
        self.edit.clear()
        self.edit.blockSignals(False)

    def get_value(self) -> float:
        try:
            return float(self.edit.text().replace(",", "").strip() or 0.0)
        except ValueError:
            return 0.0


class CenteredCostRow(QFrame):
    """Centralized operation row with attached Rs. price input."""

    cost_changed = Signal()

    def __init__(self, section: str, line_name: str, parent=None) -> None:
        super().__init__(parent)
        self.section = section
        self.line_name = line_name

        self.setObjectName("CenteredCostRow")
        self.setStyleSheet("""
            QFrame#CenteredCostRow {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F1F5F9;
            }
            QFrame#CenteredCostRow:hover {
                background-color: #F8FAFC;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 6, 24, 6)
        layout.setSpacing(16)

        # 1. Operation Name
        self.lbl_name = QLabel(line_name)
        self.lbl_name.setStyleSheet("color: #1E293B; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.lbl_name, 1)

        # 2. Centered Cost Input Box with attached 'Rs.' (spacious 160px)
        self.price_input = PriceInputGroup(placeholder="0.00", width=160, height=32)
        self.price_input.valueChanged.connect(lambda: self.cost_changed.emit())
        layout.addWidget(self.price_input, 0, Qt.AlignmentFlag.AlignCenter)

    def get_cost(self) -> float:
        return self.price_input.get_value()

    def clear(self) -> None:
        self.price_input.clear()


class SamplingSubDropdown(QFrame):
    """Collapsible Sampling sub-table embedded directly inside the General section."""

    toggled = Signal()
    cost_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.is_expanded = False
        self.rows: list[CenteredCostRow] = []

        self.setStyleSheet("""
            QFrame#SamplingSubDropdown {
                background-color: #F8FAFC;
                border: 1px dashed #CBD5E1;
                border-radius: 7px;
                margin: 6px 16px 10px 16px;
            }
        """)
        self.setObjectName("SamplingSubDropdown")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header for Sampling Sub-table
        self.header = QFrame()
        self.header.setObjectName("SamplingHeader")
        self.header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header.setStyleSheet("""
            QFrame#SamplingHeader {
                background-color: #F1F5F9;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QFrame#SamplingHeader:hover {
                background-color: #E2E8F0;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(10, 6, 10, 6)
        h_layout.setSpacing(10)

        # Title
        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        lbl_t = QLabel("Sampling Breakdown (Optional Sub-Process)")
        lbl_t.setStyleSheet("font-size: 9pt; font-weight: 700; color: #334155;")
        lbl_sub = QLabel("Click to open sampling process table inside General")
        lbl_sub.setStyleSheet("font-size: 8pt; color: #64748B; border: none; background: transparent;")
        lbl_sub.setWordWrap(True)
        t_box.addWidget(lbl_t)
        t_box.addWidget(lbl_sub)
        h_layout.addLayout(t_box, 1)

        # Subtotal Pill
        self.pill_subtotal = QLabel("Sampling: Rs. 0.00")
        self.pill_subtotal.setStyleSheet("""
            background-color: #FFFFFF;
            color: #64748B;
            border: 1px solid #CBD5E1;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 8.5pt;
            font-weight: 600;
        """)
        h_layout.addWidget(self.pill_subtotal)

        # Toggle Button / Chevron
        self.lbl_arrow = QLabel("▼ Open")
        self.lbl_arrow.setStyleSheet("color: #2563EB; font-size: 8.5pt; font-weight: 700; padding: 2px 6px;")
        h_layout.addWidget(self.lbl_arrow)

        main_layout.addWidget(self.header)

        # Body Container (Starts HIDDEN)
        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 4)
        body_layout.setSpacing(0)

        sampling_operations = (
            "Sample Design",
            "Sample Card",
            "Sample Printing",
            "Sample Die / Block",
            "Sample Proofing / Testing",
            "Sample Others",
        )

        for name in sampling_operations:
            rw = CenteredCostRow("general_sampling", name)
            rw.cost_changed.connect(self._on_row_cost_changed)
            self.rows.append(rw)
            body_layout.addWidget(rw)

        self.body.setVisible(False)
        main_layout.addWidget(self.body)

        self.header.mousePressEvent = self._toggle

    def _toggle(self, event) -> None:
        self.is_expanded = not self.is_expanded
        self.body.setVisible(self.is_expanded)
        self.lbl_arrow.setText("▲ Close" if self.is_expanded else "▼ Open")
        self.toggled.emit()

    def _on_row_cost_changed(self) -> None:
        self.update_subtotal()
        self.cost_changed.emit()

    def update_subtotal(self) -> float:
        subtotal = sum(r.get_cost() for r in self.rows)
        if subtotal > 0:
            self.pill_subtotal.setText(f"Sampling: Rs. {_fmt(subtotal)}")
            self.pill_subtotal.setStyleSheet("""
                background-color: #ECFDF5;
                color: #047857;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 8.5pt;
                font-weight: 700;
            """)
        else:
            self.pill_subtotal.setText("Sampling: Rs. 0.00")
            self.pill_subtotal.setStyleSheet("""
                background-color: #FFFFFF;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 8.5pt;
                font-weight: 600;
            """)
        return subtotal

    def clear(self) -> None:
        for r in self.rows:
            r.clear()
        self.update_subtotal()


class CollapsibleSection(QFrame):
    """Sleek collapsible accordion card that starts CLOSED by default."""

    toggled = Signal()
    cost_changed = Signal()

    def __init__(
        self,
        key: str,
        title: str,
        subtitle: str,
        row_names: tuple[str, ...],
        include_sampling_sub: bool = False,
        include_inventory_picker: bool = False,
        parent=None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        super().__init__(parent)
        self.key = key
        self.is_expanded = False  # Starts CLOSED by default
        self.rows: list[CenteredCostRow] = []
        self.sampling_sub: SamplingSubDropdown | None = None

        self.setObjectName("CollapsibleSection")
        self.setStyleSheet("""
            QFrame#CollapsibleSection {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Header (Clickable toggle)
        self.header = QFrame()
        self.header.setObjectName("HeaderFrame")
        self.header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.header.setStyleSheet("""
            QFrame#HeaderFrame {
                background-color: #FFFFFF;
                border-radius: 9px;
                padding: 6px 14px;
            }
            QFrame#HeaderFrame:hover {
                background-color: #F8FAFC;
            }
        """)

        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(14)

        # Vector Emblem Logo
        self.badge = SectionIconBadge(key)
        h_layout.addWidget(self.badge)

        # Title & Subtitle
        t_box = QVBoxLayout()
        t_box.setSpacing(1)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10.5pt; font-weight: 700; color: #0F172A; border: none; background: transparent;")
        sub_count = len(row_names) + (6 if include_sampling_sub else 0)
        lbl_sub = QLabel(f"{sub_count} operations  ·  {subtitle}")
        lbl_sub.setStyleSheet("font-size: 8.5pt; color: #64748B; border: none; background: transparent;")
        lbl_sub.setWordWrap(True)
        t_box.addWidget(lbl_t)
        t_box.addWidget(lbl_sub)
        h_layout.addLayout(t_box, 1)

        # Subtotal Pill
        self.pill_subtotal = QLabel("Subtotal: Rs. 0.00")
        self.pill_subtotal.setStyleSheet("""
            background-color: #F1F5F9;
            color: #64748B;
            border-radius: 5px;
            padding: 4px 12px;
            font-size: 9pt;
            font-weight: 600;
        """)
        h_layout.addWidget(self.pill_subtotal)

        # Chevron Indicator Button
        self.btn_toggle = QLabel("▼ Open")
        self.btn_toggle.setStyleSheet("""
            QLabel {
                color: #2563EB;
                background-color: #EFF6FF;
                border: 1px solid #DBEAFE;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 8.5pt;
                font-weight: 700;
            }
            QLabel:hover {
                background-color: #DBEAFE;
            }
        """)
        h_layout.addWidget(self.btn_toggle)

        layout.addWidget(self.header)

        # 2. Body Container (Starts HIDDEN)
        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 8)
        body_layout.setSpacing(0)

        # Table Column Header (Clean & borderless, no box)
        th = QWidget()
        th.setStyleSheet("background: transparent; border: none;")
        th_l = QHBoxLayout(th)
        th_l.setContentsMargins(24, 8, 24, 4)
        th_l.setSpacing(16)

        th_name = QLabel("OPERATION / PROCESS")
        th_name.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: none; background: transparent;")
        th_l.addWidget(th_name, 1)

        th_cost = QLabel("PROCESS COST")
        th_cost.setFixedWidth(160)
        th_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        th_cost.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: none; background: transparent;")
        th_l.addWidget(th_cost, 0, Qt.AlignmentFlag.AlignCenter)

        body_layout.addWidget(th)

        # Rows
        for r_name in row_names:
            rw = CenteredCostRow(key, r_name)
            rw.cost_changed.connect(lambda: self.cost_changed.emit())
            self.rows.append(rw)
            body_layout.addWidget(rw)

        # Optional embedded Sampling sub-table inside General section
        if include_sampling_sub:
            self.sampling_sub = SamplingSubDropdown()
            self.sampling_sub.cost_changed.connect(lambda: self.cost_changed.emit())
            body_layout.addWidget(self.sampling_sub)

        # Embedded Barcode Inventory Material Picker for Barcode section (only when enabled)
        self.barcode_inventory_picker = None
        if include_inventory_picker and key == "barcode":
            from app.costing.barcode_inventory_picker import BarcodeInventoryCostingWidget
            self.barcode_inventory_picker = BarcodeInventoryCostingWidget(connection=connection)
            self.barcode_inventory_picker.cost_changed.connect(lambda: self.cost_changed.emit())
            body_layout.addWidget(self.barcode_inventory_picker)

        self.body.setVisible(False)  # CLOSED by default
        layout.addWidget(self.body)

        self.header.mousePressEvent = self._toggle

    def _toggle(self, event) -> None:
        self.is_expanded = not self.is_expanded
        self.body.setVisible(self.is_expanded)
        if self.is_expanded and hasattr(self, "barcode_inventory_picker") and self.barcode_inventory_picker:
            self.barcode_inventory_picker.refresh_inventory()
        self.btn_toggle.setText("▲ Close" if self.is_expanded else "▼ Open")
        self.header.setStyleSheet(f"""
            QFrame#HeaderFrame {{
                background-color: {"#F8FAFC" if self.is_expanded else "#FFFFFF"};
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
                border-bottom-left-radius: {"0px" if self.is_expanded else "9px"};
                border-bottom-right-radius: {"0px" if self.is_expanded else "9px"};
                padding: 6px 14px;
            }}
            QFrame#HeaderFrame:hover {{
                background-color: #F8FAFC;
            }}
        """)
        self.toggled.emit()

    def update_subtotal(self) -> float:
        subtotal = sum(r.get_cost() for r in self.rows)
        if self.sampling_sub:
            subtotal += self.sampling_sub.update_subtotal()
        if hasattr(self, "barcode_inventory_picker") and self.barcode_inventory_picker:
            subtotal += self.barcode_inventory_picker.get_total()

        if subtotal > 0:
            self.pill_subtotal.setText(f"Subtotal: Rs. {_fmt(subtotal)}")
            self.pill_subtotal.setStyleSheet("""
                background-color: #ECFDF5;
                color: #047857;
                border: 1px solid #A7F3D0;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 9pt;
                font-weight: 700;
            """)
        else:
            self.pill_subtotal.setText("Subtotal: Rs. 0.00")
            self.pill_subtotal.setStyleSheet("""
                background-color: #F1F5F9;
                color: #64748B;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 9pt;
                font-weight: 600;
            """)
        return subtotal

    def clear(self) -> None:
        for r in self.rows:
            r.clear()
        if self.sampling_sub:
            self.sampling_sub.clear()
        if hasattr(self, "barcode_inventory_picker") and self.barcode_inventory_picker:
            self.barcode_inventory_picker.clear()
        self.update_subtotal()


class CostingPage(QWidget):
    """Direct centralized Costing & Profit Calculator with clean breathing room."""

    document_opened = Signal(str)
    list_shown = Signal()

    def __init__(self, connection=None, parent=None) -> None:
        super().__init__(parent)
        self._sections: dict[str, CollapsibleSection] = {}

        self.setObjectName("CostingCalculatorPage")
        self.setStyleSheet("QWidget#CostingCalculatorPage { background-color: #F8FAFC; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll Area: strictly disable horizontal scroll to eliminate width overflow
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background-color: #F8FAFC; border: none; }")

        # Outer canvas with full comfortable workspace width and generous bottom padding
        canvas = QWidget()
        canvas.setStyleSheet("background-color: #F8FAFC;")
        center_layout = QVBoxLayout(canvas)
        center_layout.setContentsMargins(28, 20, 28, 60)
        center_layout.setSpacing(14)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. Top Header Title
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        t_info = QVBoxLayout()
        t_info.setSpacing(2)
        lbl_head = QLabel("Costing & Profit Calculator")
        lbl_head.setStyleSheet("font-size: 15pt; font-weight: 800; color: #0F172A;")
        lbl_sub = QLabel("Calculate production cost, per-unit price, and profit instantly")
        lbl_sub.setStyleSheet("font-size: 8.5pt; color: #64748B;")
        t_info.addWidget(lbl_head)
        t_info.addWidget(lbl_sub)
        top_bar.addLayout(t_info, 1)

        # Reset Calculator Button
        self.clear_btn = QPushButton("Reset Calculator")
        self.clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 9pt;
                font-weight: 600;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                border-color: #FCA5A5;
                color: #DC2626;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_all)
        top_bar.addWidget(self.clear_btn)

        center_layout.addLayout(top_bar)

        # 2. Main Parameters & Profit Card
        calc_card = QFrame()
        calc_card.setStyleSheet("""
            QFrame#MainCalcCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        calc_card.setObjectName("MainCalcCard")

        c_layout = QVBoxLayout(calc_card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(14)

        # --- Row 1: The 4-step inputs and indicators ---
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(14)

        # Step 1: Total Cost (Auto sum from all sections)
        t_cost_box = QVBoxLayout()
        t_cost_box.setSpacing(3)
        t_cost_lbl = QLabel("1. TOTAL PRODUCTION COST")
        t_cost_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_cost_lbl.setStyleSheet("color: #64748B; font-size: 7.5pt; font-weight: 800; letter-spacing: 0.5px;")
        self.val_total_cost = QLabel("Rs. 0.00")
        self.val_total_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_total_cost.setStyleSheet("color: #0F172A; font-size: 14pt; font-weight: 800;")
        t_cost_box.addWidget(t_cost_lbl)
        t_cost_box.addWidget(self.val_total_cost)
        inputs_row.addLayout(t_cost_box, 3)

        # Step 2: Quantity Input Box
        qty_box = QVBoxLayout()
        qty_box.setSpacing(3)
        qty_lbl = QLabel("2. QUANTITY (PCS)")
        qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty_lbl.setStyleSheet("color: #64748B; font-size: 7.5pt; font-weight: 800; letter-spacing: 0.5px;")
        self.qty_edit = QLineEdit("1000")
        self.qty_edit.setValidator(QIntValidator(1, 10000000, self))
        self.qty_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 10.5pt;
                font-weight: 700;
                color: #0F172A;
            }
            QLineEdit:focus { border: 1.5px solid #2563EB; background-color: #F8FAFC; }
        """)
        self.qty_edit.setFixedHeight(32)
        self.qty_edit.textChanged.connect(self._recalculate)
        qty_box.addWidget(qty_lbl)
        qty_box.addWidget(self.qty_edit)
        inputs_row.addLayout(qty_box, 2)

        # Step 3: Cost Per Unit Box
        unit_cost_box = QVBoxLayout()
        unit_cost_box.setSpacing(3)
        unit_cost_lbl = QLabel("3. COST / UNIT")
        unit_cost_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unit_cost_lbl.setStyleSheet("color: #64748B; font-size: 7.5pt; font-weight: 800; letter-spacing: 0.5px;")
        self.val_unit_cost = QLabel("Rs. 0.00")
        self.val_unit_cost.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_unit_cost.setStyleSheet("color: #2563EB; font-size: 14pt; font-weight: 800;")
        unit_cost_box.addWidget(unit_cost_lbl)
        unit_cost_box.addWidget(self.val_unit_cost)
        inputs_row.addLayout(unit_cost_box, 2)

        # Step 4: Sell Price Input with attached 'Rs.' prefix (no wasted gap!)
        sell_box = QVBoxLayout()
        sell_box.setSpacing(3)
        sell_lbl = QLabel("4. SELL PRICE / UNIT")
        sell_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sell_lbl.setStyleSheet("color: #047857; font-size: 7.5pt; font-weight: 800; letter-spacing: 0.5px;")

        sell_input_wrapper = QHBoxLayout()
        sell_input_wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sell_price_input = PriceInputGroup(placeholder="0.00", width=160, height=32)
        self.sell_price_input.valueChanged.connect(self._recalculate)
        sell_input_wrapper.addWidget(self.sell_price_input)

        sell_box.addWidget(sell_lbl)
        sell_box.addLayout(sell_input_wrapper)
        inputs_row.addLayout(sell_box, 3)

        c_layout.addLayout(inputs_row)

        # Subtle horizontal divider between inputs and profit results
        div = QFrame()
        div.setStyleSheet("background-color: #F1F5F9; border: none; max-height: 1px;")
        div.setFixedHeight(1)
        c_layout.addWidget(div)

        # --- Row 2: Focused Profit Outcomes (Clean & borderless, no box) ---
        profit_bar = QWidget()
        profit_bar.setStyleSheet("background: transparent; border: none;")
        p_layout = QHBoxLayout(profit_bar)
        p_layout.setContentsMargins(12, 6, 12, 2)
        p_layout.setSpacing(18)

        def make_profit_stat(title: str, default: str, color: str = "#0F172A"):
            box = QVBoxLayout()
            box.setSpacing(2)
            t = QLabel(title)
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
            v = QLabel(default)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet(f"font-size: 13pt; font-weight: 800; color: {color};")
            box.addWidget(t)
            box.addWidget(v)
            return box, v

        b1, self.val_unit_profit = make_profit_stat("PROFIT / PIECE", "Rs. 0.00", "#059669")
        b2, self.val_total_profit = make_profit_stat("NET PROFIT (TOTAL)", "Rs. 0.00", "#047857")
        b3, self.val_margin = make_profit_stat("PROFIT MARGIN", "0.0%", "#059669")

        p_layout.addLayout(b1, 3)
        p_layout.addLayout(b2, 4)
        p_layout.addLayout(b3, 3)

        c_layout.addWidget(profit_bar)

        center_layout.addWidget(calc_card)

        # 3. Hint Banner
        lbl_hint = QLabel("Enter your process costs below. Sections start closed — click any section to open:")
        lbl_hint.setStyleSheet("font-size: 8.5pt; color: #64748B; font-weight: 500;")
        center_layout.addWidget(lbl_hint)

        # 4. Collapsible Dropdown Sections (All start CLOSED by default)
        # Section 1: General Printing & Finishing (with its own inner Sampling sub-table!)
        sec_general = CollapsibleSection(
            key="general",
            title="General Printing & Finishing",
            subtitle="Design, plates, paper card, printing, lamination, and sampling",
            row_names=(
                "Design",
                "Plates",
                "Card (Paper)",
                "Printing",
                "Lamination",
                "Pasting",
                "Block",
                "Cutting",
                "Banding",
                "Dai Make",
                "Dai Cut",
                "Others",
            ),
            include_sampling_sub=True,  # Full sampling table dropdown included inside General
        )
        sec_general.cost_changed.connect(self._recalculate)
        self._sections["general"] = sec_general
        center_layout.addWidget(sec_general)

        # Section 2: Barcode Stickers & Labels (Pure rate estimator: Media, Ribbon, Labour, Electricity)
        sec_barcode = CollapsibleSection(
            key="barcode",
            title="Barcode Stickers & Labels",
            subtitle="Media, ribbon, labour, electricity & machine process costs",
            row_names=(
                "Media",
                "Ribbon",
                "Labour",
                "Electricity + Labour",
                "Others",
            ),
            include_sampling_sub=False,
            include_inventory_picker=False,
        )
        sec_barcode.cost_changed.connect(self._recalculate)
        self._sections["barcode"] = sec_barcode
        center_layout.addWidget(sec_barcode)

        # Section 3: Dedicated Standalone Sampling & Prototyping
        sec_sampling = CollapsibleSection(
            key="sampling",
            title="Sampling & Prototyping (Dedicated)",
            subtitle="Pre-production mockups, test cards, trial printing, and proofing",
            row_names=(
                "Sample Design",
                "Sample Card",
                "Sample Printing",
                "Sample Die / Block",
                "Sample Proofing / Testing",
                "Sample Others",
            ),
            include_sampling_sub=False,
        )
        sec_sampling.cost_changed.connect(self._recalculate)
        self._sections["sampling"] = sec_sampling
        center_layout.addWidget(sec_sampling)

        # Generous bottom breathing spacer so the content never sticks to the screen edge
        center_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        scroll.setWidget(canvas)
        root.addWidget(scroll)

        self._recalculate()

    def reset_to_list(self) -> None:
        """Main window interface callback."""
        pass

    def get_quantity(self) -> float:
        try:
            val = float(self.qty_edit.text().strip() or 1.0)
            return max(1.0, val)
        except ValueError:
            return 1.0

    def get_sell_price(self) -> float:
        return self.sell_price_input.get_value()

    def _recalculate(self) -> None:
        # 1. Total Cost = Direct sum of all process costs across sections
        grand_total_cost = 0.0
        for sec in self._sections.values():
            grand_total_cost += sec.update_subtotal()

        qty = self.get_quantity()
        unit_cost = (grand_total_cost / qty) if qty > 0 else 0.0
        sell_price = self.get_sell_price()

        # Update Top Cost Displays
        self.val_total_cost.setText(f"Rs. {_fmt(grand_total_cost)}")
        self.val_unit_cost.setText(f"Rs. {_fmt(unit_cost)}")

        # Profit Calculations (Total Invoice Value completely removed)
        if sell_price > 0:
            unit_profit = sell_price - unit_cost
            total_profit = unit_profit * qty
            total_sale = sell_price * qty
            margin = (total_profit / total_sale * 100.0) if total_sale > 0 else 0.0

            if total_profit >= 0:
                profit_color = "#047857"
                sign = "+"
            else:
                profit_color = "#DC2626"
                sign = ""

            self.val_unit_profit.setText(f"{sign}Rs. {_fmt(unit_profit)}")
            self.val_unit_profit.setStyleSheet(f"font-size: 13pt; font-weight: 800; color: {profit_color};")

            self.val_total_profit.setText(f"{sign}Rs. {_fmt(total_profit)}")
            self.val_total_profit.setStyleSheet(f"font-size: 15pt; font-weight: 800; color: {profit_color};")

            self.val_margin.setText(f"{margin:+.1f}%")
            self.val_margin.setStyleSheet(f"font-size: 13pt; font-weight: 800; color: {profit_color};")
        else:
            self.val_unit_profit.setText("Rs. 0.00")
            self.val_unit_profit.setStyleSheet("font-size: 13pt; font-weight: 800; color: #64748B;")
            self.val_total_profit.setText("Rs. 0.00")
            self.val_total_profit.setStyleSheet("font-size: 15pt; font-weight: 800; color: #64748B;")
            self.val_margin.setText("0.0%")
            self.val_margin.setStyleSheet("font-size: 13pt; font-weight: 800; color: #64748B;")

    def clear_all(self) -> None:
        """Reset all inputs to zero."""
        for sec in self._sections.values():
            sec.clear()
        self.qty_edit.setText("1000")
        self.sell_price_input.clear()
        self._recalculate()
