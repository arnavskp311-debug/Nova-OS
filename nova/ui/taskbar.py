"""
Futuristic Cyber Taskbar and App Launcher for NOVA OS.
Hosts the Start Menu, active window task buttons, system status indicators, and live clock.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QFrame, QMenu, QWidgetAction, QLineEdit,
    QGridLayout, QApplication, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QFont, QCursor
from nova.config import APP_NAME

class LauncherPopup(QFrame):
    app_launch_requested = Signal(str)
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(380, 520)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        top_box = QHBoxLayout()
        logo = QLabel("❖")
        logo.setStyleSheet("font-size: 22px; color: #00f0ff; font-weight: bold;")
        top_box.addWidget(logo)

        header_text = QVBoxLayout()
        title = QLabel(APP_NAME.upper())
        title.setStyleSheet("font-weight: bold; font-size: 15px; color: #ffffff; letter-spacing: 1px;")
        header_text.addWidget(title)

        sub = QLabel("AI Trial Desktop Runtime")
        sub.setObjectName("MutedLabel")
        header_text.addWidget(sub)
        top_box.addLayout(header_text)
        top_box.addStretch()
        layout.addLayout(top_box)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search apps or directives...")
        self.search_box.textChanged.connect(self.filter_apps)
        layout.addWidget(self.search_box)

        # Scroll Area for Applications
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #080d1a;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 240, 255, 0.3);
                border-radius: 3px;
            }
        """)

        # Apps Grid (All 20 features)
        self.apps = [
            ("browser", "🌐 NOVA Cyber Browser", "Secure web runtime with Safe Chrome Companion"),
            ("dashboard", "📊 Performance Center", "Live CPU, RAM, Disk & Network diagnostics"),
            ("workspace", "🗂 Workspace Profiles", "Switch between Study, Coding, Research & Personal"),
            ("backup", "📦 Backup & Restore", "Snapshot settings, workspaces, notes & browser data"),
            ("docsearch", "🔍 AI Document Search", "Private local search across documents and project files"),
            ("chat", "🤖 NOVA AI Assistant", "Local LLM chat powered by Ollama"),
            ("notes", "📝 NovaPad Knowledge", "Local notes & markdown documentation"),
            ("calendar", "📅 Calendar & Reminders", "Schedule agendas, tasks and focus timers"),
            ("automation", "⚡ Automation Studio", "Create and execute safe custom workflows"),
            ("memory", "🧠 AI Memory Manager", "View and control user-approved AI memories"),
            ("privacy", "🛡️ Privacy Center", "Control data retention, history & voice permissions"),
            ("novasearch", "❖ NOVA Search Portal", "Independent cyber search engine prototype"),
            ("terminal", "💻 Cyber Safe Terminal", "Interactive sandboxed shell environment"),
            ("files", "📁 Sandbox File Vault", "Project file explorer & storage health"),
            ("settings", "⚙ Control Center", "Configure AI models, themes & security"),
            ("clipboard", "📋 Clipboard History", "Browse and restore recent copied snippets"),
            ("voice", "🎙 NOVA Voice Assistant", "Conversational AI voice powered by Kokoro-82M"),
        ]

        self.apps_container = QWidget()
        self.apps_layout = QVBoxLayout(self.apps_container)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(6)

        self.app_buttons = []
        for app_id, name, desc in self.apps:
            btn = QPushButton(f"{name}\n{desc}")
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    background: #111827;
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 6px;
                    color: #cbd5e1;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #1c273e;
                    border-color: #00f0ff;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, a=app_id: self.on_app_clicked(a))
            self.apps_layout.addWidget(btn)
            self.app_buttons.append((app_id, name, desc, btn))

        self.scroll.setWidget(self.apps_container)
        layout.addWidget(self.scroll, stretch=1)

        # Bottom Safeguard & Exit Bar
        footer = QHBoxLayout()
        safe_tag = QLabel("🛡 Safe Windows Trial")
        safe_tag.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: 600;")
        footer.addWidget(safe_tag)

        footer.addStretch()

        exit_btn = QPushButton("Exit NOVA OS")
        exit_btn.setObjectName("DangerButton")
        exit_btn.clicked.connect(self.on_exit_clicked)
        footer.addWidget(exit_btn)

        layout.addLayout(footer)

    def filter_apps(self, text: str):
        query = text.lower().strip()
        for app_id, name, desc, btn in self.app_buttons:
            match = not query or query in name.lower() or query in desc.lower()
            btn.setVisible(match)

    def on_app_clicked(self, app_id: str):
        self.hide()
        self.app_launch_requested.emit(app_id)

    def on_exit_clicked(self):
        self.hide()
        self.exit_requested.emit()

class Taskbar(QFrame):
    app_launch_requested = Signal(str)
    window_toggle_requested = Signal(str)
    universal_search_requested = Signal()
    quick_settings_requested = Signal()
    clipboard_requested = Signal()
    voice_assistant_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskbarFrame")
        self.window_buttons = {}
        self.setup_ui()

        # Clock timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

    def setup_ui(self):
        self.setFixedHeight(54)
        self.setStyleSheet("""
            QFrame#TaskbarFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(14, 20, 36, 0.95), stop:1 rgba(8, 12, 22, 0.98));
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 26px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(8)

        # Start Button (❖ NOVA)
        self.start_btn = QPushButton("❖ NOVA")
        self.start_btn.setFixedSize(86, 36)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0052cc, stop:1 #00f0ff);
                color: #ffffff;
                font-weight: 800;
                font-size: 12px;
                border-radius: 18px;
                border: 1px solid #00f0ff;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: #ffffff;
                color: #000000;
                border-color: #ffffff;
            }
        """)
        self.launcher = LauncherPopup(self)
        self.launcher.app_launch_requested.connect(self.app_launch_requested)
        self.launcher.exit_requested.connect(self.exit_requested)
        self.start_btn.clicked.connect(self.toggle_launcher)
        layout.addWidget(self.start_btn)

        # Universal Search Trigger Button (Pill Search)
        self.search_btn = QPushButton("🔍 Search... (Ctrl+Space)")
        self.search_btn.setFixedHeight(34)
        self.search_btn.setFixedWidth(160)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setToolTip("Universal Search & Directives (Ctrl+Space / Alt+Space)")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background: #0f172a;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 17px;
                color: #94a3b8;
                padding: 0 12px;
                font-weight: 500;
                font-size: 11px;
                text-align: left;
            }
            QPushButton:hover {
                background: #1e293b;
                border-color: #00f0ff;
                color: #ffffff;
            }
        """)
        self.search_btn.clicked.connect(self.universal_search_requested.emit)
        layout.addWidget(self.search_btn)

        # Voice Assistant Trigger Button (Violet Neon Glow)
        self.voice_btn = QPushButton("🎙 Voice")
        self.voice_btn.setFixedHeight(34)
        self.voice_btn.setCursor(Qt.PointingHandCursor)
        self.voice_btn.setToolTip("NOVA Voice Assistant (Ctrl+Shift+Space / F4)")
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #1a1638;
                border: 1px solid #b026ff;
                border-radius: 17px;
                color: #e2b3ff;
                padding: 0 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #b026ff;
                color: #ffffff;
            }
        """)
        self.voice_btn.clicked.connect(self.voice_assistant_requested.emit)
        layout.addWidget(self.voice_btn)

        # Quick Launchers
        quick_icons = [
            ("browser", "🌐", "NOVA Cyber Browser"),
            ("dashboard", "📊", "Telemetry Dashboard"),
            ("chat", "🤖", "NOVA AI Assistant"),
            ("notes", "📝", "NovaPad Notes & Reminders"),
            ("terminal", "💻", "Safe Cyber Terminal"),
            ("files", "📁", "File Vault"),
            ("settings", "⚙", "Control Center"),
        ]
        for app_id, icon, tip in quick_icons:
            btn = QPushButton(icon)
            btn.setFixedSize(34, 34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet("""
                QPushButton {
                    background: #12192c;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 17px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    border-color: #00f0ff;
                    background: #1a2542;
                }
            """)
            btn.clicked.connect(lambda checked, a=app_id: self.app_launch_requested.emit(a))
            layout.addWidget(btn)

        # Clipboard History quick button
        self.clip_btn = QPushButton("📋")
        self.clip_btn.setFixedSize(34, 34)
        self.clip_btn.setCursor(Qt.PointingHandCursor)
        self.clip_btn.setToolTip("Clipboard History (Ctrl+Shift+V)")
        self.clip_btn.setStyleSheet("""
            QPushButton {
                background: #12192c;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 17px;
                font-size: 14px;
            }
            QPushButton:hover {
                border-color: #00f0ff;
                background: #1a2542;
            }
        """)
        self.clip_btn.clicked.connect(self.clipboard_requested.emit)
        layout.addWidget(self.clip_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: rgba(0, 240, 255, 0.2);")
        layout.addWidget(sep)

        # Active Tasks Bar
        self.tasks_container = QWidget()
        self.tasks_layout = QHBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(6)
        self.tasks_layout.addStretch()
        layout.addWidget(self.tasks_container, stretch=1)

        # Right Side System Tray
        # AI Status Tag (Dynamic Pill)
        self.ai_tag = QLabel("○ CHECKING AI")
        self.ai_status_lbl = self.ai_tag
        self.ai_tag.setStyleSheet("""
            QLabel {
                color: #ffaa00;
                font-weight: bold;
                font-size: 10px;
                padding: 4px 10px;
                background: #1c1808;
                border-radius: 12px;
                border: 1px solid rgba(255, 170, 0, 0.4);
            }
        """)
        self.ai_tag.setToolTip("Verifying Ollama local model service status...")
        layout.addWidget(self.ai_tag)

        # Quick Settings button
        self.quick_settings_btn = QPushButton("⚡")
        self.quick_settings_btn.setFixedSize(34, 34)
        self.quick_settings_btn.setCursor(Qt.PointingHandCursor)
        self.quick_settings_btn.setToolTip("Quick Settings, Power Profiles & Cache Purge (Ctrl+Shift+S)")
        self.quick_settings_btn.setStyleSheet("""
            QPushButton {
                background: #101728;
                border: 1px solid rgba(255, 170, 0, 0.4);
                border-radius: 17px;
                color: #ffaa00;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ffaa00;
                color: #000000;
            }
        """)
        self.quick_settings_btn.clicked.connect(self.quick_settings_requested.emit)
        layout.addWidget(self.quick_settings_btn)

        # Digital Clock (Responsive, non-clipped)
        self.clock_lbl = QLabel()
        self.clock_lbl.setMinimumWidth(88)
        self.clock_lbl.setAlignment(Qt.AlignCenter)
        self.clock_lbl.setCursor(Qt.PointingHandCursor)
        self.clock_lbl.setToolTip("System Clock & Calendar • Click for Quick Settings")
        self.clock_lbl.setStyleSheet("color: #e2e8f0; font-family: 'Segoe UI', monospace; font-size: 11px; font-weight: 600; padding: 0 4px;")
        self.clock_lbl.mousePressEvent = lambda e: self.quick_settings_requested.emit()
        layout.addWidget(self.clock_lbl)

        # Safe Exit Button
        exit_icon_btn = QPushButton("⏻")
        exit_icon_btn.setFixedSize(34, 34)
        exit_icon_btn.setCursor(Qt.PointingHandCursor)
        exit_icon_btn.setToolTip("Safely Close NOVA OS Trial (Ctrl+Q)")
        exit_icon_btn.setObjectName("DangerButton")
        exit_icon_btn.setStyleSheet("""
            QPushButton#DangerButton {
                background: #1f121d;
                border: 1px solid #ff2a55;
                border-radius: 17px;
                color: #ff2a55;
                font-size: 14px;
            }
            QPushButton#DangerButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        exit_icon_btn.clicked.connect(self.exit_requested)
        layout.addWidget(exit_icon_btn)

    def set_ai_status(self, is_online: bool, model_name: str = "", checking: bool = False):
        """Dynamically updates the AI Status pill based on verified Ollama connectivity."""
        if checking:
            self.ai_tag.setText("○ CHECKING AI")
            self.ai_tag.setStyleSheet("""
                QLabel {
                    color: #ffaa00;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 4px 10px;
                    background: #1c1808;
                    border-radius: 12px;
                    border: 1px solid rgba(255, 170, 0, 0.4);
                }
            """)
            self.ai_tag.setToolTip("Verifying Ollama local model service status...")
        elif is_online:
            label = f"● AI READY ({model_name})" if model_name else "● AI READY"
            self.ai_tag.setText(label)
            self.ai_tag.setStyleSheet("""
                QLabel {
                    color: #00ff88;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 4px 10px;
                    background: #081a18;
                    border-radius: 12px;
                    border: 1px solid rgba(0, 255, 136, 0.4);
                }
            """)
            self.ai_tag.setToolTip(f"Ollama local AI is online and responsive (Model: {model_name or 'qwen2.5:0.5b'})")
        else:
            self.ai_tag.setText("○ AI OFFLINE")
            self.ai_tag.setStyleSheet("""
                QLabel {
                    color: #ff4466;
                    font-weight: bold;
                    font-size: 10px;
                    padding: 4px 10px;
                    background: #240c12;
                    border-radius: 12px;
                    border: 1px solid rgba(255, 68, 102, 0.4);
                }
            """)
            self.ai_tag.setToolTip("Ollama service unreachable at 127.0.0.1:11434. Local LLM offline.")

    def toggle_launcher(self):
        if self.launcher.isVisible():
            self.launcher.hide()
        else:
            # Position above start button
            global_pos = self.start_btn.mapToGlobal(QPoint(0, 0))
            self.launcher.move(global_pos.x(), global_pos.y() - self.launcher.height() - 10)
            self.launcher.show()
            self.launcher.search_box.setFocus()

    def update_clock(self):
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%b %d, %Y")
        self.clock_lbl.setText(f"{time_str}\n{date_str}")

    def update_active_windows(self, open_windows: dict):
        """Updates taskbar buttons corresponding to open windows."""
        # Clear existing buttons
        for btn in self.window_buttons.values():
            btn.deleteLater()
        self.window_buttons.clear()

        # Re-add stretch at end
        while self.tasks_layout.count() > 0:
            item = self.tasks_layout.takeAt(0)

        for win_id, (frame, is_visible) in open_windows.items():
            btn = QPushButton(f"{frame.icon_text} {frame.title_text}")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            bg = "#1a2542" if is_visible else "#0d1322"
            border = "#00f0ff" if is_visible else "rgba(255,255,255,0.12)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    border: 1px solid {border};
                    border-radius: 14px;
                    color: #ffffff;
                    padding: 0 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    border-color: #00f0ff;
                    background: #233358;
                }}
            """)
            btn.clicked.connect(lambda checked, w=win_id: self.window_toggle_requested.emit(w))
            self.tasks_layout.addWidget(btn)
            self.window_buttons[win_id] = btn

        self.tasks_layout.addStretch()
