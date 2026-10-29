"""
NOVA OS: Left Navigation Sidebar.
Matches the official reference design layout:
- Top branding: "❖ NOVA OS" with tagline "Smarter. Safer. Yours."
- Navigation pills: Home, Browser, File Manager, AI Assistant, Terminal, Settings, System Monitor, Voice, Apps, Workspace.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

class LeftNavSidebar(QFrame):
    """
    Compact, persistent left navigation sidebar matching the reference design.
    """
    app_requested = Signal(str)

    NAV_ITEMS = [
        ("home", "🏠 Home", "Desktop Home & Overview"),
        ("browser", "🌐 Browser", "Web Browser & Research"),
        ("files", "📁 File Manager", "Workspace File Vault"),
        ("chat", "🤖 AI Assistant", "Neural Chat & Local LLM"),
        ("terminal", "💻 Terminal", "Safe Sandboxed Shell"),
        ("settings", "⚙ Settings", "System & UI Configuration"),
        ("dashboard", "📊 System Monitor", "Hardware Telemetry & Metrics"),
        ("voice", "🎙 Voice", "Speech Engine & Assistant"),
        ("winapps", "▦ Apps", "Applications Hub"),
        ("workspace", "🗂 Workspace", "Virtual Profiles & Desktops"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LeftNavSidebar")
        self.setFixedWidth(190)
        self._active_key = "home"
        self._buttons = {}
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame#LeftNavSidebar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(8, 14, 26, 0.94),
                    stop:1 rgba(10, 18, 34, 0.88));
                border-right: 1px solid rgba(0, 210, 230, 0.18);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(6)

        # 1. Branding Header
        header_container = QWidget()
        h_layout = QVBoxLayout(header_container)
        h_layout.setContentsMargins(0, 0, 0, 14)
        h_layout.setSpacing(2)

        brand_lbl = QLabel("❖ NOVA OS")
        brand_lbl.setFont(QFont("Consolas", 13, QFont.Bold))
        brand_lbl.setStyleSheet("color: #FFFFFF; letter-spacing: 0.5px;")
        h_layout.addWidget(brand_lbl)

        tagline_lbl = QLabel("Space Desktop Runtime")
        tagline_lbl.setFont(QFont("Segoe UI", 9))
        tagline_lbl.setStyleSheet("color: #00F0FF; opacity: 0.85;")
        h_layout.addWidget(tagline_lbl)

        layout.addWidget(header_container)

        # 2. Navigation Items
        for key, label, tooltip in self.NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked=False, k=key: self._on_item_clicked(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        self._refresh_styles()

    def set_active(self, key: str):
        self._active_key = key
        self._refresh_styles()

    def _on_item_clicked(self, key: str):
        self.set_active(key)
        self.app_requested.emit(key)

    def _refresh_styles(self):
        for key, btn in self._buttons.items():
            is_active = (key == self._active_key)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0052cc, stop:1 #0099ff);
                        color: #FFFFFF;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 11px;
                        font-weight: 700;
                        text-align: left;
                        padding-left: 14px;
                        border-radius: 8px;
                        border: 1px solid rgba(0, 210, 230, 0.45);
                    }
                    QPushButton:hover {
                        background: #0066ff;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #94A3B8;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 11px;
                        font-weight: 500;
                        text-align: left;
                        padding-left: 14px;
                        border-radius: 8px;
                        border: 1px solid transparent;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.05);
                        color: #E2E8F0;
                        border: 1px solid rgba(0, 240, 255, 0.15);
                    }
                """)
