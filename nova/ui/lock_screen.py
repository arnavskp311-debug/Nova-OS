"""
Cyber Lock Screen Subsystem for NOVA OS.
Provides a secure, immersive lock screen with live neon clock, system status,
PIN / password authentication keypad, and inactivity auto-lock.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QGridLayout, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QPainter

from nova.database import get_setting, set_setting

class CyberLockScreen(QFrame):
    unlocked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LockScreen")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QFrame#LockScreen {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #050811, stop:0.5 #080d1e, stop:1 #03050a);
            }
        """)
        self.pin_code = get_setting("lock_screen_pin") or "0000"
        self.entered_pin = ""
        self.setup_ui()

        # Clock timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 60, 40, 40)
        main_layout.setAlignment(Qt.AlignCenter)

        # Upper Clock Display
        self.clock_lbl = QLabel()
        self.clock_lbl.setAlignment(Qt.AlignCenter)
        self.clock_lbl.setStyleSheet("color: #00f0ff; font-size: 54px; font-weight: 800; letter-spacing: 2px;")
        main_layout.addWidget(self.clock_lbl)

        self.date_lbl = QLabel()
        self.date_lbl.setAlignment(Qt.AlignCenter)
        self.date_lbl.setStyleSheet("color: #94a3b8; font-size: 16px; font-weight: 500; margin-bottom: 24px;")
        main_layout.addWidget(self.date_lbl)

        # Auth Container Box
        auth_box = QFrame()
        auth_box.setFixedSize(320, 360)
        auth_box.setStyleSheet("""
            QFrame {
                background-color: rgba(14, 21, 38, 0.95);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 16px;
            }
        """)
        a_lay = QVBoxLayout(auth_box)
        a_lay.setContentsMargins(24, 20, 24, 20)
        a_lay.setSpacing(12)

        user_title = QLabel("❖ NOVA SECURITY VAULT")
        user_title.setAlignment(Qt.AlignCenter)
        user_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        a_lay.addWidget(user_title)

        sub_msg = QLabel("Enter 4-Digit Security PIN (Default: 0000)")
        sub_msg.setAlignment(Qt.AlignCenter)
        sub_msg.setStyleSheet("color: #64748b; font-size: 10px;")
        a_lay.addWidget(sub_msg)

        # PIN display dots
        self.pin_display = QLabel("○  ○  ○  ○")
        self.pin_display.setAlignment(Qt.AlignCenter)
        self.pin_display.setStyleSheet("color: #00f0ff; font-size: 22px; font-weight: bold; padding: 6px;")
        a_lay.addWidget(self.pin_display)

        self.status_msg = QLabel("")
        self.status_msg.setAlignment(Qt.AlignCenter)
        self.status_msg.setStyleSheet("color: #ff2a55; font-size: 10px; font-weight: bold;")
        a_lay.addWidget(self.status_msg)

        # 3x4 Keypad Grid
        grid = QGridLayout()
        grid.setSpacing(8)

        digits = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("CLR", 3, 0), ("0", 3, 1), ("OK", 3, 2),
        ]

        for text, r, c in digits:
            btn = QPushButton(text)
            btn.setFixedSize(54, 40)
            btn.setCursor(Qt.PointingHandCursor)
            if text in ("CLR", "OK"):
                btn.setStyleSheet("""
                    QPushButton {
                        background: #1c152a;
                        border: 1px solid #b026ff;
                        color: #e2b3ff;
                        font-weight: bold;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: #b026ff;
                        color: #ffffff;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #111a2f;
                        border: 1px solid rgba(0, 240, 255, 0.2);
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: #00f0ff;
                        color: #050811;
                    }
                """)

            if text == "CLR":
                btn.clicked.connect(self.clear_pin)
            elif text == "OK":
                btn.clicked.connect(self.verify_pin)
            else:
                btn.clicked.connect(lambda chk, d=text: self.append_digit(d))

            grid.addWidget(btn, r, c)

        a_lay.addLayout(grid)
        main_layout.addWidget(auth_box, alignment=Qt.AlignCenter)

    def update_clock(self):
        now = datetime.now()
        self.clock_lbl.setText(now.strftime("%I:%M %p"))
        self.date_lbl.setText(now.strftime("%A, %B %d, %Y"))

    def append_digit(self, digit: str):
        if len(self.entered_pin) < 6:
            self.entered_pin += digit
            self.update_pin_dots()
            if len(self.entered_pin) == 4:
                self.verify_pin()

    def clear_pin(self):
        self.entered_pin = ""
        self.status_msg.setText("")
        self.update_pin_dots()

    def update_pin_dots(self):
        length = len(self.entered_pin)
        dots = []
        for i in range(4):
            dots.append("●" if i < length else "○")
        self.pin_display.setText("  ".join(dots))

    def verify_pin(self):
        current_pin = get_setting("lock_screen_pin") or "0000"
        if self.entered_pin == current_pin:
            self.status_msg.setStyleSheet("color: #00ff88; font-size: 10px; font-weight: bold;")
            self.status_msg.setText("ACCESS GRANTED")
            QTimer.singleShot(250, self.do_unlock)
        else:
            self.status_msg.setStyleSheet("color: #ff2a55; font-size: 10px; font-weight: bold;")
            self.status_msg.setText("INVALID PIN - ACCESS DENIED")
            self.entered_pin = ""
            self.update_pin_dots()

    def do_unlock(self):
        self.hide()
        self.clear_pin()
        self.unlocked.emit()

    def lock(self):
        self.clear_pin()
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.show()
        self.raise_()
        self.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if Qt.Key_0 <= key <= Qt.Key_9:
            self.append_digit(chr(ord('0') + (key - Qt.Key_0)))
            event.accept()
        elif key == Qt.Key_Backspace:
            self.entered_pin = self.entered_pin[:-1]
            self.update_pin_dots()
            event.accept()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.verify_pin()
            event.accept()
        elif key == Qt.Key_Escape:
            self.clear_pin()
            event.accept()
        else:
            super().keyPressEvent(event)
