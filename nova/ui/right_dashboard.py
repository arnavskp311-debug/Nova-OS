"""
NOVA OS: Right System Dashboard.
Matches the official reference design layout:
- Top Clock & Date (e.g. 10:24 AM, Wed, Apr 23, 2025)
- Weather Card (18°C, Partly Cloudy, London, UK)
- Quick Hardware Status Bar (Wi-Fi, Bluetooth, Audio, Battery, Heart, Lock)
- System Monitor Card with 3 Circular Radial Progress Rings (CPU, RAM, Disk)
- Recent Activity List with timestamps
- Quick Actions 2x2 Grid (Settings, Dark Mode, Focus Mode, Lock Screen)
"""

import time
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from nova.system_monitor import SystemMonitor

class CircularMeter(QWidget):
    """
    Circular Radial Progress Ring drawn via QPainter.
    Matches the exact cyan/green/blue dials in the reference image.
    """
    def __init__(self, title: str, color: QColor, initial_val: int = 12, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.value = initial_val
        self.setFixedSize(70, 80)

    def set_value(self, val: int):
        self.value = max(0, min(100, int(val)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        dial_size = 54
        rect = QRectF((w - dial_size) / 2, 4, dial_size, dial_size)

        # Background track ring
        track_pen = QPen(QColor(255, 255, 255, 20), 4.5)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Foreground progress arc (starts at 12 o'clock, clockwise)
        span_angle = int(- (self.value / 100.0) * 360 * 16)
        progress_pen = QPen(self.color, 4.5, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(progress_pen)
        painter.drawArc(rect, 90 * 16, span_angle)

        # Inner percentage text
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        val_str = f"{self.value}%"
        painter.drawText(QRectF(rect.x(), rect.y() + 2, rect.width(), rect.height()), Qt.AlignCenter, val_str)

        # Label underneath
        painter.setPen(QColor("#94A3B8"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Medium))
        painter.drawText(QRectF(0, h - 18, w, 16), Qt.AlignCenter, self.title)

        painter.end()


class RightSystemDashboard(QFrame):
    """
    Persistent right-side cyber dashboard matching the reference layout.
    """
    settings_requested = Signal()
    dark_mode_toggled = Signal()
    focus_mode_toggled = Signal()
    lock_requested = Signal()

    def __init__(self, system_monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.setObjectName("RightSystemDashboard")
        self.monitor = system_monitor
        self.setFixedWidth(275)
        self.init_ui()

        # Telemetry & Clock update timer (every 1 second)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_telemetry)
        self.timer.start(1000)
        self._refresh_telemetry()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame#RightSystemDashboard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(10, 18, 34, 0.90),
                    stop:1 rgba(7, 12, 22, 0.95));
                border-left: 1px solid rgba(0, 210, 230, 0.18);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(10)

        # 1. Top Clock & Date
        clock_card = QWidget()
        cc_layout = QVBoxLayout(clock_card)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(2)

        self.clock_lbl = QLabel("10:24 AM")
        self.clock_lbl.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.clock_lbl.setStyleSheet("color: #FFFFFF; letter-spacing: 0.5px;")
        cc_layout.addWidget(self.clock_lbl)

        self.date_lbl = QLabel("Wed, Apr 23, 2025")
        self.date_lbl.setFont(QFont("Segoe UI", 10))
        self.date_lbl.setStyleSheet("color: #94A3B8;")
        cc_layout.addWidget(self.date_lbl)
        layout.addWidget(clock_card)

        # 2. Weather Card
        weather_card = QFrame()
        weather_card.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(0, 240, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
        """)
        w_layout = QHBoxLayout(weather_card)
        w_layout.setContentsMargins(10, 8, 10, 8)
        w_layout.setSpacing(10)

        weather_icon = QLabel("⛅")
        weather_icon.setFont(QFont("Segoe UI Emoji", 20))
        w_layout.addWidget(weather_icon)

        w_text_box = QVBoxLayout()
        w_text_box.setSpacing(1)
        self.temp_lbl = QLabel("18°C")
        self.temp_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.temp_lbl.setStyleSheet("color: #FFFFFF;")
        w_text_box.addWidget(self.temp_lbl)

        self.weather_desc = QLabel("Partly Cloudy\nLondon, UK")
        self.weather_desc.setFont(QFont("Segoe UI", 8))
        self.weather_desc.setStyleSheet("color: #94A3B8;")
        w_text_box.addWidget(self.weather_desc)
        w_layout.addLayout(w_text_box)
        w_layout.addStretch()

        layout.addWidget(weather_card)

        # 3. Quick Status Bar Icons
        status_bar = QHBoxLayout()
        status_bar.setSpacing(8)
        status_icons = [("📶", "Wi-Fi Connected"), ("ᛒ", "Bluetooth Active"),
                        ("🔊", "Audio 80%"), ("☀️", "Display & Power"),
                        ("🛡️", "Security Safe"), ("🔒", "Session Protected")]
        for icon, tip in status_icons:
            btn = QPushButton(icon)
            btn.setFixedSize(26, 26)
            btn.setToolTip(tip)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #00F0FF;
                    font-size: 11px;
                    border: none;
                }
                QPushButton:hover {
                    color: #FFFFFF;
                }
            """)
            status_bar.addWidget(btn)
        status_bar.addStretch()
        layout.addLayout(status_bar)

        # 4. System Monitor Card with 3 Radial Progress Rings
        monitor_card = QFrame()
        monitor_card.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(0, 240, 255, 0.12);
                border-radius: 8px;
            }
        """)
        mc_layout = QVBoxLayout(monitor_card)
        mc_layout.setContentsMargins(10, 8, 10, 8)
        mc_layout.setSpacing(6)

        m_title = QLabel("System Monitor")
        m_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        m_title.setStyleSheet("color: #E2E8F0;")
        mc_layout.addWidget(m_title)

        dials_row = QHBoxLayout()
        dials_row.setSpacing(4)
        self.cpu_dial = CircularMeter("CPU", QColor("#00F0FF"), 12)
        self.ram_dial = CircularMeter("RAM", QColor("#00FF88"), 38)
        self.disk_dial = CircularMeter("Disk", QColor("#0099FF"), 24)

        dials_row.addWidget(self.cpu_dial)
        dials_row.addWidget(self.ram_dial)
        dials_row.addWidget(self.disk_dial)
        mc_layout.addLayout(dials_row)
        layout.addWidget(monitor_card)

        # 5. Recent Activity Card
        act_card = QFrame()
        act_card.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(0, 240, 255, 0.12);
                border-radius: 8px;
            }
        """)
        ac_layout = QVBoxLayout(act_card)
        ac_layout.setContentsMargins(10, 8, 10, 8)
        ac_layout.setSpacing(6)

        act_title = QLabel("Recent Activity")
        act_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        act_title.setStyleSheet("color: #E2E8F0;")
        ac_layout.addWidget(act_title)

        activities = [
            ("🔍", "Research completed", "10:12 AM"),
            ("📥", "File downloaded", "09:45 AM"),
            ("⚙️", "System update available", "08:30 AM")
        ]
        for icon, desc, t_str in activities:
            row = QHBoxLayout()
            row.setSpacing(6)
            i_lbl = QLabel(icon)
            i_lbl.setFixedWidth(16)
            row.addWidget(i_lbl)

            d_lbl = QLabel(desc)
            d_lbl.setFont(QFont("Segoe UI", 9))
            d_lbl.setStyleSheet("color: #CBD5E1;")
            row.addWidget(d_lbl, stretch=1)

            t_lbl = QLabel(t_str)
            t_lbl.setFont(QFont("Segoe UI", 8))
            t_lbl.setStyleSheet("color: #64748B;")
            row.addWidget(t_lbl)
            ac_layout.addLayout(row)

        layout.addWidget(act_card)

        # 6. Quick Actions 2x2 Grid
        actions_box = QVBoxLayout()
        actions_box.setSpacing(4)
        qa_title = QLabel("Quick Actions")
        qa_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        qa_title.setStyleSheet("color: #E2E8F0;")
        actions_box.addWidget(qa_title)

        grid = QGridLayout()
        grid.setSpacing(6)

        btn_settings = self._create_action_button("⚙ Settings")
        btn_settings.clicked.connect(self.settings_requested.emit)
        grid.addWidget(btn_settings, 0, 0)

        btn_dark = self._create_action_button("🌙 Dark Mode")
        btn_dark.clicked.connect(self.dark_mode_toggled.emit)
        grid.addWidget(btn_dark, 0, 1)

        btn_focus = self._create_action_button("🎯 Focus Mode")
        btn_focus.clicked.connect(self.focus_mode_toggled.emit)
        grid.addWidget(btn_focus, 1, 0)

        btn_lock = self._create_action_button("🔒 Lock Screen")
        btn_lock.clicked.connect(self.lock_requested.emit)
        grid.addWidget(btn_lock, 1, 1)

        actions_box.addLayout(grid)
        layout.addLayout(actions_box)

        layout.addStretch()

    def _create_action_button(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(30)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(0, 240, 255, 0.20);
                border-radius: 6px;
                color: #CBD5E1;
                font-family: 'Segoe UI', sans-serif;
                font-size: 9px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(0, 240, 255, 0.15);
                border-color: #00F0FF;
                color: #FFFFFF;
            }
        """)
        return btn

    def _refresh_telemetry(self):
        # 1. Update Clock & Date
        now = datetime.datetime.now()
        self.clock_lbl.setText(now.strftime("%I:%M %p"))
        self.date_lbl.setText(now.strftime("%a, %b %d, %Y"))

        # 2. Update System Metrics Dials via SystemMonitor
        if hasattr(self.monitor, "get_metrics"):
            metrics = self.monitor.get_metrics()
            cpu_val = int(metrics.get("cpu_percent", 12))
            ram_val = int(metrics.get("ram_percent", 38))
            disk_val = int(metrics.get("disk_percent", 24))
        elif hasattr(self.monitor, "get_realtime_metrics"):
            rt = self.monitor.get_realtime_metrics()
            cpu_val = int(rt.get("cpu_percent", 12))
            ram_val = int(rt.get("memory", {}).get("percent", 38))
            disk_val = int(rt.get("disk", {}).get("percent", 24))
        else:
            cpu_val, ram_val, disk_val = 12, 38, 24

        self.cpu_dial.set_value(cpu_val)
        self.ram_dial.set_value(ram_val)
        self.disk_dial.set_value(disk_val)

    def set_update_interval(self, ms: int):
        """Throttles or boosts telemetry polling interval (e.g. 3000ms in Battery Saver)."""
        if hasattr(self, "timer"):
            self.timer.setInterval(max(200, ms))

    def cleanup(self):
        """Stops background telemetry polling timer on application exit."""
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
