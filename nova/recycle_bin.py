"""
Recycle Bin & Safe Trash Subsystem for NOVA OS.
Prevents accidental data loss by quarantining deleted files in a local trash vault,
recording original paths, and supporting 1-click restore to original locations.
"""

import os
import shutil
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from nova.config import DATA_DIR

TRASH_ROOT = DATA_DIR / "recycle_bin"
TRASH_FILES = TRASH_ROOT / "files"
MANIFEST_FILE = TRASH_ROOT / "manifest.json"

class RecycleBin:
    """Manages file deletion quarantine and 1-click restoration."""

    @classmethod
    def _init_storage(cls):
        TRASH_FILES.mkdir(parents=True, exist_ok=True)
        if not MANIFEST_FILE.exists():
            with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        cls._init_storage()
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def _save_manifest(cls, data: List[Dict[str, Any]]):
        cls._init_storage()
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def send_to_trash(cls, file_path: str) -> Optional[str]:
        """Moves a file or directory into the trash vault and logs manifest."""
        src = Path(file_path).resolve()
        if not src.exists():
            return None

        cls._init_storage()
        item_id = f"item_{int(time.time() * 1000)}"
        dest = TRASH_FILES / f"{item_id}_{src.name}"

        try:
            shutil.move(str(src), str(dest))
            size = dest.stat().st_size if dest.is_file() else 0

            manifest = cls.get_manifest()
            manifest.append({
                "id": item_id,
                "name": src.name,
                "original_path": str(src),
                "trash_path": str(dest),
                "size_bytes": size,
                "deleted_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            cls._save_manifest(manifest)
            return item_id
        except Exception:
            return None

    @classmethod
    def restore(cls, item_id: str) -> bool:
        """Restores a trashed item back to its original path."""
        manifest = cls.get_manifest()
        target = None
        for item in manifest:
            if item["id"] == item_id:
                target = item
                break

        if not target:
            return False

        trash_path = Path(target["trash_path"])
        orig_path = Path(target["original_path"])

        if not trash_path.exists():
            manifest.remove(target)
            cls._save_manifest(manifest)
            return False

        try:
            orig_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash_path), str(orig_path))
            manifest.remove(target)
            cls._save_manifest(manifest)
            return True
        except Exception:
            return False

    @classmethod
    def empty_trash(cls) -> int:
        """Permanently purges all trashed files."""
        manifest = cls.get_manifest()
        count = len(manifest)
        cls._init_storage()

        for item in manifest:
            p = Path(item["trash_path"])
            try:
                if p.is_dir():
                    shutil.rmtree(str(p), ignore_errors=True)
                elif p.exists():
                    p.unlink()
            except Exception:
                pass

        cls._save_manifest([])
        return count


class RecycleBinWidget(QWidget):
    """UI for inspecting and restoring trashed files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Toolbar
        bar = QHBoxLayout()
        icon = QLabel("🗑️")
        icon.setStyleSheet("font-size: 20px;")
        bar.addWidget(icon)

        title = QLabel("NOVA RECYCLE BIN")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        bar.addWidget(title)
        bar.addStretch()

        self.restore_btn = QPushButton("↺ Restore Selected")
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.restore_btn.clicked.connect(self.on_restore_selected)
        bar.addWidget(self.restore_btn)

        self.empty_btn = QPushButton("Purge & Empty")
        self.empty_btn.setStyleSheet("""
            QPushButton {
                background: #2b1216;
                border: 1px solid #ff2a55;
                border-radius: 6px;
                color: #ff2a55;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.empty_btn.clicked.connect(self.on_empty_trash)
        bar.addWidget(self.empty_btn)
        layout.addLayout(bar)

        # Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Original Path", "Size", "Deleted At"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1424;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 6px;
                color: #e2e8f0;
                gridline-color: #1a243c;
            }
            QHeaderView::section {
                background-color: #111a30;
                color: #00f0ff;
                font-weight: bold;
                border: 1px solid #1a243c;
                padding: 4px;
            }
        """)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        items = RecycleBin.get_manifest()
        self.table.setRowCount(len(items))
        for r, item in enumerate(items):
            it_name = QTableWidgetItem(f"📄 {item['name']}")
            it_name.setData(Qt.UserRole, item["id"])
            self.table.setItem(r, 0, it_name)

            self.table.setItem(r, 1, QTableWidgetItem(item["original_path"]))

            kb = item.get("size_bytes", 0) / 1024
            self.table.setItem(r, 2, QTableWidgetItem(f"{kb:.1f} KB"))

            self.table.setItem(r, 3, QTableWidgetItem(item.get("deleted_at", "")))

    def on_restore_selected(self):
        curr_row = self.table.currentRow()
        if curr_row < 0:
            return
        item_0 = self.table.item(curr_row, 0)
        if not item_0:
            return
        item_id = item_0.data(Qt.UserRole)
        success = RecycleBin.restore(item_id)
        if success:
            self.refresh_table()

    def on_empty_trash(self):
        count = RecycleBin.empty_trash()
        self.refresh_table()
