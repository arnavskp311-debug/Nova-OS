"""
NOVA Browser - Chrome Safe Integration & Permissions Dialog.
Provides user-controlled permissions, profile selection, reversible data imports,
security disclosures, and official Native Messaging documentation.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QComboBox, QTabWidget,
    QTextEdit, QFrame, QMessageBox, QGroupBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtGui import QFont

from nova.chrome_integration import ChromeIntegrationManager
from nova.database import delete_imported_bookmarks, clear_browser_history

class DataImportWorker(QThread):
    """Background worker to import Chrome data without freezing UI."""
    import_finished = Signal(int, str)

    def __init__(self, target_func, *args):
        super().__init__()
        self.target_func = target_func
        self.args = args

    def run(self):
        try:
            count, msg = self.target_func(*self.args)
            self.import_finished.emit(count, msg)
        except Exception as e:
            self.import_finished.emit(0, f"Import Error: {str(e)}")

class ChromeConnectDialog(QDialog):
    data_changed = Signal()

    def __init__(self, manager: ChromeIntegrationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("NOVA Browser // Google Chrome Safe Integration Gateway")
        self.setMinimumSize(680, 560)
        self.setModal(True)

        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title
        header = QHBoxLayout()
        icon_lbl = QLabel("🛡️")
        icon_lbl.setStyleSheet("font-size: 24px;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title = QLabel("GOOGLE CHROME SAFE INTEGRATION")
        title.setObjectName("HeaderTitle")
        title_box.addWidget(title)

        subtitle = QLabel("User-controlled read-only imports and URL handoff. No token, password, or cookie extraction.")
        subtitle.setObjectName("MutedLabel")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()

        self.status_pill = QLabel("DISCONNECTED")
        self.status_pill.setStyleSheet(
            "padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 11px; "
            "background: #2a1215; color: #ff2a55; border: 1px solid #ff2a55;"
        )
        header.addWidget(self.status_pill, alignment=Qt.AlignVCenter)
        main_layout.addLayout(header)

        # Tab Widget
        tabs = QTabWidget()

        # Tab 1: Connection & Permissions
        tab_connect = QWidget()
        connect_layout = QVBoxLayout(tab_connect)
        connect_layout.setContentsMargins(12, 14, 12, 12)
        connect_layout.setSpacing(12)

        # Chrome Detection Box
        detect_box = QFrame()
        detect_box.setObjectName("AccentCard")
        detect_layout = QVBoxLayout(detect_box)
        detect_layout.setContentsMargins(12, 10, 12, 10)
        detect_layout.setSpacing(6)

        self.install_lbl = QLabel("Chrome Installation: Checking...")
        self.install_lbl.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        detect_layout.addWidget(self.install_lbl)

        self.path_lbl = QLabel("Executable: --")
        self.path_lbl.setObjectName("MutedLabel")
        detect_layout.addWidget(self.path_lbl)
        connect_layout.addWidget(detect_box)

        # Profile Selector
        prof_row = QHBoxLayout()
        prof_lbl = QLabel("Select Chrome Profile:")
        prof_lbl.setStyleSheet("color: #EAF4FF; font-weight: bold; font-size: 12px;")
        prof_row.addWidget(prof_lbl)
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(260)
        prof_row.addWidget(self.profile_combo)
        prof_row.addStretch()
        connect_layout.addLayout(prof_row)

        # Permissions Group
        perm_group = QGroupBox("Granted Permissions")
        perm_group.setStyleSheet("QGroupBox { font-weight: bold; color: #00f0ff; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 8px; margin-top: 10px; padding-top: 15px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; } QGroupBox QCheckBox { color: #EAF4FF; font-size: 12px; }")
        perm_layout = QVBoxLayout(perm_group)
        perm_layout.setSpacing(8)

        self.perm_bm_cb = QCheckBox("Allow reading Bookmarks (Read-only from Chrome Bookmarks JSON)")
        perm_layout.addWidget(self.perm_bm_cb)

        self.perm_hist_cb = QCheckBox("Allow reading Browsing History (Temporary non-locking snapshot)")
        perm_layout.addWidget(self.perm_hist_cb)

        self.perm_handoff_cb = QCheckBox("Allow Bi-directional URL Handoff (Launch URLs in Chrome)")
        self.perm_handoff_cb.setChecked(True)
        perm_layout.addWidget(self.perm_handoff_cb)

        connect_layout.addWidget(perm_group)

        # Actions & Reversible Data Management
        actions_group = QGroupBox("Import & Reversible Data Operations")
        actions_group.setStyleSheet("QGroupBox { font-weight: bold; color: #00ff88; border: 1px solid rgba(0, 255, 136, 0.2); border-radius: 8px; margin-top: 10px; padding-top: 15px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; } QGroupBox QLabel { color: #EAF4FF; }")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(8)

        # Bookmarks row
        bm_row = QHBoxLayout()
        self.import_bm_btn = QPushButton("📥 Import Bookmarks")
        self.import_bm_btn.setObjectName("PrimaryButton")
        self.import_bm_btn.clicked.connect(self.on_import_bookmarks)
        bm_row.addWidget(self.import_bm_btn)

        self.purge_bm_btn = QPushButton("🗑 Purge Imported Bookmarks")
        self.purge_bm_btn.setObjectName("DangerButton")
        self.purge_bm_btn.setToolTip("Reversibly deletes bookmarks imported from Chrome without touching native items.")
        self.purge_bm_btn.clicked.connect(self.on_purge_bookmarks)
        bm_row.addWidget(self.purge_bm_btn)
        actions_layout.addLayout(bm_row)

        # History row
        hist_row = QHBoxLayout()
        self.import_hist_btn = QPushButton("📥 Import History Snapshot")
        self.import_hist_btn.clicked.connect(self.on_import_history)
        hist_row.addWidget(self.import_hist_btn)

        self.purge_hist_btn = QPushButton("🗑 Purge Imported History")
        self.purge_hist_btn.setObjectName("DangerButton")
        self.purge_hist_btn.setToolTip("Removes imported history without modifying Chrome.")
        self.purge_hist_btn.clicked.connect(self.on_purge_history)
        hist_row.addWidget(self.purge_hist_btn)
        actions_layout.addLayout(hist_row)

        connect_layout.addWidget(actions_group)
        connect_layout.addStretch()

        tabs.addTab(tab_connect, "Connection & Data")

        # Tab 2: Security & Privacy Disclosures
        tab_sec = QWidget()
        sec_layout = QVBoxLayout(tab_sec)
        sec_layout.setContentsMargins(14, 14, 14, 14)
        sec_layout.setSpacing(10)

        disclosures = self.manager.get_security_disclosures()

        sec_scroll = QScrollArea()
        sec_scroll.setWidgetResizable(True)
        sec_container = QWidget()
        sec_container_layout = QVBoxLayout(sec_container)
        sec_container_layout.setSpacing(12)

        # Supported Box
        sup_box = QFrame()
        sup_box.setObjectName("AccentCard")
        sup_layout = QVBoxLayout(sup_box)
        sup_title = QLabel("✅ SUPPORTED CAPABILITIES")
        sup_title.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 13px;")
        sup_layout.addWidget(sup_title)
        for item in disclosures["supported"]:
            lbl = QLabel(f"• {item}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; margin-left: 6px;")
            sup_layout.addWidget(lbl)
        sec_container_layout.addWidget(sup_box)

        # Blocked Box
        blk_box = QFrame()
        blk_box.setObjectName("AccentCard")
        blk_layout = QVBoxLayout(blk_box)
        blk_title = QLabel("🚫 STRICTLY BLOCKED & PROHIBITED OPERATIONS")
        blk_title.setStyleSheet("color: #ff2a55; font-weight: bold; font-size: 13px;")
        blk_layout.addWidget(blk_title)
        for item in disclosures["unsupported_and_blocked"]:
            lbl = QLabel(f"• {item}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #fca5a5; font-size: 12px; margin-left: 6px;")
            blk_layout.addWidget(lbl)
        sec_container_layout.addWidget(blk_box)

        # Safe Alternatives Box
        alt_box = QFrame()
        alt_box.setObjectName("AccentCard")
        alt_layout = QVBoxLayout(alt_box)
        alt_title = QLabel("💡 SAFE SESSION ALTERNATIVES")
        alt_title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px;")
        alt_layout.addWidget(alt_title)
        alt_text = QLabel(disclosures["safe_alternatives"])
        alt_text.setWordWrap(True)
        alt_text.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.4;")
        alt_layout.addWidget(alt_text)
        sec_container_layout.addWidget(alt_box)

        sec_scroll.setWidget(sec_container)
        sec_layout.addWidget(sec_scroll)

        tabs.addTab(tab_sec, "Security & Privacy Guarantees")

        # Tab 3: Official Native Messaging Bridge
        tab_ext = QWidget()
        ext_layout = QVBoxLayout(tab_ext)
        ext_layout.setContentsMargins(14, 14, 14, 14)
        ext_layout.setSpacing(10)

        nm_info = self.manager.get_native_messaging_info()

        ext_title = QLabel("Official Chrome Native Messaging Host Architecture")
        ext_title.setStyleSheet("font-weight: bold; color: #00f0ff; font-size: 13px;")
        ext_layout.addWidget(ext_title)

        ext_summary = QLabel(nm_info["protocol_summary"])
        ext_summary.setWordWrap(True)
        ext_summary.setStyleSheet("color: #94a3b8; font-size: 12px;")
        ext_layout.addWidget(ext_summary)

        manifest_lbl = QLabel("Host JSON Manifest Template (com.nova.os.browser.bridge.json):")
        manifest_lbl.setStyleSheet("color: #EAF4FF; font-weight: bold;")
        ext_layout.addWidget(manifest_lbl)
        manifest_edit = QTextEdit()
        manifest_edit.setReadOnly(True)
        manifest_edit.setFont(QFont("Consolas", 10))
        manifest_edit.setPlainText(nm_info["manifest_json"])
        manifest_edit.setMaximumHeight(130)
        ext_layout.addWidget(manifest_edit)

        lim_label = QLabel(f"Note on Extension Scope: {nm_info['limitations']}")
        lim_label.setWordWrap(True)
        lim_label.setStyleSheet("color: #64748b; font-size: 11px;")
        ext_layout.addWidget(lim_label)

        tabs.addTab(tab_ext, "Native Messaging & Extensions")

        main_layout.addWidget(tabs)

        # Bottom Bar
        bottom_bar = QHBoxLayout()
        self.toggle_connect_btn = QPushButton("Connect with Chrome")
        self.toggle_connect_btn.setObjectName("PrimaryButton")
        self.toggle_connect_btn.clicked.connect(self.on_toggle_connection)
        bottom_bar.addWidget(self.toggle_connect_btn)

        bottom_bar.addStretch()

        self.apply_btn = QPushButton("Save Preferences")
        self.apply_btn.clicked.connect(self.on_save_preferences)
        bottom_bar.addWidget(self.apply_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom_bar.addWidget(close_btn)

        main_layout.addLayout(bottom_bar)

    def refresh_status(self):
        status = self.manager.get_connection_status()
        installed = status["installed"]

        if installed:
            self.install_lbl.setText("Google Chrome Detected (Operational)")
            self.path_lbl.setText(f"Executable: {status['chrome_path']}")
        else:
            self.install_lbl.setText("Google Chrome Not Detected on Standard Windows Paths")
            self.path_lbl.setText("Expected: Program Files / LocalAppData")

        # Load Profiles
        profiles = self.manager.get_available_profiles()
        self.profile_combo.clear()
        selected_index = 0
        for idx, p in enumerate(profiles):
            has_bm = "⭐ Bookmarks" if p["has_bookmarks"] else "No Bookmarks"
            has_h = "🕒 History" if p["has_history"] else "No History"
            label = f"{p['name']} ({p['id']}) [{has_bm}, {has_h}]"
            self.profile_combo.addItem(label, p["id"])
            if p["id"] == status["selected_profile"]:
                selected_index = idx

        if self.profile_combo.count() > 0:
            self.profile_combo.setCurrentIndex(selected_index)

        # Permissions
        self.perm_bm_cb.setChecked(status["perm_bookmarks"])
        self.perm_hist_cb.setChecked(status["perm_history"])
        self.perm_handoff_cb.setChecked(status["perm_handoff"])

        # Status badge & button text
        if status["connected"]:
            self.status_pill.setText("CONNECTED")
            self.status_pill.setStyleSheet(
                "padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 11px; "
                "background: #0f2d22; color: #00ff88; border: 1px solid #00ff88;"
            )
            self.toggle_connect_btn.setText("Disconnect from Chrome")
            self.toggle_connect_btn.setObjectName("DangerButton")
            self.import_bm_btn.setEnabled(True)
            self.import_hist_btn.setEnabled(True)
        else:
            self.status_pill.setText("DISCONNECTED")
            self.status_pill.setStyleSheet(
                "padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 11px; "
                "background: #2a1215; color: #ff2a55; border: 1px solid #ff2a55;"
            )
            self.toggle_connect_btn.setText("Connect with Chrome")
            self.toggle_connect_btn.setObjectName("PrimaryButton")
            self.import_bm_btn.setEnabled(False)
            self.import_hist_btn.setEnabled(False)

        # Force style re-polish
        self.toggle_connect_btn.style().polish(self.toggle_connect_btn)

    def on_toggle_connection(self):
        status = self.manager.get_connection_status()
        if status["connected"]:
            # Disconnect
            self.manager.set_connection_status(
                connected=False,
                perm_bookmarks=False,
                perm_history=False,
                perm_handoff=self.perm_handoff_cb.isChecked(),
                profile=self.profile_combo.currentData() or "Default"
            )
            QMessageBox.information(
                self,
                "Disconnected",
                "Chrome Integration disconnected. All active permissions have been revoked."
            )
        else:
            if not self.manager.is_chrome_installed():
                QMessageBox.warning(
                    self,
                    "Chrome Missing",
                    "Google Chrome was not detected on standard Windows paths."
                )
                return

            reply = QMessageBox.question(
                self,
                "Grant Permission to Connect with Chrome",
                "NOVA OS will operate alongside Google Chrome in read-only mode.\n\n"
                "• It will NOT read passwords, tokens, or cookies.\n"
                "• It will NOT modify Chrome's files or interfere with Chrome.\n"
                "• Selected data imports remain isolated and reversible.\n\n"
                "Do you consent to enable Chrome Integration?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.manager.set_connection_status(
                    connected=True,
                    perm_bookmarks=self.perm_bm_cb.isChecked(),
                    perm_history=self.perm_hist_cb.isChecked(),
                    perm_handoff=self.perm_handoff_cb.isChecked(),
                    profile=self.profile_combo.currentData() or "Default"
                )

        self.refresh_status()

    def on_save_preferences(self):
        status = self.manager.get_connection_status()
        if status["connected"]:
            self.manager.set_connection_status(
                connected=True,
                perm_bookmarks=self.perm_bm_cb.isChecked(),
                perm_history=self.perm_hist_cb.isChecked(),
                perm_handoff=self.perm_handoff_cb.isChecked(),
                profile=self.profile_combo.currentData() or "Default"
            )
            QMessageBox.information(self, "Preferences Saved", "Integration permissions and profile preference updated.")
        self.refresh_status()

    def on_import_bookmarks(self):
        profile_id = self.profile_combo.currentData() or "Default"
        self.import_bm_btn.setEnabled(False)
        self.import_bm_btn.setText("📥 Importing...")

        self._bm_worker = DataImportWorker(self.manager.import_bookmarks, profile_id)
        self._bm_worker.import_finished.connect(self._on_bm_imported)
        self._bm_worker.start()

    @Slot(int, str)
    def _on_bm_imported(self, count: int, msg: str):
        self.import_bm_btn.setEnabled(True)
        self.import_bm_btn.setText("📥 Import Bookmarks")
        if count > 0:
            QMessageBox.information(self, "Bookmarks Imported", msg)
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Import Notice", msg)

    def on_purge_bookmarks(self):
        reply = QMessageBox.question(
            self,
            "Confirm Purge",
            "This will remove all bookmarks imported from Chrome.\nNative NOVA bookmarks will NOT be affected.\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            deleted = delete_imported_bookmarks("Chrome")
            QMessageBox.information(self, "Bookmarks Purged", f"Removed {deleted} imported Chrome bookmarks.")
            self.data_changed.emit()

    def on_import_history(self):
        profile_id = self.profile_combo.currentData() or "Default"
        self.import_hist_btn.setEnabled(False)
        self.import_hist_btn.setText("📥 Importing...")

        self._hist_worker = DataImportWorker(self.manager.import_history, profile_id, 200)
        self._hist_worker.import_finished.connect(self._on_hist_imported)
        self._hist_worker.start()

    @Slot(int, str)
    def _on_hist_imported(self, count: int, msg: str):
        self.import_hist_btn.setEnabled(True)
        self.import_hist_btn.setText("📥 Import History Snapshot")
        if count > 0:
            QMessageBox.information(self, "History Imported", msg)
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Import Notice", msg)

    def on_purge_history(self):
        reply = QMessageBox.question(
            self,
            "Confirm History Purge",
            "This will remove all history records imported from Chrome.\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            deleted = clear_browser_history(only_imported=True)
            QMessageBox.information(self, "History Purged", f"Removed {deleted} imported Chrome history records.")
            self.data_changed.emit()
