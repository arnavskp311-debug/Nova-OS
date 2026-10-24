"""
NOVA OS Cyber HUD Notification & Toast System.
Non-blocking, animated alert overlays for desktop notifications,
reminders, security alerts, and system telemetry warnings.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, Signal, QObject
from PySide6.QtGui import QFont, QColor

class NotificationToast(QFrame):
    closed = Signal(object)

    COLORS = {
        "info": "#00f0ff",     # Cyan
        "success": "#00ff88",  # Green
        "warning": "#ffaa00",  # Amber
        "error": "#ff2a55",    # Red
        "reminder": "#b026ff"  # Violet
    }

    ICONS = {
        "info": "❖",
        "success": "✓",
        "warning": "⚠",
        "error": "✖",
        "reminder": "🔔"
    }

    def __init__(self, title: str, message: str, level: str = "info", duration_ms: int = 4000, parent=None):
        super().__init__(parent)
        self.level = level if level in self.COLORS else "info"
        self.accent_color = self.COLORS[self.level]
        self.icon_symbol = self.ICONS.get(self.level, "❖")
        self.duration_ms = duration_ms

        self.setObjectName("NotificationToast")
        self.setFixedWidth(320)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.setup_ui(title, message)
        self.setup_animation()

        # Auto-dismiss timer
        if self.duration_ms > 0:
            self.dismiss_timer = QTimer(self)
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self.fade_out_and_close)
            self.dismiss_timer.start(self.duration_ms)
        else:
            self.dismiss_timer = None

    def setup_ui(self, title: str, message: str):
        self.setStyleSheet(f"""
            QFrame#NotificationToast {{
                background-color: rgba(10, 15, 28, 0.96);
                border: 1px solid {self.accent_color};
                border-left: 4px solid {self.accent_color};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(8)

        icon_lbl = QLabel(self.icon_symbol)
        icon_lbl.setStyleSheet(f"color: {self.accent_color}; font-size: 14px; font-weight: bold;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
        header.addWidget(title_lbl, stretch=1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.fade_out_and_close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Message Body
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.3;")
        layout.addWidget(msg_lbl)

    def setup_animation(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(220)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.start()

    def enterEvent(self, event):
        """Pause auto-dismiss when user hovers mouse over toast."""
        if self.dismiss_timer and self.dismiss_timer.isActive():
            self.dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resume dismiss after mouse leaves."""
        if self.dismiss_timer:
            self.dismiss_timer.start(2000)
        super().leaveEvent(event)

    def fade_out_and_close(self):
        if hasattr(self, "_closing") and self._closing:
            return
        self._closing = True
        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(180)
        self.fade_out_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.finished.connect(self._do_close)
        self.fade_out_anim.start()

    def _do_close(self):
        self.closed.emit(self)
        self.close()

class NotificationManager(QObject):
    """Manages active toast notifications stack on top-right of canvas."""
    def __init__(self, parent_canvas: QWidget):
        super().__init__(parent_canvas)
        self.parent_canvas = parent_canvas
        self.toasts: List[NotificationToast] = []

    def notify(self, title: str, message: str, level: str = "info", duration_ms: int = 4000) -> NotificationToast:
        toast = NotificationToast(title, message, level=level, duration_ms=duration_ms, parent=self.parent_canvas)
        toast.closed.connect(self._on_toast_closed)
        self.toasts.append(toast)
        self.reposition_toasts()
        toast.show()
        toast.raise_()
        return toast

    def _on_toast_closed(self, toast: NotificationToast):
        if toast in self.toasts:
            self.toasts.remove(toast)
        self.reposition_toasts()

    def reposition_toasts(self):
        """Stacks toasts from top-right corner downward."""
        margin_right = 20
        margin_top = 20
        spacing = 10
        current_y = margin_top
        canvas_width = self.parent_canvas.width()

        for toast in self.toasts:
            toast_w = toast.width()
            pos_x = max(10, canvas_width - toast_w - margin_right)
            toast.move(pos_x, current_y)
            current_y += toast.sizeHint().height() + spacing
