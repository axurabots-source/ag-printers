"""Left navigation sidebar - collapsible rail with pill-style active state.

Expanded mode shows icon + text labels; collapsed mode shows icons only
(with tooltips). The width transition is animated, and a single rounded
active pill (``ActiveIndicator``) glides smoothly from the previous item to
the newly selected one. All 11 module placeholders and the
``page_selected`` signal behave exactly as before.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)

from app import __version__
from app.pdf_settings import get_pdf_export_dir, set_pdf_export_dir
from app.ui import icons
from app.ui.active_indicator import INSET, ActiveIndicator
from app.ui.nav_button import NavButton
from app.ui.theme import GREEN, SIDEBAR_TEXT


class Sidebar(QFrame):
    """Premium deep-blue navigation rail for AG Printers modules."""

    #: Emitted with the destination name when a nav item is clicked.
    page_selected = Signal(str)

    NAV_ITEMS: tuple[str, ...] = (
        "Dashboard",
        "New Job",
        "Parties",
        "Gate Pass",
        "Invoices",
        "Costing",
        "Inventory",
        "Ledger",
        "Settings",
    )

    EXPANDED_WIDTH = 248
    COLLAPSED_WIDTH = 80
    ANIMATION_MS = 220
    INDICATOR_MS = 180  # active-pill glide: quick and professional

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self._collapsed = True
        self._vis_state: tuple[bool, bool, bool, bool] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 12)
        layout.setSpacing(4)

        # Sliding active indicator. Created *before* the nav buttons so it stays
        # behind them: the buttons paint transparent surfaces and let the pill
        # show through. It is not part of the layout - the sidebar positions it
        # manually and animates its geometry between items.
        self._indicator = ActiveIndicator(self)
        self._indicator_ready = False
        self._indicator_anim = QPropertyAnimation(self._indicator, b"geometry", self)
        self._indicator_anim.setDuration(self.INDICATOR_MS)
        self._indicator_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Branding row: title + collapse toggle -----------------------------
        self._title = QLabel("AG Printers")
        self._title.setObjectName("SidebarTitle")
        self._subtitle = QLabel("Business Management")
        self._subtitle.setObjectName("SidebarSubtitle")

        text_column = QVBoxLayout()
        text_column.setSpacing(1)
        text_column.addWidget(self._title)
        text_column.addWidget(self._subtitle)

        self._toggle = QPushButton()
        self._toggle.setObjectName("SidebarToggle")
        self._toggle.setFixedSize(30, 30)
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._toggle.setIconSize(QSize(18, 18))
        self._toggle.setIcon(icons.icon("chevron_right", SIDEBAR_TEXT))
        self._toggle.setToolTip("Expand sidebar")
        self._toggle.clicked.connect(self.toggle_collapsed)

        self._brand_row = QHBoxLayout()
        self._brand_row.setSpacing(8)
        self._brand_row.addLayout(text_column)
        # Spacer A pushes the toggle to the right; when both spacers expand
        # equally the toggle is centred (collapsed mode).
        self._spacer_a = QSpacerItem(
            0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._spacer_b = QSpacerItem(
            0, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        self._brand_row.addItem(self._spacer_a)
        self._brand_row.addWidget(self._toggle)
        self._brand_row.addItem(self._spacer_b)
        layout.addLayout(self._brand_row)

        layout.addSpacing(16)
        self._section = QLabel("MENU")
        self._section.setObjectName("SectionLabel")
        layout.addWidget(self._section)
        layout.addSpacing(2)

        # Navigation buttons (placeholders - no pages yet) ------------------
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[NavButton] = []
        for index, name in enumerate(self.NAV_ITEMS):
            button = NavButton(name, icons.NAV_ICONS[name])
            button.clicked.connect(
                lambda _checked=False, dest=name: self.page_selected.emit(dest)
            )
            button.toggled.connect(
                lambda on=False, b=button: self._on_nav_toggled(b, on)
            )
            self._group.addButton(button, index)
            layout.addWidget(button)
            self._buttons.append(button)

        layout.addStretch(1)

        # PDF Save Folder Section --------------------------------------------
        self._pdf_section = QFrame()
        self._pdf_section.setObjectName("PdfSectionFrame")
        self._pdf_section.setStyleSheet("""
            QFrame#PdfSectionFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
        """)
        pdf_sec_layout = QVBoxLayout(self._pdf_section)
        pdf_sec_layout.setContentsMargins(8, 8, 8, 8)
        pdf_sec_layout.setSpacing(6)

        pdf_title_row = QHBoxLayout()
        pdf_title_row.setContentsMargins(0, 0, 0, 0)
        pdf_title_lbl = QLabel("PDF SAVE FOLDER")
        pdf_title_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")
        pdf_title_row.addWidget(pdf_title_lbl)

        self._choose_folder_btn = QPushButton("Change")
        self._choose_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._choose_folder_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton:pressed {
                background: #1e40af;
            }
        """)
        self._choose_folder_btn.clicked.connect(self._on_choose_pdf_folder)
        pdf_title_row.addWidget(self._choose_folder_btn)
        pdf_sec_layout.addLayout(pdf_title_row)

        self._pdf_path_label = QLabel()
        self._pdf_path_label.setStyleSheet("font-size: 11px; color: #cbd5e1; background: transparent;")
        self._pdf_path_label.setWordWrap(True)
        pdf_sec_layout.addWidget(self._pdf_path_label)

        self._update_pdf_folder_display()
        layout.addWidget(self._pdf_section)
        layout.addSpacing(6)

        self._footer = QLabel(
            f'<span style="color:{GREEN};">●</span>  Offline  ·  v{__version__}'
        )
        self._footer.setObjectName("SidebarFooter")
        layout.addWidget(self._footer)

        self._buttons[0].setChecked(True)

        # Smooth expand / collapse width animation ---------------------------
        self._anim = QPropertyAnimation(self, b"minimumWidth", self)
        self._anim.setDuration(self.ANIMATION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.valueChanged.connect(self._on_width_changed)

        self._apply_visual_state(self.COLLAPSED_WIDTH)

    # -- collapse / expand ---------------------------------------------------

    @property
    def is_collapsed(self) -> bool:
        """True while the sidebar is in (or heading to) icon-only mode."""
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        """Expand or collapse the sidebar with an animated width change."""
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        target = self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH
        self._toggle.setIcon(
            icons.icon("chevron_right" if collapsed else "chevron_left", SIDEBAR_TEXT)
        )
        self._toggle.setToolTip("Expand sidebar" if collapsed else "Collapse sidebar")
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target)
        self._anim.start()

    def toggle_collapsed(self) -> None:
        """Switch between expanded and collapsed modes."""
        self.set_collapsed(not self._collapsed)

    def _on_width_changed(self, value) -> None:
        width = int(round(float(value)))
        # Keep minimum == maximum so the layout follows the animation exactly.
        self.setFixedWidth(width)
        self._apply_visual_state(width)

    def _apply_visual_state(self, width: int) -> None:
        show_brand = width >= 210
        show_aux = width >= 150  # MENU caption + footer
        icons_only = width < 140  # rail-style buttons
        centred_toggle = width < 180  # brand hidden -> sandwich the toggle

        state = (show_brand, show_aux, icons_only, centred_toggle)
        if state == self._vis_state:
            return
        self._vis_state = state

        self._title.setVisible(show_brand)
        self._subtitle.setVisible(show_brand)
        self._section.setVisible(show_aux)
        self._pdf_section.setVisible(show_aux)
        self._footer.setVisible(show_aux)

        self._spacer_a.changeSize(
            0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._spacer_b.changeSize(
            0,
            0,
            QSizePolicy.Policy.Expanding
            if centred_toggle
            else QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Minimum,
        )
        self._brand_row.invalidate()

        for button in self._buttons:
            button.setIconsOnly(icons_only)
        # The pill follows the rail through the width animation.
        self._indicator.set_icons_only(icons_only)
        self._place_indicator(animate=False)

    # -- sliding active indicator ---------------------------------------------

    def _active_pill_rect(self) -> QRect | None:
        """Geometry the pill should occupy for the currently checked item."""
        button = self._group.checkedButton()
        if button is None:
            return None
        rect = QRect(button.mapTo(self, QPoint(0, 0)), button.size())
        return rect.adjusted(INSET, 0, -INSET, 0)

    def _place_indicator(self, animate: bool) -> None:
        """Glide the pill to the active item (snap when *animate* is False)."""
        pill = self._active_pill_rect()
        if pill is None:
            self._indicator.setVisible(False)
            return
        self._indicator_anim.stop()
        self._indicator.setVisible(True)
        if animate and self._indicator_ready:
            self._indicator_anim.setStartValue(self._indicator.geometry())
            self._indicator_anim.setEndValue(pill)
            self._indicator_anim.start()
        else:
            self._indicator.setGeometry(pill)
            self._indicator_ready = True

    def _on_nav_toggled(self, button: NavButton, checked: bool) -> None:
        """Repaint the button and slide the pill onto newly selected items."""
        button.update()
        if checked:
            self._place_indicator(animate=True)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Button geometry is final only after the first show.
        self._place_indicator(animate=False)
        QTimer.singleShot(0, lambda: self._place_indicator(animate=False))

    def resizeEvent(self, event) -> None:
        # Width-animation frames and window resizes: keep the pill glued to the
        # active item without starting a competing glide animation.
        super().resizeEvent(event)
        if getattr(self, "_indicator", None) is not None:
            self._place_indicator(animate=False)


    @property
    def checked_item(self) -> str:
        """Label of the currently selected nav item (empty if none)."""
        button = self._group.checkedButton()
        return button.text() if button else ""

    def set_active_page(self, name: str) -> None:
        """Programmatically check the button for *name* without breaking exclusive group."""
        for button in self._buttons:
            if button.text() == name:
                button.setChecked(True)
                break

    def _update_pdf_folder_display(self) -> None:
        current_dir = get_pdf_export_dir()
        path_str = str(current_dir)
        self._pdf_path_label.setText(path_str)
        self._pdf_path_label.setToolTip(f"Invoices and Gate Passes will be saved here:\n{path_str}")

    def _on_choose_pdf_folder(self) -> None:
        current = str(get_pdf_export_dir())
        chosen = QFileDialog.getExistingDirectory(self, "Select PDF Save Folder", current)
        if chosen:
            set_pdf_export_dir(chosen)
            self._update_pdf_folder_display()


