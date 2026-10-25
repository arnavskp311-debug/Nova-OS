"""
Privacy Center Dashboard for NOVA OS (Feature 16).
Provides centralized user control over data retention, browsing history,
AI memory permissions, and microphone access.
Matching Panel 16 of the reference design.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QCheckBox, QComboBox, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from nova.database import (
    get_setting, set_setting, clear_browser_history,
    clear_all_ai_memory, get_browser_history, get_ai_memories,
    purge_transient_cache
)


class PrivacyCenterWidget(QWidget):
    notification_requested = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_privacy_status()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🛡️")
        icon.setStyleSheet("font-size: 22px;")
        head.addWidget(icon)

        title = QLabel("PRIVACY CENTER // DATA & PERMISSION CONTROLS")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00ff88; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        main_layout.addLayout(head)

        sub_lbl = QLabel("Zero telemetry phoning home. Your activity, chat transcripts, and files remain strictly offline on your Windows SSD.")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        main_layout.addWidget(sub_lbl)

        # Split Layout: Left Navigation, Right Settings Cards
        content_box = QHBoxLayout()
        content_box.setSpacing(14)

        # Left Nav List (Matching Panel 16 categories)
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(180)
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: #080d1a;
                border: 1px solid rgba(0, 255, 136, 0.25);
                border-radius: 8px;
                padding: 6px;
                color: #e2e8f0;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 4px;
                font-weight: 600;
                font-size: 12px;
            }
            QListWidget::item:hover {
                background: #0d221c;
                color: #00ff88;
            }
            QListWidget::item:selected {
                background: #0f2c24;
                border-left: 3px solid #00ff88;
                color: #ffffff;
            }
        """)
        for item_name in ["Overview", "History & Cookies", "AI & Voice Consent", "Permissions", "Data Retention"]:
            self.nav_list.addItem(item_name)
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self.on_nav_changed)
        content_box.addWidget(self.nav_list)

        # Right Settings Container
        self.settings_card = QFrame()
        self.settings_card.setStyleSheet("""
            QFrame {
                background: #0a1420;
                border: 1px solid rgba(0, 255, 136, 0.25);
                border-radius: 10px;
                padding: 14px;
            }
        """)
        self.card_layout = QVBoxLayout(self.settings_card)
        self.card_layout.setSpacing(12)

        # Row 1: Browser History Control
        r1_box = QFrame()
        r1_box.setStyleSheet("background: #0d1b2a; border-radius: 6px; padding: 10px;")
        r1_layout = QHBoxLayout(r1_box)
        self.cb_history = QCheckBox("Track Local Browser History")
        self.cb_history.setChecked(get_setting("privacy_track_history", "true") == "true")
        self.cb_history.toggled.connect(self.toggle_track_history)
        r1_layout.addWidget(self.cb_history)
        r1_layout.addStretch()

        self.hist_count_lbl = QLabel("0 items stored")
        self.hist_count_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        r1_layout.addWidget(self.hist_count_lbl)

        clear_hist_btn = QPushButton("Clear History")
        clear_hist_btn.setStyleSheet("""
            QPushButton {
                background: #240c12;
                border: 1px solid #ff2a55;
                border-radius: 4px;
                color: #ff2a55;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        clear_hist_btn.clicked.connect(self.clear_history)
        r1_layout.addWidget(clear_hist_btn)
        self.card_layout.addWidget(r1_box)

        # Row 2: AI Local Memory Control
        r2_box = QFrame()
        r2_box.setStyleSheet("background: #0d1b2a; border-radius: 6px; padding: 10px;")
        r2_layout = QHBoxLayout(r2_box)
        self.cb_memory = QCheckBox("Enable AI Memory & Persistent Preferences")
        self.cb_memory.setChecked(get_setting("privacy_enable_memory", "true") == "true")
        self.cb_memory.toggled.connect(self.toggle_enable_memory)
        r2_layout.addWidget(self.cb_memory)
        r2_layout.addStretch()

        self.mem_count_lbl = QLabel("0 approved memories")
        self.mem_count_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        r2_layout.addWidget(self.mem_count_lbl)

        clear_mem_btn = QPushButton("Purge Memory")
        clear_mem_btn.setStyleSheet("""
            QPushButton {
                background: #1f121d;
                border: 1px solid #ff2a55;
                border-radius: 4px;
                color: #ff6b8b;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        clear_mem_btn.clicked.connect(self.clear_memory)
        r2_layout.addWidget(clear_mem_btn)
        self.card_layout.addWidget(r2_box)

        # Row 3: Microphone & Audio Input Permission
        r3_box = QFrame()
        r3_box.setStyleSheet("background: #0d1b2a; border-radius: 6px; padding: 10px;")
        r3_layout = QHBoxLayout(r3_box)
        self.cb_mic = QCheckBox("Microphone Access (NOVA Voice Assistant)")
        self.cb_mic.setChecked(get_setting("mic_permission_allowed", "true") == "true")
        self.cb_mic.toggled.connect(self.toggle_mic_permission)
        r3_layout.addWidget(self.cb_mic)
        r3_layout.addStretch()

        self.mic_status_lbl = QLabel("Active / Push-to-Talk")
        self.mic_status_lbl.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: bold;")
        r3_layout.addWidget(self.mic_status_lbl)
        self.card_layout.addWidget(r3_box)

        # Row 4: Data Retention Policy Dropdown
        r4_box = QFrame()
        r4_box.setStyleSheet("background: #0d1b2a; border-radius: 6px; padding: 10px;")
        r4_layout = QHBoxLayout(r4_box)
        r4_layout.addWidget(QLabel("Automatic Cache & Log Retention:"))
        self.retention_combo = QComboBox()
        self.retention_combo.addItems([
            "Auto-purge transient cache every 7 days",
            "Auto-purge transient cache every 30 days",
            "Manual purge only (Keep all logs)"
        ])
        saved_policy = get_setting("retention_policy", "Auto-purge transient cache every 30 days")
        self.retention_combo.setCurrentText(saved_policy)
        self.retention_combo.currentTextChanged.connect(lambda v: set_setting("retention_policy", v))
        r4_layout.addWidget(self.retention_combo)
        r4_layout.addStretch()

        purge_now_btn = QPushButton("Purge Cache Now")
        purge_now_btn.setStyleSheet("background: #111d33; border: 1px solid #00f0ff; color: #00f0ff; border-radius: 4px; padding: 4px 10px;")
        purge_now_btn.clicked.connect(self.purge_cache_now)
        r4_layout.addWidget(purge_now_btn)
        self.card_layout.addWidget(r4_box)

        self.card_layout.addStretch()
        content_box.addWidget(self.settings_card, stretch=1)
        main_layout.addLayout(content_box)

    def load_privacy_status(self):
        try:
            h = get_browser_history()
            self.hist_count_lbl.setText(f"{len(h)} items stored")
        except Exception:
            pass

        try:
            m = get_ai_memories()
            self.mem_count_lbl.setText(f"{len(m)} memories stored")
        except Exception:
            pass

    def on_nav_changed(self, idx: int):
        pass  # Kept unified in single comprehensive dashboard view

    def toggle_track_history(self, state: bool):
        set_setting("privacy_track_history", "true" if state else "false")
        self.notification_requested.emit(
            "PRIVACY UPDATED",
            f"Browser history tracking is now {'ENABLED' if state else 'DISABLED'}.",
            "info"
        )

    def toggle_enable_memory(self, state: bool):
        set_setting("privacy_enable_memory", "true" if state else "false")
        self.notification_requested.emit(
            "AI MEMORY UPDATED",
            f"Local AI contextual memory is now {'ENABLED' if state else 'DISABLED'}.",
            "info"
        )

    def toggle_mic_permission(self, state: bool):
        set_setting("mic_permission_allowed", "true" if state else "false")
        self.mic_status_lbl.setText("Allowed" if state else "Blocked")
        self.mic_status_lbl.setStyleSheet(f"color: {'#00ff88' if state else '#ff2a55'}; font-size: 11px; font-weight: bold;")
        self.notification_requested.emit(
            "PERMISSION UPDATED",
            f"Microphone input for voice assistant is {'ALLOWED' if state else 'REVOKED'}.",
            "info"
        )

    def clear_history(self):
        del_count = clear_browser_history()
        self.load_privacy_status()
        self.notification_requested.emit("HISTORY PURGED", f"Cleared {del_count} browsing entries.", "success")
        QMessageBox.information(self, "History Cleared", f"Successfully cleared {del_count} browser history records.")

    def clear_memory(self):
        del_count = clear_all_ai_memory()
        self.load_privacy_status()
        self.notification_requested.emit("MEMORY CLEARED", f"Purged {del_count} AI memories.", "success")
        QMessageBox.information(self, "Memory Cleared", f"Successfully purged {del_count} AI contextual memory records.")

    def purge_cache_now(self):
        res = purge_transient_cache()
        self.notification_requested.emit(
            "CACHE PURGED",
            f"Freed {res['freed_mb']} MB of transient browser and voice buffers.",
            "success"
        )
        QMessageBox.information(self, "Cache Purged", f"Freed {res['freed_mb']} MB disk space.\nPurged: {', '.join(res['purged_items'])}")
