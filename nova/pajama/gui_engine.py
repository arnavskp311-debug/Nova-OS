"""
PAJAMA NATIVE GUI ENGINE & CYBERPUNK INTERACTIVE WIDGETS.
Provides zero-boilerplate GUI windows, interactive stopwatches, dialogs,
and custom controls for the Pajama programming language.
"""

import time
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QLineEdit, QDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor

from nova.sound_fx import play_sound


# =============================================================================
# Interactive Cyber Stopwatch Window
# =============================================================================

class CyberStopwatchWidget(QWidget):
    """Futuristic interactive stopwatch with millisecond precision, laps, and sound cues."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CYBER STOPWATCH // NOVA OS")
        self.resize(360, 240)
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0e14;
                color: #e6edf3;
            }
        """)

        self.elapsed_ms = 0
        self.is_running = False

        self.timer = QTimer(self)
        self.timer.setInterval(25)  # 40 FPS refresh
        self.timer.timeout.connect(self._on_tick)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Title
        hdr = QHBoxLayout()
        title = QLabel("⏱️ CYBER STOPWATCH")
        title.setFont(QFont("Consolas", 10, QFont.Bold))
        title.setStyleSheet("color: #00e5ff; letter-spacing: 1px;")
        hdr.addWidget(title)
        hdr.addStretch()
        self.status_lbl = QLabel("PAUSED")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: bold;")
        hdr.addWidget(self.status_lbl)
        layout.addLayout(hdr)

        # Main Digital Display
        disp_box = QFrame()
        disp_box.setStyleSheet("""
            QFrame {
                background-color: #131924;
                border: 2px solid #00e5ff;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        disp_layout = QVBoxLayout(disp_box)
        disp_layout.setAlignment(Qt.AlignCenter)

        self.time_label = QLabel("00:00:00.00")
        self.time_label.setFont(QFont("Consolas", 28, QFont.Bold))
        self.time_label.setStyleSheet("color: #00e5ff; text-shadow: 0 0 10px #00e5ff;")
        self.time_label.setAlignment(Qt.AlignCenter)
        disp_layout.addWidget(self.time_label)

        layout.addWidget(disp_box)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_toggle = QPushButton("▶ START")
        self.btn_toggle.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.btn_toggle.clicked.connect(self.toggle_start_pause)
        btn_box.addWidget(self.btn_toggle)

        self.btn_reset = QPushButton("↺ RESET")
        self.btn_reset.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #30363d; color: #58a6ff; }
        """)
        self.btn_reset.clicked.connect(self.reset_timer)
        btn_box.addWidget(self.btn_reset)

        self.btn_lap = QPushButton("🏁 LAP")
        self.btn_lap.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_lap.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        self.btn_lap.clicked.connect(self.record_lap)
        btn_box.addWidget(self.btn_lap)

        layout.addLayout(btn_box)

        # Lap Summary Line
        self.lap_lbl = QLabel("Ready")
        self.lap_lbl.setFont(QFont("Consolas", 9))
        self.lap_lbl.setStyleSheet("color: #8b949e;")
        self.lap_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lap_lbl)

    def toggle_start_pause(self):
        play_sound("click")
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.btn_toggle.setText("▶ RESUME")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background-color: #2ea043; }
            """)
            self.status_lbl.setText("PAUSED")
            self.status_lbl.setStyleSheet("color: #ffb800; font-size: 10px; font-weight: bold;")
        else:
            self.timer.start()
            self.is_running = True
            self.btn_toggle.setText("⏸ PAUSE")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #da3633;
                    color: #ffffff;
                    border-radius: 4px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background-color: #f85149; }
            """)
            self.status_lbl.setText("RUNNING")
            self.status_lbl.setStyleSheet("color: #3fb950; font-size: 10px; font-weight: bold;")

    def reset_timer(self):
        play_sound("click")
        self.timer.stop()
        self.is_running = False
        self.elapsed_ms = 0
        self.time_label.setText("00:00:00.00")
        self.btn_toggle.setText("▶ START")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.status_lbl.setText("RESET")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: bold;")
        self.lap_lbl.setText("Reset to 00:00:00.00")

    def record_lap(self):
        if self.elapsed_ms > 0:
            play_sound("blip")
            current = self._format_ms(self.elapsed_ms)
            self.lap_lbl.setText(f"Last Lap: {current}")

    def _on_tick(self):
        self.elapsed_ms += 25
        self.time_label.setText(self._format_ms(self.elapsed_ms))

    def _format_ms(self, total_ms: int) -> str:
        hours = total_ms // 3600000
        mins = (total_ms % 3600000) // 60000
        secs = (total_ms % 60000) // 1000
        centis = (total_ms % 1000) // 10
        return f"{hours:02d}:{mins:02d}:{secs:02d}.{centis:02d}"


# Global reference to keep GUI window open
_active_stopwatch_window: Optional[CyberStopwatchWidget] = None

def show_stopwatch_gui() -> str:
    """Instantiates and presents the Cyber Stopwatch window."""
    global _active_stopwatch_window
    try:
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            return "[Error: GUI not available in non-Qt environment]"

        if _active_stopwatch_window is None or not _active_stopwatch_window.isVisible():
            _active_stopwatch_window = CyberStopwatchWidget()
            _active_stopwatch_window.show()
            _active_stopwatch_window.raise_()
        else:
            _active_stopwatch_window.raise_()
            _active_stopwatch_window.activateWindow()

        play_sound("success")
        return "[Cyber Stopwatch GUI launched successfully]"
    except Exception as e:
        return f"[Failed to launch Stopwatch GUI: {e}]"
