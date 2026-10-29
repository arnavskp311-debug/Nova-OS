"""
Interactive Cyber System Tray Flyouts for NOVA OS:
- Master Volume & Audio Output Flyout
- Wi-Fi Network Picker & Connection Manager
- Battery Telemetry & Power Profile Selector
- Display Brightness & Eye-Care Night Light Overlay
- Bluetooth Peripheral Hub
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSlider, QProgressBar,
    QLineEdit, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QFont, QColor

from nova.hardware import (
    AudioController, WifiController, BatteryController,
    DisplayController, BluetoothController
)

# ============================================================================
# 1. MASTER VOLUME FLYOUT
# ============================================================================

class VolumeFlyout(QFrame):
    volume_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(300, 240)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🔊")
        icon.setStyleSheet("font-size: 16px; color: #00f0ff;")
        head.addWidget(icon)

        title = QLabel("SYSTEM AUDIO")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        self.mute_btn = QPushButton("MUTE")
        self.mute_btn.setFixedSize(54, 22)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background: #1e1528;
                border: 1px solid #b026ff;
                border-radius: 6px;
                color: #e2b3ff;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #b026ff;
                color: #ffffff;
            }
        """)
        self.mute_btn.clicked.connect(self.toggle_mute)
        head.addWidget(self.mute_btn)
        layout.addLayout(head)

        # Volume slider and percent
        slider_row = QHBoxLayout()
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        curr_vol = AudioController.get_master_volume()
        self.vol_slider.setValue(curr_vol)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #141d33;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052cc, stop:1 #00f0ff);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #00f0ff;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
        """)
        self.vol_slider.valueChanged.connect(self.on_slider_changed)
        slider_row.addWidget(self.vol_slider)

        self.percent_lbl = QLabel(f"{curr_vol}%")
        self.percent_lbl.setFixedWidth(36)
        self.percent_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        slider_row.addWidget(self.percent_lbl)
        layout.addLayout(slider_row)

        # Output Device list
        out_lbl = QLabel("PLAYBACK OUTPUT")
        out_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        layout.addWidget(out_lbl)

        devices = AudioController.get_audio_endpoints()
        for d in devices:
            d_box = QHBoxLayout()
            d_icon = "🎧" if d["type"] == "Headphones" else "🔈"
            lbl = QLabel(f"{d_icon} {d['name']}")
            lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
            d_box.addWidget(lbl)
            d_box.addStretch()
            if d.get("active"):
                chk = QLabel("● ACTIVE")
                chk.setStyleSheet("color: #00ff88; font-size: 9px; font-weight: bold;")
                d_box.addWidget(chk)
            layout.addLayout(d_box)

    def on_slider_changed(self, val: int):
        self.percent_lbl.setText(f"{val}%")
        AudioController.set_master_volume(val)
        self.volume_changed.emit(val)

    def toggle_mute(self):
        is_muted = AudioController.toggle_mute()
        if is_muted:
            self.mute_btn.setText("UNMUTE")
            self.mute_btn.setStyleSheet("""
                QPushButton {
                    background: #2b1216;
                    border: 1px solid #ff2a55;
                    border-radius: 6px;
                    color: #ff2a55;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
        else:
            self.mute_btn.setText("MUTE")
            self.mute_btn.setStyleSheet("""
                QPushButton {
                    background: #1e1528;
                    border: 1px solid #b026ff;
                    border-radius: 6px;
                    color: #e2b3ff;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)


# ============================================================================
# 2. WI-FI NETWORK FLYOUT
# ============================================================================

class WifiFlyout(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(320, 400)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        head = QHBoxLayout()
        icon = QLabel("📶")
        icon.setStyleSheet("font-size: 16px; color: #00ff88;")
        head.addWidget(icon)

        title = QLabel("WIRELESS NETWORK")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(24, 24)
        refresh_btn.setToolTip("Scan nearby Wi-Fi networks")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #12192c;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 12px;
                color: #00f0ff;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_networks)
        head.addWidget(refresh_btn)
        layout.addLayout(head)

        # Current Connection Badge
        curr = WifiController.get_current_connection()
        conn_box = QFrame()
        conn_box.setStyleSheet("background: #0d1628; border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 8px; padding: 6px;")
        c_layout = QVBoxLayout(conn_box)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(4)

        status_text = f"Connected: {curr.get('ssid', 'Unknown')}" if curr.get("connected") else "Status: Disconnected"
        self.status_lbl = QLabel(status_text)
        self.status_lbl.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 11px;")
        c_layout.addWidget(self.status_lbl)

        ip_lbl = QLabel(f"IP: {curr.get('ip_address', '127.0.0.1')} • Signal: {curr.get('signal', 0)}%")
        ip_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        c_layout.addWidget(ip_lbl)
        layout.addWidget(conn_box)

        # Available Networks Header
        avail_lbl = QLabel("AVAILABLE NETWORKS")
        avail_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; margin-top: 4px;")
        layout.addWidget(avail_lbl)

        # Scroll Area for networks
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.net_container = QWidget()
        self.net_layout = QVBoxLayout(self.net_container)
        self.net_layout.setContentsMargins(0, 0, 0, 0)
        self.net_layout.setSpacing(6)
        scroll.setWidget(self.net_container)
        layout.addWidget(scroll, stretch=1)

        self.populate_networks()

    def populate_networks(self):
        # Clear existing
        while self.net_layout.count():
            item = self.net_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        networks = WifiController.scan_networks()
        for net in networks:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: #101729;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 6px;
                }
                QFrame:hover {
                    border-color: #00f0ff;
                }
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(8, 6, 8, 6)

            info_box = QVBoxLayout()
            s_name = QLabel(f"📶 {net.get('ssid', 'Unknown')}")
            s_name.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 11px;")
            info_box.addWidget(s_name)

            sub = QLabel(f"Signal: {net.get('signal', 0)}% • {net.get('auth', 'Secured')}")
            sub.setStyleSheet("color: #64748b; font-size: 9px;")
            info_box.addWidget(sub)
            c_lay.addLayout(info_box)
            c_lay.addStretch()

            if net.get("connected"):
                btn = QPushButton("Disconnect")
                btn.setStyleSheet("background: #2b1216; border: 1px solid #ff2a55; border-radius: 4px; color: #ff2a55; font-size: 9px; padding: 4px 8px;")
                btn.clicked.connect(self.on_disconnect_clicked)
            else:
                btn = QPushButton("Connect")
                btn.setStyleSheet("background: #0052cc; border: 1px solid #00f0ff; border-radius: 4px; color: #ffffff; font-size: 9px; padding: 4px 8px;")
                btn.clicked.connect(lambda chk, s=net.get("ssid"): self.on_connect_clicked(s))
            c_lay.addWidget(btn)

            self.net_layout.addWidget(card)

        self.net_layout.addStretch()

    def refresh_networks(self):
        self.populate_networks()

    def on_connect_clicked(self, ssid: str):
        WifiController.connect_network(ssid)
        self.refresh_networks()

    def on_disconnect_clicked(self):
        WifiController.disconnect_network()
        self.refresh_networks()


# ============================================================================
# 3. BATTERY & POWER FLYOUT
# ============================================================================

class BatteryFlyout(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(310, 310)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🔋")
        icon.setStyleSheet("font-size: 16px; color: #00ff88;")
        head.addWidget(icon)

        title = QLabel("POWER & BATTERY HEALTH")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        head.addWidget(title)
        layout.addLayout(head)

        # Telemetry Box
        info = BatteryController.get_battery_info()
        card = QFrame()
        card.setStyleSheet("background: #0d1628; border: 1px solid rgba(0, 255, 136, 0.25); border-radius: 8px; padding: 8px;")
        c_lay = QVBoxLayout(card)

        pct_row = QHBoxLayout()
        self.pct_lbl = QLabel(f"{info.get('status_icon', '🔋')} {info.get('percent', 100)}%")
        self.pct_lbl.setStyleSheet("color: #00ff88; font-size: 22px; font-weight: bold;")
        pct_row.addWidget(self.pct_lbl)
        pct_row.addStretch()

        self.time_lbl = QLabel(info.get("time_left_str", "AC Power Connected"))
        self.time_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        pct_row.addWidget(self.time_lbl)
        c_lay.addLayout(pct_row)

        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(info.get("percent", 100))
        self.pbar.setFixedHeight(8)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("QProgressBar::chunk { background: #00ff88; border-radius: 4px; }")
        c_lay.addWidget(self.pbar)
        layout.addWidget(card)

        # Power Plan Profiles
        plan_lbl = QLabel("POWER PROFILE SCHEME")
        plan_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        layout.addWidget(plan_lbl)

        for p_key, p_data in BatteryController.POWER_PROFILES.items():
            btn = QPushButton(f"⚡ {p_data['name']}")
            btn.setStyleSheet("""
                QPushButton {
                    background: #111a2e;
                    border: 1px solid rgba(0, 240, 255, 0.2);
                    border-radius: 6px;
                    color: #cbd5e1;
                    font-size: 11px;
                    font-weight: 600;
                    text-align: left;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    border-color: #00ff88;
                    color: #ffffff;
                    background: #172442;
                }
            """)
            btn.clicked.connect(lambda chk, k=p_key: self.on_plan_selected(k))
            layout.addWidget(btn)

    def on_plan_selected(self, key: str):
        BatteryController.set_power_profile(key)
        self.hide()


# ============================================================================
# 4. DISPLAY & NIGHT LIGHT OVERLAY
# ============================================================================

class NightLightOverlay(QWidget):
    """Ambient amber tint overlay for sleep-friendly night coding."""

    _instance: Optional["NightLightOverlay"] = None

    @classmethod
    def get_instance(cls) -> "NightLightOverlay":
        if cls._instance is None:
            cls._instance = NightLightOverlay()
        return cls._instance

    def __init__(self):
        super().__init__()
        # Click-through, borderless, stays on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTransparentForInput |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Cover all screens
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QBrush
        painter = QPainter(self)
        # Warm amber filter 3500K equivalent (#ff9e3b at 18% opacity)
        painter.fillRect(self.rect(), QBrush(QColor(255, 158, 59, 45)))
        painter.end()


class DisplayFlyout(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(300, 220)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("☀️")
        icon.setStyleSheet("font-size: 16px; color: #ffaa00;")
        head.addWidget(icon)

        title = QLabel("DISPLAY & EYE-CARE")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        head.addWidget(title)
        layout.addLayout(head)

        # Brightness
        b_lbl = QLabel("MONITOR BRIGHTNESS")
        b_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        layout.addWidget(b_lbl)

        b_row = QHBoxLayout()
        self.b_slider = QSlider(Qt.Horizontal)
        self.b_slider.setRange(10, 100)
        curr_b = DisplayController.get_brightness()
        self.b_slider.setValue(curr_b)
        self.b_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #141d33; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #ffaa00; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffffff; width: 14px; margin: -4px 0; border-radius: 7px; }
        """)
        self.b_slider.valueChanged.connect(self.on_brightness_changed)
        b_row.addWidget(self.b_slider)

        self.b_val_lbl = QLabel(f"{curr_b}%")
        self.b_val_lbl.setFixedWidth(36)
        self.b_val_lbl.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 11px;")
        b_row.addWidget(self.b_val_lbl)
        layout.addLayout(b_row)

        # Night Light Toggle
        nl_row = QHBoxLayout()
        nl_lbl = QLabel("🌙 Cyber Night Light (Warm Filter)")
        nl_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        nl_row.addWidget(nl_lbl)
        nl_row.addStretch()

        self.nl_toggle_btn = QPushButton("OFF")
        self.nl_toggle_btn.setFixedSize(54, 24)
        self.update_nl_button_style()
        self.nl_toggle_btn.clicked.connect(self.on_toggle_night_light)
        nl_row.addWidget(self.nl_toggle_btn)
        layout.addLayout(nl_row)

    def on_brightness_changed(self, val: int):
        self.b_val_lbl.setText(f"{val}%")
        DisplayController.set_brightness(val)

    def update_nl_button_style(self):
        active = DisplayController.is_night_light_active()
        if active:
            self.nl_toggle_btn.setText("ON")
            self.nl_toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #ffaa00;
                    color: #050811;
                    font-weight: bold;
                    border-radius: 12px;
                    border: none;
                }
            """)
        else:
            self.nl_toggle_btn.setText("OFF")
            self.nl_toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #111a2e;
                    color: #64748b;
                    font-weight: bold;
                    border-radius: 12px;
                    border: 1px solid rgba(255,255,255,0.1);
                }
            """)

    def on_toggle_night_light(self):
        new_state = DisplayController.toggle_night_light()
        self.update_nl_button_style()
        overlay = NightLightOverlay.get_instance()
        if new_state:
            overlay.show()
        else:
            overlay.hide()


# ============================================================================
# 5. BLUETOOTH FLYOUT
# ============================================================================

class BluetoothFlyout(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(300, 260)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()
        icon = QLabel("ᛒ")
        icon.setStyleSheet("font-size: 18px; color: #00f0ff; font-weight: bold;")
        head.addWidget(icon)

        title = QLabel("BLUETOOTH DEVICES")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        head.addWidget(title)
        layout.addLayout(head)

        devices = BluetoothController.get_devices()
        for d in devices:
            box = QFrame()
            box.setStyleSheet("background: #0e1628; border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 6px;")
            b_lay = QHBoxLayout(box)
            b_lay.setContentsMargins(6, 4, 6, 4)

            d_info = QVBoxLayout()
            d_name = QLabel(f"ᛒ {d['name']}")
            d_name.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 11px;")
            d_info.addWidget(d_name)

            d_stat = QLabel(f"{d['status']} • Battery: {d['battery']}%")
            d_stat.setStyleSheet("color: #00ff88 if 'Connected' in d['status'] else #64748b; font-size: 9px;")
            d_info.addWidget(d_stat)
            b_lay.addLayout(d_info)
            b_lay.addStretch()

            btn = QPushButton("Toggle")
            btn.setStyleSheet("background: #172442; border: 1px solid #00f0ff; border-radius: 4px; color: #00f0ff; font-size: 9px; padding: 3px 6px;")
            b_lay.addWidget(btn)
            layout.addWidget(box)

        layout.addStretch()
