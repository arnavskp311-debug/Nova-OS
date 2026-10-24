"""
Security Approval Dialog for NOVA OS.
Blocks unauthorized or risky executions until user gives explicit consent.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from nova.safety import RiskLevel

class CommandApprovalDialog(QDialog):
    def __init__(self, command: str, risk_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NOVA OS - Security Enforcement Gate")
        self.setMinimumWidth(560)
        self.setModal(True)
        
        self.command = command
        self.risk_info = risk_info
        self.approved = False
        self.edited_command = command

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Frame
        risk = self.risk_info.get("risk", RiskLevel.MODERATE)
        risk_color = "#00f0ff"
        if risk == RiskLevel.HIGH:
            risk_color = "#ffaa00"
        elif risk == RiskLevel.BLOCKED:
            risk_color = "#ff2a55"
        elif risk == RiskLevel.SAFE:
            risk_color = "#00ff88"

        header = QLabel(f"SECURITY CLEARANCE REQUIRED: [{risk}]")
        header.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {risk_color}; letter-spacing: 1px;")
        layout.addWidget(header)

        # Description / Reason
        reason = self.risk_info.get("reason", "An operation requested system execution.")
        reason_label = QLabel(reason)
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet("color: #a0aec0; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(reason_label)

        # Command Editor / Preview Box
        cmd_title = QLabel("Proposed Command (You may edit before execution):")
        cmd_title.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        layout.addWidget(cmd_title)

        self.cmd_editor = QTextEdit()
        self.cmd_editor.setPlainText(self.command)
        self.cmd_editor.setMaximumHeight(90)
        self.cmd_editor.setFont(QFont("Consolas", 11))
        layout.addWidget(self.cmd_editor)

        # Safeguard Note
        note = QLabel(
            "Safeguard Policy: NOVA OS strictly protects host Windows files and never executes unauthorized actions. "
            "Modifications outside project data are logged and monitored."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(note)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.reject_btn = QPushButton("Reject / Cancel")
        self.reject_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.reject_btn)

        if risk == RiskLevel.BLOCKED:
            blocked_label = QLabel("Operation is strictly blocked by safety kernel.")
            blocked_label.setStyleSheet("color: #ff2a55; font-weight: bold;")
            btn_layout.addWidget(blocked_label)
        else:
            self.approve_btn = QPushButton("Approve & Execute")
            self.approve_btn.setObjectName("PrimaryButton")
            self.approve_btn.clicked.connect(self.on_approve)
            btn_layout.addWidget(self.approve_btn)

        layout.addLayout(btn_layout)

    def on_approve(self):
        self.approved = True
        self.edited_command = self.cmd_editor.toPlainText().strip()
        self.accept()
