"""Custom sidebar navigation button with an animated hover state.

The active pill is not painted here any more - the sidebar's
``ActiveIndicator`` slides between items and is drawn *behind* the buttons.
This widget paints the hover surface, the focus ring, the icon and the label,
fading them in and out with a short ``QPropertyAnimation`` running on its own
``hoverProgress`` property.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QSizePolicy

from app.ui import icons
from app.ui.theme import (
    SIDEBAR_FOCUS,
    SIDEBAR_HOVER,
    SIDEBAR_ICON,
    SIDEBAR_TEXT,
)

HOVER_MS = 140      # fast and professional - not flashy
ICON_PX = 20
ICON_GROWTH = 1.0   # the icon grows by at most 1px while hovering


def _blend(start: str, end: str, progress: float) -> QColor:
    """Colour fade used for the animated hover transition."""
    first, second = QColor(start), QColor(end)
    return QColor(
        int(first.red() + (second.red() - first.red()) * progress),
        int(first.green() + (second.green() - first.green()) * progress),
        int(first.blue() + (second.blue() - first.blue()) * progress),
    )


def _quantise(color: QColor) -> str:
    """Snap a colour to 8-value steps so the icon cache stays small."""
    values = []
    for value in (color.red(), color.green(), color.blue()):
        values.append(min(255, int(round(value / 8.0)) * 8))
    return QColor(*values).name()


class NavButton(QPushButton):
    """Sidebar item: animated hover feedback, icons-only when collapsed."""

    def __init__(self, text: str, kind: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("NavButton")
        self._kind = kind
        self._icons_only = False
        # Initialised before the animation below, which reads this property
        # (via the Qt meta-object) as soon as it is constructed.
        self._hover = 0.0
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip(text)  # useful in collapsed (icon-only) mode
        self.setAccessibleName(text)

        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(HOVER_MS)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # -- animated hover progress ---------------------------------------

    def _get_hover_progress(self) -> float:
        # Defensive: Qt may query the property before __init__ finishes.
        return getattr(self, "_hover", 0.0)

    def _set_hover_progress(self, value: float) -> None:
        self._hover = float(value)
        self.update()

    hoverProgress = Property(float, _get_hover_progress, _set_hover_progress)

    def _animate_hover(self, target: float) -> None:
        """Ease the hover fade to *target* (1.0 = hovered, 0.0 = idle)."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def setIconsOnly(self, icons_only: bool) -> None:
        """Show icons only (collapsed rail) instead of icon + label."""
        if icons_only != self._icons_only:
            self._icons_only = icons_only
            self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._animate_hover(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate_hover(0.0)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        hover = getattr(self, "_hover", 0.0)
        checked = self.isChecked()
        surface = self.rect().adjusted(3, 3, -3, -3)
        radius = surface.height() / 2.0

        # Hover surface: raised dark surface normally, faint wash over the
        # active item (the blue pill itself is the sliding indicator's job).
        if hover > 0.001:
            if checked:
                fill = QColor("#FFFFFF")
                fill.setAlphaF(0.07 * hover)
            else:
                fill = QColor(SIDEBAR_HOVER)
                fill.setAlphaF(0.9 * hover)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(surface, radius, radius)

        # Keyboard focus ring - neutral; green stays an accent, never a border.
        if self.hasFocus():
            ring = self.rect().adjusted(1, 1, -1, -1)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(SIDEBAR_FOCUS), 1.6))
            painter.drawRoundedRect(ring, ring.height() / 2.0, ring.height() / 2.0)

        # Icon: subtle grow + colour fade driven by hoverProgress.
        icon_size = ICON_PX + int(round(ICON_GROWTH * hover))
        if self._icons_only:
            icon_x = (self.width() - icon_size) // 2
        else:
            icon_x = 14 - int(round(ICON_GROWTH * hover))
        icon_y = (self.height() - icon_size) // 2
        if checked:
            icon_color = "#FFFFFF"
        else:
            icon_color = _quantise(_blend(SIDEBAR_ICON, "#FFFFFF", hover))
        icons.icon(self._kind, icon_color).paint(
            painter, QRect(icon_x, icon_y, icon_size, icon_size)
        )

        if not self._icons_only:
            font = self.font()
            font.setBold(checked)
            painter.setFont(font)
            if checked:
                text_color = QColor("#FFFFFF")
            else:
                text_color = _blend(SIDEBAR_TEXT, "#FFFFFF", hover)
            painter.setPen(text_color)
            text_x = icon_x + 28
            text_w = max(0, self.width() - text_x - 12 - (24 if checked else 0))
            label = QFontMetrics(font).elidedText(
                self.text(), Qt.TextElideMode.ElideRight, text_w
            )
            painter.drawText(
                QRect(text_x, 0, text_w, self.height()),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
