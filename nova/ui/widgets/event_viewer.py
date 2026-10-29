"""
System Event Viewer & Diagnostic Timeline for NOVA OS.
Monitors and displays application logs, hardware events, and security audits
in an interactive real-time timeline.
"""

import time
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt

from nova.database import get_recent_command_logs

class SystemEventViewer(QWidget):
    """Interactive Event Viewer table for diagnostics and audits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        head = QHBoxLayout()
        icon = QLabel("📜")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("SYSTEM EVENT VIEWER & DIAGNOSTICS")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #111a2f;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #00f0ff;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_events)
        head.addWidget(refresh_btn)
        layout.addLayout(head)

        # Filters
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        f_lbl = QLabel("Severity:")
        f_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        filter_bar.addWidget(f_lbl)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["All Events", "INFO", "WARNING", "ERROR"])
        self.severity_combo.currentIndexChanged.connect(self.refresh_events)
        filter_bar.addWidget(self.severity_combo)

        filter_bar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter events...")
        self.search_box.textChanged.connect(self.refresh_events)
        self.search_box.setFixedWidth(200)
        filter_bar.addWidget(self.search_box)
        layout.addLayout(filter_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Severity", "Source / Command", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
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

        self.refresh_events()

    def refresh_events(self):
        logs = get_recent_command_logs(50)
        q = self.search_box.text().strip().lower()
        sev_filter = self.severity_combo.currentText()

        filtered = []
        for l in logs:
            status = l.get("status", "SUCCESS")
            sev = "ERROR" if status == "BLOCKED" or "fail" in status.lower() else "INFO"

            if sev_filter != "All Events" and sev != sev_filter:
                continue

            cmd_txt = l.get("command", "")
            desc_txt = l.get("description", "")
            if q and (q not in cmd_txt.lower() and q not in desc_txt.lower()):
                continue

            filtered.append({
                "timestamp": l.get("timestamp", ""),
                "severity": sev,
                "source": cmd_txt,
                "details": desc_txt or f"Safety: {l.get('safety_level')}"
            })

        self.table.setRowCount(len(filtered))
        for r, ev in enumerate(filtered):
            self.table.setItem(r, 0, QTableWidgetItem(ev["timestamp"]))

            sev_item = QTableWidgetItem(ev["severity"])
            if ev["severity"] == "ERROR":
                sev_item.setForeground(Qt.red)
            else:
                sev_item.setForeground(Qt.green)
            self.table.setItem(r, 1, sev_item)

            self.table.setItem(r, 2, QTableWidgetItem(ev["source"]))
            self.table.setItem(r, 3, QTableWidgetItem(ev["details"]))
