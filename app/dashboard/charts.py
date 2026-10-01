"""Clean graphical charts and visual breakdown widgets for AG Printers Dashboard."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)


class TrendChartWidget(QWidget):
    """Clean bar chart for Revenue and Net Profit with muted corporate palette."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: list[dict[str, Any]] = []
        self._hovered_idx: int = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: list[dict[str, Any]]) -> None:
        self._data = data
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if not self._data:
            return
        w = self.width()
        padding_l = 55
        padding_r = 20
        plot_w = w - padding_l - padding_r
        n = len(self._data)
        if n == 0 or plot_w <= 0:
            return

        x = event.position().x()
        if x < padding_l or x > w - padding_r:
            self._hovered_idx = -1
            self.update()
            return

        step = plot_w / n
        idx = int((x - padding_l) // step)
        if 0 <= idx < n and idx != self._hovered_idx:
            self._hovered_idx = idx
            item = self._data[idx]
            tip = (
                f"<b>{item.get('label', '')}</b> ({item.get('date', '')})<br/>"
                f"Client: {item.get('party', '')}<br/>"
                f"Revenue: Rs. {item.get('revenue', 0):,.2f}<br/>"
                f"Profit: Rs. {item.get('profit', 0):,.2f}"
            )
            QToolTip.showText(self.mapToGlobal(event.position().toPoint()), tip, self)
            self.update()

    def leaveEvent(self, event) -> None:
        self._hovered_idx = -1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        padding_l = 55
        padding_r = 20
        padding_t = 34
        padding_b = 35

        plot_w = w - padding_l - padding_r
        plot_h = h - padding_t - padding_b

        # White canvas
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        # Legend (top right)
        legend_font = QFont("Plus Jakarta Sans", 9)
        painter.setFont(legend_font)

        # Revenue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1d4e89"))
        painter.drawEllipse(QRectF(w - 180, 13, 7, 7))
        painter.setPen(QColor("#475569"))
        painter.drawText(QRectF(w - 165, 8, 65, 16), Qt.AlignmentFlag.AlignVCenter, "Revenue")

        # Profit
        painter.setBrush(QColor("#059669"))
        painter.drawEllipse(QRectF(w - 95, 13, 7, 7))
        painter.setPen(QColor("#475569"))
        painter.drawText(QRectF(w - 80, 8, 65, 16), Qt.AlignmentFlag.AlignVCenter, "Profit")

        if not self._data:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Plus Jakarta Sans", 10))
            painter.drawText(
                QRectF(0, 0, w, h),
                Qt.AlignmentFlag.AlignCenter,
                "No bill data available yet.",
            )
            return

        # Determine scale max
        max_val = max(
            max(item.get("revenue", 0.0), item.get("profit", 0.0))
            for item in self._data
        )
        if max_val <= 0:
            max_val = 1000.0
        scale_max = max_val * 1.15

        # Horizontal Grid Lines & Y-axis labels
        grid_pen = QPen(QColor("#f1f5f9"), 1, Qt.PenStyle.SolidLine)
        axis_font = QFont("Plus Jakarta Sans", 8)
        painter.setFont(axis_font)

        grid_steps = 4
        for i in range(grid_steps + 1):
            y_ratio = i / grid_steps
            y_pos = padding_t + plot_h - (y_ratio * plot_h)
            val = y_ratio * scale_max

            painter.setPen(grid_pen)
            painter.drawLine(QPointF(padding_l, y_pos), QPointF(w - padding_r, y_pos))

            label = f"{val/1000:.1f}k" if val >= 1000 else f"{int(val)}"
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(
                QRectF(6, y_pos - 8, padding_l - 12, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Draw Bars
        n = len(self._data)
        col_w = plot_w / n
        bar_group_w = min(col_w * 0.65, 46.0)
        single_bar_w = (bar_group_w - 4) / 2.0

        for idx, item in enumerate(self._data):
            center_x = padding_l + (idx * col_w) + (col_w / 2.0)
            group_left = center_x - (bar_group_w / 2.0)

            rev = item.get("revenue", 0.0)
            profit = item.get("profit", 0.0)

            rev_h = (rev / scale_max) * plot_h if scale_max > 0 else 0
            profit_h = (profit / scale_max) * plot_h if scale_max > 0 else 0

            # Subtle hover band
            if idx == self._hovered_idx:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#f8fafc"))
                painter.drawRect(
                    QRectF(center_x - (col_w * 0.48), padding_t, col_w * 0.96, plot_h)
                )

            # Revenue Bar
            rev_rect = QRectF(group_left, padding_t + plot_h - rev_h, single_bar_w, rev_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#1d4e89" if idx != self._hovered_idx else "#1e40af"))
            painter.drawRect(rev_rect)

            # Profit Bar
            prof_x = group_left + single_bar_w + 4
            prof_rect = QRectF(prof_x, padding_t + plot_h - profit_h, single_bar_w, profit_h)
            painter.setBrush(QColor("#059669" if idx != self._hovered_idx else "#047857"))
            painter.drawRect(prof_rect)

            # X-Axis label
            x_label = item.get("label", "")
            painter.setFont(QFont("Plus Jakarta Sans", 8))
            painter.setPen(QColor("#334155" if idx == self._hovered_idx else "#64748b"))
            painter.drawText(
                QRectF(center_x - (col_w / 2.0), padding_t + plot_h + 6, col_w, 18),
                Qt.AlignmentFlag.AlignCenter,
                x_label,
            )


class TopClientsWidget(QFrame):
    """Clean ranking of top clients with uniform brand bars."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 8px;
            }
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr_lbl = QLabel("Top Clients")
        hdr_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        hdr.addWidget(hdr_lbl)
        hdr.addStretch(1)

        share_lbl = QLabel("Share")
        share_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        hdr.addWidget(share_lbl)
        self._layout.addLayout(hdr)

        self._items_container = QVBoxLayout()
        self._items_container.setSpacing(8)
        self._layout.addLayout(self._items_container)
        self._layout.addStretch(1)

    def set_data(self, clients: list[dict[str, Any]]) -> None:
        while self._items_container.count():
            item = self._items_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not clients:
            empty = QLabel("No client billing history.")
            empty.setStyleSheet("font-size: 11px; color: #94a3b8; font-style: italic; padding: 12px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._items_container.addWidget(empty)
            return

        for idx, client in enumerate(clients):
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(3)

            info_row = QHBoxLayout()
            name_lbl = QLabel(f"{idx+1}. {client['party_name']}")
            name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #1e293b;")
            info_row.addWidget(name_lbl)
            info_row.addStretch(1)

            amt_lbl = QLabel(f"Rs. {client['revenue']:,.0f} ({client['share_percentage']}%)")
            amt_lbl.setStyleSheet("font-size: 11px; color: #475569;")
            info_row.addWidget(amt_lbl)
            row_layout.addLayout(info_row)

            bar = QProgressBar()
            bar.setFixedHeight(6)
            bar.setTextVisible(False)
            bar.setMaximum(100)
            bar.setValue(int(round(client["share_percentage"])))
            bar.setStyleSheet("""
                QProgressBar {
                    background: #f1f5f9;
                    border: none;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    background: #1d4e89;
                    border-radius: 3px;
                }
            """)
            row_layout.addWidget(bar)
            self._items_container.addWidget(row)
