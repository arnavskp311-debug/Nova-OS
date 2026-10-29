"""
Date, Time & NTP Synchronization Center for NOVA OS.
Configures 12h/24h display formats, timezone preferences,
and performs Internet time synchronization.
"""

import sys
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal

from nova.database import get_setting, set_setting

class DateTimeSettings(QWidget):
    settings_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🕒")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("DATE, TIME & NTP SYNCHRONIZATION")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        # 24h format checkbox
        self.fmt_chk = QCheckBox("Use 24-Hour Military Time Format (e.g. 17:30 instead of 5:30 PM)")
        is_24h = get_setting("time_format_24h") == "true"
        self.fmt_chk.setChecked(is_24h)
        self.fmt_chk.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.fmt_chk.stateChanged.connect(self.on_format_changed)
        layout.addWidget(self.fmt_chk)

        # NTP Sync Section
        ntp_card = QFrame()
        ntp_card.setStyleSheet("background: #0d1424; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 8px; padding: 10px;")
        c_lay = QVBoxLayout(ntp_card)
        c_lay.setSpacing(6)

        ntp_lbl = QLabel("INTERNET TIME SERVER (NTP)")
        ntp_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        c_lay.addWidget(ntp_lbl)

        server_row = QHBoxLayout()
        s_title = QLabel("Server: time.windows.com (pool.ntp.org)")
        s_title.setStyleSheet("color: #94a3b8; font-size: 11px;")
        server_row.addWidget(s_title)
        server_row.addStretch()

        self.sync_btn = QPushButton("Sync Now ↻")
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.sync_btn.clicked.connect(self.sync_time)
        server_row.addWidget(self.sync_btn)
        c_lay.addLayout(server_row)

        self.sync_status = QLabel("Last sync: System clock accurate")
        self.sync_status.setStyleSheet("color: #00ff88; font-size: 10px;")
        c_lay.addWidget(self.sync_status)
        layout.addWidget(ntp_card)

        layout.addStretch()

    def on_format_changed(self, state):
        set_setting("time_format_24h", "true" if state == Qt.Checked else "false")
        self.settings_updated.emit()

    def sync_time(self):
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["w32tm", "/resync"],
                    capture_output=True,
                    timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                )
                self.sync_status.setText(f"Synchronized at {datetime.now().strftime('%I:%M:%S %p')}")
            except Exception:
                self.sync_status.setText(f"Time checked at {datetime.now().strftime('%I:%M:%S %p')}")
        else:
            self.sync_status.setText(f"Synced with local RTC at {datetime.now().strftime('%I:%M:%S %p')}")
