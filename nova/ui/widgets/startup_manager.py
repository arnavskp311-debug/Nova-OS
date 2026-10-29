"""
Startup Applications Manager for NOVA OS.
Configures which native applications and background tasks launch automatically
upon system boot or login.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QCheckBox,
    QHeaderView, QFrame
)
from PySide6.QtCore import Qt

from nova.config import DATA_DIR

STARTUP_FILE = DATA_DIR / "startup_apps.json"

DEFAULT_STARTUP = [
    {"id": "dashboard", "name": "Telemetry Dashboard", "enabled": True, "desc": "Live hardware performance metrics"},
    {"id": "chat", "name": "NOVA AI Assistant", "enabled": False, "desc": "Local Ollama AI copilot"},
    {"id": "pajama", "name": "Pajama Studio IDE", "enabled": False, "desc": "Cyber coding environment"},
    {"id": "calendar", "name": "Calendar & Agendas", "enabled": True, "desc": "Daily reminders & scheduled alarms"},
]

class StartupManager(QWidget):
    """Configures startup applications."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def _load_apps(self) -> List[Dict[str, Any]]:
        if not STARTUP_FILE.exists():
            self._save_apps(DEFAULT_STARTUP)
            return list(DEFAULT_STARTUP)
        try:
            with open(STARTUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return list(DEFAULT_STARTUP)

    def _save_apps(self, apps: List[Dict[str, Any]]):
        try:
            with open(STARTUP_FILE, "w", encoding="utf-8") as f:
                json.dump(apps, f, indent=2)
        except Exception:
            pass

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🚀")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("STARTUP APPLICATIONS MANAGER")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        info = QLabel("Enable or disable services and programs that launch automatically with NOVA OS.")
        info.setStyleSheet("color: #94a3b8; font-size: 10px;")
        layout.addWidget(info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Launch", "Application", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
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
        apps = self._load_apps()
        self.table.setRowCount(len(apps))

        for r, app in enumerate(apps):
            # Checkbox
            chk = QCheckBox()
            chk.setChecked(app.get("enabled", False))
            chk.stateChanged.connect(lambda state, idx=r: self.on_toggle(idx, state == Qt.Checked))
            
            chk_widget = QWidget()
            chk_lay = QHBoxLayout(chk_widget)
            chk_lay.addWidget(chk)
            chk_lay.setAlignment(Qt.AlignCenter)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(r, 0, chk_widget)

            name_item = QTableWidgetItem(app.get("name", "Unknown"))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 1, name_item)

            desc_item = QTableWidgetItem(app.get("desc", ""))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 2, desc_item)

    def on_toggle(self, row_idx: int, enabled: bool):
        apps = self._load_apps()
        if 0 <= row_idx < len(apps):
            apps[row_idx]["enabled"] = enabled
            self._save_apps(apps)
