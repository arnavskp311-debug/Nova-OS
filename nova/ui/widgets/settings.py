"""
NOVA OS Settings & Control Center.
Configure AI endpoints, security policies, theme accents, and data management.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QCheckBox,
    QFrame, QMessageBox, QGroupBox, QFileDialog,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from nova.config import (
    DEFAULT_OLLAMA_HOST, DEFAULT_MODEL, ACCENT_COLORS,
    DEFAULT_ACCENT, APP_NAME, APP_VERSION, BACKUPS_DIR
)
from nova.database import (
    get_setting, set_setting, get_recent_command_logs,
    create_database_backup, restore_database_backup, check_database_integrity
)
from nova.ollama_client import OllamaClient

class SettingsModelWorker(QThread):
    models_ready = Signal(list)

    def __init__(self, client: OllamaClient):
        super().__init__()
        self.client = client

    def run(self):
        try:
            models = self.client.get_available_models(force_refresh=False)
            self.models_ready.emit(models)
        except Exception:
            self.models_ready.emit([])

class SettingsWidget(QWidget):
    theme_changed = Signal(str)
    performance_mode_changed = Signal(str)

    def __init__(self, ollama_client: OllamaClient, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        # Header
        header = QLabel("NOVA CONTROL CENTER // SETTINGS")
        header.setObjectName("HeaderTitle")
        layout.addWidget(header)

        # AI Configuration Group
        def _make_group_style(color: str, border_rgba: str) -> str:
            return f"""
                QGroupBox {{
                    font-weight: bold;
                    color: {color};
                    border: 1px solid {border_rgba};
                    border-radius: 8px;
                    margin-top: 14px;
                    padding-top: 16px;
                    padding-left: 10px;
                    padding-right: 10px;
                    padding-bottom: 10px;
                    background: transparent;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 10px;
                    padding: 0 4px;
                    color: {color};
                    font-size: 12px;
                    font-weight: bold;
                }}
                QGroupBox QLabel {{
                    color: #EAF4FF;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QGroupBox QCheckBox {{
                    color: #EAF4FF;
                    font-size: 12px;
                }}
                QGroupBox QCheckBox:disabled {{
                    color: #718096;
                }}
                QGroupBox QComboBox {{
                    background-color: #121829;
                    color: #EAF4FF;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    padding: 6px 12px;
                }}
                QGroupBox QLineEdit {{
                    background-color: #0A0E19;
                    color: #EAF4FF;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
            """

        ai_group = QGroupBox("Local AI & Ollama Configuration")
        ai_group.setStyleSheet(_make_group_style("#00F0FF", "rgba(0, 240, 255, 0.25)"))
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(10)

        host_row = QHBoxLayout()
        host_lbl = QLabel("Ollama Endpoint:")
        host_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        host_row.addWidget(host_lbl)
        self.host_input = QLineEdit()
        self.host_input.setText(DEFAULT_OLLAMA_HOST)
        host_row.addWidget(self.host_input)

        self.test_conn_btn = QPushButton("Test Ping")
        self.test_conn_btn.clicked.connect(self.on_test_connection)
        host_row.addWidget(self.test_conn_btn)
        ai_layout.addLayout(host_row)

        model_row = QHBoxLayout()
        model_lbl = QLabel("Preferred Model:")
        model_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        model_row.addWidget(model_lbl)
        self.model_combo = QComboBox()
        model_row.addWidget(self.model_combo)
        model_row.addStretch()
        ai_layout.addLayout(model_row)

        layout.addWidget(ai_group)

        # Voice Assistant & Kokoro-82M TTS Group
        voice_group = QGroupBox("NOVA Voice & Speech Synthesis (Kokoro-82M / Piper)")
        voice_group.setStyleSheet(_make_group_style("#00F0FF", "rgba(0, 240, 255, 0.25)"))
        voice_layout = QVBoxLayout(voice_group)
        voice_layout.setSpacing(10)

        v_engine_row = QHBoxLayout()
        v_engine_lbl = QLabel("Primary TTS Engine:")
        v_engine_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        v_engine_row.addWidget(v_engine_lbl)
        self.v_engine_combo = QComboBox()
        self.v_engine_combo.addItems([
            "Kokoro-82M (Neural High-Fidelity)",
            "Piper TTS (Local Low-RAM Fast)",
            "Windows SAPI (Instant Fallback)"
        ])
        v_engine_row.addWidget(self.v_engine_combo)
        v_engine_row.addStretch()
        voice_layout.addLayout(v_engine_row)

        v_profile_row = QHBoxLayout()
        v_profile_lbl = QLabel("Neural Voice Profile:")
        v_profile_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        v_profile_row.addWidget(v_profile_lbl)
        self.v_profile_combo = QComboBox()
        from nova.voice.kokoro_tts import RECOMMENDED_VOICES
        for v_id, v_label, _ in RECOMMENDED_VOICES:
            self.v_profile_combo.addItem(f"{v_id} — {v_label}", v_id)
        v_profile_row.addWidget(self.v_profile_combo)
        v_profile_row.addStretch()
        voice_layout.addLayout(v_profile_row)

        voice_note = QLabel("Kokoro-82M (Apache 2.0) • Piper (MIT) • Offline Local Speech • Intel Core i3 Optimized")
        voice_note.setStyleSheet("color: #A9BCD4; font-size: 11px;")
        voice_layout.addWidget(voice_note)

        layout.addWidget(voice_group)

        # Visual Theme Group (Matching Panel 7)
        theme_group = QGroupBox("NOVA Themes & Icon Packs")
        theme_group.setStyleSheet(_make_group_style("#B026FF", "rgba(176, 38, 255, 0.25)"))
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(10)

        # Theme Archetype Row
        t_row = QHBoxLayout()
        t_lbl = QLabel("Interface Theme:")
        t_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        t_row.addWidget(t_lbl)
        self.theme_preset_combo = QComboBox()
        self.theme_preset_combo.addItems([
            "Cyber Dark (Default)",
            "Cyber Neon Glow",
            "Matrix Emerald Dark",
            "High Contrast Daylight"
        ])
        t_row.addWidget(self.theme_preset_combo)
        t_row.addStretch()
        theme_layout.addLayout(t_row)

        # Accent Neon Color Row
        accent_row = QHBoxLayout()
        accent_lbl = QLabel("Accent Neon Color:")
        accent_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        accent_row.addWidget(accent_lbl)
        self.accent_combo = QComboBox()
        for name in ACCENT_COLORS.keys():
            self.accent_combo.addItem(name)
        self.accent_combo.currentTextChanged.connect(self.on_accent_changed)
        accent_row.addWidget(self.accent_combo)
        accent_row.addStretch()
        theme_layout.addLayout(accent_row)

        # Icon Pack Selector (Matching Panel 7: NOVA Default, Neon, Minimal)
        icon_row = QHBoxLayout()
        icon_lbl = QLabel("Desktop Icon Pack:")
        icon_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        icon_row.addWidget(icon_lbl)
        self.icon_pack_combo = QComboBox()
        self.icon_pack_combo.addItems([
            "NOVA Cyber (Default)",
            "Neon Glow Extended",
            "Minimalist Monoline"
        ])
        saved_pack = get_setting("icon_pack", "NOVA Cyber (Default)")
        self.icon_pack_combo.setCurrentText(saved_pack)
        self.icon_pack_combo.currentTextChanged.connect(lambda p: set_setting("icon_pack", p))
        icon_row.addWidget(self.icon_pack_combo)
        icon_row.addStretch()

        reset_theme_btn = QPushButton("↺ Reset Theme Defaults")
        reset_theme_btn.setStyleSheet("background: #151d30; border: 1px solid rgba(0, 240, 255, 0.3); color: #00f0ff; padding: 4px 10px; border-radius: 4px;")
        reset_theme_btn.clicked.connect(self.reset_theme_defaults)
        icon_row.addWidget(reset_theme_btn)
        theme_layout.addLayout(icon_row)

        layout.addWidget(theme_group)

        # Performance & Hardware Optimization Group
        perf_group = QGroupBox("Performance & Hardware Profile")
        perf_group.setStyleSheet(_make_group_style("#FFAA00", "rgba(255, 170, 0, 0.25)"))
        perf_layout = QVBoxLayout(perf_group)
        perf_layout.setSpacing(8)

        perf_row = QHBoxLayout()
        perf_lbl = QLabel("Resource Profile:")
        perf_lbl.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        perf_row.addWidget(perf_lbl)
        self.perf_combo = QComboBox()
        self.perf_combo.addItems([
            "Balanced (Recommended)",
            "High Fidelity (Maximum Visuals & Updates)",
            "Low Resource / Battery Saver (Throttled Backgrounds)"
        ])
        perf_row.addWidget(self.perf_combo)
        perf_row.addStretch()
        perf_layout.addLayout(perf_row)

        perf_tip = QLabel("Balanced mode optimizes background polling and caches desktop rendering to eliminate lag.")
        perf_tip.setStyleSheet("color: #A9BCD4; font-size: 11px;")
        perf_layout.addWidget(perf_tip)
        layout.addWidget(perf_group)

        # Safety & Sandbox Policy Group
        safety_group = QGroupBox("Host Protection & Security Gate")
        safety_group.setStyleSheet(_make_group_style("#00FF88", "rgba(0, 255, 136, 0.25)"))
        safety_layout = QVBoxLayout(safety_group)
        safety_layout.setSpacing(8)

        self.require_approval_cb = QCheckBox("Require explicit user approval dialog for any modifying command")
        self.require_approval_cb.setChecked(True)
        safety_layout.addWidget(self.require_approval_cb)

        self.simulated_controls_cb = QCheckBox("Simulate risky operating system features (poweroff, reboot, upgrade) safely")
        self.simulated_controls_cb.setChecked(True)
        safety_layout.addWidget(self.simulated_controls_cb)

        self.block_destructive_cb = QCheckBox("Strictly block host system alterations (Registry, Boot, Windows files)")
        self.block_destructive_cb.setChecked(True)
        self.block_destructive_cb.setEnabled(False) # Always forced on for safety
        safety_layout.addWidget(self.block_destructive_cb)

        layout.addWidget(safety_group)

        # Data Backup & Recovery Group
        backup_group = QGroupBox("Data Backup, Recovery & Schema Vault")
        backup_group.setStyleSheet(_make_group_style("#00F0FF", "rgba(0, 240, 255, 0.25)"))
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.setSpacing(8)

        backup_btns_row = QHBoxLayout()
        self.create_backup_btn = QPushButton("📦 Create Full Backup")
        self.create_backup_btn.setToolTip("Safely snapshot all chats, notes, settings, and browser bookmarks")
        self.create_backup_btn.clicked.connect(self.on_create_backup)
        backup_btns_row.addWidget(self.create_backup_btn)

        self.restore_backup_btn = QPushButton("🔄 Restore from Backup...")
        self.restore_backup_btn.setToolTip("Select a verified backup file to restore NOVA application state")
        self.restore_backup_btn.clicked.connect(self.on_restore_backup)
        backup_btns_row.addWidget(self.restore_backup_btn)

        self.verify_db_btn = QPushButton("🩺 Verify Database Integrity")
        self.verify_db_btn.setToolTip("Run SQLite PRAGMA integrity check and verify schema migrations")
        self.verify_db_btn.clicked.connect(self.on_verify_integrity)
        backup_btns_row.addWidget(self.verify_db_btn)

        backup_layout.addLayout(backup_btns_row)
        layout.addWidget(backup_group)

        # Disclaimer & App Info Card
        info_frame = QFrame()
        info_frame.setObjectName("AccentCard")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(14, 10, 14, 10)

        info_title = QLabel(f"{APP_NAME} v{APP_VERSION} (Windows Trial Application)")
        info_title.setStyleSheet("font-weight: bold; color: #FFFFFF;")
        info_layout.addWidget(info_title)

        info_desc = QLabel(
            "This application is an AI desktop environment trial designed to run completely inside Windows. "
            "It does NOT replace Windows, alter your bootloader, touch BIOS/UEFI, or modify registry entries. "
            "All data is contained in the application folder and can be cleanly uninstalled at any time by deleting the project directory."
        )
        info_desc.setWordWrap(True)
        info_desc.setStyleSheet("color: #A9BCD4; font-size: 11px; line-height: 1.4;")
        info_layout.addWidget(info_desc)

        layout.addWidget(info_frame)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.view_audit_btn = QPushButton("View Security Audit Log")
        self.view_audit_btn.clicked.connect(self.on_view_audit)
        btn_row.addWidget(self.view_audit_btn)

        self.save_btn = QPushButton("Apply Settings")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save_settings)
        btn_row.addWidget(self.save_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    def load_settings(self):
        saved_host = get_setting("ollama_host", DEFAULT_OLLAMA_HOST)
        self.host_input.setText(saved_host)

        saved_accent = get_setting("accent_color", DEFAULT_ACCENT)
        self.accent_combo.setCurrentText(saved_accent)

        saved_perf = get_setting("performance_mode", "Balanced (Recommended)")
        idx = self.perf_combo.findText(saved_perf)
        if idx >= 0:
            self.perf_combo.setCurrentIndex(idx)

        # Voice Settings
        saved_v_engine = get_setting("voice_engine", "Kokoro-82M (Neural High-Fidelity)")
        v_idx = self.v_engine_combo.findText(saved_v_engine)
        if v_idx >= 0:
            self.v_engine_combo.setCurrentIndex(v_idx)

        saved_v_profile = get_setting("voice_profile", "af_nova")
        for i in range(self.v_profile_combo.count()):
            if self.v_profile_combo.itemData(i) == saved_v_profile:
                self.v_profile_combo.setCurrentIndex(i)
                break

        # Asynchronously fetch models without blocking UI
        self.model_combo.clear()
        self.model_combo.addItem("Loading installed models...")
        self._worker = SettingsModelWorker(self.ollama_client)
        self._worker.models_ready.connect(self._on_models_loaded)
        self._worker.start()

    @Slot(list)
    def _on_models_loaded(self, models: list):
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
            saved_model = get_setting("default_model", DEFAULT_MODEL)
            if saved_model in models:
                self.model_combo.setCurrentText(saved_model)
        else:
            self.model_combo.addItem("No models found / Offline")

    def on_test_connection(self):
        self.ollama_client.host = self.host_input.text().strip()
        if self.ollama_client.check_connection(force_refresh=True):
            models = self.ollama_client.get_available_models(force_refresh=True)
            QMessageBox.information(
                self,
                "Connection Successful",
                f"Connected to Ollama service.\nAvailable models: {', '.join(models) if models else 'None'}"
            )
            self._on_models_loaded(models)
        else:
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"Could not reach Ollama at {self.ollama_client.host}.\nMake sure Ollama is running (`ollama serve`)."
            )

    def on_accent_changed(self, new_accent: str):
        self.theme_changed.emit(new_accent)

    def reset_theme_defaults(self):
        self.accent_combo.setCurrentText(DEFAULT_ACCENT)
        self.theme_preset_combo.setCurrentText("Cyber Dark (Default)")
        self.icon_pack_combo.setCurrentText("NOVA Cyber (Default)")
        set_setting("accent_color", DEFAULT_ACCENT)
        set_setting("icon_pack", "NOVA Cyber (Default)")
        self.theme_changed.emit(DEFAULT_ACCENT)
        QMessageBox.information(self, "Theme Reset", "Restored default NOVA Cyber Cyan theme and icon pack.")

    def save_settings(self):
        perf_mode = self.perf_combo.currentText()
        set_setting("ollama_host", self.host_input.text().strip())
        set_setting("default_model", self.model_combo.currentText())
        set_setting("accent_color", self.accent_combo.currentText())
        set_setting("performance_mode", perf_mode)
        set_setting("require_approval", self.require_approval_cb.isChecked())
        set_setting("simulated_controls", self.simulated_controls_cb.isChecked())
        set_setting("voice_engine", self.v_engine_combo.currentText())
        set_setting("voice_profile", self.v_profile_combo.currentData() or "af_nova")

        self.performance_mode_changed.emit(perf_mode)
        QMessageBox.information(self, "Settings Saved", "Application and performance preferences have been stored locally.")

    def on_view_audit(self):
        logs = get_recent_command_logs(limit=20)
        if not logs:
            QMessageBox.information(self, "Security Audit Log", "No commands have been logged yet.")
            return

        lines = ["=== RECENT COMMAND SECURITY AUDIT LOGS ==="]
        for l in logs:
            approved = "YES" if l["approved"] else "NO"
            lines.append(f"[{l['executed_at']}] [{l['risk_level']}] Approved:{approved} Status:{l['status']}\nCmd: {l['command']}")

        msg = "\n\n".join(lines)
        QMessageBox.information(self, "Security Audit Logs", msg[:1500])

    def on_create_backup(self):
        ok, msg, path = create_database_backup()
        if ok:
            QMessageBox.information(
                self,
                "Backup Successful",
                f"{msg}\nSaved to:\n{path}"
            )
        else:
            QMessageBox.critical(self, "Backup Failed", msg)

    def on_restore_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select NOVA Backup File to Restore",
            str(BACKUPS_DIR),
            "NOVA Database Backups (*.db);;All Files (*.*)"
        )
        if not file_path:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Database Restore",
            f"Restoring this backup will replace current application data with the backup snapshot.\n\n"
            f"File: {Path(file_path).name}\n\nDo you wish to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = restore_database_backup(Path(file_path))
            if ok:
                QMessageBox.information(self, "Restore Completed", msg)
                self.load_settings()
            else:
                QMessageBox.critical(self, "Restore Failed", msg)

    def on_verify_integrity(self):
        ok, msg, ver = check_database_integrity()
        status_title = "Database Healthy" if ok else "Integrity Warning"
        info = (
            f"Status: {'HEALTHY' if ok else 'UNHEALTHY'}\n"
            f"Schema Version: v{ver}\n"
            f"Integrity Check: {msg}"
        )
        if ok:
            QMessageBox.information(self, status_title, info)
        else:
            QMessageBox.warning(self, status_title, info)

