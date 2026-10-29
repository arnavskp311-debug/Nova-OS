"""
Application Uninstaller & Package Cleaner for NOVA OS.
Safely removes user-installed shortcuts, extensions, and resets cached app data.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PySide6.QtCore import Qt

from nova.config import DATA_DIR

SHORTCUTS_FILE = DATA_DIR / "desktop_shortcuts.json"

class AppUninstaller(QWidget):
    """UI for managing and cleanly removing installed desktop shortcuts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def _load_shortcuts(self) -> List[Dict[str, Any]]:
        if not SHORTCUTS_FILE.exists():
            return []
        try:
            with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_shortcuts(self, data: List[Dict[str, Any]]):
        try:
            with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("📦")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("APPLICATION UNINSTALLER & CLEANER")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        self.uninstall_btn = QPushButton("🗑 Uninstall Selected")
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background: #2b1216;
                border: 1px solid #ff2a55;
                border-radius: 6px;
                color: #ff2a55;
                font-weight: bold;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.uninstall_btn.clicked.connect(self.on_uninstall_selected)
        bar_widget = QWidget()
        layout.addLayout(head)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["App Name", "App ID / Target", "Type"])
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
        layout.addWidget(self.uninstall_btn, alignment=Qt.AlignRight)

        self.refresh_table()

    def refresh_table(self):
        items = self._load_shortcuts()
        self.table.setRowCount(len(items))

        for r, item in enumerate(items):
            self.table.setItem(r, 0, QTableWidgetItem(f"{item.get('icon', '◈')} {item.get('name', 'Unknown')}"))
            self.table.setItem(r, 1, QTableWidgetItem(item.get("app_id", "")))
            t_str = "Windows App" if item.get("app_id", "").startswith("winapp_") else "System Tool"
            self.table.setItem(r, 2, QTableWidgetItem(t_str))

    def on_uninstall_selected(self):
        curr_row = self.table.currentRow()
        if curr_row < 0:
            return

        items = self._load_shortcuts()
        if 0 <= curr_row < len(items):
            removed = items.pop(curr_row)
            self._save_shortcuts(items)
            self.refresh_table()
