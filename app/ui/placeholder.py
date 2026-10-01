"""Placeholder page shown for each not-yet-implemented module."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """A neutral 'coming soon' card for a future AG Printers module."""

    def __init__(self, page_name: str, parent=None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        card = QFrame()
        card.setObjectName("PlaceholderCard")
        card.setFixedWidth(560)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(12)

        initials = "".join(part[0] for part in page_name.split()).upper()[:2]
        icon = QLabel(initials)
        icon.setObjectName("PlaceholderIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(56, 56)

        title = QLabel(page_name)
        title.setObjectName("PlaceholderTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text = QLabel(
            "This page is coming in a future version of AG Printers."
        )
        text.setObjectName("PlaceholderText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)

        card_layout.addSpacing(8)
        card_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
        card_layout.addWidget(title)
        card_layout.addWidget(text)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)
