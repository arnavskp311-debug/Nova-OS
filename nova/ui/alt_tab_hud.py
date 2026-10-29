"""
Visual Alt+Tab App Switcher HUD for NOVA OS.
Displays an interactive translucent cyberpunk card deck of open windows with
keyboard arrow navigation, Enter activation, and auto-focus raising.
"""

from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QKeyEvent, QFont

class AltTabHUD(QFrame):
    window_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AltTabHUD")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QFrame#AltTabHUD {
                background-color: rgba(9, 14, 26, 0.95);
                border: 2px solid #00f0ff;
                border-radius: 16px;
            }
        """)
        self.windows_list: List[Tuple[str, str, object]] = []  # (title, icon, frame_obj)
        self.selected_index = 0
        self.cards: List[QFrame] = []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(12)

        # Header Title
        title = QLabel("ACTIVE APPS (ALT + TAB)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        self.main_layout.addWidget(title)

        # Cards container
        self.deck_container = QWidget()
        self.deck_layout = QHBoxLayout(self.deck_container)
        self.deck_layout.setContentsMargins(0, 0, 0, 0)
        self.deck_layout.setSpacing(12)
        self.main_layout.addWidget(self.deck_container)

    def show_switcher(self, open_windows: List[Tuple[str, str, object]], parent_widget: Optional[QWidget] = None):
        """Populates and opens the HUD centered on screen."""
        self.windows_list = open_windows
        if not self.windows_list:
            return

        # Clear existing
        while self.deck_layout.count():
            item = self.deck_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        # Build cards
        for idx, (title, icon_txt, frame_obj) in enumerate(self.windows_list):
            card = QFrame()
            card.setFixedSize(110, 100)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(8, 8, 8, 8)
            c_lay.setSpacing(4)
            c_lay.setAlignment(Qt.AlignCenter)

            icon_lbl = QLabel(icon_txt or "◈")
            icon_lbl.setStyleSheet("font-size: 26px; color: #00f0ff;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            c_lay.addWidget(icon_lbl)

            name_lbl = QLabel(title[:14] + "..." if len(title) > 14 else title)
            name_lbl.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 600;")
            name_lbl.setAlignment(Qt.AlignCenter)
            c_lay.addWidget(name_lbl)

            card.mousePressEvent = lambda e, i=idx: self.select_and_activate(i)
            self.cards.append(card)
            self.deck_layout.addWidget(card)

        # Start with next window selected (standard Alt+Tab behavior)
        self.selected_index = 1 if len(self.windows_list) > 1 else 0
        self.update_card_styles()

        # Center in parent or screen
        width = max(300, len(self.windows_list) * 122 + 40)
        self.setFixedSize(width, 160)
        if parent_widget:
            p_geom = parent_widget.geometry()
            x = p_geom.x() + (p_geom.width() - width) // 2
            y = p_geom.y() + (p_geom.height() - 160) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen()
            if screen:
                s_geom = screen.geometry()
                self.move((s_geom.width() - width) // 2, (s_geom.height() - 160) // 2)

        self.show()
        self.raise_()
        self.setFocus()

    def cycle_next(self):
        """Advances selection to the next open window."""
        if not self.windows_list:
            return
        self.selected_index = (self.selected_index + 1) % len(self.windows_list)
        self.update_card_styles()

    def cycle_prev(self):
        """Moves selection to previous window."""
        if not self.windows_list:
            return
        self.selected_index = (self.selected_index - 1) % len(self.windows_list)
        self.update_card_styles()

    def update_card_styles(self):
        for idx, card in enumerate(self.cards):
            if idx == self.selected_index:
                card.setStyleSheet("""
                    QFrame {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a274c, stop:1 #0e1933);
                        border: 2px solid #00f0ff;
                        border-radius: 10px;
                    }
                """)
            else:
                card.setStyleSheet("""
                    QFrame {
                        background: #0f1629;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 10px;
                    }
                """)

    def select_and_activate(self, index: int):
        if 0 <= index < len(self.windows_list):
            _, _, frame_obj = self.windows_list[index]
            self.hide()
            self.window_selected.emit(frame_obj)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Tab:
            if event.modifiers() & Qt.ShiftModifier:
                self.cycle_prev()
            else:
                self.cycle_next()
            event.accept()
        elif event.key() == Qt.Key_Right:
            self.cycle_next()
            event.accept()
        elif event.key() == Qt.Key_Left:
            self.cycle_prev()
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.select_and_activate(self.selected_index)
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)
