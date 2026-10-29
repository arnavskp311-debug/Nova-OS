"""
Security Fortress & Privacy Protection Center Widget for NOVA OS.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QFileDialog, QLineEdit,
    QProgressBar, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer

from nova.security_fortress import SecureFileShredder, TOTPAuthenticator, EmergencyPanicWipe

class SecurityFortressWidget(QWidget):
    """High-security forensic defense and 2FA center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()
        icon = QLabel("🛡️")
        icon.setStyleSheet("font-size: 22px;")
        head.addWidget(icon)

        title = QLabel("SECURITY FORTRESS & FORENSIC PRIVACY")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(0, 240, 255, 0.25); background: #090e1a; border-radius: 6px; }
            QTabBar::tab { background: #0f1629; color: #94a3b8; padding: 6px 14px; margin-right: 4px; border-radius: 4px; font-weight: 600; }
            QTabBar::tab:selected { background: #0052cc; color: #ffffff; border: 1px solid #00f0ff; }
        """)

        # Tab 1: 2FA TOTP
        self.tab_totp = self._create_totp_tab()
        self.tabs.addTab(self.tab_totp, "🔑 2FA Authenticator")

        # Tab 2: Shredder
        self.tab_shred = self._create_shredder_tab()
        self.tabs.addTab(self.tab_shred, "🔥 7-Pass Shredder")

        # Tab 3: Panic Wipe
        self.tab_panic = self._create_panic_tab()
        self.tabs.addTab(self.tab_panic, "🚨 Emergency Panic")

        layout.addWidget(self.tabs)

    def _create_totp_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        card = QFrame()
        card.setStyleSheet("background: #0d1628; border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 8px; padding: 16px;")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(8)

        t_lbl = QLabel("TWO-FACTOR AUTHENTICATOR (RFC 6238)")
        t_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        c_lay.addWidget(t_lbl)

        code_row = QHBoxLayout()
        self.totp_code_lbl = QLabel("------")
        self.totp_code_lbl.setStyleSheet("color: #00ff88; font-size: 32px; font-weight: 800; font-family: 'Consolas'; letter-spacing: 4px;")
        code_row.addWidget(self.totp_code_lbl)
        code_row.addStretch()

        copy_btn = QPushButton("📋 Copy Token")
        copy_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        copy_btn.clicked.connect(self._copy_totp)
        code_row.addWidget(copy_btn)
        c_lay.addLayout(code_row)

        self.totp_timer_bar = QProgressBar()
        self.totp_timer_bar.setRange(0, 30)
        self.totp_timer_bar.setValue(30)
        self.totp_timer_bar.setFixedHeight(6)
        self.totp_timer_bar.setTextVisible(False)
        self.totp_timer_bar.setStyleSheet("QProgressBar::chunk { background: #00f0ff; border-radius: 3px; }")
        c_lay.addWidget(self.totp_timer_bar)

        lay.addWidget(card)
        lay.addStretch()

        self.totp_ticker = QTimer(self)
        self.totp_ticker.timeout.connect(self._refresh_totp)
        self.totp_ticker.start(1000)
        self._refresh_totp()

        return w

    def _refresh_totp(self):
        code, remaining = TOTPAuthenticator.generate_totp()
        self.totp_code_lbl.setText(code)
        self.totp_timer_bar.setValue(remaining)

    def _copy_totp(self):
        QApplication.clipboard().setText(self.totp_code_lbl.text())

    def _create_shredder_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("DoD 5220.22-M 7-Pass Military Grade File Shredder:"))
        desc = QLabel("Permanently overwrites target file data with 7 passes of zeros, ones, and cryptographic pseudorandom bytes. Unrecoverable.")
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        shred_btn = QPushButton("🔥 Select File & Shred Permanently")
        shred_btn.setStyleSheet("background: #2b1216; border: 1px solid #ff2a55; color: #ff2a55; font-weight: bold; padding: 10px; border-radius: 6px;")
        shred_btn.clicked.connect(self._shred_file_action)
        lay.addWidget(shred_btn)

        self.shred_status = QLabel("Ready.")
        self.shred_status.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        lay.addWidget(self.shred_status)
        lay.addStretch()
        return w

    def _shred_file_action(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select File to Shred Permanently")
        if fname:
            ok, msg = SecureFileShredder.shred_file(fname)
            self.shred_status.setText(msg)

    def _create_panic_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        card = QFrame()
        card.setStyleSheet("background: #240c12; border: 2px solid #ff2a55; border-radius: 8px; padding: 16px;")
        c_lay = QVBoxLayout(card)
        c_lay.setSpacing(10)

        t_lbl = QLabel("EMERGENCY SYSTEM PANIC DEFENSE")
        t_lbl.setStyleSheet("color: #ff2a55; font-weight: 800; font-size: 13px; letter-spacing: 1px;")
        c_lay.addWidget(t_lbl)

        info = QLabel("Triggering Panic Mode immediately flushes working set physical memory, purges transient browser and SQL caches, and triggers system lockdown.")
        info.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        info.setWordWrap(True)
        c_lay.addWidget(info)

        panic_btn = QPushButton("🚨 TRIGGER PANIC LOCKDOWN NOW")
        panic_btn.setStyleSheet("background: #ff2a55; color: #ffffff; font-weight: 800; padding: 12px; border-radius: 6px; font-size: 12px;")
        panic_btn.clicked.connect(self._trigger_panic)
        c_lay.addWidget(panic_btn)

        self.panic_status = QLabel("")
        self.panic_status.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 11px;")
        c_lay.addWidget(self.panic_status)

        lay.addWidget(card)
        lay.addStretch()
        return w

    def _trigger_panic(self):
        res = EmergencyPanicWipe.execute_panic()
        self.panic_status.setText(f"DEFENSE ACTIVE: Memory flushed & cache purged at {res['timestamp']}")
