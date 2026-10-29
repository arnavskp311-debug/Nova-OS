"""
Global Hotkey & Shortcut Management Registry for NOVA OS.
Manages customizable system keybindings for instant access to tools and features.
"""

import json
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal

from nova.config import DATA_DIR

HOTKEYS_FILE = DATA_DIR / "hotkeys.json"

DEFAULT_HOTKEYS = {
    "universal_search": {"name": "Universal Search & Directives", "shortcut": "Ctrl+Space"},
    "voice_assistant": {"name": "Voice Assistant", "shortcut": "Ctrl+Shift+Space"},
    "quick_settings": {"name": "Quick Settings Flyout", "shortcut": "Ctrl+Shift+S"},
    "lock_screen": {"name": "Lock NOVA Screen", "shortcut": "Ctrl+L"},
    "alt_tab": {"name": "App Switcher Carousel", "shortcut": "Alt+Tab"},
    "terminal": {"name": "Safe Cyber Terminal", "shortcut": "Ctrl+Alt+T"},
    "pajama": {"name": "Pajama Studio IDE", "shortcut": "Ctrl+Shift+P"},
    "fullscreen_kiosk": {"name": "Toggle Borderless Fullscreen", "shortcut": "F11"}
}

class HotkeyRegistry:
    """Manages system shortcut configuration."""

    @classmethod
    def get_hotkeys(cls) -> Dict[str, Dict[str, str]]:
        if not HOTKEYS_FILE.exists():
            cls._save(DEFAULT_HOTKEYS)
            return dict(DEFAULT_HOTKEYS)
        try:
            with open(HOTKEYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return dict(DEFAULT_HOTKEYS)

    @classmethod
    def _save(cls, data: Dict[str, Dict[str, str]]):
        try:
            with open(HOTKEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def set_shortcut(cls, action_id: str, new_shortcut: str):
        hk = cls.get_hotkeys()
        if action_id in hk:
            hk[action_id]["shortcut"] = new_shortcut
            cls._save(hk)


class HotkeyRebinderWidget(QWidget):
    """UI for viewing and configuring shortcut keys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("⌨️")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("GLOBAL HOTKEY & SHORTCUT REBINDER")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut Key"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0d1424;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
                color: #e2e8f0;
            }
            QHeaderView::section {
                background: #111a30;
                color: #00f0ff;
                font-weight: bold;
                padding: 4px;
            }
        """)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        hotkeys = HotkeyRegistry.get_hotkeys()
        self.table.setRowCount(len(hotkeys))

        for r, (a_id, data) in enumerate(hotkeys.items()):
            self.table.setItem(r, 0, QTableWidgetItem(data.get("name", a_id)))
            
            sc_item = QTableWidgetItem(data.get("shortcut", ""))
            sc_item.setForeground(Qt.cyan)
            self.table.setItem(r, 1, sc_item)
