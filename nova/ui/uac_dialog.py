"""
Cyber User Account Control (UAC) & Sudo Elevation Prompt for NOVA OS.
Presents a high-security visual authorization dialog before executing
consequential or privileged operations.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit
)
from PySide6.QtCore import Qt
from nova.database import get_setting

class UACDialog(QDialog):
    """Visual privilege elevation prompt."""

    def __init__(self, action_name: str, app_name: str = "NOVA OS Kernel", details: str = "", parent=None):
        super().__init__(parent)
        self.action_name = action_name
        self.app_name = app_name
        self.details = details
        self.approved = False

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setFixedSize(400, 260)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #090e1a;
                border: 2px solid #ffaa00;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # Header with Security Shield
        head = QHBoxLayout()
        shield = QLabel("🛡️")
        shield.setStyleSheet("font-size: 24px;")
        head.addWidget(shield)

        title_box = QVBoxLayout()
        t1 = QLabel("USER ACCOUNT CONTROL")
        t1.setStyleSheet("color: #ffaa00; font-weight: 800; font-size: 13px; letter-spacing: 1px;")
        title_box.addWidget(t1)

        t2 = QLabel("Elevated Privilege Request")
        t2.setStyleSheet("color: #94a3b8; font-size: 10px;")
        title_box.addWidget(t2)
        head.addLayout(title_box)
        head.addStretch()
        layout.addLayout(head)

        # Action Details Card
        card = QFrame()
        card.setStyleSheet("background: #0f1629; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px;")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(4)

        act_lbl = QLabel(f"Program: {self.app_name}")
        act_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px;")
        c_lay.addWidget(act_lbl)

        det_lbl = QLabel(f"Action: {self.action_name}")
        det_lbl.setStyleSheet("color: #00f0ff; font-size: 10px;")
        c_lay.addWidget(det_lbl)

        if self.details:
            extra = QLabel(self.details)
            extra.setStyleSheet("color: #64748b; font-size: 9px;")
            extra.setWordWrap(True)
            c_lay.addWidget(extra)

        layout.addWidget(card)

        # Query Prompt
        q_lbl = QLabel("Do you want to allow this app to make changes?")
        q_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 500;")
        layout.addWidget(q_lbl)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.block_btn = QPushButton("Block (No)")
        self.block_btn.setFixedHeight(32)
        self.block_btn.setStyleSheet("""
            QPushButton {
                background: #1e121d;
                border: 1px solid #ff2a55;
                color: #ff2a55;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.block_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.block_btn)

        self.allow_btn = QPushButton("Allow (Yes)")
        self.allow_btn.setFixedHeight(32)
        self.allow_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                color: #ffffff;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.allow_btn.clicked.connect(self.accept)
        btn_box.addWidget(self.allow_btn)

        layout.addLayout(btn_box)

    @classmethod
    def request_elevation(cls, action_name: str, app_name: str = "NOVA OS Kernel", details: str = "", parent=None) -> bool:
        """Helper to invoke UAC modal and return True if granted."""
        dialog = cls(action_name, app_name, details, parent)
        result = dialog.exec()
        return result == QDialog.Accepted
