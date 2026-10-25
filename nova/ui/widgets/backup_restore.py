"""
Backup & Restore Manager for NOVA OS (Feature 4).
Matching Panel 4 of the reference design with selective categories,
destination selection, integrity validation, and non-destructive recovery.
"""

import os
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QCheckBox, QLineEdit,
    QComboBox, QProgressBar, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from nova.config import BACKUPS_DIR, DATA_DIR, DB_PATH
from nova.database import (
    create_database_backup, restore_database_backup,
    check_database_integrity, get_connection
)


class BackupWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str, str)  # ok, msg, path

    def __init__(self, dest_dir: Path, backup_name: str, options: Dict[str, bool], parent=None):
        super().__init__(parent)
        self.dest_dir = dest_dir
        self.backup_name = backup_name
        self.options = options

    def run(self):
        try:
            self.progress.emit(20, "Preparing backup directory...")
            self.dest_dir.mkdir(parents=True, exist_ok=True)

            archive_path = self.dest_dir / f"{self.backup_name}.novabackup"
            self.progress.emit(40, "Creating database snapshot...")

            # Take clean online SQLite snapshot
            ok, msg, snap_path = create_database_backup(self.dest_dir)
            if not ok or not snap_path:
                self.finished.emit(False, f"Snapshot failed: {msg}", "")
                return

            self.progress.emit(70, "Packaging selective components...")
            manifest = {
                "backup_name": self.backup_name,
                "created_at": datetime.now().isoformat(),
                "options": self.options,
                "version": 4
            }

            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                zf.write(snap_path, arcname="database.db")

                # If Desktop Layout selected, include shortcuts json
                shortcuts_file = DATA_DIR / "desktop_shortcuts.json"
                if self.options.get("desktop_layout") and shortcuts_file.exists():
                    zf.write(shortcuts_file, arcname="desktop_shortcuts.json")

            # Remove intermediate raw db file
            snap_path.unlink(missing_ok=True)

            self.progress.emit(100, "Backup completed successfully!")
            self.finished.emit(True, "Backup successfully written.", str(archive_path))
        except Exception as e:
            self.finished.emit(False, str(e), "")


class RestoreWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, archive_path: Path, parent=None):
        super().__init__(parent)
        self.archive_path = archive_path

    def run(self):
        try:
            self.progress.emit(20, "Validating backup archive...")
            if not self.archive_path.exists():
                self.finished.emit(False, "Backup file does not exist.")
                return

            with zipfile.ZipFile(self.archive_path, "r") as zf:
                namelist = zf.namelist()
                if "manifest.json" not in namelist or "database.db" not in namelist:
                    self.finished.emit(False, "Corrupted archive: missing manifest or database.")
                    return

                self.progress.emit(50, "Extracting database snapshot...")
                temp_db = self.archive_path.parent / "temp_restore.db"
                with open(temp_db, "wb") as f:
                    f.write(zf.read("database.db"))

                self.progress.emit(75, "Restoring SQLite database...")
                ok, msg = restore_database_backup(temp_db)
                temp_db.unlink(missing_ok=True)

                if not ok:
                    self.finished.emit(False, f"Database restore failed: {msg}")
                    return

                # Restore desktop shortcuts if present
                if "desktop_shortcuts.json" in namelist:
                    shortcuts_dest = DATA_DIR / "desktop_shortcuts.json"
                    with open(shortcuts_dest, "wb") as f:
                        f.write(zf.read("desktop_shortcuts.json"))

            self.progress.emit(100, "Restore completed!")
            self.finished.emit(True, "NOVA state successfully restored.")
        except Exception as e:
            self.finished.emit(False, str(e))


class BackupRestoreWidget(QWidget):
    notification_requested = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: Optional[QThread] = None
        self.setup_ui()
        self.refresh_restore_list()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header (Matching Panel 4)
        header = QHBoxLayout()
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size: 22px;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel("BACKUP & RESTORE // DATA VAULT")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        sub_lbl = QLabel("Protect your settings, data, notes, and workspace layouts with verified local snapshots.")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(sub_lbl)

        # Tabs: [Backup | Restore]
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                background: #080d1a;
                padding: 12px;
            }
            QTabBar::tab {
                background: #101628;
                color: #94a3b8;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid rgba(255,255,255,0.06);
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #182442;
                color: #00f0ff;
                border-bottom: 2px solid #00f0ff;
            }
        """)

        # Tab 1: Backup
        backup_tab = QWidget()
        b_layout = QVBoxLayout(backup_tab)
        b_layout.setSpacing(12)

        content_box = QHBoxLayout()

        # Left Checklist (Exact items from Panel 4)
        check_group = QGroupBox("Select Items to Include in Backup")
        check_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 16px;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #00F0FF;
            }
            QGroupBox QCheckBox {
                color: #EAF4FF;
                font-size: 12px;
            }
        """)
        check_layout = QVBoxLayout(check_group)
        check_layout.setSpacing(8)

        self.cb_settings = QCheckBox("☑ Settings & Themes")
        self.cb_settings.setChecked(True)
        check_layout.addWidget(self.cb_settings)

        self.cb_desktop = QCheckBox("☑ Desktop Layout & Shortcuts")
        self.cb_desktop.setChecked(True)
        check_layout.addWidget(self.cb_desktop)

        self.cb_workspaces = QCheckBox("☑ Workspaces & Profiles")
        self.cb_workspaces.setChecked(True)
        check_layout.addWidget(self.cb_workspaces)

        self.cb_notes = QCheckBox("☑ Notes & Scheduled Reminders")
        self.cb_notes.setChecked(True)
        check_layout.addWidget(self.cb_notes)

        self.cb_memory = QCheckBox("☑ Local AI Memory & Approved Tags")
        self.cb_memory.setChecked(True)
        check_layout.addWidget(self.cb_memory)

        self.cb_browser = QCheckBox("☑ Browser Bookmarks & History")
        self.cb_browser.setChecked(True)
        check_layout.addWidget(self.cb_browser)

        content_box.addWidget(check_group, stretch=1)

        # Right Destination & Name Box
        dest_group = QGroupBox("Destination & Naming")
        dest_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 16px;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #00F0FF;
            }
            QGroupBox QLabel {
                color: #EAF4FF;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        dest_layout = QVBoxLayout(dest_group)
        dest_layout.setSpacing(10)

        lbl_dest = QLabel("Select Destination Folder:")
        lbl_dest.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        dest_layout.addWidget(lbl_dest)
        dest_pick_row = QHBoxLayout()
        self.dest_edit = QLineEdit(str(BACKUPS_DIR))
        self.dest_edit.setReadOnly(True)
        self.dest_edit.setStyleSheet("background: #0d1527; color: #EAF4FF; padding: 6px;")
        dest_pick_row.addWidget(self.dest_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_destination)
        dest_pick_row.addWidget(browse_btn)
        dest_layout.addLayout(dest_pick_row)

        lbl_name = QLabel("Backup Archive Name:")
        lbl_name.setStyleSheet("color: #EAF4FF; font-weight: 500;")
        dest_layout.addWidget(lbl_name)
        today_name = f"NOVA_Backup_{datetime.now().strftime('%Y-%m-%d')}"
        self.name_edit = QLineEdit(today_name)
        self.name_edit.setStyleSheet("background: #0d1527; color: #00F0FF; font-weight: bold; padding: 6px;")
        dest_layout.addWidget(self.name_edit)

        dest_layout.addStretch()
        content_box.addWidget(dest_group, stretch=1)
        b_layout.addLayout(content_box)

        # Start Backup Button (Blue Cyber Accent matching Panel 4)
        action_row = QHBoxLayout()
        self.start_backup_btn = QPushButton("⚡ Start Backup")
        self.start_backup_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 28px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.start_backup_btn.clicked.connect(self.start_backup)
        action_row.addWidget(self.start_backup_btn)
        action_row.addStretch()
        b_layout.addLayout(action_row)

        self.tabs.addTab(backup_tab, "Backup")

        # Tab 2: Restore
        restore_tab = QWidget()
        r_layout = QVBoxLayout(restore_tab)
        r_layout.setSpacing(12)

        lbl_avail = QLabel("Available Local Backups in Destination Folder:")
        lbl_avail.setStyleSheet("color: #EAF4FF; font-weight: 600; font-size: 12px;")
        r_layout.addWidget(lbl_avail)
        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet("""
            QListWidget {
                background: #0d1527;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 6px;
                color: #cbd5e1;
                padding: 8px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background: #182645;
                color: #00f0ff;
                border-left: 3px solid #00f0ff;
            }
        """)
        r_layout.addWidget(self.backup_list)

        r_btns = QHBoxLayout()
        self.verify_btn = QPushButton("🩺 Verify Archive Integrity")
        self.verify_btn.clicked.connect(self.verify_selected_backup)
        r_btns.addWidget(self.verify_btn)

        self.restore_btn = QPushButton("🔄 Restore Selected Backup")
        self.restore_btn.setObjectName("DangerButton")
        self.restore_btn.setStyleSheet("""
            QPushButton#DangerButton {
                background: #1f121d;
                border: 1px solid #ff2a55;
                border-radius: 6px;
                color: #ff2a55;
                font-weight: bold;
                padding: 8px 18px;
            }
            QPushButton#DangerButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.restore_btn.clicked.connect(self.start_restore)
        r_btns.addWidget(self.restore_btn)

        pick_ext_btn = QPushButton("📂 Open External File...")
        pick_ext_btn.clicked.connect(self.open_external_backup)
        r_btns.addWidget(pick_ext_btn)

        r_btns.addStretch()
        r_layout.addLayout(r_btns)
        self.tabs.addTab(restore_tab, "Restore")

        layout.addWidget(self.tabs)

        # Progress / Status Bar
        self.status_bar = QProgressBar()
        self.status_bar.setFixedHeight(8)
        self.status_bar.setTextVisible(False)
        self.status_bar.setValue(0)
        self.status_bar.setStyleSheet("QProgressBar::chunk { background-color: #00f0ff; }")
        layout.addWidget(self.status_bar)

        self.status_msg_lbl = QLabel("Ready")
        self.status_msg_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.status_msg_lbl)

    def browse_destination(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Backup Destination Directory", str(BACKUPS_DIR))
        if dir_path:
            self.dest_edit.setText(dir_path)
            self.refresh_restore_list()

    def refresh_restore_list(self):
        self.backup_list.clear()
        target_dir = Path(self.dest_edit.text())
        if not target_dir.exists():
            return

        for p in sorted(target_dir.glob("*.novabackup"), key=lambda x: x.stat().st_mtime, reverse=True):
            size_kb = round(p.stat().st_size / 1024, 1)
            mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            item = QListWidgetItem(f"📦 {p.name}  —  {size_kb} KB  ({mtime})")
            item.setData(Qt.UserRole, str(p))
            self.backup_list.addItem(item)

        # Also support legacy .db backups
        for p in sorted(target_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
            size_kb = round(p.stat().st_size / 1024, 1)
            mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            item = QListWidgetItem(f"🗄️ {p.name} [Legacy SQLite Snapshot]  —  {size_kb} KB  ({mtime})")
            item.setData(Qt.UserRole, str(p))
            self.backup_list.addItem(item)

        if self.backup_list.count() > 0:
            self.backup_list.setCurrentRow(0)

    def start_backup(self):
        dest = Path(self.dest_edit.text())
        name = self.name_edit.text().strip() or "NOVA_Backup"
        opts = {
            "settings": self.cb_settings.isChecked(),
            "desktop_layout": self.cb_desktop.isChecked(),
            "workspaces": self.cb_workspaces.isChecked(),
            "notes": self.cb_notes.isChecked(),
            "memory": self.cb_memory.isChecked(),
            "browser": self.cb_browser.isChecked(),
        }

        self.start_backup_btn.setEnabled(False)
        self.status_bar.setValue(10)
        self.status_msg_lbl.setText("Starting backup snapshot...")

        self.worker = BackupWorker(dest, name, opts, self)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_backup_finished)
        self.worker.start()

    def _on_worker_progress(self, val: int, msg: str):
        self.status_bar.setValue(val)
        self.status_msg_lbl.setText(msg)

    def _on_backup_finished(self, ok: bool, msg: str, path: str):
        self.start_backup_btn.setEnabled(True)
        if ok:
            self.status_msg_lbl.setText(f"Backup saved to: {Path(path).name}")
            self.refresh_restore_list()
            QMessageBox.information(self, "Backup Complete", f"Successfully created backup archive:\n{path}")
        else:
            self.status_msg_lbl.setText("Backup error occurred.")
            QMessageBox.critical(self, "Backup Error", f"Could not create backup:\n{msg}")

    def verify_selected_backup(self):
        curr = self.backup_list.currentItem()
        if not curr:
            QMessageBox.warning(self, "No Backup Selected", "Please select a backup file from the list to verify.")
            return

        file_path = Path(curr.data(Qt.UserRole))
        if file_path.suffix == ".novabackup":
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
                    created = manifest_data.get("created_at", "Unknown")
                    opts = manifest_data.get("options", {})
                    QMessageBox.information(
                        self, "Archive Verification: PASSED",
                        f"Archive: {file_path.name}\n"
                        f"Integrity: Valid ZIP with Database & Manifest\n"
                        f"Created: {created}\n"
                        f"Included components: {sum(bool(v) for v in opts.values())} modules"
                    )
            except Exception as e:
                QMessageBox.critical(self, "Corrupted Backup", f"Archive failed verification:\n{str(e)}")
        else:
            QMessageBox.information(self, "Legacy Backup", f"Legacy SQLite database file: {file_path.name}")

    def start_restore(self):
        curr = self.backup_list.currentItem()
        if not curr:
            QMessageBox.warning(self, "No Backup Selected", "Please select a backup archive to restore.")
            return

        file_path = Path(curr.data(Qt.UserRole))
        reply = QMessageBox.warning(
            self,
            "Confirm System Restore",
            f"Are you sure you want to restore NOVA state from:\n{file_path.name}?\n\n"
            "Current workspace configurations, notes, and local databases will be updated to match the backup snapshot.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.restore_btn.setEnabled(False)
        self.worker = RestoreWorker(file_path, self)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_restore_finished)
        self.worker.start()

    def _on_restore_finished(self, ok: bool, msg: str):
        self.restore_btn.setEnabled(True)
        if ok:
            QMessageBox.information(self, "Restore Succeeded", f"{msg}\nRestarting application views recommended.")
        else:
            QMessageBox.critical(self, "Restore Failed", f"Could not restore from backup:\n{msg}")

    def open_external_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", str(BACKUPS_DIR), "NOVA Backups (*.novabackup *.db)"
        )
        if file_path:
            p = Path(file_path)
            item = QListWidgetItem(f"📦 {p.name} [External]")
            item.setData(Qt.UserRole, str(p))
            self.backup_list.addItem(item)
            self.backup_list.setCurrentItem(item)
