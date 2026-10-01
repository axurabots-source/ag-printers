"""Auto-capitalization utility and widgets for AG Printers desktop application.

Ensures any manually typed text automatically begins with a capital letter
(capitalizes the initial letter of each word/delimiter-separated token).
"""

from __future__ import annotations

import re
from typing import Union
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit


def capitalize_words(text: str) -> str:
    """Capitalize the first character of each word, preserving existing uppercase and formatting.

    Examples:
        'visiting card' -> 'Visiting Card'
        'box packaging 350gsm' -> 'Box Packaging 350gsm'
        'po-1234' -> 'Po-1234'
        'AG PRINTERS' -> 'AG PRINTERS'
    """
    if not text:
        return text
    # Capitalize any lowercase letter that appears at the start of string
    # or directly after whitespace, hyphen, underscore, slash, bracket, dot, comma, or hash
    pattern = r"(^|[\s\-_/\[\(.\',#])([a-z])"
    return re.sub(pattern, lambda m: m.group(1) + m.group(2).upper(), text)


def enable_auto_capitalization(widget: Union[QLineEdit, QPlainTextEdit, QTextEdit]) -> None:
    """Attaches an auto-capitalization handler to a text input widget."""
    if isinstance(widget, QLineEdit):
        def _on_text_changed(text: str) -> None:
            new_text = capitalize_words(text)
            if new_text != text:
                pos = widget.cursorPosition()
                widget.blockSignals(True)
                widget.setText(new_text)
                widget.setCursorPosition(pos)
                widget.blockSignals(False)

        widget.textChanged.connect(_on_text_changed)

    elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
        def _on_doc_changed() -> None:
            text = widget.toPlainText()
            new_text = capitalize_words(text)
            if new_text != text:
                cursor = widget.textCursor()
                pos = cursor.position()
                widget.blockSignals(True)
                widget.setPlainText(new_text)
                cursor.setPosition(min(pos, len(new_text)))
                widget.setTextCursor(cursor)
                widget.blockSignals(False)

        widget.textChanged.connect(_on_doc_changed)


class CapitalizedLineEdit(QLineEdit):
    """QLineEdit with auto-capitalization enabled by default."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        enable_auto_capitalization(self)


class CapitalizedPlainTextEdit(QPlainTextEdit):
    """QPlainTextEdit with auto-capitalization enabled by default."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        enable_auto_capitalization(self)
