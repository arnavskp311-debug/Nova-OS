"""
NOVA OS Quick Settings Panel.
Glassmorphic flyout for fast toggling of performance modes, cyber themes,
audio feedback, SSD storage status, and cache management.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSlider, QProgressBar,
    QGridLayout, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from nova.config import ACCENT_COLORS
from nova.database import get_setting, set_setting, purge_transient_cache
import psutil

class QuickSettingsFlyout(QFrame):
    theme_changed = Signal(str)
    performance_mode_changed = Signal(str)
    open_full_settings = Signal()
    notification_requested = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(320, 420)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("❖")
        icon.setStyleSheet("color: #00f0ff; font-size: 16px; font-weight: bold;")
        head.addWidget(icon)

        title = QLabel("QUICK SETTINGS")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("background: transparent; border: none; color: #64748b; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        head.addWidget(close_btn)
        layout.addLayout(head)

        # 1. Performance Mode Quick Selector
        perf_box = QVBoxLayout()
        perf_lbl = QLabel("PERFORMANCE PROFILE")
        perf_lbl.setStyleSheet("color: #ffaa00; font-size: 10px; font-weight: bold;")
        perf_box.addWidget(perf_lbl)

        perf_row = QHBoxLayout()
        perf_row.setSpacing(4)
        self.perf_btns = {}
        for mode, short_label in [
            ("Balanced", "Balanced"),
            ("High Fidelity", "High Perf"),
            ("Low Resource / Battery Saver", "Battery Saver")
        ]:
            b = QPushButton(short_label)
            b.setStyleSheet("""
                QPushButton {
                    background: #101728;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 4px;
                    color: #cbd5e1;
                    font-size: 10px;
                    padding: 5px;
                }
                QPushButton:hover {
                    border-color: #ffaa00;
                    color: #ffffff;
                }
            """)
            b.clicked.connect(lambda checked, m=mode: self.set_perf_mode(m))
            perf_row.addWidget(b)
            self.perf_btns[mode] = b
        perf_box.addLayout(perf_row)
        layout.addLayout(perf_box)

        # 2. Cyber Accent Selector
        theme_box = QVBoxLayout()
        theme_lbl = QLabel("CYBER THEME ACCENT")
        theme_lbl.setStyleSheet("color: #b026ff; font-size: 10px; font-weight: bold;")
        theme_box.addWidget(theme_lbl)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(6)
        for name, hex_code in ACCENT_COLORS.items():
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setToolTip(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {hex_code};
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            btn.clicked.connect(lambda checked, n=name: self.on_theme_picked(n))
            accent_row.addWidget(btn)
        accent_row.addStretch()
        theme_box.addLayout(accent_row)
        layout.addLayout(theme_box)

        # 3. SSD Storage Space Status
        storage_box = QVBoxLayout()
        storage_box.setSpacing(4)
        self.storage_lbl = QLabel("SSD STORAGE (C:)")
        self.storage_lbl.setStyleSheet("color: #00ff88; font-size: 10px; font-weight: bold;")
        storage_box.addWidget(self.storage_lbl)

        self.storage_bar = QProgressBar()
        self.storage_bar.setFixedHeight(8)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setStyleSheet("QProgressBar::chunk { background-color: #00ff88; border-radius: 4px; }")
        storage_box.addWidget(self.storage_bar)

        self.storage_detail_lbl = QLabel("Checking storage...")
        self.storage_detail_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        storage_box.addWidget(self.storage_detail_lbl)
        layout.addLayout(storage_box)

        # 4. Cache & Memory Cleaner Button
        clean_btn = QPushButton("🧹 Purge Transient Cache & RAM Buffers")
        clean_btn.setStyleSheet("""
            QPushButton {
                background: #111a2f;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 4px;
                color: #00f0ff;
                padding: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
        """)
        clean_btn.clicked.connect(self.on_clean_cache)
        layout.addWidget(clean_btn)

        layout.addStretch()

        # Footer Button: Full Control Center
        full_settings_btn = QPushButton("Open Full Control Center ➔")
        full_settings_btn.setObjectName("PrimaryButton")
        full_settings_btn.clicked.connect(self.on_open_full_settings)
        layout.addWidget(full_settings_btn)

    def refresh_status(self):
        # Update storage meter
        try:
            usage = psutil.disk_usage("C:\\")
            free_gb = round(usage.free / (1024**3), 1)
            total_gb = round(usage.total / (1024**3), 1)
            percent = int(usage.percent)
            self.storage_bar.setValue(percent)
            self.storage_detail_lbl.setText(f"{free_gb} GB Free of {total_gb} GB ({percent}% Used)")
        except Exception:
            pass

    def set_perf_mode(self, mode: str):
        set_setting("performance_mode", mode)
        self.performance_mode_changed.emit(mode)
        self.notification_requested.emit("PERFORMANCE MODE", f"Profile switched to: {mode}", "warning")

    def on_theme_picked(self, theme_name: str):
        set_setting("accent_color", theme_name)
        self.theme_changed.emit(theme_name)
        self.notification_requested.emit("ACCENT UPDATED", f"Neon theme switched to: {theme_name}", "info")

    def on_clean_cache(self):
        res = purge_transient_cache()
        freed = res.get("freed_mb", 0)
        self.notification_requested.emit(
            "STORAGE RECLAIMED",
            f"Purged transient cache and compacting buffers.\nFreed: {freed} MB",
            "success"
        )
        self.refresh_status()

    def on_open_full_settings(self):
        self.hide()
        self.open_full_settings.emit()
