"""
Keyboard Layout Switcher for NOVA OS.
Presents a compact system tray indicator (ENG / US / INTL) and allows
quick layout toggling.
"""

from typing import List
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Signal

class KeyboardSwitcherPill(QPushButton):
    layout_changed = Signal(str)

    LAYOUTS = ["ENG", "US", "INTL"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_idx = 0
        self.setFixedSize(38, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Keyboard Layout (Click or Alt+Shift to toggle)")
        self.setStyleSheet("""
            QPushButton {
                background: #111a2f;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 13px;
                color: #00f0ff;
                font-weight: 800;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.update_label()
        self.clicked.connect(self.cycle_layout)

    def update_label(self):
        self.setText(self.LAYOUTS[self.current_idx])

    def cycle_layout(self):
        self.current_idx = (self.current_idx + 1) % len(self.LAYOUTS)
        self.update_label()
        self.layout_changed.emit(self.LAYOUTS[self.current_idx])
