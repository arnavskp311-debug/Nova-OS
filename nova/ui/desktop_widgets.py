"""
Desktop Widgets & Sticky Notes for NOVA OS (Feature 6).
Displays live clock & calendar, miniature CPU/RAM meters, and user-editable sticky notes
directly on the Cyber Desktop canvas below active application windows.
"""

from datetime import datetime
import calendar
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QGridLayout,
    QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QPoint, QTimer, Signal
from PySide6.QtGui import QMouseEvent, QFont, QColor, QPainter

from nova.system_monitor import SystemMonitor
from nova.database import get_desktop_widgets, save_desktop_widget, delete_desktop_widget


class BaseDesktopWidget(QFrame):
    """
    Base draggable desktop widget container.
    Persists position (x, y) and dimensions to database on mouse release.
    """
    closed = Signal(str)

    def __init__(self, widget_id: str, widget_type: str, title: str, parent=None):
        super().__init__(parent)
        self.widget_id = widget_id
        self.widget_type = widget_type
        self.widget_title = title
        self._dragging = False
        self._drag_offset = QPoint()

        self.setObjectName("DesktopWidgetFrame")
        self.setStyleSheet("""
            QFrame#DesktopWidgetFrame {
                background-color: rgba(11, 18, 34, 0.92);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 10px;
            }
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            new_pos = self.mapToParent(event.pos() - self._drag_offset)
            # Bound within parent
            p = self.parentWidget()
            if p:
                max_x = max(0, p.width() - self.width())
                max_y = max(0, p.height() - self.height())
                nx = max(0, min(new_pos.x(), max_x))
                ny = max(0, min(new_pos.y(), max_y))
                self.move(nx, ny)
            else:
                self.move(new_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging and event.button() == Qt.LeftButton:
            self._dragging = False
            self.persist_geometry()
            event.accept()
        super().mouseReleaseEvent(event)

    def persist_geometry(self):
        save_desktop_widget(
            self.widget_id,
            self.widget_type,
            self.widget_title,
            getattr(self, "widget_content", ""),
            self.x(),
            self.y(),
            self.width(),
            self.height(),
            1 if self.isVisible() else 0
        )


class ClockCalendarWidget(BaseDesktopWidget):
    """
    Live digital clock, weather pill, and monthly calendar matching Panel 6.
    """
    def __init__(self, widget_id: str = "clock_cal", parent=None):
        super().__init__(widget_id, "clock_calendar", "Digital Clock & Calendar", parent)
        self.setFixedSize(260, 210)
        self.setup_ui()

        # Update clock every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row: Time + Weather
        head_box = QHBoxLayout()
        self.time_lbl = QLabel("10:45")
        self.time_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #ffffff; font-family: 'Segoe UI', monospace;")
        head_box.addWidget(self.time_lbl)
        head_box.addStretch()

        self.weather_lbl = QLabel("⛅ 22°C Partly Cloudy")
        self.weather_lbl.setStyleSheet("""
            background: #141f38;
            color: #7dd3fc;
            border: 1px solid rgba(0, 240, 255, 0.2);
            border-radius: 10px;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 8px;
        """)
        head_box.addWidget(self.weather_lbl)
        layout.addLayout(head_box)

        # Date Row
        self.date_lbl = QLabel("Tue, Oct 25, 2026")
        self.date_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.date_lbl)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.08);")
        layout.addWidget(sep)

        # Mini Calendar Grid
        self.cal_grid = QGridLayout()
        self.cal_grid.setSpacing(3)
        self.cal_grid.setContentsMargins(0, 0, 0, 0)
        self.render_calendar_grid()
        layout.addLayout(self.cal_grid)

    def render_calendar_grid(self):
        # Clear existing
        while self.cal_grid.count() > 0:
            item = self.cal_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        now = datetime.now()
        cal = calendar.monthcalendar(now.year, now.month)
        days = ["M", "T", "W", "T", "F", "S", "S"]

        for col, d in enumerate(days):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #00f0ff; font-size: 9px; font-weight: bold;")
            self.cal_grid.addWidget(lbl, 0, col)

        for row_idx, week in enumerate(cal[:4]):  # Show up to 4-5 compact weeks
            for col_idx, day_num in enumerate(week):
                if day_num == 0:
                    lbl = QLabel("")
                else:
                    lbl = QLabel(str(day_num))
                    lbl.setAlignment(Qt.AlignCenter)
                    if day_num == now.day:
                        lbl.setStyleSheet("""
                            background: #0052cc;
                            color: #ffffff;
                            font-weight: bold;
                            border-radius: 9px;
                            font-size: 10px;
                        """)
                    else:
                        lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
                self.cal_grid.addWidget(lbl, row_idx + 1, col_idx)

    def update_clock(self):
        now = datetime.now()
        self.time_lbl.setText(now.strftime("%I:%M %p"))
        self.date_lbl.setText(now.strftime("%a, %b %d, %Y"))


class SystemMetersWidget(BaseDesktopWidget):
    """
    Miniature CPU & RAM meters matching Panel 6.
    """
    def __init__(self, system_monitor: Optional[SystemMonitor] = None, widget_id: str = "meters", parent=None):
        super().__init__(widget_id, "meters", "CPU & RAM Lab", parent)
        self.monitor = system_monitor or SystemMonitor()
        self.setFixedSize(260, 130)
        self.setup_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(3000)
        self.update_metrics()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("SYSTEM RESOURCE LAB")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        layout.addWidget(title)

        # CPU Row
        cpu_box = QHBoxLayout()
        self.cpu_lbl = QLabel("CPU: 12%")
        self.cpu_lbl.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 11px;")
        cpu_box.addWidget(self.cpu_lbl)
        cpu_box.addStretch()
        self.cpu_freq_lbl = QLabel("2.4 GHz")
        self.cpu_freq_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        cpu_box.addWidget(self.cpu_freq_lbl)
        layout.addLayout(cpu_box)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFixedHeight(5)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setValue(12)
        self.cpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #00f0ff; border-radius: 2px; }")
        layout.addWidget(self.cpu_bar)

        # RAM Row
        ram_box = QHBoxLayout()
        self.ram_lbl = QLabel("RAM: 2.8 / 4 GB")
        self.ram_lbl.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 11px;")
        ram_box.addWidget(self.ram_lbl)
        ram_box.addStretch()
        self.ram_pct_lbl = QLabel("70%")
        self.ram_pct_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        ram_box.addWidget(self.ram_pct_lbl)
        layout.addLayout(ram_box)

        self.ram_bar = QProgressBar()
        self.ram_bar.setFixedHeight(5)
        self.ram_bar.setTextVisible(False)
        self.ram_bar.setValue(70)
        self.ram_bar.setStyleSheet("QProgressBar::chunk { background-color: #b026ff; border-radius: 2px; }")
        layout.addWidget(self.ram_bar)

    def update_metrics(self):
        try:
            m = self.monitor.get_realtime_metrics()
            cpu_val = int(m.get("cpu_percent", 0))
            self.cpu_lbl.setText(f"CPU: {cpu_val}%")
            self.cpu_bar.setValue(min(100, max(0, cpu_val)))
            self.cpu_freq_lbl.setText(str(m.get("cpu_freq_live", "")))

            ram = m.get("memory", {})
            used_gb = ram.get("used_gb", 0)
            total_gb = ram.get("total_gb", 4.0)
            ram_pct = int(ram.get("percent", 0))
            self.ram_lbl.setText(f"RAM: {used_gb} / {total_gb} GB")
            self.ram_pct_lbl.setText(f"{ram_pct}%")
            self.ram_bar.setValue(min(100, max(0, ram_pct)))
        except Exception:
            pass


class StickyNoteWidget(BaseDesktopWidget):
    """
    User-editable cybernetic sticky note matching Panel 6 ("Stay focused: Build amazing things - NOVA").
    """
    def __init__(self, widget_id: str = "sticky_note", initial_text: str = "Stay focused:\nBuild amazing things\n- NOVA", parent=None):
        super().__init__(widget_id, "sticky_note", "Sticky Note", parent)
        self.widget_content = initial_text
        self.setFixedSize(260, 150)
        self.setStyleSheet("""
            QFrame#DesktopWidgetFrame {
                background-color: #fef08a;
                border: 1px solid #eab308;
                border-radius: 8px;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        head = QHBoxLayout()
        pin = QLabel("📌 STICKY NOTE")
        pin.setStyleSheet("font-size: 10px; font-weight: bold; color: #854d0e; letter-spacing: 1px;")
        head.addWidget(pin)
        head.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #854d0e;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #b91c1c;
            }
        """)
        close_btn.clicked.connect(self.hide_note)
        head.addWidget(close_btn)
        layout.addLayout(head)

        self.edit = QTextEdit()
        self.edit.setPlainText(self.widget_content)
        self.edit.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #1e1b4b;
                line-height: 1.3;
            }
        """)
        self.edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.edit)

    def on_text_changed(self):
        self.widget_content = self.edit.toPlainText()
        self.persist_geometry()

    def hide_note(self):
        self.hide()
        self.persist_geometry()
        self.closed.emit(self.widget_id)
