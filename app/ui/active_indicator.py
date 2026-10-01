"""Sliding active-item indicator for the sidebar navigation.

A single rounded pill that floats *behind* the navigation buttons (the buttons
stay transparent so the pill shows through). The sidebar animates this widget's
geometry when the selection changes, so the highlight glides smoothly from the
previous item to the new one - in expanded and collapsed mode alike.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from app.ui.theme import GREEN, PRIMARY

#: Horizontal inset applied to the button rectangle (also lets the rounded
#: ends of the pill breathe inside the sidebar padding).
INSET = 3


class ActiveIndicator(QWidget):
    """Rounded pill drawn behind the selected navigation button."""

    DOT_RADIUS = 3.2      # green secondary accent (expanded mode)
    BAR_WIDTH = 12.0      # green secondary accent (collapsed mode)
    BAR_HEIGHT = 2.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._icons_only = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVisible(False)

    def set_icons_only(self, icons_only: bool) -> None:
        """Collapsed mode places the green accent above the icon instead."""
        if icons_only != self._icons_only:
            self._icons_only = icons_only
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Clean stadium shape - the "curved" active background.
        radius = self.height() / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PRIMARY))
        painter.drawRoundedRect(self.rect(), radius, radius)

        # Green is a secondary accent only - never a border, never loud.
        painter.setBrush(QColor(GREEN))
        if self._icons_only:
            # Small centred bar below the icon (keeps the icon unobstructed).
            bar = (self.width() - self.BAR_WIDTH) / 2.0
            top = self.height() - self.BAR_HEIGHT - 3.0
            painter.drawRoundedRect(
                bar, top, self.BAR_WIDTH, self.BAR_HEIGHT,
                self.BAR_HEIGHT / 2.0, self.BAR_HEIGHT / 2.0,
            )
        else:
            painter.drawEllipse(
                QPointF(max(9.0, self.width() - 14.0), self.height() / 2.0),
                self.DOT_RADIUS,
                self.DOT_RADIUS,
            )
